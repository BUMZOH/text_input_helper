# Python `keyboard.add_hotkey()` が途中から反応しなくなる問題の原因追究

## 1. 概要

Tkinter と `keyboard`
ライブラリを使った入力補助アプリで、起動直後は正常に動作していた
グローバルホットキー

``` text
Ctrl + Shift + Space
```

が、しばらくアプリを使用していると反応しなくなる現象が発生した。

当初のホットキー処理は次のような構成だった。

``` python
def hotkey_worker() -> None:
    keyboard.add_hotkey(HOTKEY, show_window)
    keyboard.wait()
```

設定値は次のとおり。

``` python
HOTKEY = "ctrl+shift+space"
```

ホットキーが検出されると、次の関数が呼ばれる。

``` python
def show_window() -> None:
    print("Hotkey detected.")
    root.after(0, _show_window)


def _show_window() -> None:
    print("Showing window.")

    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)

    entry.delete(0, tk.END)
    entry.focus_force()
```

正常時にはターミナルへ、

``` text
Hotkey detected.
Showing window.
```

と表示される。

しかし問題発生後は、**この2つがどちらも表示されなかった**。

このことから、単にTkinterのウィンドウ表示に失敗しているのではなく、
`show_window()` 自体が呼ばれていない可能性が考えられた。

------------------------------------------------------------------------

## 2. 原因追究の基本方針

今回重要だったのは、すぐにプログラムを書き換えるのではなく、

> **どの段階までは正常に動いていて、どこから動いていないのか**

を順番に切り分けたことである。

処理の流れを単純化すると次のようになる。

``` text
Windowsのキーボード入力
        ↓
keyboardライブラリ
        ↓
keyboard.add_hotkey()
        ↓
show_window()
        ↓
root.after()
        ↓
_show_window()
        ↓
Tkinterウィンドウ表示
```

この各段階を順番に確認した。

------------------------------------------------------------------------

## 3. 調査1：Windowsのキー入力そのものを確認

まず、ホットキーが反応しなくなった状態で、

``` text
Ctrl+C
Ctrl+V
Shift+A
Space
```

を通常のWindowsアプリで使用した。

### 結果

すべて正常に使用できた。

### 判断

少なくとも、

-   Ctrlキーが押されっぱなしになっている
-   Shiftキーが押されっぱなしになっている
-   Spaceキーがおかしくなっている
-   Windows全体でキーボード入力がおかしくなっている

といった可能性は低くなった。

------------------------------------------------------------------------

## 4. 調査2：ホットキー監視スレッドが生きているか確認

ホットキー処理は別スレッドで実行していた。

``` python
thread = Thread(
    target=hotkey_worker,
    daemon=True,
)

thread.start()
```

そこで、監視スレッドが途中で終了していないか確認するため、
一時的に次のようなログを追加した。

``` python
def hotkey_worker() -> None:
    print("Hotkey worker started.")

    keyboard.add_hotkey(HOTKEY, show_window)

    while True:
        print("Hotkey worker is alive.")
        time.sleep(10)
```

### 問題発生後の結果

``` text
Hotkey worker is alive.
Hotkey worker is alive.
Hotkey worker is alive.
```

は表示され続けていた。

一方、

``` text
Hotkey detected.
Showing window.
```

は表示されなかった。

### 判断

**ホットキー監視用のスレッドそのものは終了していない。**

したがって、

``` text
daemon=True だから途中でスレッドが終了した
```

という問題ではない。

`daemon=True` のスレッドは、メインスレッドが終了したときに
Pythonプロセス終了を妨げないスレッドである。

今回のアプリではTkinterの

``` python
root.mainloop()
```

がメインスレッドで動作し続けているため、`daemon=True`
であることだけを理由に 監視スレッドが途中で終了するわけではない。

------------------------------------------------------------------------

## 5. 調査3：`keyboard` ライブラリ自体が生きているか確認

次に、

> `keyboard`
> ライブラリそのものがキーボード入力を取得できなくなったのではないか

