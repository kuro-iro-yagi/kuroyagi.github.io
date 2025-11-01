# 仮想環境を作る
```py -m venv .venv```
# 仮想環境を有効化
```.venv\Scripts\Activate.ps1```
# 必要なライブラリを仮想環境内にインストール
```pip install pillow```
# スクリプトを実行
```
py generate_gallery.py --base-url "https://kuro-iro-yagi.github.io/kuroyagi.github.io/gallery/"
```
# 仮想環境を無効化
```deactivate```