# Text Input Helper
# ホットキーのSpaceが元アプリへ入力される問題と対策

## 1. 概要

Text Input Helperでは、次のホットキーを使用して定型文選択画面を表示している。

```python
HOTKEY = "ctrl+shift+space"
```

当初は `keyboard.add_hotkey()` を使用していたが、長時間使用するとホットキーが反応しなくなることがあった。

そのため、ホットキーの検出方法を次のようなポーリング方式へ変更した。

```python
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

この変更によって、ホットキーが長時間使用後に反応しなくなる問題は大きく改善した。

しかし、新たに次の問題が発生した。

> `Ctrl + Shift + Space` を押した瞬間、  
> Text Input Helperは正常に表示されるが、  
> 元のアプリケーションにもSpaceが入力されてしまう。

本資料では、この問題の原因と対策について整理する。

---

# 2. なぜSpaceが元アプリへ入力されるのか

重要なのは、

```python
keyboard.is_pressed("space")
```

は、

> Spaceキーが押されているかを確認する

ための処理であり、

> Spaceキーの入力を他のアプリへ送らない

ための処理ではないということである。

つまり、次の処理では、

```python
space = keyboard.is_pressed("space")
```

Python側がSpaceキーの状態を確認しているだけである。

Windowsから見れば、通常どおりSpaceキーが押されたことになる。

そのため、

```text
Ctrl + Shift + Space
        │
        ├── Windows
        │      ↓
        │   元アプリへSpaceを送る
        │
        └── Python
               ↓
        is_pressed("space")
               ↓
        ホットキー成立
               ↓
        Text Input Helperを表示
```

という動作になる。

つまり、

> ホットキーの検出

と

> キー入力の抑止

は別の処理である。

ここが今回の重要なポイントである。

---

# 3. 最初に試した対策

Spaceキーを元アプリへ送らないため、

```python
keyboard.block_key("space")
```

を利用することを考えた。

そこで、ホットキーを検出した直後にSpaceをブロックする方法を試した。

概念的には次のような処理である。

```python
if ctrl and shift and space:
    keyboard.block_key("space")
    show_window()
```

実際には、ブロック状態を管理するために次のようにした。

```python
def hotkey_worker() -> None:
    hotkey_pressed = False
    space_blocked = False

    while True:
        ctrl = keyboard.is_pressed("ctrl")
        shift = keyboard.is_pressed("shift")
        space = keyboard.is_pressed("space")

        if ctrl and shift and space:
            if not hotkey_pressed:
                hotkey_pressed = True

                if not space_blocked:
                    keyboard.block_key("space")
                    space_blocked = True

                show_window()

        else:
            hotkey_pressed = False

            if space_blocked:
                keyboard.unblock_key("space")
                space_blocked = False

        time.sleep(0.01)
```

しかし、この方法では問題を解決できなかった。

元アプリへSpaceが入力されてしまった。

---

# 4. なぜ最初の対策は失敗したのか

原因は処理の順番にある。

上記の方法では、

```text
Spaceを押す
    ↓
Space DOWNイベント発生
    ↓
元アプリがSpaceを受信
    ↓
PythonがSpace押下を検出
    ↓
keyboard.block_key("space")
```

という順番になる可能性がある。

例えば、概念的には次のようになる。

```text
0.000秒  Spaceキーを押す

0.002秒  Windowsが元アプリへSpaceを送る

0.007秒  Pythonがis_pressed("space")で検出

0.008秒  keyboard.block_key("space")を実行
```

この場合、

```python
keyboard.block_key("space")
```

を実行した時点では、

**すでにSpaceが元アプリへ届いている。**

つまり、

> Spaceが押されたことを確認してからSpaceを止める

のでは遅い。

---

# 5. 発想を変更する

そこで考え方を変更した。

ホットキーは、

```text
Ctrl + Shift + Space
```

である。

つまり、通常は、

```text
Ctrl
 ↓
Shift
 ↓
Space
```

という順番でキーが押される。

そこで、

> Ctrl + Shiftが押された時点で、  
> Spaceが押される前にSpaceをブロックする

という方法へ変更した。

これによってSpaceを「後から止める」のではなく、

**Spaceが押される前から待ち構える**

ことができる。

---

# 6. 改善版 hotkey_worker()

今回、良好な結果が得られたコードは次のとおり。

```python
def hotkey_worker() -> None:
    hotkey_pressed = False
    space_blocked = False

    while True:
        ctrl = keyboard.is_pressed("ctrl")
        shift = keyboard.is_pressed("shift")

        # Block Space in advance while Ctrl + Shift are pressed.
        if ctrl and shift:
            if not space_blocked:
                keyboard.block_key("space")
                space_blocked = True

            space = keyboard.is_pressed("space")

            if space:
                if not hotkey_pressed:
                    hotkey_pressed = True
                    show_window()
            else:
                hotkey_pressed = False

        else:
            hotkey_pressed = False

            if space_blocked:
                keyboard.unblock_key("space")
                space_blocked = False

        time.sleep(0.01)
