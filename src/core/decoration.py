import cv2
import numpy as np
import exifread
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

import os
import sys

# プロジェクトのルートディレクトリ (main.py の2つ上)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent

FONTS_DIR = _BASE_DIR / "assets" / "fonts"
# ロゴは SIGMA add/sigmalogo/ に格納
LOGOS_DIR = _BASE_DIR.parent / "sigmalogo"

# ロゴ選択肢の定義（実ファイル名に合わせる）
LOGO_OPTIONS = [
    ("なし", None),
    ("SIGMA New Black",  str(LOGOS_DIR / "SIGMA new b.png")),
    ("SIGMA New White",  str(LOGOS_DIR / "SIGMA new w.png")),
    ("SIGMA Old Black",  str(LOGOS_DIR / "SIGMA old b.png")),
    ("SIGMA Old White",  str(LOGOS_DIR / "SIGMA old w.png")),
]

# ロゴサイズ7段階 (画像の短辺に対する比率) — 最小2%
LOGO_SCALES = [0.02, 0.04, 0.06, 0.08, 0.12, 0.16, 0.20]


class DecorationEngine:
    def __init__(self):
        self.font_path = self._find_modern_font()

    # ─────────────────────────────────────────
    # フォント管理
    # ─────────────────────────────────────────

    def _find_modern_font(self):
        """assets/fonts/ を優先し、なければシステムフォントにフォールバック"""
        # まず assets/fonts/ を探す
        custom = self.get_custom_fonts()
        if custom:
            return custom[0][1]  # 最初のカスタムフォントを使用
        # システムフォントを探す
        return self._find_system_font()

    def _find_system_font(self):
        """システムにインストールされているモダンなSans-Serifフォントを探す"""
        candidates = []
        if sys.platform.startswith('win'):
            base_dir = "C:\\Windows\\Fonts"
            candidates = [
                os.path.join(base_dir, "arial.ttf"),
                os.path.join(base_dir, "segoeui.ttf"),
                os.path.join(base_dir, "YuGothM.ttc"),
                os.path.join(base_dir, "calibri.ttf"),
            ]
        elif sys.platform.startswith('darwin'):
            candidates = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return "arial.ttf"

    def get_custom_fonts(self) -> list[tuple[str, str]]:
        """assets/fonts/ 内のフォントファイルを (表示名, パス) のリストで返す"""
        results = []
        if FONTS_DIR.exists():
            for f in sorted(FONTS_DIR.iterdir()):
                if f.suffix.lower() in ('.ttf', '.otf', '.ttc'):
                    results.append((f.stem, str(f)))
        return results

    def get_all_fonts(self) -> list[tuple[str, str]]:
        """カスタムフォント + 代表的なシステムフォントのリスト"""
        fonts = []
        # カスタム優先
        fonts.extend(self.get_custom_fonts())
        # システムフォントの候補
        system_candidates = []
        if sys.platform.startswith('win'):
            base = "C:\\Windows\\Fonts"
            system_candidates = [
                ("Arial",       os.path.join(base, "arial.ttf")),
                ("Arial Bold",  os.path.join(base, "arialbd.ttf")),
                ("Segoe UI",    os.path.join(base, "segoeui.ttf")),
                ("Calibri",     os.path.join(base, "calibri.ttf")),
                ("游ゴシック",  os.path.join(base, "YuGothM.ttc")),
            ]
        for name, path in system_candidates:
            if os.path.exists(path):
                fonts.append((name, path))
        return fonts

    def set_font(self, font_path: str):
        """外部からフォントパスを設定する"""
        if os.path.exists(font_path):
            self.font_path = font_path

    # ─────────────────────────────────────────
    # EXIF 読み込み
    # ─────────────────────────────────────────

    def extract_exif(self, file_path) -> dict:
        """exifread を用いて画像から基本的な撮影情報を抽出する。"""
        exif_data = {}
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

                camera = tags.get('Image Make', '')
                model  = tags.get('Image Model', '')
                exif_data['camera'] = f"{camera} {model}".strip()

                exif_data['lens'] = str(tags.get('EXIF LensModel', 'Unknown Lens'))

                f_number = tags.get('EXIF FNumber', '')
                if f_number and hasattr(f_number.values[0], 'num'):
                    val = f_number.values[0]
                    f_val = val.num / val.den if val.den != 0 else 0
                    exif_data['aperture'] = f"F{f_val:.1f}"

                shutter = tags.get('EXIF ExposureTime', '')
                if shutter:
                    exif_data['shutter_speed'] = f"{shutter}s"

                iso = tags.get('EXIF ISOSpeedRatings', '')
                if iso:
                    exif_data['iso'] = f"ISO{iso}"

        except Exception as e:
            print(f"EXIF read error: {e}")

        return exif_data

    # ─────────────────────────────────────────
    # 位置計算
    # ─────────────────────────────────────────

    def _get_position_coords(self, width, height, obj_w, obj_h, position, margin=40):
        if position == 'bottom_right':
            return width - obj_w - margin, height - obj_h - margin
        elif position == 'bottom_left':
            return margin, height - obj_h - margin
        elif position == 'top_right':
            return width - obj_w - margin, margin
        elif position == 'top_left':
            return margin, margin
        elif position == 'bottom_center':
            return (width - obj_w) // 2, height - obj_h - margin
        elif position == 'top_center':
            return (width - obj_w) // 2, margin
        else:
            return margin, margin

    # ─────────────────────────────────────────
    # EXIF テキスト色プリセット
    EXIF_COLORS = [
        (255, 255, 255, 255),  # 白
        (80,  80,  80,  255),  # ダークグレー
        (180, 180, 180, 255),  # ライトグレー
        (0,   0,   0,   255),  # 黒
    ]

    def create_text_overlay(self, width, height, texts, font_size=40,
                            position='bottom_right', color_idx=0, border_pad=0,
                            opacity=1.0):
        """RGBA テキストオーバーレイを float32 numpy 配列で返す。
        texts: 描画する文字列のリスト (None / 空文字は除外される)
        color_idx: EXIF_COLORS のインデックス
        border_pad: 白枠のパッド幅 (px)。>0 なら白枠領域の中央にテキスト配置
        """
        img_pil = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img_pil)

        try:
            font = ImageFont.truetype(self.font_path, font_size)
        except IOError:
            font = ImageFont.load_default()

        text_str = " | ".join([t for t in texts if t])
        if not text_str:
            return np.zeros((height, width, 4), dtype=np.float32)

        bbox   = draw.textbbox((0, 0), text_str, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if border_pad > 0:
            # 白枠がある場合: パッド領域の中央に配置
            # X方向もパッド幅をマージンにして上下左右の余白を揃える
            inset = border_pad  # 写真端からの距離 = パッド幅

            if 'right' in position:
                x = width - text_w - inset // 2
            elif 'left' in position:
                x = inset // 2
            elif 'center' in position:
                x = (width - text_w) // 2
            else:
                x = inset // 2

            if 'bottom' in position:
                y = height - border_pad + (border_pad - text_h) // 2
            elif 'top' in position:
                y = (border_pad - text_h) // 2
            else:
                y = height - border_pad + (border_pad - text_h) // 2
        else:
            x, y = self._get_position_coords(width, height, text_w, text_h, position)

        base_color = self.EXIF_COLORS[color_idx] if color_idx < len(self.EXIF_COLORS) else (255, 255, 255, 255)
        alpha = int(base_color[3] * max(0.0, min(1.0, opacity)))
        fill = (base_color[0], base_color[1], base_color[2], alpha)
        draw.text((x, y), text_str, font=font, fill=fill)

        overlay_np = np.array(img_pil).astype(np.float32) / 255.0
        return overlay_np

    # ─────────────────────────────────────────
    # ロゴオーバーレイ
    # ─────────────────────────────────────────

    def create_logo_overlay(self, width, height, logo_path, scale=0.1,
                            position='bottom_right', opacity=1.0, border_pad=0):
        """ロゴ（透かし画像）を読み込み、指定サイズで配置した RGBA float32 を返す。
        scale: 短辺に対するスケール比率
        opacity: 透明度 (0.0=完全透明, 1.0=不透明)
        border_pad: 白枠のパッド幅 (px)。>0 なら白枠領域の中央にロゴ配置
        """
        img_pil = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        if not logo_path or not os.path.exists(logo_path):
            return np.zeros((height, width, 4), dtype=np.float32)

        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_w, logo_h = logo.size
            if logo_h == 0:
                return np.zeros((height, width, 4), dtype=np.float32)
            target_h = max(1, int(min(width, height) * scale))
            target_w = max(1, int(logo_w * (target_h / logo_h)))
            logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # 透明度を適用
            if opacity < 1.0:
                r, g, b, a = logo.split()
                a = a.point(lambda x: int(x * opacity))
                logo = Image.merge("RGBA", (r, g, b, a))

            if border_pad > 0:
                # 白枠パッド領域の中央に配置
                if 'right' in position:
                    x = width - target_w - border_pad // 2
                elif 'left' in position:
                    x = border_pad // 2
                elif 'center' in position:
                    x = (width - target_w) // 2
                else:
                    x = border_pad // 2

                if 'bottom' in position:
                    y = height - border_pad + (border_pad - target_h) // 2
                elif 'top' in position:
                    y = (border_pad - target_h) // 2
                else:
                    y = height - border_pad + (border_pad - target_h) // 2
            else:
                x, y = self._get_position_coords(width, height, target_w, target_h, position, margin=40)

            img_pil.paste(logo, (x, y), mask=logo)

        except Exception as e:
            print(f"Failed to load logo: {e}")

        overlay_np = np.array(img_pil).astype(np.float32) / 255.0
        return overlay_np

    # ─────────────────────────────────────────
    # 白枠
    # ─────────────────────────────────────────

    def apply_white_border(self, img_float, padding_ratio=0.05):
        """画像の周囲に白枠を追加する。"""
        if padding_ratio <= 0.0:
            return img_float
        h, w = img_float.shape[:2]
        pad_size = int(min(h, w) * padding_ratio)
        new_h = h + pad_size * 2
        new_w = w + pad_size * 2
        border_img = np.ones((new_h, new_w, 3), dtype=np.float32)
        border_img[pad_size:pad_size+h, pad_size:pad_size+w] = img_float
        return border_img

    # ─────────────────────────────────────────
    # アルファブレンド
    # ─────────────────────────────────────────

    def blend_overlay(self, img_float, overlay_float):
        """RGB (float32) に RGBA オーバーレイ (float32) を合成する。"""
        if overlay_float.shape[2] != 4:
            return img_float
        alpha      = overlay_float[:, :, 3:]
        rgb_overlay = overlay_float[:, :, :3]
        return img_float * (1.0 - alpha) + rgb_overlay * alpha
