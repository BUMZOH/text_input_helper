# Text Input Helper 技術解説

## グローバルホットキーの不具合調査と解決

## 1. はじめに

このアプリは、Windows上で常駐させて使用するシンプルな定型文入力支援ツールです。

通常はコンソールだけを表示した状態で待機し、

``` text
Ctrl + Shift + Space
```

を押すとTkinterの小さな選択画面を表示します。

画面上で定型文の番号を入力してEnterを押すと、その定型文を
クリップボードへコピーし、直前に使用していたアプリへ `Ctrl + V`
で貼り付けます。

今回、グローバルホットキーがときどき反応しない現象が発生しました。

最終的には、

``` python
keyboard.add_hotkey()
```

による組み合わせ判定を使わず、

``` python
keyboard.on_press()
keyboard.is_pressed()
```

を組み合わせて、自分でホットキー成立を判定する方式へ変更しました。

この変更後は動作が改善したため、しばらくこの方式で運用して
様子を見ることにしました。

------------------------------------------------------------------------

# 2. 現在のプログラム

``` python
import json
import time
import tkinter as tk
from pathlib import Path
from threading import Thread

import keyboard
import pyperclip


# ================================================
#   Settings
# ================================================
HOTKEY = "ctrl+shift+space"

BASE_DIR = Path(__file__).resolve().parent
PHRASES_PATH = BASE_DIR / "phrases.json"


# ================================================
#   Load phrases
# ================================================
def load_phrases():
    with open(PHRASES_PATH, encoding="utf-8") as file:
        return json.load(file)


PHRASES = load_phrases()


# ================================================
#   Paste phrase
# ================================================
def paste_phrase(text):
    pyperclip.copy(text)

    root.withdraw()

    # Wait for focus to return to the previous window.
    time.sleep(0.2)

    keyboard.press_and_release("ctrl+v")


# ================================================
#   Enter key
# ================================================
def on_enter(event=None):
    value = entry.get().strip()

    if not value.isdigit():
        return

    index = int(value) - 1

    if not 0 <= index < len(PHRASES):
        return

    text = PHRASES[index]["text"]

    entry.delete(0, tk.END)

    paste_phrase(text)


# ================================================
#   Escape key
# ================================================
def on_escape(event=None):
    entry.delete(0, tk.END)
    root.withdraw()


# ================================================
#   Show window
# ================================================
def show_window():
    print("Hotkey detected.")   # For troubleshooting
    root.after(0, _show_window)


def _show_window():
    print("_show_window started.")  # For troubleshooting

    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)

    entry.delete(0, tk.END)
    entry.focus_force()


# ================================================
#   Hotkey worker
# ================================================
def on_key_press(event):
    if event.name != "space":
        return

    if not keyboard.is_pressed("ctrl"):
        return

    if not keyboard.is_pressed("shift"):
        return

    show_window()


def hotkey_worker():
    keyboard.on_press(on_key_press)
    keyboard.wait()


# ================================================
#   Close button
# ================================================
def on_close():
    root.withdraw()


# ================================================
#   Tkinter
# ================================================
root = tk.Tk()

root.title("Text Input Helper")
root.geometry("500x280")

# Clicking the X button hides the window instead of terminating the app.
root.protocol("WM_DELETE_WINDOW", on_close)

title_label = tk.Label(
    root,
    text="定型文を選択してください",
    font=("Yu Gothic UI", 14),
)
title_label.pack(pady=(20, 10))

for index, phrase in enumerate(PHRASES, start=1):
    label = tk.Label(
        root,
        text=f'{index}) {phrase["name"]}',
        anchor="w",
        font=("Yu Gothic UI", 11),
    )
    label.pack(
        fill="x",
        padx=30,
        pady=2,
    )

entry = tk.Entry(
    root,
    font=("Consolas", 14),
    width=10,
)
entry.pack(pady=20)

entry.bind("<Return>", on_enter)
entry.bind("<Escape>", on_escape)


# ================================================
#   Start hotkey thread
# ================================================
thread = Thread(
    target=hotkey_worker,
    daemon=True,
)
thread.start()

# Hide window at startup.
root.withdraw()

# Show messages on the terminal.
print("=" * 50)
print("  Text Input Helper")
print("=" * 50)
print()
print("Text Input Helper is running.")
print()
print(f"Hotkey: {HOTKEY}")
print()
print("Press the hotkey to open the phrase selection window.")
print()
print("To exit the application, close this console window.")
print()
print("=" * 50)

root.mainloop()
```