```

---

# 7. 改善版の動作

改善版では、まず次の2キーを監視する。

```python
ctrl = keyboard.is_pressed("ctrl")
shift = keyboard.is_pressed("shift")
```

そして、

```python
if ctrl and shift:
```

が成立した時点で、

```python
keyboard.block_key("space")
```

を実行する。

したがって、処理の流れは次のようになる。

```text
Ctrlを押す
    ↓
Shiftを押す
    ↓
PythonがCtrl + Shiftを検出
    ↓
keyboard.block_key("space")
    ↓
Spaceを押す
    ↓
Spaceは元アプリへ送られない
    ↓
PythonではSpace押下を検出
    ↓
show_window()
    ↓
Text Input Helper表示
```

重要なのは、

```text
Spaceを押す
```

よりも前に、

```python
keyboard.block_key("space")
```

を実行していることである。

---

# 8. 失敗版と改善版の違い

## 失敗版

```text
Ctrl + Shift + Space
          ↓
     Spaceを検出
          ↓
     Spaceをブロック
```

これは、

> Spaceが発生してから止める

方式である。

そのため、元アプリへSpaceが届いた後にブロック処理が実行される可能性がある。

---

## 改善版

```text
Ctrl + Shift
     ↓
Spaceをブロック
     ↓
Spaceを押す
     ↓
ホットキー成立
```

こちらは、

> Spaceが発生する前に止める

方式である。

この違いが非常に重要である。

---

# 9. space_blocked変数の役割

次の変数を使用している。

```python
space_blocked = False
```

これは、

> 現在Spaceキーをブロックしているか

を管理するためのフラグである。

Ctrl + Shiftが押されたとき、

```python
if not space_blocked:
    keyboard.block_key("space")
    space_blocked = True
```

とする。

すでにSpaceをブロックしている場合には、

```python
keyboard.block_key("space")
```

を繰り返し実行しない。

---

# 10. Ctrl + Shiftを離したらSpaceを元に戻す

CtrlまたはShiftが離された場合は、

```python
else:
```

へ入る。

そして、

```python
if space_blocked:
    keyboard.unblock_key("space")
    space_blocked = False
```

を実行する。

これによって、通常のSpace入力が再び使用できるようになる。

処理のイメージは、

```text
Ctrl + Shift
    ↓
Space BLOCK
    ↓
ホットキー操作
    ↓
CtrlまたはShiftを離す
    ↓
Space UNBLOCK
    ↓
通常のSpace入力へ戻る
```

となる。

この解除処理は非常に重要である。

もし、

```python
keyboard.unblock_key("space")
```

を実行しなければ、Text Input Helper以外でもSpaceが使用できなくなる可能性がある。

---

# 11. hotkey_pressedが必要な理由

もう一つ重要なのが、

```python
hotkey_pressed = False
```

である。

ポーリングは、

```python
while True:
```

によって何度も繰り返される。

例えば、

```python
time.sleep(0.01)
```

なら、概算では1秒間に最大100回程度状態を確認する。

そのため、Ctrl + Shift + Spaceを0.5秒間押し続けただけでも、

```text
検出
検出
検出
検出
検出
...
```

となる。

そのたびに、

```python
show_window()
```

を実行するのは望ましくない。

そこで、

```python
if space:
    if not hotkey_pressed:
        hotkey_pressed = True
        show_window()
```

としている。

最初の検出時に、

```python
hotkey_pressed = True
```

となるため、その後Spaceを押し続けても `show_window()` は再実行されない。

Spaceを離すと、

```python
else:
    hotkey_pressed = False
```

となる。

これによって、

```text
Space DOWN
    ↓
1回だけshow_window()

Spaceを押し続ける
    ↓
何もしない

Space UP
    ↓
hotkey_pressed = False

次のSpace DOWN
    ↓
再び1回だけshow_window()
```

という動作になる。

---

# 12. sleepを0.01秒にした理由

当初は、

```python
time.sleep(0.05)
```

としていた。

これは50ms間隔である。

今回のようなキー入力制御では、できるだけ早く、

```text
Ctrl + Shift
```

を検出して、

```python
keyboard.block_key("space")
```

を実行したい。

そのため、

```python
time.sleep(0.01)
```

へ変更した。

これは10ms間隔である。

概念的には、

```text
0 ms
10 ms
20 ms
30 ms
40 ms
...
```

という間隔でキー状態を確認する。

ただし、PythonやWindowsのスケジューリングなどの影響があるため、厳密に10ms周期で実行されることを保証するものではない。

今回の用途では、反応速度とCPU負荷のバランスを取るための値として使用している。

---

# 13. 現在のText Input Helperの構成

今回の改良によって、Text Input Helperは複数の仕組みを役割分担して使用する構成になった。

```text
Text Input Helper
│
├─ Tkinter
│   │
│   └─ 定型文選択GUI
│
├─ メインスレッド
│   │
│   └─ root.mainloop()
│
├─ サブスレッド
│   │
│   └─ hotkey_worker()
│
├─ keyboard.is_pressed()
│   │
│   └─ ホットキー状態をポーリング監視
│
├─ keyboard.block_key()
│   │
│   └─ Spaceを元アプリへ送らない
│
├─ keyboard.unblock_key()
│   │
│   └─ Space入力を通常状態へ戻す
│
└─ root.after()
    │
    └─ Tkinter操作をメインスレッドへ依頼
