"""
ThumbnailStrip: メインウィンドウ下部のサムネイルバー
- 横スクロールで画像サムネイルを表示
- クリックで画像選択
- 右クリックメニューで削除
- 「+」ボタンで画像追加
"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QScrollArea, QLabel,
                               QPushButton, QMenu, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QPixmap, QImage, QMouseEvent, QAction
import numpy as np


class ThumbLabel(QLabel):
    """個別のサムネイルラベル"""
    clicked = Signal(int)
    right_clicked = Signal(int, QPoint)

    def __init__(self, index: int, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.index = index
        self.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setFixedSize(84, 84)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(self._normal_style())
        self.setCursor(Qt.PointingHandCursor)

    def _normal_style(self):
        return "border: 2px solid transparent; background: transparent; padding: 0px;"

    def _selected_style(self):
        return "border: 2px solid #111111; background: transparent; padding: 0px;"

    def set_selected(self, selected: bool):
        self.setStyleSheet(self._selected_style() if selected else self._normal_style())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.index, event.globalPosition().toPoint())
        super().mousePressEvent(event)


class ThumbnailStrip(QWidget):
    """横スクロール可能なサムネイルストリップ"""
    image_selected = Signal(int)       # インデックスが選択された
    image_removed  = Signal(int)       # インデックスが削除された
    add_requested  = Signal()          # 「+」ボタンが押された
    collage_requested = Signal()       # コラージュ作成が要求された

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet("""
            ThumbnailStrip {
                background-color: #E0E0E0;
                border-top: 1px solid #BBBBBB;
            }
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(0)

        # スクロールエリア
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")

        self.container = QWidget()
        self.thumb_layout = QHBoxLayout(self.container)
        self.thumb_layout.setContentsMargins(0, 0, 0, 0)
        self.thumb_layout.setSpacing(6)
        self.thumb_layout.setAlignment(Qt.AlignLeft)
        self.scroll.setWidget(self.container)

        outer.addWidget(self.scroll, 1)

        # 右側ボタン群
        btn_col = QHBoxLayout()
        btn_col.setSpacing(4)

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(56, 56)
        self.btn_add.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.btn_add.setToolTip("画像を追加 (最大10枚)")
        self.btn_add.clicked.connect(self.add_requested.emit)
        btn_col.addWidget(self.btn_add)

        self.btn_collage = QPushButton("▦")
        self.btn_collage.setFixedSize(56, 56)
        self.btn_collage.setStyleSheet("font-size: 20px;")
        self.btn_collage.setToolTip("コラージュ作成")
        self.btn_collage.clicked.connect(self.collage_requested.emit)
        btn_col.addWidget(self.btn_collage)

        outer.addLayout(btn_col)

        self._thumb_labels: list[ThumbLabel] = []
        self._selected_index = -1

    def refresh(self, thumbnails: list[np.ndarray], selected_index: int):
        """サムネイル一覧を再描画する"""
        # 既存のウィジェットをクリア
        for lbl in self._thumb_labels:
            self.thumb_layout.removeWidget(lbl)
            lbl.deleteLater()
        self._thumb_labels.clear()

        self._selected_index = selected_index

        for i, thumb_rgb in enumerate(thumbnails):
            h, w = thumb_rgb.shape[:2]
            qimg = QImage(thumb_rgb.data, w, h, w * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            lbl = ThumbLabel(i, pixmap)
            lbl.set_selected(i == selected_index)
            lbl.clicked.connect(self._on_thumb_clicked)
            lbl.right_clicked.connect(self._on_thumb_right_click)
            self.thumb_layout.addWidget(lbl)
            self._thumb_labels.append(lbl)

    def _on_thumb_clicked(self, index: int):
        self._selected_index = index
        for lbl in self._thumb_labels:
            lbl.set_selected(lbl.index == index)
        self.image_selected.emit(index)

    def _on_thumb_right_click(self, index: int, pos: QPoint):
        menu = QMenu(self)
        remove_action = menu.addAction("この画像を削除")
        action = menu.exec(pos)
        if action == remove_action:
            self.image_removed.emit(index)
