import cv2
import numpy as np
from pathlib import Path
import tifffile
from PIL import Image

class ImageExporter:
    def __init__(self):
        pass

    def fit_within(self, img_float, max_w, max_h):
        """
        指定された最大幅(max_w)と最大高さ(max_h)の枠内に収まるように、
        アスペクト比を維持して高品質にリサイズする。
        """
        h, w = img_float.shape[:2]
        
        # 既に枠内に収まっていれば何もしない
        if w <= max_w and h <= max_h:
            return img_float
            
        scale_w = max_w / float(w)
        scale_h = max_h / float(h)
        scale = min(scale_w, scale_h)
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # 縮小時は INTER_AREA を使用するとモアレやジャギーが抑えられる
        resized = cv2.resize(img_float, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized

    def apply_sharpening(self, img_float, strength=1.0):
        """
        アンシャープマスクによるシャープネス処理。
        縮小によって失われた解像感を補うために使用。
        """
        if strength == 0.0:
            return img_float
            
        # ガウシアンブラー
        blurred = cv2.GaussianBlur(img_float, (0, 0), sigmaX=1.0)
        
        # シャープネスの適用: オリジナル + (オリジナル - ぼかし) * strength
        sharpened = img_float + (img_float - blurred) * strength
        return np.clip(sharpened, 0.0, 1.0)

    def export(self, img_float, save_path, format='jpeg', quality=90, preset_idx=0, apply_sharpen=True, sharpen_strength=1.0):
        """
        画像を保存する。
        preset_idx:
          0="オリジナル (リサイズなし)"
          1="X / Twitter 用 (長辺最大 4096px)"
          2="Instagram 通常投稿 用 (枠: 1080x1350)"
          3="Instagram ストーリー 用 (枠: 1080x1920)"
        """
        output_img = img_float.copy()
        
        # プリセットごとのリサイズ
        if preset_idx == 1:
            output_img = self.fit_within(output_img, 4096, 4096)
        elif preset_idx == 2:
            output_img = self.fit_within(output_img, 1080, 1350)
        elif preset_idx == 3:
            output_img = self.fit_within(output_img, 1080, 1920)
            
        # 縮小が適用されたり、明示的に指定された場合のみシャープネス
        if preset_idx > 0 and apply_sharpen and sharpen_strength > 0.0:
            output_img = self.apply_sharpening(output_img, sharpen_strength)
                
        path = Path(save_path)
        
        if format.lower() in ['tif', 'tiff']:
            # 16-bit TIFFとして保存
            output_16bit = np.clip(output_img * 65535, 0, 65535).astype(np.uint16)
            tifffile.imwrite(str(path), output_16bit, photometric='rgb')
        else:
            # 8-bit JPEG / PNG として保存 (sRGBへの変換などが本来は必要だが、ここでは単純に8-bit化)
            # ガンマ変換等を行う場合は、事前に処理されている前提とする
            output_8bit = np.clip(output_img * 255.0, 0, 255).astype(np.uint8)
            output_bgr = cv2.cvtColor(output_8bit, cv2.COLOR_RGB2BGR)
            
            if format.lower() in ['jpg', 'jpeg']:
                cv2.imwrite(str(path), output_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            else:
                cv2.imwrite(str(path), output_bgr)
                
        return True
