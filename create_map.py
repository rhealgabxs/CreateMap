"""
地形生成
"""
import numpy as np
import random
import sys
from PIL import Image, ImageDraw
# perlin.py は下記 noise 1.2.3 を使用
# https://github.com/caseman/noise
import perlin


class CreateMap:
    """ 地図作成クラス """
    # 地図の大きさ
    #size_x = 200
    #size_y = 200
    
    # 高さマップ（2次元numpy）
    map_height = None
    # 湿度マップ（2次元numpy）
    map_wet = None
    
    # 合成回数
    octaves = 4
    # 周波数（開始）
    freq_start = 4
    # 周波数（倍数）
    freq_multiple = 2
    # 合成回数（湿度マップ用）
    octaves_wet = 3
    # 周波数（湿度マップ用）
    freq_wet = 4
    # 合成毎の振幅倍数
    amplitude = 1
    # 合成毎の減衰量
    persistence = 0.5
    
    def __init__(self, width=200, height=200, seed=0):
        """ コンストラクタ """
        # 地形の横の大きさ
        self.size_x = width
        # 地形の縦の大きさ
        self.size_y = height
        # 乱数のシード設定
        random.seed(seed)
    
    def create_map(self):
        """ 地図作成 """
        # 高さマップの生成（Simplex Noise使用）
        snoise = perlin.SimplexNoise(randint_function=random.randint)
        snoise.randomize()
        canvas = np.zeros((self.size_x, self.size_y))
        sum_amp = 0
        amp = self.amplitude
        for octave in range(self.octaves):
            freq = self.freq_start * (self.freq_multiple ** octave)
            canvas_temp = np.array(
                [[snoise.noise2(x / self.size_x * freq, y / self.size_y * freq)
                    for x in range(self.size_x)]
                    for y in range(self.size_y)])
            canvas += canvas_temp * amp
            sum_amp += amp
            amp *= self.persistence
        # マップを -amp 〜 +amp の範囲にする
        self.map_height = canvas / sum_amp
        
        # 湿度マップの生成（Simplex Noise使用）
        snoise_wet = perlin.SimplexNoise(randint_function=random.randint)
        snoise_wet.randomize()
        canvas = np.zeros((self.size_x, self.size_y))
        sum_amp = 0
        amp = self.amplitude
        for octave in range(self.octaves_wet):
            freq = self.freq_start * (self.freq_multiple ** octave)
            canvas_temp = np.array(
                [[snoise_wet.noise2(x / self.size_x * freq, y / self.size_y * freq)
                    for x in range(self.size_x)]
                    for y in range(self.size_y)])
            canvas += canvas_temp * amp
            sum_amp += amp
            amp *= self.persistence
        # マップを -amp 〜 +amp の範囲にする
        self.map_wet = canvas / sum_amp
    
    """ 河川作成用 """
    # 河川マップ（2次元配列、河川有り：1, 無し:0）
    map_river = None
    # 河川になる割合
    river_rate = 50
    # 海岸の高さ
    height_coast = 0.0
    
    def create_river(self):
        """ 河川作成 """
        # 高さピークの取り出し
        peak_pos = []
        for y in range(0, self.size_y - 10):
            for x in range(0, self.size_x - 10):
                peak = np.max(self.map_height[y:y+10, x:x+10])
                if self.map_height[y, x] == peak:
                    pos = (y, x)
                    # 既に追加した位置付近にある場合は追加しないようにする
                    peak_flag = 1
                    for p in peak_pos:
                        pos_y, pos_x = p
                        if (pos_x - 5 < x < pos_x + 5) and (pos_y - 5 < y < pos_y + 5):
                            peak_flag = 0
                            break
                    if peak_flag == 1:
                        peak_pos.append(pos)
        
        # 高さピークから水を流す
        self.map_river = [[0 for x in range(self.size_x)] for y in range(self.size_y)]
        for pos in peak_pos:
            if self.river_rate < random.randrange(100):
                continue
            y, x = pos
            # 低い方向に川を流す
            while True:
                # マップ外、海、川にいきあたったら終了
                h = self.map_height[y, x]
                if (x < 1 or x >= self.size_x - 1
                    or y < 1 or y >= self.size_y - 1
                    or h < self.height_coast
                    or self.map_river[y][x] == 1
                    ):
                    break
                # 川を流す
                self.map_river[y][x] = 1
                # 4方向を調べる
                hl = self.map_height[y, x - 1]
                hr = self.map_height[y, x + 1]
                hu = self.map_height[y - 1, x]
                hd = self.map_height[y + 1, x]
                # 低い方向に進む（確率で違う方向に進ませることもありかも）
                h_low = min(h, hl, hr, hu, hd)
                if h_low == hl:
                    x -= 1
                elif h_low == hr:
                    x += 1
                elif h_low == hu:
                    y -= 1
                elif h_low == hd:
                    y += 1
                else:
                    # 周りの全てが高かったならば湖にして終了
                    for j in [-1, 0, 1]:
                        for i in [-1, 0, 1]:
                            self.map_river[y + j][x + i] = 1
                    break
    
    
    """ 地形出力用 """
    # 海と浅瀬の境界
    height_sea = -0.1
    # 海岸
    #height_coast = 0.0
    # 平原
    height_plain = 0.1
    # 丘陵
    height_hill = 0.3
    # 山岳
    height_mountain = 0.5
    # 高山
    height_alp = 0.7
    
    # 砂漠
    wet_desert = -0.6
    # 荒地
    wet_waste = -0.4
    # 平原
    wet_plain = 0
    # 森林
    wet_forest = 0.3
    # 密林
    ewt_jungle = 0.65
    
    def output_pixel(self, pixel_file='create_map.png'):
        """ 地形の画像出力 """
        if self.map_height is None:
            print('地形がないため作成します')
            self.create_map()
        if self.map_river is None:
            #self.create_river()
            print('河川がないため空を作成します')
            self.map_river = [[0 for x in range(cm.size_x)] for y in range(cm.size_y)]
        
        # 地形の色
        COLOR_NONE = (0, 0, 0)
        COLOR_SEA = (0, 0, 255)
        COLOR_RIVER = (128, 255, 255)
        COLOR_SHALLOW = (0, 255, 255)
        COLOR_PLAIN = (128, 255, 0)
        COLOR_HILL = (255, 165, 0)
        COLOR_MOUNTAIN = (165, 42, 42)
        COLOR_ALP = (255, 255, 255)
        COLOR_DESERT = (255, 255, 0)
        COLOR_WASTELAND = (128, 128, 128)
        COLOR_FOREST = (50, 205, 50)
        COLOR_JUNGLE = (0, 100, 0)
        
        # 地形、湿度、河川の状況により色の点を付ける
        im = Image.new('RGB', (self.size_x, self.size_y), COLOR_NONE)
        draw = ImageDraw.Draw(im)
        for y in range(self.size_y):
            for x in range(self.size_x):
                # if文で上側を優先して色の点を付ける
                if self.map_height[y, x] < self.height_sea:
                    # 海
                    draw.point((y, x), fill=COLOR_SEA)
                elif self.map_height[y, x] < self.height_coast:
                    # 浅瀬
                    draw.point((y, x), fill=COLOR_SHALLOW)
                elif self.map_height[y, x] > self.height_alp:
                    # 高山
                    draw.point((y, x), fill=COLOR_ALP)
                elif self.map_river[y][x] == 1:
                    # 河川
                    draw.point((y, x), fill=COLOR_RIVER)
                elif self.map_height[y, x] > self.height_mountain:
                    # 山岳
                    draw.point((y, x), fill=COLOR_MOUNTAIN)
                elif self.map_wet[y, x] < self.wet_desert:
                    # 砂漠
                    draw.point((y, x), fill=COLOR_DESERT)
                elif self.map_wet[y, x] < self.wet_waste:
                    # 荒地
                    draw.point((y, x), fill=COLOR_WASTELAND)
                elif self.map_wet[y, x] > self.ewt_jungle:
                    # 密林
                    draw.point((y, x), fill=COLOR_JUNGLE)
                elif self.map_wet[y, x] > self.wet_forest:
                    # 森
                    draw.point((y, x), fill=COLOR_FOREST)
                elif self.map_height[y, x] > self.height_hill:
                    # 丘陵
                    draw.point((y, x), fill=COLOR_HILL)
                else:
                    # 平原
                    draw.point((y, x), fill=COLOR_PLAIN)
        # 画像保存
        im.save(pixel_file)


