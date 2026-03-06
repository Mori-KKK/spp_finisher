import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

# ─── テーマ定義（背景色 → 各要素の色をセット） ───────────────────────
def _build_theme_qss(bg, bg2, border, text, text_sub, accent, accent_text):
    """テーマカラーからQSSを動的生成する"""
    return f"""
/* === SPP Finisher - Dynamic Theme === */

QMainWindow, QWidget {{
    background-color: {bg};
    color: {text};
    font-family: "Segoe UI", "Yu Gothic UI", "Arial", sans-serif;
    font-size: 12px;
}}
QMenuBar {{
    background-color: {bg};
    color: {text};
    border-bottom: 1px solid {border};
    padding: 2px 8px;
    spacing: 4px;
}}
QMenuBar::item {{ background: transparent; padding: 4px 10px; border-radius: 2px; }}
QMenuBar::item:selected {{ background-color: {accent}; color: {accent_text}; }}
QMenu {{
    background-color: {bg};
    border: 1px solid {border};
    padding: 4px 0;
}}
QMenu::item {{ padding: 6px 24px; color: {text}; }}
QMenu::item:selected {{ background-color: {accent}; color: {accent_text}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 0; }}
QMenu::item:checked {{ font-weight: bold; }}
QSplitter::handle {{ background-color: {border}; width: 1px; }}
QScrollArea {{ border: none; background-color: {bg}; }}
QScrollBar:vertical {{ background: {bg2}; width: 6px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {text_sub}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QGroupBox {{
    border: none;
    border-top: 1px solid {accent};
    margin-top: 12px;
    padding-top: 14px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1.5px;
    color: {accent};
    background-color: {bg};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    left: 0px;
    top: -1px;
    color: {accent};
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1.5px;
    background-color: {bg};
}}
QLabel {{ color: {text}; background: transparent; }}
QSlider::groove:horizontal {{ height: 1px; background: {border}; border-radius: 1px; }}
QSlider::handle:horizontal {{
    background: {accent};
    width: 10px; height: 10px;
    border-radius: 5px;
    margin: -5px 0;
}}
QSlider::handle:horizontal:hover {{ background: {text_sub}; }}
QSlider::sub-page:horizontal {{ background: {accent}; height: 1px; border-radius: 1px; }}
QSpinBox, QDoubleSpinBox {{
    border: none;
    border-bottom: 1px solid {border};
    background: transparent;
    color: {text};
    padding: 2px 4px;
    font-size: 11px;
    min-width: 52px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-bottom: 1px solid {accent}; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; height: 0; border: none; }}
QLineEdit {{
    border: none;
    border-bottom: 1px solid {border};
    background: transparent;
    color: {text};
    padding: 3px 4px;
    font-size: 11px;
}}
QLineEdit:focus {{ border-bottom: 1px solid {accent}; }}
QComboBox {{
    border: none;
    border-bottom: 1px solid {border};
    background: transparent;
    color: {text};
    padding: 3px 8px 3px 4px;
    font-size: 11px;
    min-width: 80px;
}}
QComboBox:focus {{ border-bottom: 1px solid {accent}; }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text_sub};
    width: 0; height: 0;
}}
QComboBox QAbstractItemView {{
    background: {bg};
    border: 1px solid {border};
    selection-background-color: {accent};
    selection-color: {accent_text};
    outline: none;
}}
QCheckBox {{ color: {text}; spacing: 8px; font-size: 11px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {text_sub};
    border-radius: 2px;
    background: {bg};
}}
QCheckBox::indicator:checked {{ background: {accent}; border: 1px solid {accent}; }}
QCheckBox::indicator:checked:hover {{ background: {text_sub}; }}
QPushButton {{
    background: transparent;
    border: 1px solid {accent};
    color: {text};
    padding: 7px 16px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.8px;
    border-radius: 0px;
}}
QPushButton:hover {{ background: {accent}; color: {accent_text}; }}
QPushButton:pressed {{ background: {text_sub}; color: {accent_text}; }}
QPushButton#btn_export {{
    background: {accent};
    border: 1px solid {accent};
    color: {accent_text};
    padding: 10px 16px;
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 1.5px;
}}
QPushButton#btn_export:hover {{ background: {text_sub}; }}
"""

# ─── テーマプリセット ───────────────────────────────────────────────────
THEMES = {
    "Light Gray":  dict(bg="#F0F0F0", bg2="#E8E8E8", border="#CCCCCC", text="#111111", text_sub="#555555", accent="#111111", accent_text="#FFFFFF"),
    "Pure White":  dict(bg="#FFFFFF", bg2="#F5F5F5", border="#E0E0E0", text="#111111", text_sub="#555555", accent="#111111", accent_text="#FFFFFF"),
    "Warm Cream":  dict(bg="#F5F0E8", bg2="#EDE8E0", border="#C8C0B0", text="#2A2018", text_sub="#6A5840", accent="#2A2018", accent_text="#F5F0E8"),
    "Dark":        dict(bg="#1A1A1A", bg2="#242424", border="#3A3A3A", text="#E0E0E0", text_sub="#999999", accent="#E0E0E0", accent_text="#1A1A1A"),
    "Dark Warm":   dict(bg="#1E1C19", bg2="#272420", border="#3E3A35", text="#DDD8CC", text_sub="#9A9080", accent="#DDD8CC", accent_text="#1E1C19"),
}

SETTINGS_KEY = "theme_name"

def apply_theme(app, theme_name: str) -> str:
    """テーマを適用してQSSを返す"""
    theme = THEMES.get(theme_name, THEMES["Light Gray"])
    qss = _build_theme_qss(**theme)
    app.setStyleSheet(qss)
    return qss


def main():
    app = QApplication(sys.argv)

    # メインウィンドウの作成と表示
    window = MainWindow(apply_theme_fn=lambda name: apply_theme(app, name))

    # 保存済みテーマを復元（デフォルト: Light Gray）
    from PySide6.QtCore import QSettings
    s = QSettings("SIGMA_add", "SPP_Finisher")
    saved_theme = s.value("theme_name", "Light Gray")
    apply_theme(app, saved_theme)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
