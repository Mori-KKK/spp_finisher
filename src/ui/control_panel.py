from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QSlider, QPushButton, QGroupBox,
                               QFileDialog, QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox,
                               QScrollArea, QLineEdit)
from PySide6.QtCore import Qt, Signal
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
try:
    from decoration import DecorationEngine, LOGO_OPTIONS, LOGO_SCALES
except ImportError:
    LOGO_OPTIONS = [("なし", None)]
    LOGO_SCALES  = [0.05, 0.08, 0.12, 0.16, 0.20]

class ControlPanel(QWidget):
    # 値が変更された際のシグナル
    grading_changed = Signal(dict)
    export_requested = Signal()
    folder_select_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # 外側のレイアウト (スクロールエリアを入れるだけ)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # スクロールエリアの設定
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)  # 内側ウィジェットをリサイズに追従
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 横スクロールはなし
        outer_layout.addWidget(scroll)
        
        # スクロール内のコンテナウィジェット
        container = QWidget()
        scroll.setWidget(container)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(4)
        
        # -- HOT FOLDER --
        folder_group = QGroupBox("HOT FOLDER")
        folder_layout = QHBoxLayout(folder_group)
        folder_layout.setContentsMargins(0, 12, 0, 8)
        self.lbl_folder = QLabel("フォルダー未選択")
        self.lbl_folder.setStyleSheet("color: #888888; font-size: 11px;")
        btn_folder = QPushButton("参照")
        btn_folder.setFixedWidth(60)
        btn_folder.clicked.connect(self.folder_select_requested.emit)
        folder_layout.addWidget(self.lbl_folder, 1)
        folder_layout.addWidget(btn_folder)
        layout.addWidget(folder_group)
        
        # -- TONE --
        tone_group = QGroupBox("TONE")
        tone_layout = QVBoxLayout(tone_group)
        tone_layout.setContentsMargins(0, 12, 0, 8)
        tone_layout.setSpacing(6)
        self.slider_exp = self._create_slider(tone_layout, "露光量", -300, 300, 0, scale=100.0)
        self.slider_contrast = self._create_slider(tone_layout, "コントラスト", 0, 200, 100, scale=100.0)
        self.slider_high = self._create_slider(tone_layout, "ハイライト", -100, 100, 0, scale=100.0)
        self.slider_shadow = self._create_slider(tone_layout, "シャドウ", -100, 100, 0, scale=100.0)
        self.slider_white = self._create_slider(tone_layout, "白レベル", -100, 100, 0, scale=100.0)
        self.slider_black = self._create_slider(tone_layout, "黒レベル", -100, 100, 0, scale=100.0)
        layout.addWidget(tone_group)

        # -- COLOR & TEXTURE --
        color_group = QGroupBox("COLOR")
        color_layout = QVBoxLayout(color_group)
        color_layout.setContentsMargins(0, 12, 0, 8)
        color_layout.setSpacing(6)
        
        self.slider_hue = self._create_slider(color_layout, "色相", -180, 180, 0)
        self.slider_sat = self._create_slider(color_layout, "彩度", 0, 200, 100, scale=100.0)
        self.slider_vibrance = self._create_slider(color_layout, "自然な彩度", -100, 100, 0, scale=100.0)
        self.slider_light = self._create_slider(color_layout, "輝度", 0, 200, 100, scale=100.0)
        
        sep2 = QLabel("TEXTURE")
        sep2.setStyleSheet("color: #AAAAAA; font-size: 9px; letter-spacing: 1.5px; padding-top: 8px;")
        color_layout.addWidget(sep2)
        self.slider_grain = self._create_slider(color_layout, "Grain", 0, 100, 0, scale=100.0)
        self.slider_clarity = self._create_slider(color_layout, "Clarity", 0, 100, 0, scale=100.0)
        self.slider_vignette = self._create_slider(color_layout, "Vignette", 0, 100, 0, scale=100.0)
        
        layout.addWidget(color_group)

        # -- Decoration --
        dec_group = QGroupBox("🖌 装飾 (透かし・情報)")
        dec_layout = QVBoxLayout(dec_group)
        
        # ── フォント選択 ──
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("フォント:"))
        self.cmb_font = QComboBox()
        self._font_paths = []
        self._populate_fonts()
        self.cmb_font.currentIndexChanged.connect(self._on_value_changed)
        font_row.addWidget(self.cmb_font)
        dec_layout.addLayout(font_row)
        
        # ── EXIF テキスト ──
        dec_layout.addWidget(QLabel("── EXIFテキスト表示 ──"))
        self.chk_exif = QCheckBox("EXIFテキストを合成")
        self.chk_exif.stateChanged.connect(self._on_value_changed)
        dec_layout.addWidget(self.chk_exif)
        
        exif_labels   = ["カメラ", "レンズ", "絞り値", "シャッター", "ISO"]
        self.exif_lines = []
        for lbl in exif_labels:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{lbl}:"))
            le = QLineEdit()
            le.setPlaceholderText("EXIFから自動取得または手入力")
            le.textChanged.connect(self._on_value_changed)
            row.addWidget(le)
            dec_layout.addLayout(row)
            self.exif_lines.append(le)
        
        exif_pos_row = QHBoxLayout()
        exif_pos_row.addWidget(QLabel("EXIF位置:"))
        self.cmb_exif_position = QComboBox()
        self.cmb_exif_position.addItems(["右下", "左下", "右上", "左上", "下中央", "上中央"])
        self.cmb_exif_position.currentIndexChanged.connect(self._on_value_changed)
        exif_pos_row.addWidget(self.cmb_exif_position)
        dec_layout.addLayout(exif_pos_row)
        
        exif_color_row = QHBoxLayout()
        exif_color_row.addWidget(QLabel("EXIF色:"))
        self.cmb_exif_color = QComboBox()
        self.cmb_exif_color.addItems(["白", "ダークグレー", "ライトグレー", "黒"])
        self.cmb_exif_color.currentIndexChanged.connect(self._on_value_changed)
        exif_color_row.addWidget(self.cmb_exif_color)
        dec_layout.addLayout(exif_color_row)

        self.slider_exif_size = self._create_slider(dec_layout, "EXIFサイズ", 10, 80, 30)
        self.slider_exif_opacity = self._create_slider(dec_layout, "EXIF透明度", 10, 100, 100, scale=100.0)
        
        # ── ロゴ透かし ──
        dec_layout.addWidget(QLabel("── ロゴ透かし ──"))
        self.chk_logo = QCheckBox("ロゴを合成")
        self.chk_logo.stateChanged.connect(self._on_value_changed)
        dec_layout.addWidget(self.chk_logo)
        
        logo_row = QHBoxLayout()
        logo_row.addWidget(QLabel("ロゴ選択:"))
        self.cmb_logo = QComboBox()
        for name, _ in LOGO_OPTIONS:
            self.cmb_logo.addItem(name)
        self.cmb_logo.currentIndexChanged.connect(self._on_value_changed)
        logo_row.addWidget(self.cmb_logo)
        dec_layout.addLayout(logo_row)
        
        logo_size_row = QHBoxLayout()
        logo_size_row.addWidget(QLabel("ロゴサイズ:"))
        self.cmb_logo_size = QComboBox()
        self.cmb_logo_size.addItems(["2%", "4%", "6%", "8%", "12%", "16%", "20%"])
        self.cmb_logo_size.setCurrentIndex(3)
        self.cmb_logo_size.currentIndexChanged.connect(self._on_value_changed)
        logo_size_row.addWidget(self.cmb_logo_size)
        dec_layout.addLayout(logo_size_row)
        
        logo_pos_row = QHBoxLayout()
        logo_pos_row.addWidget(QLabel("ロゴ位置:"))
        self.cmb_logo_position = QComboBox()
        self.cmb_logo_position.addItems(["右下", "左下", "右上", "左上", "下中央", "上中央"])
        self.cmb_logo_position.currentIndexChanged.connect(self._on_value_changed)
        logo_pos_row.addWidget(self.cmb_logo_position)
        dec_layout.addLayout(logo_pos_row)
        
        self.slider_logo_opacity = self._create_slider(dec_layout, "Opacity", 10, 100, 100, scale=100.0)
        
        # ── 白の額縁 ──
        sep_border = QLabel("BORDER")
        sep_border.setStyleSheet("color: #AAAAAA; font-size: 9px; letter-spacing: 1.5px; padding-top: 8px;")
        dec_layout.addWidget(sep_border)
        self.chk_white_border = QCheckBox("白枠を有効化")
        self.chk_white_border.stateChanged.connect(self._on_value_changed)
        dec_layout.addWidget(self.chk_white_border)
        self.slider_white_border_pw = self._create_slider(dec_layout, "幅(%)", 1, 15, 5)
        
        layout.addWidget(dec_group)

        # -- CROP --
        crop_group = QGroupBox("CROP")
        crop_layout = QVBoxLayout(crop_group)
        crop_layout.setContentsMargins(0, 12, 0, 8)
        crop_layout.setSpacing(6)
        
        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(QLabel("比率:"))
        self.cmb_crop = QComboBox()
        self.cmb_crop.addItems([
            "Original",
            "1:1  Square",
            "4:5  Instagram",
            "16:9  Wide",
            "9:16  Story"
        ])
        self.cmb_crop.currentIndexChanged.connect(self._on_value_changed)
        ratio_layout.addWidget(self.cmb_crop)
        crop_layout.addLayout(ratio_layout)
        
        self.slider_crop_x = self._create_slider(crop_layout, "X", 0, 100, 50, scale=100.0)
        self.slider_crop_y = self._create_slider(crop_layout, "Y", 0, 100, 50, scale=100.0)
        
        layout.addWidget(crop_group)

        # -- EXPORT --
        export_group = QGroupBox("EXPORT")
        export_layout = QVBoxLayout(export_group)
        export_layout.setContentsMargins(0, 12, 0, 8)
        export_layout.setSpacing(8)
        
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("出力:"))
        self.cmb_preset = QComboBox()
        self.cmb_preset.addItems([
            "Original",
            "X / Twitter  (4096px)",
            "Instagram  Post",
            "Instagram  Story"
        ])
        preset_layout.addWidget(self.cmb_preset)
        export_layout.addLayout(preset_layout)
        
        self.chk_sharpen = QCheckBox("リサイズ時にシャープネスを適用")
        self.chk_sharpen.setChecked(True)
        export_layout.addWidget(self.chk_sharpen)
        
        self.btn_export = QPushButton("EXPORT IMAGE")
        self.btn_export.setObjectName("btn_export")
        self.btn_export.setMinimumHeight(44)
        self.btn_export.clicked.connect(self.export_requested.emit)
        export_layout.addWidget(self.btn_export)
        
        layout.addWidget(export_group)
        layout.addStretch()

    def _create_slider(self, layout, label_text, vmin, vmax, vdefault, scale=1.0):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setMinimumWidth(100)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(vmin, vmax)
        slider.setValue(vdefault)
        slider.setProperty("scale_factor", scale)
        
        # 表示のみの更新と双方向バインディング
        if scale != 1.0:
            spin_box = QDoubleSpinBox()
            spin_box.setRange(vmin / scale, vmax / scale)
            spin_box.setDecimals(2)
            spin_box.setSingleStep(1.0 / scale if scale >= 10.0 else 0.1)
            spin_box.setValue(vdefault / scale)
            
            # Slider -> SpinBox
            slider.valueChanged.connect(lambda v, sb=spin_box, s=scale: sb.setValue(v / s))
            # SpinBox -> Slider
            spin_box.valueChanged.connect(lambda v, sl=slider, s=scale: self._safe_set_slider_value(sl, int(v * s)))
        else:
            spin_box = QSpinBox()
            spin_box.setRange(vmin, vmax)
            spin_box.setValue(vdefault)
            
            slider.valueChanged.connect(spin_box.setValue)
            spin_box.valueChanged.connect(slider.setValue)

        spin_box.setMinimumWidth(60)
        slider.valueChanged.connect(self._on_value_changed)
        
        row.addWidget(lbl)
        row.addWidget(slider)
        row.addWidget(spin_box)
        layout.addLayout(row)
        return slider
        
    def _create_color_slider(self, layout, label_text, vmin, vmax, vdefault):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setMinimumWidth(100)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(vmin, vmax)
        slider.setValue(vdefault)
        slider.setProperty("scale_factor", 1.0)
        
        spin_box = QSpinBox()
        spin_box.setRange(vmin, vmax)
        spin_box.setValue(vdefault)
        spin_box.setMinimumWidth(60)
        
        slider.valueChanged.connect(spin_box.setValue)
        spin_box.valueChanged.connect(slider.setValue)
        
        # Color Chip (色表示用ラベル)
        color_lbl = QLabel()
        color_lbl.setFixedSize(20, 20)
        color_lbl.setStyleSheet("background-color: hsv(0, 255, 255); border: 1px solid gray;")
        
        # 色相スライダー変更時に色チップを更新するラムダ式を追加
        slider.valueChanged.connect(lambda v, l=color_lbl: l.setStyleSheet(f"background-color: hsv({v}, 255, 255); border: 1px solid gray;"))
        slider.valueChanged.connect(self._on_value_changed)

        row.addWidget(lbl)
        row.addWidget(slider)
        row.addWidget(spin_box)
        row.addWidget(color_lbl)
        layout.addLayout(row)
        return slider, color_lbl

    def _safe_set_slider_value(self, slider, val):
        if slider.value() != val:
            slider.setValue(val)

    def _get_scaled_value(self, slider):
        scale = slider.property("scale_factor")
        return slider.value() / scale

    def _populate_fonts(self):
        """decoration.DecorationEngineからフォント一覧を取得しComboBoxに登録"""
        try:
            eng = DecorationEngine()
            fonts = eng.get_all_fonts()
        except Exception:
            fonts = []
        self.cmb_font.clear()
        self._font_paths = []
        for name, path in fonts:
            self.cmb_font.addItem(name)
            self._font_paths.append(path)
        if not fonts:
            self.cmb_font.addItem("デフォルト")
            self._font_paths.append(None)
        
    def _create_slider(self, layout, label_text, vmin, vmax, vdefault, scale=1.0):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setMinimumWidth(100)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(vmin, vmax)
        slider.setValue(vdefault)
        slider.setProperty("scale_factor", scale)
        
        if scale != 1.0:
            spin_box = QDoubleSpinBox()
            spin_box.setRange(vmin / scale, vmax / scale)
            spin_box.setDecimals(2)
            spin_box.setSingleStep(1.0 / scale if scale >= 10.0 else 0.1)
            spin_box.setValue(vdefault / scale)
            slider.valueChanged.connect(lambda v, sb=spin_box, s=scale: sb.setValue(v / s))
            spin_box.valueChanged.connect(lambda v, sl=slider, s=scale: self._safe_set_slider_value(sl, int(v * s)))
        else:
            spin_box = QSpinBox()
            spin_box.setRange(vmin, vmax)
            spin_box.setValue(vdefault)
            slider.valueChanged.connect(spin_box.setValue)
            spin_box.valueChanged.connect(slider.setValue)

        spin_box.setMinimumWidth(60)
        slider.valueChanged.connect(self._on_value_changed)
        
        row.addWidget(lbl)
        row.addWidget(slider)
        row.addWidget(spin_box)
        layout.addLayout(row)
        return slider
        
    def _create_color_slider(self, layout, label_text, vmin, vmax, vdefault):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setMinimumWidth(100)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(vmin, vmax)
        slider.setValue(vdefault)
        slider.setProperty("scale_factor", 1.0)
        
        spin_box = QSpinBox()
        spin_box.setRange(vmin, vmax)
        spin_box.setValue(vdefault)
        spin_box.setMinimumWidth(60)
        
        slider.valueChanged.connect(spin_box.setValue)
        spin_box.valueChanged.connect(slider.setValue)
        
        color_lbl = QLabel()
        color_lbl.setFixedSize(20, 20)
        color_lbl.setStyleSheet("background-color: hsv(0, 255, 255); border: 1px solid gray;")
        slider.valueChanged.connect(lambda v, l=color_lbl: l.setStyleSheet(f"background-color: hsv({v}, 255, 255); border: 1px solid gray;"))
        slider.valueChanged.connect(self._on_value_changed)

        row.addWidget(lbl)
        row.addWidget(slider)
        row.addWidget(spin_box)
        row.addWidget(color_lbl)
        layout.addLayout(row)
        return slider, color_lbl

    def _safe_set_slider_value(self, slider, val):
        if slider.value() != val:
            slider.setValue(val)

    def _get_scaled_value(self, slider):
        scale = slider.property("scale_factor")
        return slider.value() / scale

    def _on_value_changed(self):
        pos_list = ['bottom_right', 'bottom_left', 'top_right', 'top_left', 'bottom_center', 'top_center']
        
        # EXIF各行の手入力テキストを収集
        exif_custom_texts = [le.text() for le in self.exif_lines]
        
        # フォントパス
        font_idx = self.cmb_font.currentIndex()
        font_path = self._font_paths[font_idx] if font_idx < len(self._font_paths) else None
        
        # ロゴ 選択情報
        logo_idx  = self.cmb_logo.currentIndex()
        logo_path = LOGO_OPTIONS[logo_idx][1] if logo_idx < len(LOGO_OPTIONS) else None
        logo_scale = LOGO_SCALES[self.cmb_logo_size.currentIndex()] if LOGO_SCALES else 0.1
        
        params = {
            'basic_tone': {
                'exposure':    self._get_scaled_value(self.slider_exp),
                'contrast':    self._get_scaled_value(self.slider_contrast),
                'highlights':  self._get_scaled_value(self.slider_high),
                'shadows':     self._get_scaled_value(self.slider_shadow),
                'whites':      self._get_scaled_value(self.slider_white),
                'blacks':      self._get_scaled_value(self.slider_black)
            },
            'vibrance': self._get_scaled_value(self.slider_vibrance),
            'hsl': {
                'hue':   self._get_scaled_value(self.slider_hue),
                'sat':   self._get_scaled_value(self.slider_sat),
                'light': self._get_scaled_value(self.slider_light),
            },
            'clarity':  self._get_scaled_value(self.slider_clarity),
            'vignette': self._get_scaled_value(self.slider_vignette),
            'grain':    self._get_scaled_value(self.slider_grain),
            'decoration': {
                'exif':           self.chk_exif.isChecked(),
                'exif_texts':     exif_custom_texts,
                'exif_pos_idx':   self.cmb_exif_position.currentIndex(),
                'exif_color_idx': self.cmb_exif_color.currentIndex(),
                'exif_size':      int(self.slider_exif_size.value()),
                'exif_opacity':   self._get_scaled_value(self.slider_exif_opacity),
                'logo':           self.chk_logo.isChecked(),
                'logo_path':      logo_path,
                'logo_scale':     logo_scale,
                'logo_pos_idx':   self.cmb_logo_position.currentIndex(),
                'logo_opacity':   self._get_scaled_value(self.slider_logo_opacity),
                'font_path':      font_path,
                'white_border':   self.chk_white_border.isChecked(),
                'white_border_pw': self._get_scaled_value(self.slider_white_border_pw)
            },
            'crop': {
                'ratio_idx': self.cmb_crop.currentIndex(),
                'offset_x':  self._get_scaled_value(self.slider_crop_x),
                'offset_y':  self._get_scaled_value(self.slider_crop_y)
            }
        }
        self.grading_changed.emit(params)

    def _set_slider_raw(self, slider, raw_value):
        """scale_factorを考慮してスライダーに値を復元する"""
        scale = slider.property("scale_factor")
        if scale and scale != 0:
            slider.setValue(int(raw_value * scale))
        else:
            slider.setValue(int(raw_value))

    def restore_params(self, params: dict):
        """パラメータ dict を受け取り、全スライダー・チェックボックス・ComboBox の状態を復元する。
        復元中はシグナルをブロックする。
        """
        if not params:
            return

        self.blockSignals(True)
        try:
            bt = params.get('basic_tone', {})
            self._set_slider_raw(self.slider_exp, bt.get('exposure', 0))
            self._set_slider_raw(self.slider_contrast, bt.get('contrast', 1.0))
            self._set_slider_raw(self.slider_high, bt.get('highlights', 0))
            self._set_slider_raw(self.slider_shadow, bt.get('shadows', 0))
            self._set_slider_raw(self.slider_white, bt.get('whites', 0))
            self._set_slider_raw(self.slider_black, bt.get('blacks', 0))

            self._set_slider_raw(self.slider_vibrance, params.get('vibrance', 0))

            hsl = params.get('hsl', {})
            self._set_slider_raw(self.slider_hue, hsl.get('hue', 0))
            self._set_slider_raw(self.slider_sat, hsl.get('sat', 1.0))
            self._set_slider_raw(self.slider_light, hsl.get('light', 1.0))



            self._set_slider_raw(self.slider_clarity, params.get('clarity', 0))
            self._set_slider_raw(self.slider_vignette, params.get('vignette', 0))
            self._set_slider_raw(self.slider_grain, params.get('grain', 0))

            dec = params.get('decoration', {})
            self.chk_exif.setChecked(dec.get('exif', False))
            self.cmb_exif_position.setCurrentIndex(dec.get('exif_pos_idx', 0))
            self.cmb_exif_color.setCurrentIndex(dec.get('exif_color_idx', 0))
            self.slider_exif_size.setValue(dec.get('exif_size', 30))
            self._set_slider_raw(self.slider_exif_opacity, dec.get('exif_opacity', 1.0))
            exif_texts = dec.get('exif_texts', [''] * 5)
            for i, le in enumerate(self.exif_lines):
                le.setText(exif_texts[i] if i < len(exif_texts) else '')

            self.chk_logo.setChecked(dec.get('logo', False))
            self.cmb_logo_position.setCurrentIndex(dec.get('logo_pos_idx', 0))
            self._set_slider_raw(self.slider_logo_opacity, dec.get('logo_opacity', 1.0))

            self.chk_white_border.setChecked(dec.get('white_border', False))
            self._set_slider_raw(self.slider_white_border_pw, dec.get('white_border_pw', 5.0))

            crop = params.get('crop', {})
            self.cmb_crop.setCurrentIndex(crop.get('ratio_idx', 0))
            self._set_slider_raw(self.slider_crop_x, crop.get('offset_x', 0.5))
            self._set_slider_raw(self.slider_crop_y, crop.get('offset_y', 0.5))
        finally:
            self.blockSignals(False)
