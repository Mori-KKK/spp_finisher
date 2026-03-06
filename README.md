# SPP Finisher

**SIGMA Photo Pro (SPP) で書き出した TIFF / JPEG を仕上げるための Windows デスクトップアプリケーション**

Foveon センサーの色味を活かしたまま、トーン調整・カラーグレーディング・EXIF テキスト / ロゴ透かし・白枠・コラージュ作成まで一貫して行えます。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## ✨ 主な機能

| カテゴリ | 機能 |
|---------|------|
| **TONE** | 露光量 / コントラスト / ハイライト / シャドウ / 白レベル / 黒レベル |
| **COLOR** | 色相 / 彩度 / 自然な彩度 / 輝度 |
| **TEXTURE** | Grain / Clarity / Vignette |
| **装飾** | EXIF テキスト合成（サイズ・色・透明度・位置）/ ロゴ透かし（サイズ・透明度・位置）|
| **白枠** | 額縁風の白ボーダー（EXIF・ロゴは枠の上に配置）|
| **コラージュ** | 最大 10 枚 / 9 種レイアウト / SNS アスペクト比 10 種 |
| **画像管理** | 最大 10 枚のマルチ画像管理 / 画像ごとの個別パラメータ |
| **HOT FOLDER** | フォルダ監視で SPP 書き出しを自動検出 |
| **テーマ** | Light Gray / Pure White / Warm Cream / Dark / Dark Warm |
| **エクスポート** | JPEG (Quality 95) / 16bit TIFF / ファイル名に `_Fin` 自動付加 |

---

## 🚀 セットアップ

### 必要環境

- **Python 3.10 以上**
- **Windows 10 / 11**

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/<your-username>/spp_finisher.git
cd spp_finisher

# 仮想環境を作成（推奨）
python -m venv venv
venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

### 起動

```bash
python src/main.py
```

---

## 📦 Windows 実行ファイル（.exe）のビルド

PyInstaller でスタンドアロン exe を作成できます。

```bash
# PyInstaller をインストール
pip install pyinstaller

# ビルド実行
build.bat
```

`dist/SPP_Finisher/SPP_Finisher.exe` が生成されます。

---

## 📁 プロジェクト構成

```
spp_finisher/
├── src/
│   ├── main.py              # エントリーポイント（テーマ定義含む）
│   ├── core/
│   │   ├── color_grading.py  # トーン・カラー処理エンジン
│   │   ├── decoration.py     # EXIF テキスト・ロゴ・白枠
│   │   ├── collage_engine.py # コラージュレイアウト & レンダリング
│   │   ├── image_manager.py  # マルチ画像管理
│   │   ├── exporter.py       # JPEG / TIFF 書き出し
│   │   └── folder_monitor.py # HOT FOLDER 監視
│   └── ui/
│       ├── main_window.py    # メインウィンドウ
│       ├── control_panel.py  # スライダー・設定パネル
│       ├── image_view.py     # 画像プレビュー
│       ├── thumbnail_strip.py# サムネイルストリップ
│       └── collage_dialog.py # コラージュ作成ダイアログ
├── assets/
│   ├── app_icon.png          # アプリアイコン
│   └── fonts/                # フォントファイル
├── requirements.txt
├── build.bat                 # PyInstaller ビルドスクリプト
├── SPP_Finisher.spec         # PyInstaller 設定
├── LICENSE
└── README.md
```

---

## 🎨 ロゴ透かし

`sigmalogo/` フォルダに PNG ロゴを配置すると、ロゴ選択ドロップダウンに表示されます。

ロゴファイルのパスは `src/core/decoration.py` 内の `LOGO_OPTIONS` で定義されています。

---

## 📝 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照してください。

---

## 🤝 コントリビュート

Issue や Pull Request を歓迎します。

1. このリポジトリを Fork
2. Feature ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. コミット (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Pull Request を作成