------------------------------------------------------------------------

# 3. アプリ全体の構成

大きく分けると、このアプリには次の処理があります。

``` text
phrases.json
    ↓
定型文を読み込む

Tkinter
    ↓
定型文一覧と番号入力欄を作る

別スレッド
    ↓
keyboardでグローバルキー入力を監視

Ctrl + Shift + Space
    ↓
Tkinter画面を表示

番号 + Enter
    ↓
定型文をクリップボードへコピー
    ↓
Tkinter画面を隠す
    ↓
Ctrl + V
    ↓
元のアプリへ貼り付け
```

ポイントは、TkinterのGUI処理とグローバルキーボード監視を
分けていることです。

------------------------------------------------------------------------

# 4. JSONから定型文を読み込む

定型文はPythonコードへ直接書かず、`phrases.json` に保存しています。

例：

``` json
[
    {
        "name": "挨拶",
        "text": "お世話になっております。"
    },
    {
        "name": "締め",
        "text": "よろしくお願いいたします。"
    }
]
```

読み込み部分は次の関数です。

``` python
def load_phrases():
    with open(PHRASES_PATH, encoding="utf-8") as file:
        return json.load(file)
```

そして、

``` python
PHRASES = load_phrases()
```

で起動時に一度読み込みます。

この方式なら定型文を増減するときに、Pythonコードを変更する必要が
ありません。

------------------------------------------------------------------------

# 5. Tkinter画面

Tkinterのメインウィンドウは、

``` python
root = tk.Tk()
```

で作成しています。

サイズは、

``` python
root.geometry("500x280")
```

です。

起動直後には、

``` python
root.withdraw()
```

を実行して画面を非表示にしています。

つまりアプリ自体は動作していますが、Tkinter画面は普段見えません。

------------------------------------------------------------------------

# 6. `withdraw()` と `deiconify()`

今回のアプリでは、この2つが重要です。

## 非表示

``` python
root.withdraw()
```

Tkinterウィンドウを隠します。

アプリ自体を終了しているわけではありません。

## 再表示

``` python
root.deiconify()
```

隠れていたTkinterウィンドウを再表示します。

そのため、

``` text
起動
 ↓
withdraw()
 ↓
非表示で待機
 ↓
ホットキー
 ↓
deiconify()
 ↓
表示
```

という動作になります。

------------------------------------------------------------------------

# 7. 画面を前面へ表示する処理

``` python
def _show_window():
    print("_show_window started.")  # For troubleshooting

    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)

    entry.delete(0, tk.END)
    entry.focus_force()
```

それぞれの役割は次のとおりです。

### `root.deiconify()`

非表示だった画面を再表示します。

### `root.lift()`

ウィンドウを他のウィンドウより前へ持ってきます。

### `root.attributes("-topmost", True)`

最前面ウィンドウとして扱います。

### `entry.delete(0, tk.END)`

前回入力した番号を削除します。

### `entry.focus_force()`

番号入力欄へキーボードフォーカスを移します。

したがって、ホットキーを押した直後に数字を入力できるように
なっています。

------------------------------------------------------------------------

# 8. 番号入力とEnter

Enterキーには、

``` python
entry.bind("<Return>", on_enter)
```

で `on_enter()` を割り当てています。

処理は、

``` python
value = entry.get().strip()
```