という可能性を確認した。

`keyboard.is_pressed()` を使用してF8キーを直接監視した。

概念的には次のような処理である。

``` python
if keyboard.is_pressed("f8"):
    print("F8 detected.")
```

### 問題発生後の結果

``` text
F8 detected.
```

は正常に表示された。

しかし、

``` text
Hotkey detected.
Showing window.
```

は表示されなかった。

### 判断

`keyboard` ライブラリ全体が停止しているわけではない。

少なくとも、

``` python
keyboard.is_pressed()
```

によるキー状態の取得は正常に機能している。

------------------------------------------------------------------------

## 6. 調査4：Ctrl・Shift・Spaceを個別に確認

次に、問題となっている3つのキーを `keyboard.is_pressed()`
で直接確認した。

``` python
ctrl = keyboard.is_pressed("ctrl")
shift = keyboard.is_pressed("shift")
space = keyboard.is_pressed("space")

if ctrl and shift and space:
    print("Ctrl + Shift + Space detected manually.")
```

### 問題発生後の結果

Ctrl + Shift + Space を押すと、

``` text
Ctrl + Shift + Space detected manually.
Ctrl + Shift + Space detected manually.
Ctrl + Shift + Space detected manually.
```

と表示された。

### 判断

問題発生後も `keyboard` ライブラリは、

-   Ctrl
-   Shift
-   Space

の3キーを正常に認識している。

さらに、

``` python
ctrl and shift and space
```

という3キー同時押しの判定も正常にできている。

------------------------------------------------------------------------

## 7. 調査5：`add_hotkey()` と自前判定を同時に動かす

最後に、より明確に切り分けるため、

``` python
keyboard.add_hotkey(HOTKEY, show_window)
```

を残したまま、`keyboard.is_pressed()` による自前のホットキー判定も
同時に動作させた。

``` python
def hotkey_worker() -> None:
    hotkey_pressed = False

    keyboard.add_hotkey(HOTKEY, show_window)

    while True:
        ctrl = keyboard.is_pressed("ctrl")
        shift = keyboard.is_pressed("shift")
        space = keyboard.is_pressed("space")

        if ctrl and shift and space:
            if not hotkey_pressed:
                hotkey_pressed = True
                print("Manual hotkey detected.")
        else:
            hotkey_pressed = False

        time.sleep(0.05)
```

正常時には、

``` text
Hotkey detected.
Showing window.
Manual hotkey detected.
```

の両方が確認できる。

### 問題発生後の結果

表示されたのは、

``` text
Manual hotkey detected.
```

だけだった。

一方、

``` text
Hotkey detected.
Showing window.
```

は表示されなかった。

------------------------------------------------------------------------

## 8. 調査結果

ここまでの実験結果をまとめると次のようになる。

  確認項目                                 問題発生後
  ---------------------------------------- ------------
  Windows上のCtrlキー                      正常
  Windows上のShiftキー                     正常
  Windows上のSpaceキー                     正常
  ホットキー監視スレッド                   生存
  `keyboard.is_pressed("f8")`              正常
  `keyboard.is_pressed("ctrl")`            正常
  `keyboard.is_pressed("shift")`           正常
  `keyboard.is_pressed("space")`           正常
  3キー同時押しの自前判定                  正常
  `keyboard.add_hotkey()` のコールバック   反応しない
  `show_window()`                          呼ばれない
  `_show_window()`                         呼ばれない

したがって、今回の実験から確認できた範囲では、

> **`keyboard.add_hotkey()`
> で登録したホットキーのコールバックだけが、使用中に発火しなくなる**

ところまで原因を絞り込むことができた。

ただし、この調査だけでは `keyboard` ライブラリ内部で **なぜ**
`add_hotkey()` が発火しなくなるのかまでは特定していない。

したがって、

``` text
原因：keyboard.add_hotkey() 内部の○○というバグ
```

とまでは断定しない。

正確には、

> **問題が発生している場所を `add_hotkey()`
> によるホットキー判定付近まで切り分けた**

