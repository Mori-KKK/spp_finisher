"""
CollageEngine: コラージュレイアウトの定義とレンダリング
参照画像から8種類のレイアウトパターンを用意
"""
import cv2
import numpy as np


class LayoutSlot:
    """コラージュ内の1枚分の配置情報 (正規化座標 0.0-1.0)"""
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x   # 左端 (0.0 = 左端)
        self.y = y   # 上端 (0.0 = 上端)
        self.w = w   # 幅
        self.h = h   # 高さ


class CollageLayout:
    """レイアウトパターンの定義"""
    def __init__(self, name: str, description: str, slots: list[LayoutSlot],
                 min_images: int, max_images: int, aspect_ratio: float = 1.0):
        self.name = name
        self.description = description
        self.slots = slots
        self.min_images = min_images
        self.max_images = max_images
        self.aspect_ratio = aspect_ratio   # width / height


# ── レイアウト定義 ────────────────────────────────────────────

def _grid_3x3() -> CollageLayout:
    """均等9分割グリッド (参照画像1: AESENCE)"""
    gap = 0.015   # セル間のギャップ
    cell = (1.0 - gap * 4) / 3.0
    slots = []
    for row in range(3):
        for col in range(3):
            x = gap + col * (cell + gap)
            y = gap + row * (cell + gap)
            slots.append(LayoutSlot(x, y, cell, cell))
    return CollageLayout("Grid 3×3", "均等9分割グリッド", slots, 2, 9, 1.0)


def _vertical_stack_3() -> CollageLayout:
    """縦3段積み (参照画像2)"""
    gap = 0.02
    cell_h = (1.0 - gap * 4) / 3.0
    slots = [
        LayoutSlot(gap, gap,                   1.0 - gap*2, cell_h),
        LayoutSlot(gap, gap*2 + cell_h,        1.0 - gap*2, cell_h),
        LayoutSlot(gap, gap*3 + cell_h*2,      1.0 - gap*2, cell_h),
    ]
    return CollageLayout("Vertical Stack", "縦3段積み", slots, 2, 3, 0.6)


def _magazine_1_1() -> CollageLayout:
    """マガジン風: 大1枚+小1枚 (参照画像3上段)"""
    gap = 0.015
    slots = [
        LayoutSlot(gap, gap, 0.48 - gap, 1.0 - gap*2),       # 左・大
        LayoutSlot(0.50 + gap, gap, 0.48 - gap, 1.0 - gap*2), # 右・大
    ]
    return CollageLayout("Magazine 1+1", "マガジン風 2分割", slots, 2, 2, 1.5)


def _magazine_1_2() -> CollageLayout:
    """マガジン風: 大1枚+小2枚"""
    gap = 0.015
    half_h = (1.0 - gap * 3) / 2.0
    slots = [
        LayoutSlot(gap, gap, 0.55 - gap, 1.0 - gap*2),             # 左・大
        LayoutSlot(0.55 + gap, gap,             0.45 - gap*2, half_h),   # 右上
        LayoutSlot(0.55 + gap, gap*2 + half_h,  0.45 - gap*2, half_h),  # 右下
    ]
    return CollageLayout("Magazine 1+2", "マガジン風 1+2", slots, 3, 3, 1.5)


def _side_by_side() -> CollageLayout:
    """2枚横並び (参照画像4)"""
    gap = 0.02
    slots = [
        LayoutSlot(gap, gap*4, 0.50 - gap*1.5, 1.0 - gap*8),
        LayoutSlot(0.50 + gap*0.5, gap*4, 0.50 - gap*1.5, 1.0 - gap*8),
    ]
    return CollageLayout("Side by Side", "2枚横並び", slots, 2, 2, 0.55)


def _l_shape() -> CollageLayout:
    """L字型配置 (参照画像5)"""
    gap = 0.015
    slots = [
        LayoutSlot(gap, gap, 0.55, 0.65),                  # 左下・大
        LayoutSlot(0.45, gap, 0.55 - gap, 0.45),           # 右上
        LayoutSlot(0.55, 0.50, 0.45 - gap, 0.50 - gap),    # 右下
    ]
    return CollageLayout("L-Shape", "L字型配置", slots, 2, 3, 1.0)


def _diptych() -> CollageLayout:
    """白余白付き縦2枚"""
    gap = 0.04
    img_h = (1.0 - gap * 3) / 2.0
    slots = [
        LayoutSlot(gap * 2, gap, 1.0 - gap * 4, img_h),
        LayoutSlot(gap * 2, gap * 2 + img_h, 1.0 - gap * 4, img_h),
    ]
    return CollageLayout("Diptych", "縦2枚 (白余白)", slots, 2, 2, 0.65)


