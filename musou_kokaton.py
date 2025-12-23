import math
import os
import random
import sys
import time
import pygame as pg

# ゲームウィンドウのサイズ設定
WIDTH, HEIGHT = 1100, 650
# カレントディレクトリをスクリプトの場所に固定（画像読み込み失敗防止）
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内にあるか判定し、真理値を返す
    引数：obj_rct (Rect) - 判定するオブジェクトのRect
    戻り値：(横方向, 縦方向) のタプル。画面内ならTrue
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right: yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom: tate = False
    return yoko, tate

def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    ある地点(org)から目標地点(dst)への方向ベクトル（単位ベクトル）を計算する
    引数：org - 出発点Rect, dst - 目標点Rect
    戻り値：(x方向, y方向) の単位ベクトル
    """
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.sqrt(x_diff**2 + y_diff**2)
    return x_diff/norm, y_diff/norm

class Bird(pg.sprite.Sprite):
    """
    プレイヤーキャラクター（こうかとん）を制御するクラス
    移動、HP管理、無敵時間の処理を担当する
    """
    delta = {pg.K_UP: (0, -1), pg.K_DOWN: (0, +1), pg.K_LEFT: (-1, 0), pg.K_RIGHT: (+1, 0)}

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとんを初期化する
        num: 画像番号, xy: 初期座標
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self.imgs = {
            (+1, 0): img, (+1, -1): pg.transform.rotozoom(img, 45, 0.9),
            (0, -1): pg.transform.rotozoom(img, 90, 0.9), (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),
            (-1, 0): img0, (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),
            (0, +1): pg.transform.rotozoom(img, -90, 0.9), (+1, +1): pg.transform.rotozoom(img, -45, 0.9),
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect(center=xy)
        self.speed = 10
        
        # ステータス設定
        self.hp = 100         # 現在のHP
        self.max_hp = 100     # 最大HP
        self.state = "normal" # 状態（normal/hyper）
        self.hyper_life = 0   # 無敵の残り時間（フレーム数）

    def draw_hp_bar(self, screen: pg.Surface):
        """こうかとんの頭上にHPバーを描画する"""
        bar_w, bar_h = 80, 10
        # 背面の赤いバー（減少分）
        pg.draw.rect(screen, (255, 0, 0), [self.rect.centerx - bar_w//2, self.rect.top - 20, bar_w, bar_h])
        # 前面の緑バー（現在値）
        if self.hp > 0:
            pg.draw.rect(screen, (0, 255, 0), [self.rect.centerx - bar_w//2, self.rect.top - 20, int(bar_w * (self.hp/self.max_hp)), bar_h])
        # 白い枠線
        pg.draw.rect(screen, (255, 255, 255), [self.rect.centerx - bar_w//2, self.rect.top - 20, bar_w, bar_h], 1)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        こうかとんの移動と無敵状態の更新を行う
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]; sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        
        # 無敵状態の処理
        if self.state == "hyper":
            self.hyper_life -= 1
            if self.hyper_life % 2 == 0: # 点滅させる
                self.image.set_alpha(128)
            else:
                self.image.set_alpha(255)
            if self.hyper_life < 0:
                self.state = "normal"
                self.image.set_alpha(255)
        
        screen.blit(self.image, self.rect)
        self.draw_hp_bar(screen)

class Bomb(pg.sprite.Sprite):
    """
    敵が発射する爆弾に関するクラス
    """
    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾を生成し、こうかとんの方向へ飛ばす
        """
        super().__init__()
        rad = random.randint(10, 40)
        self.image = pg.Surface((2*rad, 2*rad), pg.SRCALPHA)
        pg.draw.circle(self.image, (random.randint(50, 255), 0, 0), (rad, rad), rad)
        self.rect = self.image.get_rect(center=emy.rect.center)
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.speed = 6
        self.power = 34 # ダメージ量（34 * 3 = 102 なので3発で死ぬ）

    def update(self):
        """爆弾を移動させ、画面外に出たら削除する"""
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True): self.kill()