という結論である。

------------------------------------------------------------------------

## 9. 対策：`is_pressed()` による自前監視

今回のアプリでは `keyboard.add_hotkey()` を使わず、
`keyboard.is_pressed()` でキー状態を直接監視する方式を試した。

``` python
def hotkey_worker() -> None:
    hotkey_pressed = False

    while True:
        ctrl = keyboard.is_pressed("ctrl")
        shift = keyboard.is_pressed("shift")
        space = keyboard.is_pressed("space")

        if ctrl and shift and space:
            if not hotkey_pressed:
                hotkey_pressed = True
                show_window()
        else:
            hotkey_pressed = False

        time.sleep(0.05)
```

この方式へ変更後、従来より長くホットキーが反応し続けており、
現時点では良好な動作を確認している。

ただし、長時間運用で完全に問題が解消したかについては、
引き続き様子を見る。

------------------------------------------------------------------------

## 10. `hotkey_pressed` が必要な理由

単純に、

``` python
if ctrl and shift and space:
    show_window()
```

とすると問題がある。

監視周期が、

``` python
time.sleep(0.05)
```

なので、1秒間ではおよそ20回キー状態を確認する。

$$
\frac{1}{0.05} = 20
$$

人間がホットキーを0.3秒間押していた場合、理論上は複数回検出される可能性がある。

そこで、

``` python
hotkey_pressed = False
```

という状態変数を使用する。

処理の考え方は次のとおり。

``` text
最初
hotkey_pressed = False

        ↓

Ctrl + Shift + Spaceを押す

        ↓

3キーすべてON
かつ
hotkey_pressed == False

        ↓

show_window()

        ↓

hotkey_pressed = True

        ↓

まだ3キーを押している

        ↓

hotkey_pressed == Trueなので
show_window()を呼ばない

        ↓

キーを離す

        ↓

hotkey_pressed = False

        ↓

次のホットキー入力を受付可能
```

これは、

> **「キーが押されている状態」を監視しながら、「押した瞬間」を自分で作る**

ための処理である。

------------------------------------------------------------------------

## 11. 50 ms周期について

現在は、

``` python
time.sleep(0.05)
```

としている。

つまり約50 msごとにキー状態を確認する。

人間が操作するホットキー監視としては十分細かい周期であり、
今回の処理内容も、

``` python
keyboard.is_pressed()
```

を数回呼び出す程度なので非常に軽い。

また、`sleep()` を入れることで、

``` python
while True:
    ...
```

がCPUを使って全力で回り続けることも防いでいる。

------------------------------------------------------------------------

## 12. 今回の原因追究で重要だったこと

今回もっとも重要なのは、問題が発生した直後にコードを大きく変更せず、
処理を一段ずつ確認したことである。

最初の症状だけを見ると、

``` text
ホットキーを押してもウィンドウが表示されない
```

ため、Tkinterを疑いたくなる。

しかし実際には、

``` text
show_window()
```

の先頭にあるログすら表示されていなかった。

そのため、Tkinterより前の段階を調査した。

最終的な切り分けは次のようになった。

``` text
Windowsキーボード入力
        │
        │ 正常
        ↓
keyboardライブラリ
        │
        │ is_pressed() は正常
        ↓
Ctrl / Shift / Spaceの認識
        │
        │ 正常
        ↓
3キー同時押しの自前判定
        │
        │ 正常
        ↓
keyboard.add_hotkey()
        │
        │ ここでコールバックが発火しなくなる
        ×
        ↓
show_window()
        ↓
root.after()
        ↓
_show_window()
        ↓
Tkinter
```

このように、

> **正常な場所と異常な場所の境界を探す**

ことが、原因追究の基本になる。

------------------------------------------------------------------------

## 13. デバッグで学んだ考え方

### 13.1 「動かない」ではなく「どこまで動いているか」を調べる

悪い調べ方：

``` text
ホットキーが動かない
→ とりあえずコードを書き換える
```

良い調べ方：