def _free_grid() -> CollageLayout:
    """横2列自動配置 (最大10枚)"""
    gap = 0.01
    cols = 2
    rows = 5
    cell_w = (1.0 - gap * (cols + 1)) / cols
    cell_h = (1.0 - gap * (rows + 1)) / rows
    slots = []
    for r in range(rows):
        for c in range(cols):
            x = gap + c * (cell_w + gap)
            y = gap + r * (cell_h + gap)
            slots.append(LayoutSlot(x, y, cell_w, cell_h))
    return CollageLayout("Free Grid", "横2×N 自動配置", slots, 2, 10, 0.7)


def _triptych_horizontal() -> CollageLayout:
    """3枚横並び"""
    gap = 0.015
    cell_w = (1.0 - gap * 4) / 3.0
    slots = [
        LayoutSlot(gap,               gap, cell_w, 1.0 - gap*2),
        LayoutSlot(gap*2 + cell_w,    gap, cell_w, 1.0 - gap*2),
        LayoutSlot(gap*3 + cell_w*2,  gap, cell_w, 1.0 - gap*2),
    ]
    return CollageLayout("Triptych", "3枚横並び", slots, 3, 3, 1.5)


# ── 全レイアウト取得 ──────────────────────────────────────

ALL_LAYOUTS = [
    _grid_3x3(),
    _vertical_stack_3(),
    _magazine_1_1(),
    _magazine_1_2(),
    _side_by_side(),
    _l_shape(),
    _diptych(),
    _free_grid(),
    _triptych_horizontal(),
]


class CollageEngine:
    """コラージュをレンダリングするエンジン"""

    def __init__(self):
        self.bg_color = (1.0, 1.0, 1.0)  # 背景色 (白)
        self.gap_ratio = 1.0              # ギャップスケール (1.0 = デフォルト)

    @staticmethod
    def get_layouts() -> list[CollageLayout]:
        return ALL_LAYOUTS

    @staticmethod
    def layouts_for_count(n: int) -> list[CollageLayout]:
        """n 枚の画像に適用可能なレイアウトを返す"""
        return [l for l in ALL_LAYOUTS if l.min_images <= n <= l.max_images]

    def render(self, layout: CollageLayout, images: list[np.ndarray],
               canvas_width: int = 4000, bg_color=None,
               aspect_override=None) -> np.ndarray:
        """
        コラージュをレンダリングする
        images: float32 RGB (0-1) のリスト
        aspect_override: 上書きアスペクト比 (幅/高さ)。Noneならレイアウトデフォルト
        returns: float32 RGB (0-1) キャンバス
        """
        if bg_color is None:
            bg_color = self.bg_color

        aspect = aspect_override if aspect_override is not None else layout.aspect_ratio
        canvas_height = max(1, int(canvas_width / aspect))
        canvas = np.full((canvas_height, canvas_width, 3), bg_color, dtype=np.float32)

        num_slots = min(len(images), len(layout.slots))

        for i in range(num_slots):
            slot = layout.slots[i]
            img = images[i]

            sx = int(slot.x * canvas_width)
            sy = int(slot.y * canvas_height)
            sw = int(slot.w * canvas_width)
            sh = int(slot.h * canvas_height)

            if sw <= 0 or sh <= 0:
                continue

            fitted = self._fit_cover(img, sw, sh)

            ey = min(sy + sh, canvas_height)
            ex = min(sx + sw, canvas_width)
            fh = ey - sy
            fw = ex - sx
            canvas[sy:ey, sx:ex] = fitted[:fh, :fw]

        return canvas

    def _fit_cover(self, img: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        """画像をターゲットサイズにカバーフィット（アスペクト比維持、中央クロップ）"""
        h, w = img.shape[:2]
        scale_w = target_w / w
        scale_h = target_h / h
        scale = max(scale_w, scale_h)

        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 中央クロップ
        y0 = (new_h - target_h) // 2
        x0 = (new_w - target_w) // 2
        return resized[y0:y0+target_h, x0:x0+target_w]

    def render_preview(self, layout: CollageLayout, images: list[np.ndarray],
                       preview_width: int = 800) -> np.ndarray:
        """軽量プレビュー用のレンダリング"""
        return self.render(layout, images, canvas_width=preview_width)