class Beam(pg.sprite.Sprite):
    """
    こうかとんが放つビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """ビームをこうかとんの向いている方向へ生成する"""
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx, self.vy = math.cos(math.radians(angle)), -math.sin(math.radians(angle))
        self.rect = self.image.get_rect(center=(bird.rect.centerx + bird.rect.width*self.vx, bird.rect.centery + bird.rect.height*self.vy))
        self.speed = 10

    def update(self):
        """ビームを移動させ、画面外に出たら削除する"""
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True): self.kill()

class DamageText(pg.sprite.Sprite):
    """
    ダメージ値を画面上にポップアップ表示するクラス
    """
    def __init__(self, damage: int, center: tuple[int, int], color=(255, 0, 0)):
        super().__init__()
        self.image = pg.font.Font(None, 40).render(str(damage), True, color)
        self.rect = self.image.get_rect(center=center)
        self.life, self.vy = 30, -2 # 30フレーム表示し、上に移動する
    def update(self):
        self.rect.y += self.vy; self.life -= 1
        if self.life < 0: self.kill()

class Enemy(pg.sprite.Sprite):
    """
    敵機（エイリアン）に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect(center=(random.randint(0, WIDTH), 0))
        self.vy, self.bound = 6, random.randint(50, HEIGHT//2) # 停止位置まで降下
        self.interval = random.randint(50, 150) # 攻撃の間隔
        self.hp = 30
    def update(self, screen: pg.Surface):
        """敵機を降下させ、停止位置に到達したらHPバーを表示する"""
        if self.rect.centery < self.bound: self.rect.y += self.vy
        pg.draw.rect(screen, (255, 0, 0), [self.rect.centerx-25, self.rect.top-10, 50, 5])
        pg.draw.rect(screen, (0, 255, 0), [self.rect.centerx-25, self.rect.top-10, int(50*(self.hp/30)), 5])

def main():
    """
    メインループ：ゲームの初期化、描画、衝突判定を制御する
    """
    pg.display.set_caption("真！こうかとん無双：3ライフ版")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    bird = Bird(3, (900, 400))
    bombs, beams, emys, dmgs = pg.sprite.Group(), pg.sprite.Group(), pg.sprite.Group(), pg.sprite.Group()
    tmr, clock = 0, pg.time.Clock()

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT: return
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE: beams.add(Beam(bird))
        
        screen.blit(bg_img, [0, 0])
        
        # 敵の生成
        if tmr % 150 == 0: emys.add(Enemy())
        
        # 敵の攻撃
        for emy in emys:
            if emy.rect.centery >= emy.bound and tmr % emy.interval == 0: 
                bombs.add(Bomb(emy, bird))

        # ビーム vs 敵 の衝突判定
        for emy in pg.sprite.groupcollide(emys, beams, False, True).keys():
            emy.hp -= 10
            dmgs.add(DamageText(10, emy.rect.center, (255, 255, 0)))
            if emy.hp <= 0: emy.kill()

        # 爆弾 vs こうかとん の衝突判定
        if bird.state == "normal": # 無敵時間中でなければ判定
            bomb_hits = pg.sprite.spritecollide(bird, bombs, True)
            if bomb_hits: # 1個以上当たった場合
                bird.hp -= 34 # ダメージを与える（複数が重なっていても1フレームに34のみ）
                bird.state, bird.hyper_life = "hyper", 60 # 60フレーム(1.2秒)の無敵開始
                dmgs.add(DamageText(34, bird.rect.center))
                if bird.hp <= 0: # 死亡判定
                    time.sleep(1); return

        # 各スプライトの更新と描画
        bird.update(pg.key.get_pressed(), screen)
        beams.update(); beams.draw(screen)
        emys.update(screen); emys.draw(screen)
        bombs.update(); bombs.draw(screen)
        dmgs.update(); dmgs.draw(screen)
        
        pg.display.update()
        tmr += 1
        clock.tick(50) # 50 FPSに固定

if __name__ == "__main__":
    pg.init(); main(); pg.quit(); sys.exit()