で入力値を取得します。

次に、

``` python
if not value.isdigit():
    return
```

で数字以外を無視します。

例えば、

``` text
1
2
3
```

なら処理を続行しますが、

``` text
abc
```

なら何もしません。

------------------------------------------------------------------------

# 9. 1始まりから0始まりへの変換

ユーザーには、

``` text
1) 挨拶
2) 締め
3) 確認依頼
```

のように1から番号を表示します。

しかしPythonのリストは0から始まります。

そのため、

``` python
index = int(value) - 1
```

としています。

例えばユーザーが、

``` text
1
```

を入力した場合、

``` python
index = 0
```

となります。

------------------------------------------------------------------------

# 10. 範囲チェック

``` python
if not 0 <= index < len(PHRASES):
    return
```

によって、存在しない番号が入力された場合は何もしません。

例えば定型文が4件しかないのに、

``` text
99
```

と入力してもエラーになりません。

------------------------------------------------------------------------

# 11. 定型文の貼り付け

選択された文字列は、

``` python
text = PHRASES[index]["text"]
```

で取得します。

その後、

``` python
paste_phrase(text)
```

を呼び出します。

------------------------------------------------------------------------

# 12. クリップボードへのコピー

``` python
pyperclip.copy(text)
```

で定型文をWindowsのクリップボードへコピーします。

次に、

``` python
root.withdraw()
```

で選択画面を隠します。

------------------------------------------------------------------------

# 13. 0.2秒待つ理由

``` python
time.sleep(0.2)
```

を入れています。

Tkinter画面を隠した直後に `Ctrl + V` を送信すると、
Windows側のフォーカスが元のアプリへ戻る前に貼り付け処理が
実行される可能性があります。

そこで、

``` text
Tkinterを隠す
 ↓
0.2秒待つ
 ↓
元のアプリへフォーカスが戻る
 ↓
Ctrl + V
```

という順番にしています。

最後に、

``` python
keyboard.press_and_release("ctrl+v")
```

で貼り付けを実行します。

------------------------------------------------------------------------

# 14. Escapeキー

``` python
entry.bind("<Escape>", on_escape)
```

によってEscapeキーで選択画面を閉じられます。

``` python
def on_escape(event=None):
    entry.delete(0, tk.END)
    root.withdraw()
```

ここでもアプリ自体は終了せず、Tkinter画面を隠すだけです。

------------------------------------------------------------------------

# 15. Xボタンでも終了しない

通常、Tkinterウィンドウ右上のXボタンを押すとアプリを終了します。

今回は、

``` python
root.protocol("WM_DELETE_WINDOW", on_close)
```

としているため、Xボタンを押すと、

``` python
def on_close():
    root.withdraw()
```

が実行されます。

つまりXボタンも「終了」ではなく「非表示」です。

アプリを終了するときは、常駐状態を示しているコンソールウィンドウを
閉じます。

------------------------------------------------------------------------

# 16. なぜキーボード監視を別スレッドにするのか

Tkinterには、

``` python
root.mainloop()
```

というイベントループがあります。

これは、

``` text
マウス操作
キー入力
画面更新
ボタン操作
```

などを処理し続けています。

一方、`keyboard` 側でも、

``` python
keyboard.wait()
```

によってキー入力を待ち続けます。

同じスレッドで両方を待たせるのではなく、

``` text
メインスレッド
    └─ Tkinter

別スレッド
    └─ keyboard
```

という構成にしています。

------------------------------------------------------------------------

# 17. daemon=True の意味

``` python
thread = Thread(
    target=hotkey_worker,
    daemon=True,
)
```

ここでは、

``` python
daemon=True
```

を指定しています。

これは、このスレッドをアプリ本体に従属するバックグラウンドスレッド
として動かす指定です。

メインプログラムが終了したときに、このキーボード監視スレッドだけが
残り続けることを防ぎます。

------------------------------------------------------------------------

