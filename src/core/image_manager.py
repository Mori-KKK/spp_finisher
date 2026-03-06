"""
ImageManager: 最大10枚の画像を管理するクラス
各画像は full-resolution / preview / thumbnail の3解像度を保持する
"""
import cv2
import numpy as np
import tifffile
from pathlib import Path

MAX_IMAGES = 10
PREVIEW_MAX = 2560   # プレビュー長辺
THUMB_SIZE  = 128    # サムネイル正方形サイズ


class ImageSlot:
    """1枚の画像を表すデータスロット"""
    __slots__ = ('path', 'image_data', 'preview_data', 'thumbnail', 'params')

    def __init__(self, path: str, image_data, preview_data, thumbnail):
        self.path = path
        self.image_data = image_data      # float32 (H,W,3) full-res
        self.preview_data = preview_data  # float32 (H,W,3) ≤ 2560px
        self.thumbnail = thumbnail        # uint8 (128,128,3) for UI
        self.params = {}                  # 画像ごとの編集パラメータ


class ImageManager:
    """最大10枚の画像を管理し、選択状態を追跡する"""

    def __init__(self):
        self.slots: list[ImageSlot] = []
        self.selected_index: int = -1   # 選択中のスロットインデックス

    @property
    def count(self) -> int:
        return len(self.slots)

    @property
    def is_full(self) -> bool:
        return self.count >= MAX_IMAGES

    @property
    def selected(self) -> ImageSlot | None:
        if 0 <= self.selected_index < self.count:
            return self.slots[self.selected_index]
        return None

    # ── 読み込み ──────────────────────────────────────────

    def load_image(self, file_path: str) -> bool:
        """画像を読み込みスロットに追加する (最大10枚制限)"""
        if self.is_full:
            print(f"Image limit reached ({MAX_IMAGES})")
            return False

        image_data = self._read_file(file_path)
        if image_data is None:
            return False

        preview_data = self._make_preview(image_data)
        thumbnail    = self._make_thumbnail(image_data)

        slot = ImageSlot(file_path, image_data, preview_data, thumbnail)
        self.slots.append(slot)

        # 追加した画像を自動選択
        self.selected_index = len(self.slots) - 1
        return True

    def _read_file(self, file_path: str):
        """ファイルを読み込み float32 RGB (0-1) に変換する"""
        path = Path(file_path)
        try:
            if path.suffix.lower() in ['.tif', '.tiff']:
                img = tifffile.imread(str(path))
                if len(img.shape) == 3 and img.shape[2] >= 3:
                    img = img[:, :, :3]
                if img.dtype == np.uint16:
                    return img.astype(np.float32) / 65535.0
                else:
                    return img.astype(np.float32) / 255.0
            else:
                img = cv2.imread(str(path), cv2.IMREAD_COLOR)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    return img.astype(np.float32) / 255.0
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        return None

    def _make_preview(self, image_data) -> np.ndarray:
        """長辺を PREVIEW_MAX px にリサイズしたプレビュー画像を生成"""
        h, w = image_data.shape[:2]
        if max(h, w) > PREVIEW_MAX:
            scale = PREVIEW_MAX / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            return cv2.resize(image_data, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return image_data.copy()

    def _make_thumbnail(self, image_data) -> np.ndarray:
        """正方形にクロップ → THUMB_SIZE にリサイズした uint8 サムネイルを生成"""
        h, w = image_data.shape[:2]
        # center crop to square
        side = min(h, w)
        y0, x0 = (h - side) // 2, (w - side) // 2
        cropped = image_data[y0:y0+side, x0:x0+side]
        thumb = cv2.resize(cropped, (THUMB_SIZE, THUMB_SIZE), interpolation=cv2.INTER_AREA)
        return np.clip(thumb * 255, 0, 255).astype(np.uint8)

    # ── 管理操作 ──────────────────────────────────────────

    def remove(self, index: int):
        """指定インデックスの画像を削除する"""
        if 0 <= index < self.count:
            self.slots.pop(index)
            # 選択インデックスを調整
            if self.count == 0:
                self.selected_index = -1
            elif self.selected_index >= self.count:
                self.selected_index = self.count - 1

    def select(self, index: int):
        """指定インデックスを選択する"""
        if 0 <= index < self.count:
            self.selected_index = index

    def reorder(self, from_idx: int, to_idx: int):
        """画像の並び順を変更する（ドラッグ＆ドロップ用）"""
        if 0 <= from_idx < self.count and 0 <= to_idx < self.count:
            slot = self.slots.pop(from_idx)
            self.slots.insert(to_idx, slot)
            # 選択状態を追跡
            if self.selected_index == from_idx:
                self.selected_index = to_idx

    def clear(self):
        """全画像をクリアする"""
        self.slots.clear()
        self.selected_index = -1

    def get_selected_slots(self, indices: list[int]) -> list[ImageSlot]:
        """複数インデックスに対応するスロットを返す（コラージュ用）"""
        return [self.slots[i] for i in indices if 0 <= i < self.count]
