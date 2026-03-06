"""
CollageDialog: コラージュ作成ダイアログ
- レイアウトパターン選択 (左サイドバー)
- SNS アスペクト比対応
- プレビュー表示 (中央)
- 背景色・余白・トリミング調整・エクスポート設定
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QListWidget, QListWidgetItem,
                               QFileDialog, QSlider, QGroupBox, QWidget, QScrollArea,
                               QSpinBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
import numpy as np
import cv2
import os

from core.collage_engine import CollageEngine, CollageLayout, ALL_LAYOUTS


# SNS アスペクト比プリセット
SNS_ASPECTS = [
    ("Free (Layout default)", None),
    ("Instagram 1:1",         1.0),
    ("Instagram 4:5",         0.8),
    ("Instagram Story 9:16",  0.5625),
    ("Twitter/X 16:9",        16/9),
    ("Facebook Cover 820:312", 820/312),
    ("Pinterest 2:3",         2/3),
    ("YouTube Thumbnail 16:9", 16/9),
    ("A4 Landscape 1.414:1",  1.414),
    ("A4 Portrait 1:1.414",   1/1.414),
]


class CollageDialog(QDialog):
    """コラージュ作成ダイアログ"""

    def __init__(self, images: list[np.ndarray], parent=None):
        """
        images: float32 RGB (0-1) のリスト（コラージュに使用する画像群）
        """
        super().__init__(parent)
        self.setWindowTitle("COLLAGE")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        self._images = images
        self._engine = CollageEngine()
        self._all_layouts = ALL_LAYOUTS
        self._current_layout_idx = 0
        self._result_image = None
        self._crop_offsets = {}  # {slot_idx: (cx, cy)} slot ごとのクロップオフセット

        self._build_ui()
        self._refresh_layout_list()
        self._update_preview()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ── 左サイドバー ──
        left = QVBoxLayout()
        left.setSpacing(8)

        lbl_title = QLabel("LAYOUT")
        lbl_title.setStyleSheet("font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        left.addWidget(lbl_title)

        self.layout_list = QListWidget()
        self.layout_list.setFixedWidth(200)
        self.layout_list.setStyleSheet("font-size: 11px;")
        self.layout_list.currentRowChanged.connect(self._on_layout_changed)
        left.addWidget(self.layout_list, 1)

        # SNS アスペクト比
        aspect_group = QGroupBox("ASPECT RATIO")
        aspect_layout = QVBoxLayout(aspect_group)
        self.cmb_aspect = QComboBox()
        for name, _ in SNS_ASPECTS:
            self.cmb_aspect.addItem(name)
        self.cmb_aspect.currentIndexChanged.connect(self._on_aspect_changed)
        aspect_layout.addWidget(self.cmb_aspect)
        left.addWidget(aspect_group)

        # 背景色
        bg_group = QGroupBox("BACKGROUND")
        bg_layout = QVBoxLayout(bg_group)
        self.cmb_bg = QComboBox()
        self.cmb_bg.addItems(["White", "Light Gray", "Dark Gray", "Black", "Cream"])
        self.cmb_bg.currentIndexChanged.connect(self._update_preview)
        bg_layout.addWidget(self.cmb_bg)
        left.addWidget(bg_group)

        # 出力サイズ
        size_group = QGroupBox("OUTPUT SIZE")
        size_layout = QVBoxLayout(size_group)
        self.cmb_size = QComboBox()
        self.cmb_size.addItems(["4000px", "3000px", "2000px", "5000px", "6000px"])
        size_layout.addWidget(self.cmb_size)
        left.addWidget(size_group)

        main_layout.addLayout(left)

        # ── 中央: プレビュー ──
        center = QVBoxLayout()
        center.setSpacing(8)

        lbl_preview = QLabel("PREVIEW")
        lbl_preview.setStyleSheet("font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        center.addWidget(lbl_preview)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(500, 400)
        self.preview_label.setStyleSheet("background: #E8E8E8; border: 1px solid #CCCCCC;")
        center.addWidget(self.preview_label, 1)

        # ボタン行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_export = QPushButton("EXPORT COLLAGE")
        self.btn_export.setObjectName("btn_export")
        self.btn_export.setMinimumHeight(40)
        self.btn_export.setMinimumWidth(180)
        self.btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(self.btn_export)

        btn_cancel = QPushButton("CANCEL")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        center.addLayout(btn_row)
        main_layout.addLayout(center, 1)

    def _refresh_layout_list(self):
        """画像枚数に合ったレイアウトのみリストに表示する"""
        n = len(self._images)
        self.layout_list.clear()
        self._filtered_layouts = [l for l in self._all_layouts if l.min_images <= n <= l.max_images]
        for layout in self._filtered_layouts:
            item = QListWidgetItem(f"{layout.name}  ({layout.min_images}-{layout.max_images}枚)")
            self.layout_list.addItem(item)
        if self._filtered_layouts:
            self.layout_list.setCurrentRow(0)

    def _on_layout_changed(self, row: int):
        if 0 <= row < len(self._filtered_layouts):
            self._current_layout_idx = row
            self._update_preview()

    def _on_aspect_changed(self):
        self._update_preview()

    def _get_bg_color(self) -> tuple:
        idx = self.cmb_bg.currentIndex()
        colors = [
            (1.0, 1.0, 1.0),     # White
            (0.94, 0.94, 0.94),   # Light Gray
            (0.2, 0.2, 0.2),     # Dark Gray
            (0.0, 0.0, 0.0),     # Black
            (0.96, 0.94, 0.91),  # Cream
        ]
        return colors[idx] if idx < len(colors) else (1.0, 1.0, 1.0)

    def _get_canvas_width(self) -> int:
        idx = self.cmb_size.currentIndex()
        sizes = [4000, 3000, 2000, 5000, 6000]
        return sizes[idx] if idx < len(sizes) else 4000

    def _get_aspect_ratio(self):
        """SNSアスペクト比を取得。Noneならレイアウトデフォルト。"""
        idx = self.cmb_aspect.currentIndex()
        if idx < len(SNS_ASPECTS):
            return SNS_ASPECTS[idx][1]
        return None

    def _update_preview(self):
        if not self._filtered_layouts:
            return

        layout = self._filtered_layouts[self._current_layout_idx]
        bg = self._get_bg_color()
        aspect = self._get_aspect_ratio()

        # SNSアスペクト比が指定されている場合、レイアウトのアスペクト比を上書き
        if aspect is not None:
            effective_aspect = aspect
        else:
            effective_aspect = layout.aspect_ratio

        self._engine.bg_color = bg

        # プレビュー用（軽量）
        preview = self._engine.render(layout, self._images,
                                       canvas_width=800,
                                       bg_color=bg,
                                       aspect_override=effective_aspect)

        # float32 → uint8 → QPixmap
        preview_u8 = np.clip(preview * 255, 0, 255).astype(np.uint8)
        h, w = preview_u8.shape[:2]
        bytes_per_line = w * 3
        qimg = QImage(preview_u8.tobytes(), w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        # ラベルにフィット
        label_size = self.preview_label.size()
        scaled = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)

    def _on_export(self):
        if not self._filtered_layouts:
            return

        layout = self._filtered_layouts[self._current_layout_idx]
        bg = self._get_bg_color()
        canvas_w = self._get_canvas_width()
        aspect = self._get_aspect_ratio()

        effective_aspect = aspect if aspect is not None else layout.aspect_ratio

        # フル解像度でレンダリング
        self._result_image = self._engine.render(layout, self._images,
                                                  canvas_width=canvas_w,
                                                  bg_color=bg,
                                                  aspect_override=effective_aspect)

        # ファイルダイアログ
        path, _ = QFileDialog.getSaveFileName(
            self, "コラージュを保存",
            os.path.expanduser("~/collage_output.jpg"),
            "JPEG (*.jpg);;TIFF (*.tif);;PNG (*.png)"
        )
        if path:
            self._save(path)
            self.accept()

    def _save(self, path: str):
        if self._result_image is None:
            return

        img = self._result_image
        ext = os.path.splitext(path)[1].lower()

        if ext in ['.tif', '.tiff']:
            import tifffile
            img_u16 = np.clip(img * 65535, 0, 65535).astype(np.uint16)
            tifffile.imwrite(path, img_u16)
        else:
            img_u8 = np.clip(img * 255, 0, 255).astype(np.uint8)
            img_bgr = cv2.cvtColor(img_u8, cv2.COLOR_RGB2BGR)
            if ext == '.png':
                cv2.imwrite(path, img_bgr)
            else:
                cv2.imwrite(path, img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])

        print(f"Collage saved: {path}")
