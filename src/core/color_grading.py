import cv2
import numpy as np
from pathlib import Path

class ColorGradingEngine:
    def __init__(self):
        # 内部処理は 0.0 ~ 1.0 の np.float32 空間で行うことを前提とする
        pass

    def apply_hsl(self, img_float, hue_shift=0.0, sat_scale=1.0, light_scale=1.0):
        """
        簡易的なHSL調整。
        img_float: shape (H, W, 3) の float32 RGB画像 (0.0~1.0)
        hue_shift: -180.0 ~ 180.0
        sat_scale: 0.0 ~ 2.0 (1.0で変化なし)
        light_scale: 0.0 ~ 2.0 (1.0で変化なし)
        """
        # HLS色空間に変換 (OpenCVのHLS: H=0~360, L=0~1, S=0~1 ※float32の場合)
        hls = cv2.cvtColor(img_float, cv2.COLOR_RGB2HLS)
        
        # Hの調整
        if hue_shift != 0.0:
            hls[:,:,0] = (hls[:,:,0] + hue_shift) % 360.0
            
        # Lの調整
        if light_scale != 1.0:
            hls[:,:,1] = np.clip(hls[:,:,1] * light_scale, 0.0, 1.0)
            
        # Sの調整
        if sat_scale != 1.0:
            hls[:,:,2] = np.clip(hls[:,:,2] * sat_scale, 0.0, 1.0)
            
        # RGBに戻す
        return cv2.cvtColor(hls, cv2.COLOR_HLS2RGB)

    def apply_tone_curve(self, img_float, curve_points_x, curve_points_y):
        """
        スプライン補間等を用いたトーンカーブの適用。
        ここでは簡易的に、1DのLook Up Tableを作成して適用する。
        """
        # LUTのサイズ (例: 1024段)
        lut_size = 1024
        
        # 制御点から1D LUTを生成 (線形補間を使うか、SciPy等のスプラインを使う)
        # ここでは numpy の interp を使用
        x = np.array(curve_points_x, dtype=np.float32)
        y = np.array(curve_points_y, dtype=np.float32)
        
        # 0.0 ~ 1.0 に対応する x_eval
        x_eval = np.linspace(0.0, 1.0, lut_size, dtype=np.float32)
        y_eval = np.interp(x_eval, x, y)
        y_eval = np.clip(y_eval, 0.0, 1.0)
        
        # LUT適用 (インデックス化)
        idx = np.clip(img_float * (lut_size - 1), 0, lut_size - 1).astype(np.int32)
        return y_eval[idx]

    def apply_vignette(self, img_float, strength=0.5):
        """
        周辺減光効果 (ビネット) を適用。
        strength: 0.0 (なし) ~ 1.0 (強い)
        """
        if strength == 0.0:
            return img_float
            
        h, w = img_float.shape[:2]
        
        # 中心座標
        center_x, center_y = w / 2, h / 2
        
        # メッシュグリッドを生成し、中心からの距離を計算
        Y, X = np.ogrid[:h, :w]
        dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        
        # 画像の対角線の半分を最大距離とする
        max_dist = np.sqrt(center_x**2 + center_y**2)
        
        # 距離を0.0~1.0に正規化
        norm_dist = dist / max_dist
        
        # ビネットマスクの計算 (cosine curve などが自然)
        # strengthに応じて外側の暗さを調整
        mask = 1.0 - (norm_dist ** 2) * strength
        mask = np.clip(mask, 0.0, 1.0)
        
        # 3チャンネルに拡張して乗算
        mask_3d = np.expand_dims(mask, axis=-1)
        return img_float * mask_3d

    def apply_clarity(self, img_float, strength=0.0):
        """
        明瞭度 (Clarity) の簡易適用。
        ローカルコントラストを強調するため、大きなカーネルのアンシャープマスクを使用。
        """
        if strength == 0.0:
            return img_float
            
        # HLS色空間に変換してLチャンネルのみ処理する方が自然
        hls = cv2.cvtColor(img_float, cv2.COLOR_RGB2HLS)
        l_channel = hls[:,:,1]
        
        # ぼかし画像を生成
        blurred = cv2.GaussianBlur(l_channel, (0, 0), sigmaX=30)
        
        # ハイパス (エッジ強調用) の計算
        high_pass = l_channel - blurred
        
        # 明瞭度の適用
        l_channel_new = l_channel + high_pass * strength
        hls[:,:,1] = np.clip(l_channel_new, 0.0, 1.0)
        
        return cv2.cvtColor(hls, cv2.COLOR_HLS2RGB)

    def load_lut(self, cube_path):
        """
        .cubeファイルを解析し、colour-scienceを利用して3Dテーブルを読み込む。
        """
        try:
            import colour
            return colour.read_LUT(str(cube_path))
        except ImportError:
            print("colour-science is not installed.")
            return None
        except Exception as e:
            print(f"Failed to load LUT: {e}")
            return None

    def apply_lut(self, img_float, lut_table=None):
        """
        3D LUT (Look Up Table)の適用。
        """
        if lut_table is None:
            return img_float
        
        # colour-science の LUT オブジェクトは apply メソッドを持つ
        # RGB (0.0~1.0) の入力に対して適用可能 (float32->float64へのキャストが内部で行われる場合があるため、float32に戻す)
        result = lut_table.apply(img_float)
        return result.astype(np.float32)

    def apply_basic_tone(self, img_float, exposure=0.0, contrast=1.0, highlights=0.0, shadows=0.0, whites=0.0, blacks=0.0):
        """
        基本トーン（露光量、コントラスト、ハイライト、シャドウ、白レベル、黒レベル）の調整。
        exposure: 露出補正 (EV相当, -3.0 ~ 3.0程度)
        contrast: コントラスト (0.0 ~ 2.0程度, 1.0基準)
        highlights/shadows/whites/blacks: -1.0 ~ 1.0 (0.0基準)
        """
        # --- 1. 露光量 (Exposure) ---
        # 簡易的に 2^ev で乗算
        img = img_float * (2.0 ** exposure)
        
        # --- 2. コントラスト (Contrast) ---
        # 0.5 (グレー) を中心にコントラストカーブを適用
        if contrast != 1.0:
            img = (img - 0.5) * contrast + 0.5
            
        img = np.clip(img, 0.0, 1.0)
        
        # 輝度を計算 (Rec.709)
        luma = 0.2126 * img[:,:,0] + 0.7152 * img[:,:,1] + 0.0722 * img[:,:,2]
        luma_3d = np.expand_dims(luma, axis=-1)
        
        # --- 3. ハイライト/シャドウ/白レベル/黒レベル ---
        # マスクの生成 (ソフトなS字カーブ等を利用)
        shadow_mask = 1.0 - luma_3d
        highlight_mask = luma_3d
        
        # シャドウ/ハイライト補正 (暗部/明部のみを持ち上げ・圧縮)
        # shadows > 0: 暗部を明るく, shadows < 0: 暗部をより暗く
        img = img + (shadow_mask ** 2) * shadows * 0.5
        # highlights > 0: 明部を明るく, highlights < 0: 明部をより暗く(リカバリー)
        img = img + (highlight_mask ** 2) * highlights * 0.5
        
        # 白レベル/黒レベル補正 (極端な領域のオフセット)
        # whites: 全体的なゲインに影響を与えるがハイライト寄りに効く
        img = img + (img ** 3) * whites * 0.2
        # blacks: オフセット (黒浮き/黒沈み)
        img = img + ((1.0 - img) ** 3) * blacks * 0.2
        
        return np.clip(img, 0.0, 1.0)

    def apply_vibrance(self, img_float, vibrance=0.0):
        """
        自然な彩度 (Vibrance): 彩度が低い部分を中心に彩度を上げる処理
        vibrance: -1.0 ~ 1.0
        """
        if vibrance == 0.0:
            return img_float
            
        # HLS色空間
        hls = cv2.cvtColor(img_float, cv2.COLOR_RGB2HLS)
        s_channel = hls[:,:,2]
        
        # 彩度に応じて適用量を変化させる (彩度が低いほど強く掛かる)
        # vibrance > 0 の場合: Sが低いほど大きく増加する
        # vibrance < 0 の場合: 単純に乗算で下げる
        if vibrance > 0:
            mask = 1.0 - s_channel # 彩度が低い領域が 1 になるマスク
            s_channel = s_channel + (mask * s_channel * vibrance)
        else:
            s_channel = s_channel * (1.0 + vibrance)
            
        hls[:,:,2] = np.clip(s_channel, 0.0, 1.0)
        return cv2.cvtColor(hls, cv2.COLOR_HLS2RGB)

    def apply_3way_cc(self, img_float, shadow_hue=0.0, shadow_amt=0.0, mid_hue=0.0, mid_amt=0.0, high_hue=0.0, high_amt=0.0):
        """
        3-Way Color Correction: シャドウ、中間調、ハイライトに対する色被り付加
        hue: 0.0~360.0, amt: 0.0~1.0
        """
        if shadow_amt == 0 and mid_amt == 0 and high_amt == 0:
            return img_float
            
        # 輝度をベースにマスクを作成
        luma = 0.2126 * img_float[:,:,0] + 0.7152 * img_float[:,:,1] + 0.0722 * img_float[:,:,2]
        
        # 各帯域の適当な重み付けマスク (ガウシアンベースや単純なカーブ)
        high_mask = np.clip((luma - 0.5) * 2.0, 0.0, 1.0)
        shadow_mask = np.clip(1.0 - (luma * 2.0), 0.0, 1.0)
        mid_mask = 1.0 - np.maximum(high_mask, shadow_mask)
        
        # 指定色(Hue)からRGB(純色)を作るヘルパー
        def hue_to_rgb(hue):
            # HSVでH=hue, S=1.0, V=1.0となる1ピクセルを作成してRGBに変換
            hsv = np.array([[[hue / 2.0, 255.0, 255.0]]], dtype=np.float32) # opencv Hは0-180
            rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) / 255.0
            return rgb[0,0]
            
        res = img_float.copy()
        
        # ブレンド (加算やスクリーン、ソフトライトなどが考えられるがここでは単純な加算ベースのティント)
        if shadow_amt > 0:
            color = hue_to_rgb(shadow_hue)
            tint = np.ones_like(res) * color
            res = res + tint * shadow_amt * 0.2 * np.expand_dims(shadow_mask, -1)
            
        if mid_amt > 0:
            color = hue_to_rgb(mid_hue)
            tint = np.ones_like(res) * color
            res = res + tint * mid_amt * 0.2 * np.expand_dims(mid_mask, -1)
            
        if high_amt > 0:
            color = hue_to_rgb(high_hue)
            tint = np.ones_like(res) * color
            res = res + tint * high_amt * 0.2 * np.expand_dims(high_mask, -1)
            
        return np.clip(res, 0.0, 1.0)
        
    def apply_grain(self, img_float, amount=0.0, size=1.0):
        """
        フィルム粒子効果。
        amount: ノイズの強さ (0.0~1.0)
        size: 粒の大きさ (ぼかし量)
        """
        if amount == 0.0:
            return img_float
            
        h, w = img_float.shape[:2]
        
        # 縮小サイズの解像度でノイズを生成し、拡大することで「粒」を表現する
        noise_h, noise_w = max(1, int(h / size)), max(1, int(w / size))
        
        # ランダムノイズ生成 (-0.5 ~ 0.5 を中心とする)
        noise = np.random.normal(0, 1.0, (noise_h, noise_w, 3)).astype(np.float32)
        
        # 元サイズに拡大 (バイキュービックで滑らかに)
        noise = cv2.resize(noise, (w, h), interpolation=cv2.INTER_CUBIC)
        
        # ノイズの強さを調整 (輝度50%のオーバーレイ合成相当)
        # img_floatに対してノイズを加減算
        res = img_float + noise * amount * 0.05
        return np.clip(res, 0.0, 1.0)
        
    def apply_crop(self, img_float, ratio_idx=0, offset_x=0.5, offset_y=0.5):
        """
        アスペクト比に基づくクロップ処理。
        ratio_idx: 0=オリジナル, 1=1:1, 2=4:5, 3=16:9, 4=9:16
        offset_x/y: 0.0〜1.0 (0.5で中央)
        """
        if ratio_idx == 0:
            return img_float
            
        h, w = img_float.shape[:2]
        
        # ターゲットのアスペクト比 (幅 / 高さ)
        target_ratio = 1.0
        if ratio_idx == 1:
            target_ratio = 1.0 / 1.0 # 1:1
        elif ratio_idx == 2:
            target_ratio = 4.0 / 5.0 # 4:5
        elif ratio_idx == 3:
            target_ratio = 16.0 / 9.0 # 16:9
        elif ratio_idx == 4:
            target_ratio = 9.0 / 16.0 # 9:16
            
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            # 現在の方が横長 -> 左右をクロップ (高さを基準にする)
            new_h = h
            new_w = int(h * target_ratio)
        else:
            # 現在の方が縦長 -> 上下をクロップ (幅を基準にする)
            new_w = w
            new_h = int(w / target_ratio)
            
        # オフセットに基づく切り出し開始位置
        # offset_x=0 なら左端、1 なら右端
        start_x = int((w - new_w) * offset_x)
        start_y = int((h - new_h) * offset_y)
        
        # 念のため範囲チェック
        start_x = max(0, min(start_x, w - new_w))
        start_y = max(0, min(start_y, h - new_h))
        
        return img_float[start_y:start_y+new_h, start_x:start_x+new_w]

    def process(self, img_float, params: dict):
        """
        パラメータを受け取り、一連のパイプライン処理を実行する。
        """
        res = img_float.copy()
        
        # 1. 基本トーン
        if 'basic_tone' in params:
            bt = params['basic_tone']
            res = self.apply_basic_tone(res, 
                                        exposure=bt.get('exposure', 0.0),
                                        contrast=bt.get('contrast', 1.0),
                                        highlights=bt.get('highlights', 0.0),
                                        shadows=bt.get('shadows', 0.0),
                                        whites=bt.get('whites', 0.0),
                                        blacks=bt.get('blacks', 0.0))
                                        
        # 2. 自然な彩度
        if 'vibrance' in params:
            res = self.apply_vibrance(res, params['vibrance'])
        
        # 3. HSL (全体的な色相・彩度・輝度シフト)
        if 'hsl' in params:
            res = self.apply_hsl(
                res, 
                hue_shift=params['hsl'].get('hue', 0.0),
                sat_scale=params['hsl'].get('sat', 1.0),
                light_scale=params['hsl'].get('light', 1.0)
            )
            
        # 4. 3-Way Color Correction
        if '3way_cc' in params:
            cc = params['3way_cc']
            res = self.apply_3way_cc(res,
                                     shadow_hue=cc.get('shadow_hue', 0.0), shadow_amt=cc.get('shadow_amt', 0.0),
                                     mid_hue=cc.get('mid_hue', 0.0), mid_amt=cc.get('mid_amt', 0.0),
                                     high_hue=cc.get('high_hue', 0.0), high_amt=cc.get('high_amt', 0.0))
            
        if 'tone_curve' in params:
            curve = params['tone_curve']
            res = self.apply_tone_curve(res, curve['x'], curve['y'])
            
        if 'clarity' in params:
            res = self.apply_clarity(res, params['clarity'])
            
        if 'vignette' in params:
            res = self.apply_vignette(res, params['vignette'])
            
        if 'grain' in params:
            res = self.apply_grain(res, amount=params['grain'], size=1.5)
            
        if 'lut' in params and params['lut']:
             # params['lut'] は lut_table などのデータを想定
             res = self.apply_lut(res, params['lut'])
             
        # 最後にクロップ (構図ツール) を適用
        if 'crop' in params:
            crop = params['crop']
            res = self.apply_crop(res, 
                                  ratio_idx=crop.get('ratio_idx', 0),
                                  offset_x=crop.get('offset_x', 0.5),
                                  offset_y=crop.get('offset_y', 0.5))
             
        return res