```

それぞれに明確な役割がある。

---

# 14. ポーリングとフックを組み合わせている

今回の構成で特に興味深い点は、

> すべてを一つの方法で解決しようとしていない

ことである。

ホットキーの検出については、

```python
keyboard.is_pressed()
```

を使ったポーリング方式を採用している。

一方、

> Spaceを他のアプリへ送らない

という処理には、

```python
keyboard.block_key()
```

を使用している。

つまり、

```text
ホットキー検出
    ↓
ポーリング

キー入力抑止
    ↓
keyboardのフック機能
```

という役割分担になっている。

---

# 15. 今回の重要な教訓

今回の問題から得られた重要な考え方は、

> イベントが発生してから止めるのでは遅い場合がある

ということである。

失敗版では、

```text
Space発生
    ↓
Space検出
    ↓
Space抑止
```

だった。

改善版では、

```text
Ctrl + Shift検出
    ↓
Space抑止を準備
    ↓
Space発生
```

へ変更した。

これはホットキー処理だけに限定されない。

リアルタイム処理では、

```text
発生
↓
検出
↓
対処
```

では間に合わない場合、

```text
前兆を検出
↓
対処を準備
↓
イベント発生
```

という設計が有効になることがある。

今回のケースでは、

```text
Ctrl + Shift
```

を、

> Spaceが押される前兆

として利用したことになる。

---

# 16. 今後確認すべきこと

今回の修正では、短時間のテストでは正常に動作している。

ただし、グローバルキーボード入力を扱う処理なので、長時間テストも行った方がよい。

特に次の点を確認する。

- 長時間起動後もホットキーが反応すること
- 何十回、何百回使用しても反応すること
- 元アプリへSpaceが入力されないこと
- 通常時のSpace入力に影響しないこと
- Ctrl + Shiftを離した後、Spaceが正常に使用できること
- Ctrl、Shift、Spaceを通常と異なる順番で押した場合の挙動
- ホットキーを長押しした場合の挙動

---

# 17. 注意点

今回の方法では、

```text
Ctrl + Shift
```

が押されている間、

```python
keyboard.block_key("space")
```

によってSpaceをブロックしている。

したがって、Text Input Helperを呼び出す目的ではなく、

```text
Ctrl + Shift + Space
```

というキー操作を別アプリで使用したい場合にも影響する可能性がある。

これは今回の方式のトレードオフである。

つまり、

> Ctrl + Shiftを押している間のSpaceはText Input Helper専用

に近い扱いになる。

自分専用PCで、このキーコンビネーションを他の用途に使用しないのであれば、実用上問題にならない可能性が高い。

---

# 18. まとめ

今回の問題は、

```python
keyboard.is_pressed()
```

がキー状態を確認するだけで、キー入力そのものを抑止しないことから発生した。

最初は、

```text
Spaceを検出
↓
Spaceをブロック
```

という方法を試したが、Spaceがすでに元アプリへ届いているため間に合わなかった。

そこで、

```text
Ctrl + Shiftを検出
↓
Spaceを事前にブロック
↓
Spaceを押す
↓
ホットキー成立
```

という方式へ変更した。

改善版の中心となる処理は次のとおりである。

```python
def hotkey_worker() -> None:
    hotkey_pressed = False
    space_blocked = False

    while True:
        ctrl = keyboard.is_pressed("ctrl")
        shift = keyboard.is_pressed("shift")

        # Block Space in advance while Ctrl + Shift are pressed.
        if ctrl and shift:
            if not space_blocked:
                keyboard.block_key("space")
                space_blocked = True

            space = keyboard.is_pressed("space")

            if space:
                if not hotkey_pressed:
                    hotkey_pressed = True
                    show_window()
            else:
                hotkey_pressed = False

        else:
            hotkey_pressed = False

            if space_blocked:
                keyboard.unblock_key("space")
                space_blocked = False

        time.sleep(0.01)
```

今回の最も重要なポイントは、

> **Spaceを押してから止めるのではなく、Spaceを押す前に止めておく**

ことである。

この考え方によって、

```text
安定したホットキー検出
+
元アプリへのSpace入力防止
```

の両立を狙うことができた。

---

## 一言で覚える

```text
is_pressed()
    = 押されたことを「見る」

block_key()
    = キー入力を「止める」
```

そして、

```text
押されてから止める
    → 遅い

押される前に止める
    → 今回の解決策
```

これが今回の不具合対策の核心である。