def test():
    """ テスト """
    # テスト1
    # デフォルトのまま生成する場合
    print('テスト1')
    cm1 = CreateMap()
    cm1.create_map()
    print('max =', np.max(cm1.map_height), ', min =', np.min(cm1.map_height))
    cm1.create_river()
    cm1.output_pixel(pixel_file='create_map_test@default.png')
    
    # テスト2
    # 地形の広さとシード値を変更して生成する場合
    print('テスト2')
    cm2 = CreateMap(width=512, height=512, seed=123)
    cm2.create_map()
    print('max =', np.max(cm2.map_height), ', min =', np.min(cm2.map_height))
    cm2.create_river()
    cm2.output_pixel(pixel_file='create_map_test@512x512,seed=123.png')
    
    # テスト3
    # 海岸の高さを変更して陸地を多くする場合
    print('テスト3')
    cm3 = CreateMap(width=512, height=512, seed=123)
    cm3.height_coast = -0.1
    cm3.height_sea = -0.2
    cm3.create_map()
    print('max =', np.max(cm3.map_height), ', min =', np.min(cm3.map_height))
    cm3.create_river()
    cm3.output_pixel(pixel_file='create_map_test@512x512,seed=123,coast=-0.1.png')


if __name__ == "__main__":
    # テスト実行
    test()
    sys.exit(0)

