# ========================================================================
# Create a shortcut to run.bat in the ALIAS folder on the desktop.
# Rename the shortcut to "txt".
# You can then run this application from Win + R using the "txt" command.
# The ALIAS folder must be included in the PATH environment variable.
# ========================================================================
import json
import time
import tkinter as tk
from datetime import datetime
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
def load_phrases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


PHRASES: list[dict] = load_phrases(PHRASES_PATH)


# ================================================
#   Select phrase
# ================================================
def on_shift(event=None) -> None:
    value = entry.get().strip()

    if not value.isdigit():
        number = 1
    else:
        number = max(int(value) - 1, 1)
    

    entry.delete(0, tk.END)
    entry.insert(0, str(number))


def on_ctrl(event=None) -> None:
    value = entry.get().strip()

    if not value.isdigit():
        number = 1
    else:
        number = min(int(value) + 1, len(PHRASES))

    entry.delete(0, tk.END)
    entry.insert(0, str(number))


# ================================================
#   Paste phrase
# ================================================
def paste_phrase(text: str) -> None:
    pyperclip.copy(text)

    root.withdraw()

    time.sleep(0.2)

    keyboard.press_and_release("ctrl+v")


# ================================================
#   Show window
# ================================================
def show_window() -> None:
    print("Hotkey detected.")   # For troubleshooting
    root.after(0, _show_window)


def _show_window() -> None:
    print("Showing window.")    # For troubleshooting

    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)

    entry.delete(0, tk.END)
    entry.focus_force()


# ================================================
#   Escape key
# ================================================
def on_escape(event=None) -> None:
    entry.delete(0, tk.END)
    root.withdraw()


# ================================================
#   Close window
# ================================================
def on_close() -> None:
    root.withdraw()


# ================================================
#   Enter key
# ================================================
def on_enter(event=None) -> None:
    value = entry.get().strip()

    if not value.isdigit():
        return

    index = int(value) - 1

    if not 0 <= index < len(PHRASES):
        return

    phrase = PHRASES[index]

    if phrase["name"] == "TODAY_YYYY/MM/DD":
        text = datetime.now().strftime("%Y/%m/%d")

    elif phrase["name"] == "FOLDER_NAME":
        clipboard_text = pyperclip.paste()

        if isinstance(clipboard_text, str) and clipboard_text:
            date_text = datetime.now().strftime("%Y%m%d")
            text = f"{date_text}_{clipboard_text}→【途中】"
        else:
            text = ""

    else:
        text = phrase["text"]

    entry.delete(0, tk.END)

    paste_phrase(text)


# ================================================
#   Hotkey
# ================================================
# def hotkey_worker() -> None:
#     hotkey_pressed = False

#     while True:
#         ctrl = keyboard.is_pressed("ctrl")
#         shift = keyboard.is_pressed("shift")
#         space = keyboard.is_pressed("space")

#         if ctrl and shift and space:
#             if not hotkey_pressed:
#                 hotkey_pressed = True
#                 show_window()
#         else:
#             hotkey_pressed = False

#         time.sleep(0.05)
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

# ================================================
#   Tkinter UI
# ================================================
root = tk.Tk()
root.withdraw()

root.title("Text Input Helper")
root.geometry("500x350")
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
    label.pack(fill="x", padx=30, pady=2)

entry = tk.Entry(
    root,
    font=("Consolas", 14),
    width=10,
)
entry.pack(pady=20)
entry.bind("<Return>", on_enter)
entry.bind("<space>", on_enter)
entry.bind("<Escape>", on_escape)
entry.bind("<Shift_L>", on_shift)
entry.bind("<Control_L>", on_ctrl)


# ================================================
#   Start application
# ================================================
thread = Thread(
    target=hotkey_worker,
    daemon=True,
)
thread.start()


# ================================================
#   Terminal message
# ================================================
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


# ================================================
#   Main loop
# ================================================
root.mainloop()