``` text
キー入力は正常？
        ↓
スレッドは生きている？
        ↓
keyboardはキーを読める？
        ↓
Ctrl/Shift/Spaceは読める？
        ↓
3キー同時押しは判定できる？
        ↓
add_hotkey()はコールバックを呼ぶ？
        ↓
show_window()は呼ばれる？
        ↓
Tkinterは表示できる？
```

一段ずつ確認すると、問題の範囲を狭められる。

### 13.2 `print()` は非常に有効なデバッグ手段

今回、

``` python
print("Hotkey detected.")
print("Showing window.")
print("Hotkey worker is alive.")
print("F8 detected.")
print("Manual hotkey detected.")
```

という単純なログが非常に役立った。

高度なデバッガを使わなくても、

> **処理がその場所まで到達したか**

を確認するだけで、多くの問題を切り分けられる。

### 13.3 代替手段は原因追究にも使える

今回の `is_pressed()` は単なる代替実装ではない。

``` python
keyboard.add_hotkey()
```

と、

``` python
keyboard.is_pressed()
```

を同時に動かしたことで、

``` text
同じキーボード入力を使っているのに
片方だけ動かない
```

という比較実験ができた。

これは原因追究で非常に有効な考え方である。

------------------------------------------------------------------------

## 14. 今回の暫定結論

今回の調査で確認できたことは、

``` text
keyboardライブラリ全体が停止したわけではない
        ↓
監視スレッドが終了したわけでもない
        ↓
Windowsのキー入力異常でもない
        ↓
Ctrl / Shift / Spaceは正常に取得できる
        ↓
3キー同時押しも正常に判定できる
        ↓
add_hotkey()で登録したコールバックだけが発火しなくなる
```

ということである。

そのため現在は、

``` python
keyboard.add_hotkey()
```

を使用せず、

``` python
keyboard.is_pressed()
```

による自前監視方式を暫定対策として採用している。

現時点では従来より安定して反応し続けている。

今後、長時間運用でも問題が再発しなければ、
この方式を正式な実装として採用することを検討する。

------------------------------------------------------------------------

## 15. 今回の学習ポイント

今回のトラブルから得られる汎用的な学習ポイントは次のとおり。

1.  不具合発生時は、いきなり修正せず「どこまで正常か」を調べる。
2.  `print()` ログだけでも処理経路の切り分けには非常に有効。
3.  スレッドが生きていることと、その中で利用している機能が正常であることは別問題。
4.  ライブラリ全体が壊れているのか、一部のAPIだけに問題があるのかを分けて考える。
5.  同じ入力を別の方法で取得して比較すると、問題箇所を絞り込みやすい。
6.  `while True` で状態監視する場合は `sleep()`
    を入れてCPU負荷を抑える。
7.  ポーリングで「押した瞬間」を作る場合は、状態変数を使って連続発火を防止する。
8.  原因が完全に特定できていない場合は、「確認できた事実」と「推測」を分けて記録する。

------------------------------------------------------------------------

# まとめ

今回の問題では、最初は単純に

``` text
ホットキーが効かなくなる
```

という症状しか分からなかった。

しかし段階的に調査した結果、

``` text
Windows入力             正常
        ↓
監視スレッド            正常
        ↓
keyboard.is_pressed()   正常
        ↓
3キー同時押し判定       正常
        ↓
keyboard.add_hotkey()   ← 問題発生箇所として絞り込み
        ↓
show_window()           呼ばれない
```

というところまで問題箇所を限定できた。

最終的に、`keyboard.is_pressed()` を使って50 ms周期で
Ctrl・Shift・Spaceを直接監視する方式を試したところ、
現時点では従来より安定した動作を確認している。

今回の事例で特に重要なのは、

> **「原因を想像して修正する」のではなく、「正常と異常の境界を実験で探す」**

というデバッグの基本である。

この考え方はホットキーだけでなく、PLC通信、SQLite、ネットワーク通信、
マルチスレッド、GUI、カメラ処理など、さまざまなプログラムの
トラブルシューティングにそのまま応用できる。
