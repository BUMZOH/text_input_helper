# Text Input Helper

Windows用のシンプルな定型文入力補助アプリです。

登録した定型文をホットキーで呼び出し、キーボード操作だけで
現在の入力先へ貼り付けることができます。

定型文は `phrases.json` で自由に追加・変更できます。

## 主な機能

- `Ctrl + Shift + Space` で選択画面を表示
- 数字キーで定型文を直接選択
- `Ctrl` / `Shift` で選択番号を変更
- `Enter` または `Space` で貼り付け
- `Esc` でキャンセル
- `TODAY_YYYY/MM/DD` で今日の日付を入力
- `FOLDER_NAME` でクリップボードから日付付き文字列を生成

## 必要環境

- Windows
- Python
- Tkinter
- keyboard
- pyperclip

`keyboard` と `pyperclip` は `requirements.txt` から
インストールできます。

## ファイル構成

```text
Text Input Helper/
├─ app.py
├─ phrases.json
├─ requirements.txt
├─ run.bat
└─ .gitignore
```

## セットアップ

仮想環境を使用する場合は、プロジェクトフォルダで次を実行します。

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 起動

`run.bat` をダブルクリックします。

`run.bat` は同じフォルダにある `.venv` のPythonを使用して
`app.py` を起動します。

## 基本的な使い方

1. アプリを起動します。
2. メモ帳、メール、ブラウザなど、文字を入力したい場所を
   アクティブにします。
3. `Ctrl + Shift + Space` を押します。
4. 定型文選択画面が表示されます。
5. 定型文を選択します。
6. `Enter` または `Space` を押します。
7. 元の入力先へテキストが貼り付けられます。

### 選択方法

選択画面を開いた直後、入力欄は空です。

数字を直接入力することもできます。

```text
3
```

と入力すれば、3番の定型文を選択できます。

また、左側の `Ctrl` / `Shift` だけでも選択できます。

```text
Ctrl  : 1 → 2 → 3 → 4 ...
Shift : 4 → 3 → 2 → 1
```

入力欄が空の状態で `Ctrl` または `Shift` を押した場合は、
最初に `1` が入力されます。

最大値は `phrases.json` に登録されている項目数、
最小値は `1` です。

### 決定・キャンセル

```text
Enter または Space : 選択した内容を貼り付け
Esc                  : 貼り付けずに画面を閉じる
```

## phrases.json

通常の定型文は、`name` と `text` を指定します。

```json
{
    "name": "お礼",
    "text": "ありがとうございました。"
}
```

`name` は選択画面に表示される名前です。

`text` が実際に貼り付けられる文字列です。

### 今日の日付

`name` を次の値にすると、現在の日付を自動生成します。

```json
{
    "name": "TODAY_YYYY/MM/DD",
    "text": ""
}
```

例えば2026年9月19日に実行すると、

```text
2026/09/19
```

が貼り付けられます。

### FOLDER_NAME

`name` を `FOLDER_NAME` にすると、現在の日付と
クリップボードのテキストから文字列を生成します。

```json
{
    "name": "FOLDER_NAME",
    "text": ""
}
```

例えば2026年9月19日にクリップボードへ、

```text
YOLO映像遅延対策
```

をコピーしてから実行すると、

```text
20260919_YOLO映像遅延対策→【途中】
```

が貼り付けられます。

クリップボードが空、またはテキストを取得できない場合は
空文字になります。

## ホットキー

デフォルトのホットキーは、

```text
Ctrl + Shift + Space
```

です。

変更する場合は `app.py` の次の設定を変更します。

```python
HOTKEY = "ctrl+shift+space"
```

## Windowsの固定キーについて

このアプリでは `Shift` を連続して押して選択番号を変更できます。

Windowsでは、Shiftキーを5回連続で押すと
「固定キー機能」の確認画面が表示される場合があります。

必要に応じてWindowsの設定から、
「Shiftキーを5回押して固定キーを起動する」ショートカットを
無効にしてください。

## 終了方法

`run.bat` で起動している場合は、
コンソールウィンドウを閉じるとアプリを終了できます。

選択画面右上の `X` を押した場合はアプリを終了せず、
選択画面だけを非表示にします。

## 補足

このアプリはクリップボードへ文字列をコピーした後、
`Ctrl + V` を自動送信して貼り付けを行います。

そのため、貼り付け先のアプリケーションが
`Ctrl + V` による貼り付けに対応している必要があります。
