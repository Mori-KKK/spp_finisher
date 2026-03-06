import cv2
import numpy as np
import tifffile
from pathlib import Path

class ImageProcessor:
    def __init__(self):
        self.image_data = None  # 内部表現 (フル解像度)
        self.preview_data = None # 内部表現 (UIスライダー用の軽量版: 長辺2560px)
        self.file_path = None
        
    def load_image(self, file_path: str):
        """
        画像を読み込み、内部のパイプライン用に保持する。
        16-bit TIFFの場合は階調を保持して読み込む。
        """
        path = Path(file_path)
        self.file_path = file_path
        
        try:
            if path.suffix.lower() in ['.tif', '.tiff']:
                # tifffileを使用して16-bitとして読み込む
                img = tifffile.imread(str(path))
                
                # shapeが(H, W, 3)でなく、かつRGBAなどの場合への対応
                if len(img.shape) == 3 and img.shape[2] >= 3:
                    img = img[:, :, :3]
                
                # 内部処理用に float32 (0.0 - 1.0) に正規化することが多い
                if img.dtype == np.uint16:
                    self.image_data = img.astype(np.float32) / 65535.0
                else:
                    self.image_data = img.astype(np.float32) / 255.0
                    
            else:
                # JPEG等の場合 (OpenCVで読み込み)
                img = cv2.imread(str(path), cv2.IMREAD_COLOR)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.image_data = img.astype(np.float32) / 255.0
                else:
                    return False
                    
            # プレビュー用の軽量画像 (長辺最大2560px) を生成
            h, w = self.image_data.shape[:2]
            max_preview_len = 2560
            if max(h, w) > max_preview_len:
                scale = max_preview_len / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                self.preview_data = cv2.resize(self.image_data, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                self.preview_data = self.image_data.copy()
                
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return False
                
        return self.image_data is not None