# 18. 今回発生した不具合

最初はグローバルホットキーを次のように登録していました。

``` python
keyboard.add_hotkey(HOTKEY, show_window)
```

例えば、

``` python
HOTKEY = "ctrl+shift+space"
```

なら、

``` text
Ctrl + Shift + Space
```

が成立したときに、

``` python
show_window()
```

が呼び出される想定でした。

通常は問題なく動作しました。

しかし、実際に使用していると、

``` text
Ctrl + Shift + Spaceを押した
 ↓
何も起きない
```

という現象がときどき発生しました。

毎回発生するわけではなく、正常に動くこともあるため、
原因の切り分けが必要でした。

------------------------------------------------------------------------

# 19. 最初に考えた原因

ホットキーを押しても画面が表示されない場合、大きく分けると
次のどこかに原因があります。

``` text
① Windowsからキー入力を取得できていない

② keyboardがホットキー成立と判定していない

③ show_window() が呼ばれていない

④ Tkinterへ表示要求が届いていない

⑤ Tkinterは処理しているが画面が前面に出ていない
```

見た目だけでは、どこで止まっているのか分かりません。

そこでログを追加して、処理を段階的に確認しました。

------------------------------------------------------------------------

# 20. `Hotkey detected.` を追加

まず、

``` python
def show_window():
    print("Hotkey detected.")  # For troubleshooting
    root.after(0, _show_window)
```

としました。

正常なら、

``` text
Hotkey detected.
```

が表示されます。

これによって、

``` text
ホットキーを押した
 ↓
show_window()まで到達したか？
```

を確認できます。

------------------------------------------------------------------------

# 21. `_show_window started.` も追加

さらに、

``` python
def _show_window():
    print("_show_window started.")  # For troubleshooting
```

も追加しました。

正常時には、

``` text
Hotkey detected.
_show_window started.
```

と表示されます。

これで、

``` text
keyboard
 ↓
show_window()
 ↓
root.after()
 ↓
_show_window()
 ↓
Tkinter表示
```

のどこまで進んだのか確認できます。

------------------------------------------------------------------------

# 22. キーそのものを取得できているか調査

次に、ホットキー判定以前に、各キーを `keyboard` が認識しているか
調べました。

調査用として、

``` python
keyboard.on_press(
    lambda event: print(f"Key pressed: {event.name}")
)
```

を追加しました。

Ctrl、Alt、Spaceを押すと、

``` text
Key pressed: ctrl
Key pressed: alt
Key pressed: space
```

のように表示されます。

------------------------------------------------------------------------

# 23. 決定的だったログ

不具合発生時に確認されたログは、

``` text
Key pressed: ctrl
Key pressed: alt
Key pressed: space
```

でした。

しかし、

``` text
Hotkey detected.
```

は表示されませんでした。

ここが今回の調査で非常に重要なポイントです。

各キーは正常に検出されています。

つまり、

``` text
Ctrl       → 検出できている
Alt        → 検出できている
Space      → 検出できている
```

にもかかわらず、

``` python
keyboard.add_hotkey()
```

による「Ctrl + Alt + Space」という組み合わせの成立判定では
コールバックが呼ばれないことがありました。

少なくとも今回観測した現象については、Tkinterの画面表示より前で
処理が止まっていることが分かりました。

------------------------------------------------------------------------

# 24. 原因の切り分けで重要な考え方

このとき、

``` text
画面が出ない
```

だけを見て、

``` text
Tkinterがおかしい
```

と判断してはいけません。

ログによって、

``` text
個別キー入力
    ↓ OK

ホットキー成立
    ↓ NG

show_window()
    ↓ 未到達

Tkinter
    ↓ まだ関係ない
```

と切り分けることができました。

これは今回のアプリだけでなく、通信処理、PLC、スレッド処理、
GUIアプリなどでも非常に重要なデバッグ方法です。

------------------------------------------------------------------------

# 25. `add_hotkey()` を使わない方式へ変更

