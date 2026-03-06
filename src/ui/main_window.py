from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QFileDialog)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer, QSettings
import os
import sys
import cv2
import numpy as np

from ui.image_view import ImageViewer
from ui.control_panel import ControlPanel
from ui.thumbnail_strip import ThumbnailStrip
from ui.collage_dialog import CollageDialog
from core.image_manager import ImageManager
from core.color_grading import ColorGradingEngine
from core.decoration import DecorationEngine
from core.exporter import ImageExporter
from core.folder_monitor import FolderMonitor


class MainWindow(QMainWindow):
    def __init__(self, apply_theme_fn=None):
        super().__init__()
        self._apply_theme_fn = apply_theme_fn
        self.setWindowTitle("SPP Finisher")
        self.resize(1280, 800)

        # --- Icon Setting ---
        self._set_app_icon()

        # --- Settings (QSettings を最初に初期化) ---
        self.settings = QSettings("SIGMA_add", "SPP_Finisher")

        # -- Menu Bar --
        self._create_menu_bar()

        # ── メインレイアウト: 上部(プレビュー+コントロール) + 下部(サムネイル) ──
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_vlayout = QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(0, 0, 0, 0)
        main_vlayout.setSpacing(0)

        # 上部: スプリッター (ImageViewer | ControlPanel)
        self.splitter = QSplitter(Qt.Horizontal)

        self.image_viewer = ImageViewer()
        self.splitter.addWidget(self.image_viewer)

        self.control_panel = ControlPanel()
        self.splitter.addWidget(self.control_panel)

        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 4)

        main_vlayout.addWidget(self.splitter, 1)

        # 下部: サムネイルストリップ
        self.thumbnail_strip = ThumbnailStrip()
        main_vlayout.addWidget(self.thumbnail_strip)

        # --- Backend Initialization ---
        self.img_manager = ImageManager()
        self.grader = ColorGradingEngine()
        self.decorator = DecorationEngine()
        self.exporter = ImageExporter()
        self.monitor = FolderMonitor()

        # --- State ---
        self.current_params = {}
        self._loading_files = set()

        # --- Signals Wiring ---
        self.control_panel.folder_select_requested.connect(self._select_folder)
        self.control_panel.grading_changed.connect(self._on_grading_changed)
        self.control_panel.export_requested.connect(self._export_image)
        self.monitor.image_detected.connect(self._on_image_detected)

        # ThumbnailStrip signals
        self.thumbnail_strip.image_selected.connect(self._on_thumb_selected)
        self.thumbnail_strip.image_removed.connect(self._on_thumb_removed)
        self.thumbnail_strip.add_requested.connect(self._open_file_dialog)
        self.thumbnail_strip.collage_requested.connect(self._open_collage)

        # --- Settings (状態の復元) ---
        self._load_settings()

    def _load_settings(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        splitter_state = self.settings.value("splitter_state")
        if splitter_state:
            self.splitter.restoreState(splitter_state)

        last_folder = self.settings.value("last_folder", "")
        if last_folder and os.path.exists(last_folder):
            self.control_panel.lbl_folder.setText(last_folder)
            self.monitor.start_monitoring(last_folder)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter_state", self.splitter.saveState())
        if self.monitor.target_folder:
            self.settings.setValue("last_folder", self.monitor.target_folder)
        super().closeEvent(event)

    # ── Menu Bar ─────────────────────────────────────────────

    def _create_menu_bar(self):
        from PySide6.QtGui import QActionGroup
        menubar = self.menuBar()

        # [ファイル]
        file_menu = menubar.addMenu("ファイル(&F)")

        open_action = file_menu.addAction("画像を開く(&O)...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("終了(&X)")
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)

        # [表示]
        view_menu = menubar.addMenu("表示(&V)")
        theme_menu = view_menu.addMenu("テーマ")

        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        theme_names = [
            ("Light Gray",  "Light Gray  ライトグレー"),
            ("Pure White",  "Pure White  「白」"),
            ("Warm Cream",  "Warm Cream  ウォームクリーム"),
            ("Dark",        "Dark  ダーク"),
            ("Dark Warm",   "Dark Warm  ダークウォーム"),
        ]

        current_theme = self.settings.value("theme_name", "Light Gray")
        self._theme_actions = {}

        for theme_key, label in theme_names:
            action = theme_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(theme_key == current_theme)
            theme_group.addAction(action)
            action.triggered.connect(lambda checked, k=theme_key: self._apply_theme(k))
            self._theme_actions[theme_key] = action

    def _apply_theme(self, theme_name: str):
        if self._apply_theme_fn:
            self._apply_theme_fn(theme_name)
        self.settings.setValue("theme_name", theme_name)
        for key, action in self._theme_actions.items():
            action.setChecked(key == theme_name)

    # ── ファイル操作 ────────────────────────────────────────

    def _open_file_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "画像ファイルを開く", "",
            "画像ファイル (*.tif *.tiff *.jpg *.jpeg *.png)"
        )
        for p in paths:
            if self.img_manager.is_full:
                break
            self.img_manager.load_image(p)

        self._refresh_thumbnail_strip()
        self._update_preview()
        self._update_title()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "監視フォルダーを選択してください")
        if folder:
            self.control_panel.lbl_folder.setText(folder)
            self.monitor.start_monitoring(folder)

    # ── ホットフォルダー: 自動検知 ──────────────────────────

    def _on_image_detected(self, file_path):
        if file_path in self._loading_files:
            return
        print(f"Detected: {os.path.basename(file_path)}")
        self._loading_files.add(file_path)
        QTimer.singleShot(100, lambda: self._try_load_image(file_path, retries=30))

    def _try_load_image(self, file_path, retries):
        if self.img_manager.load_image(file_path):
            self._refresh_thumbnail_strip()
            self._update_preview()
            self._update_title()
            print(f"Loaded: {file_path}")
            self._loading_files.discard(file_path)
        else:
            if retries > 0:
                QTimer.singleShot(1000, lambda: self._try_load_image(file_path, retries - 1))
            else:
                print(f"Failed to load: {file_path}")
                self._loading_files.discard(file_path)

    # ── サムネイルストリップ操作 ────────────────────────────

    def _on_thumb_selected(self, index: int):
        # 現在のパラメータを現スロットに保存
        old_slot = self.img_manager.selected
        if old_slot is not None:
            old_slot.params = self.current_params.copy()

        # 新しいスロットを選択
        self.img_manager.select(index)

        # 選択先のパラメータを復元
        new_slot = self.img_manager.selected
        if new_slot is not None and new_slot.params:
            self.current_params = new_slot.params.copy()
            # UIスライダー・チェックボックスに反映
            self.control_panel.restore_params(self.current_params)

        self._refresh_thumbnail_strip()
        self._update_preview()
        self._update_title()

    def _on_thumb_removed(self, index: int):
        self.img_manager.remove(index)
        self._refresh_thumbnail_strip()
        self._update_preview()
        self._update_title()

    def _refresh_thumbnail_strip(self):
        thumbs = [slot.thumbnail for slot in self.img_manager.slots]
        self.thumbnail_strip.refresh(thumbs, self.img_manager.selected_index)

    def _update_title(self):
        slot = self.img_manager.selected
        if slot:
            name = os.path.basename(slot.path)
            count = self.img_manager.count
            self.setWindowTitle(f"SPP Finisher — {name}  [{count}/10]")
        else:
            self.setWindowTitle("SPP Finisher")

    # ── コラージュ ─────────────────────────────────────────

    def _open_collage(self):
        if self.img_manager.count < 2:
            return  # 2枚以上必要

        # 全画像の preview_data をコラージュに渡す
        images = [slot.preview_data for slot in self.img_manager.slots]
        dlg = CollageDialog(images, parent=self)
        dlg.exec()

    # ── グレーディング → プレビュー ────────────────────────

    def _on_grading_changed(self, params):
        self.current_params = params
        # 現在選択中のスロットにもパラメータを即座に保存
        slot = self.img_manager.selected
        if slot is not None:
            slot.params = params.copy()
        self._update_preview()

    def _apply_decoration(self, graded, dec_params, file_path=None):
        """EXIFテキスト・ロゴの合成処理（preview/export 共用）"""
        pos_list = ['bottom_right', 'bottom_left', 'top_right', 'top_left',
                     'bottom_center', 'top_center']
        h, w = graded.shape[:2]

        font_path = dec_params.get('font_path')
        if font_path:
            self.decorator.set_font(font_path)

        # 白枠
        border_pad = 0
        if dec_params.get('white_border', False):
            pw = dec_params.get('white_border_pw', 5.0) / 100.0
            border_pad = int(min(w, h) * pw)  # 白枠適用前の元画像サイズで計算
            graded = self.decorator.apply_white_border(graded, padding_ratio=pw)
            h, w = graded.shape[:2]

        # EXIF テキスト
        if dec_params.get('exif', False):
            exif_pos_idx = dec_params.get('exif_pos_idx', 0)
            exif_pos_str = pos_list[exif_pos_idx] if exif_pos_idx < len(pos_list) else 'bottom_right'
            exif_color_idx = dec_params.get('exif_color_idx', 0)
            exif_font_size = dec_params.get('exif_size', 30)
            exif_opacity = dec_params.get('exif_opacity', 1.0)

            auto_exif = {}
            if file_path:
                auto_exif = self.decorator.extract_exif(file_path)
            custom_texts = dec_params.get('exif_texts', ['', '', '', '', ''])
            auto_vals = [
                auto_exif.get('camera', ''), auto_exif.get('lens', ''),
                auto_exif.get('aperture', ''), auto_exif.get('shutter_speed', ''),
                auto_exif.get('iso', '')
            ]
            texts = [c if c.strip() else a for c, a in zip(custom_texts, auto_vals)]

            overlay = self.decorator.create_text_overlay(
                w, h, texts, font_size=exif_font_size,
                position=exif_pos_str, color_idx=exif_color_idx,
                border_pad=border_pad, opacity=exif_opacity
            )
            graded = self.decorator.blend_overlay(graded, overlay)

        # ロゴ
        if dec_params.get('logo', False):
            logo_path  = dec_params.get('logo_path')
            logo_scale = dec_params.get('logo_scale', 0.1)
            logo_opacity = dec_params.get('logo_opacity', 1.0)
            logo_pos_idx = dec_params.get('logo_pos_idx', 0)
            logo_pos_str = pos_list[logo_pos_idx] if logo_pos_idx < len(pos_list) else 'bottom_right'
            if logo_path and os.path.exists(logo_path):
                overlay = self.decorator.create_logo_overlay(
                    w, h, logo_path, scale=logo_scale, position=logo_pos_str,
                    opacity=logo_opacity, border_pad=border_pad
                )
                graded = self.decorator.blend_overlay(graded, overlay)

        return graded

    def _update_preview(self):
        slot = self.img_manager.selected
        if slot is None:
            return

        img_float = slot.preview_data
        graded = self.grader.process(img_float, self.current_params)

        dec_params = self.current_params.get('decoration', {})
        graded = self._apply_decoration(graded, dec_params, file_path=slot.path)

        preview_8bit = np.clip(graded * 255.0, 0, 255).astype(np.uint8)
        self.image_viewer.set_image(preview_8bit)

    def _export_image(self):
        slot = self.img_manager.selected
        if slot is None:
            return

        # デフォルトファイル名: 元ファイル名_Fin
        orig_path = slot.path if slot.path else ""
        if orig_path:
            base_dir = os.path.dirname(orig_path)
            base_name = os.path.splitext(os.path.basename(orig_path))[0]
            default_path = os.path.join(base_dir, f"{base_name}_Fin.jpg")
        else:
            default_path = ""

        file_path, _ = QFileDialog.getSaveFileName(
            self, "画像を保存", default_path,
            "JPEG (*.jpg *.jpeg);;TIFF (*.tif *.tiff)"
        )
        if not file_path:
            return

        preset_idx = self.control_panel.cmb_preset.currentIndex()
        apply_sharpen = self.control_panel.chk_sharpen.isChecked()

        img_float = slot.image_data
        graded = self.grader.process(img_float, self.current_params)

        dec_params = self.current_params.get('decoration', {})
        graded = self._apply_decoration(graded, dec_params, file_path=slot.path)

        path_str = str(file_path)
        fmt = 'jpeg' if path_str.lower().endswith(('.jpg', '.jpeg')) else 'tiff'

        self.exporter.export(graded, path_str, format=fmt,
                             preset_idx=preset_idx, apply_sharpen=apply_sharpen)
        self.setWindowTitle(f"SPP Finisher — Export done ({os.path.basename(path_str)})")

    # ── アイコン ───────────────────────────────────────────

    def _set_app_icon(self):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        icon_path = os.path.join(base_path, "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            fallback = os.path.join(base_path, "assets", "logo.png")
            if os.path.exists(fallback):
                self.setWindowIcon(QIcon(fallback))