そこで、

``` python
keyboard.add_hotkey(HOTKEY, show_window)
```

を使わないことにしました。

代わりに、

``` python
keyboard.on_press(on_key_press)
```

で個々のキーイベントを受け取ります。

そして、自分で、

``` text
Spaceが押されたか？

Ctrlは現在押されているか？

Shiftは現在押されているか？
```

を判定します。

------------------------------------------------------------------------

# 26. 現在のホットキー判定

現在のコードは次のとおりです。

``` python
def on_key_press(event):
    if event.name != "space":
        return

    if not keyboard.is_pressed("ctrl"):
        return

    if not keyboard.is_pressed("shift"):
        return

    show_window()
```

非常に単純な処理です。

------------------------------------------------------------------------

# 27. 1段目：Spaceだけを入口にする

``` python
if event.name != "space":
    return
```

Space以外のキーが押された場合は即座に終了します。

例えばCtrlが押されても、

``` text
event.name = "ctrl"
```

なので終了します。

Shiftでも終了します。

Spaceが押された瞬間だけ、その先の判定へ進みます。

このため、すべてのキーで毎回複雑な処理をする必要がありません。

------------------------------------------------------------------------

# 28. 2段目：Ctrlの状態確認

``` python
if not keyboard.is_pressed("ctrl"):
    return
```

Spaceが押された瞬間にCtrlが押されているか確認します。

Ctrlが押されていなければ、普通のSpaceなので何もしません。

------------------------------------------------------------------------

# 29. 3段目：Shiftの状態確認

``` python
if not keyboard.is_pressed("shift"):
    return
```

さらにShiftが押されているか確認します。

ここまで通過した場合、

``` text
Spaceが押された
AND
Ctrlが押されている
AND
Shiftが押されている
```

ことになります。

したがって、

``` python
show_window()
```

を実行します。

------------------------------------------------------------------------

# 30. 現在のホットキー判定を図にすると

``` text
何かキーが押された
        ↓
on_key_press(event)
        ↓
Spaceか？
   ├─ NO → return
   ↓ YES
Ctrlが押されているか？
   ├─ NO → return
   ↓ YES
Shiftが押されているか？
   ├─ NO → return
   ↓ YES
show_window()
        ↓
Tkinter画面を表示
```

`add_hotkey()` に組み合わせ判定を任せるのではなく、
必要な条件を自分で明示的に判定しています。

------------------------------------------------------------------------

# 31. `hotkey_worker()` もシンプルになった

以前は、

``` python
def hotkey_worker():
    keyboard.add_hotkey(HOTKEY, show_window)
    keyboard.wait()
```

という考え方でした。

現在は、

``` python
def hotkey_worker():
    keyboard.on_press(on_key_press)
    keyboard.wait()
```

です。

つまり、

``` text
ホットキーを登録する
```

のではなく、

``` text
キーが押されたらon_key_press()へ知らせる
```

だけを `keyboard` に任せています。

組み合わせの判定はPythonコード側で行います。

------------------------------------------------------------------------

# 32. なぜ今回の変更で調子が良くなったのか

今回の観測から確実に言えるのは、不具合発生時にも個々のキーイベントは
取得できていた、ということです。

一方、

``` python
keyboard.add_hotkey()
```

で登録したコールバックが呼ばれないケースがありました。

そこで、正常に取得できていた個々のキーイベントを利用し、

``` python
keyboard.on_press()
```

と、

``` python
keyboard.is_pressed()
```

で組み合わせを自前判定するようにしました。

変更後は動作が改善しています。

ただし、現時点では「`keyboard.add_hotkey()` 自体に必ず不具合がある」
と一般化するのではなく、

> 今回のPC・環境・キー組み合わせ・アプリ構成では、 `add_hotkey()`
> の成立判定を経由しない方式に変更したところ 安定性が改善した

と捉えるのが適切です。

------------------------------------------------------------------------

# 33. 今回のデバッグで学べること

今回もっとも重要なのは、単に別のコードへ変更して直ったことでは
ありません。

重要なのは、

``` text
どこまで正常に処理されているのか
```

をログで確認したことです。

最初は、

``` text
ホットキーを押しても画面が出ない
```

という曖昧な現象でした。

そこへログを追加することで、

``` text
キー入力は取得できている
 ↓
ホットキー成立コールバックが呼ばれていない
 ↓
Tkinter表示処理へ到達していない
```

というところまで絞り込みました。

これは典型的な「切り分け」の考え方です。

------------------------------------------------------------------------

# 34. デバッグでは処理の境界にログを置く

今回なら、

``` python
print("Hotkey detected.")
```

と、

``` python
print("_show_window started.")
```

を処理の境界に置きました。

例えば、

``` text
keyboard
    ↓
[LOG 1]
show_window()
    ↓
root.after()
    ↓
[LOG 2]
_show_window()
    ↓
Tkinter
```

とすることで、どこまで処理が到達したのか確認できます。

これは非常に汎用性の高い方法です。

------------------------------------------------------------------------

# 35. 「原因」と「観測事実」を分ける

デバッグではこの区別も重要です。

今回の観測事実は、

``` text
個別のCtrl、Alt、Spaceは検出された。
しかしHotkey detected.は表示されなかった。
```

です。

ここから、

``` text
show_window()より前で止まっている
```

ことは判断できます。

一方、

``` text
keyboardライブラリ内部の○○処理が原因である
```

とまでは、このログだけでは断定できません。

したがって技術的には、

``` text
add_hotkey()による組み合わせ判定を避けたところ改善した
```

と記録しておくのが安全です。

この姿勢は、将来の不具合調査でも非常に重要です。

------------------------------------------------------------------------

# 36. 現在のコードで注意しておきたい点

現在、

``` python
HOTKEY = "ctrl+shift+space"
```

という設定があります。

しかし実際のホットキー判定は、

``` python
if not keyboard.is_pressed("ctrl"):
    return

if not keyboard.is_pressed("shift"):
    return
```

とコードへ直接書かれています。

つまり現在の `HOTKEY` は主に、

``` python
print(f"Hotkey: {HOTKEY}")
```

でコンソールへ表示するために使われています。

例えば将来、

``` python
HOTKEY = "ctrl+alt+space"
```

だけ変更しても、実際の判定はまだCtrl + Shift + Spaceのままです。

ここは今後改良するときの注意点です。

現段階ではシンプルさを優先して、このまま運用しても問題ありませんが、
設定値と実際の判定条件を二重管理していることは覚えておくとよいでしょう。

------------------------------------------------------------------------

# 37. Tkinterと別スレッドについての注意

現在、

``` python
def show_window():
    root.after(0, _show_window)
```

をキーボード監視側のスレッドから呼んでいます。

今回の不具合調査では、問題発生時に `show_window()` まで到達していない
ことが確認されたため、今回観測した現象の直接の原因ではありませんでした。

ただしTkinterは基本的にメインスレッドでGUI操作を行う設計です。

もし将来、

``` text
Hotkey detected.
```

は表示されるのに、

``` text
_show_window started.
```

が表示されない、あるいはGUI動作が不安定になる場合は、
次の調査対象として、

``` text
keyboardスレッド
    ↓
threading.Event / Queue
    ↓
Tkinterメインスレッド
```

のように、GUI処理を完全にメインスレッドへ渡す構成を検討できます。

ただし、現在は動作が改善しているため、まずは今のシンプルな構成で
実運用して様子を見る方針です。

------------------------------------------------------------------------

# 38. 調査ログはしばらく残してよい

現在、

``` python
print("Hotkey detected.")  # For troubleshooting
```

と、

``` python
print("_show_window started.")  # For troubleshooting
```

が残っています。

しばらく様子を見る段階では、これらを残しておく価値があります。

もし再発した場合、

``` text
何も出ない
```

のか、

``` text
Hotkey detected.
```

だけ出るのか、

``` text
Hotkey detected.
_show_window started.
```

まで出るのかで、次の調査場所が変わります。

安定動作が十分確認できたあとで削除すればよいでしょう。

------------------------------------------------------------------------

# 39. 今回の不具合解決の流れ

今回の経緯をまとめると次のようになります。

``` text
1. add_hotkey() でグローバルホットキーを登録
        ↓
2. 通常は動作するが、ときどき反応しない
        ↓
3. Hotkey detected. のログを追加
        ↓
4. 個々のキー入力ログも追加
        ↓
5. 不具合発生時にも各キーは取得できていることを確認
        ↓
6. しかしHotkey detected.は出ない
        ↓
7. Tkinterより前で止まっていると判断
        ↓
8. add_hotkey()による組み合わせ判定を使用しない方針へ
        ↓
9. keyboard.on_press()で個別キーイベントを取得
        ↓
10. keyboard.is_pressed()でCtrlとShiftを確認
        ↓
11. 条件成立時だけshow_window()を実行
        ↓
12. 動作が改善
        ↓
13. Ctrl + Shift + Spaceでしばらく実運用して様子を見る
```

------------------------------------------------------------------------

# 40. 今回の重要ポイント

今回の経験から特に覚えておきたいポイントは次のとおりです。

### 1. 「動かない」だけでは原因は分からない

画面が出ないからといって、GUIが原因とは限りません。

### 2. 処理の途中へログを入れる

``` python
print()
```

だけでも、処理がどこまで進んだかをかなり正確に確認できます。

### 3. 入力取得と組み合わせ判定は別問題

今回、

``` text
各キーは取得できている
```

ことと、

``` text
ホットキーとして成立する
```

ことは別だと分かりました。

### 4. ライブラリの高機能APIを無理に使う必要はない

`add_hotkey()` が今回の環境で安定しないなら、

``` python
on_press()
is_pressed()
```

という単純な部品を組み合わせて自分で判定できます。

### 5. シンプルな処理はデバッグしやすい

現在の判定は、

``` python
Spaceか？
Ctrlは押されているか？
Shiftは押されているか？
```

だけです。

処理内容を目で追いやすく、将来の修正もしやすい構成です。

------------------------------------------------------------------------

# 41. まとめ

今回作成したText Input Helperは、

-   Tkinterによる小さな入力画面
-   JSONによる定型文管理
-   `keyboard` によるグローバルキー監視
-   `pyperclip` によるクリップボード操作
-   別スレッドによる常時キー監視
-   `Ctrl + V` による元アプリへの自動貼り付け

を組み合わせた、シンプルな常駐ツールです。

今回もっとも重要だったのは、グローバルホットキーが不安定だったときに
「Tkinterが悪い」「keyboardが悪い」と最初から決めつけず、
ログを追加して処理を順番に切り分けたことです。

不具合発生時のログから、

``` text
個々のキーイベントは取得できている
```

一方で、

``` text
add_hotkey()によるホットキー成立後の処理へ到達していない
```

ことを確認しました。

そこで、

``` python
keyboard.add_hotkey()
```

による組み合わせ判定をやめ、

``` python
keyboard.on_press()
keyboard.is_pressed()
```

を使った明示的な判定へ変更しました。

結果として現在は動作が改善しています。

そして今回のデバッグ方法、

``` text
現象を確認する
 ↓
処理を分割して考える
 ↓
境界へログを置く
 ↓
どこまで正常か確認する
 ↓
原因候補を絞る
 ↓
最小限の変更を行う
 ↓
再度実運用で確認する
```

は、Pythonアプリだけでなく、PLC通信、ネットワーク通信、
マルチスレッド、GUI、データベース処理などにもそのまま使える
非常に重要な不具合調査の基本手順です。
