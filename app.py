# ========================================================================
# Create a shortcut to run.bat in the ALIAS folder on the desktop.
# Rename the shortcut to "txt".
# You can then run this application from Win + R using the "txt" command.
# The ALIAS folder must be included in the PATH environment variable.
# ========================================================================
import json
import subprocess
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
BASE_DIR = Path(__file__).resolve().parent
PHRASES_PATH = BASE_DIR / "phrases.json"

WINDOW_WIDTH = 500
BASE_WINDOW_HEIGHT = 160
HEIGHT_PER_PHRASE = 18


# ================================================
#   Load phrases
# ================================================
def load_phrases(path: Path) -> list[dict]:
    """Load phrase settings from a JSON file."""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


PHRASES: list[dict] = load_phrases(PHRASES_PATH)


# ================================================
#   Select phrase
# ================================================
def on_shift(event=None) -> None:
    """Move to the previous phrase number."""
    value = entry.get().strip()

    if not value.isdigit():
        number = 1
    else:
        number = max(int(value) - 1, 1)

    entry.delete(0, tk.END)
    entry.insert(0, str(number))


def on_ctrl(event=None) -> None:
    """Move to the next phrase number."""
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
    """Copy text to the clipboard and paste it."""
    pyperclip.copy(text)

    # Hide the window before pasting.
    root.withdraw()

    # Wait for focus to return to the previous window.
    time.sleep(0.2)

    keyboard.press_and_release("ctrl+v")


# ================================================
#   Show window
# ================================================
def show_window() -> None:
    """Request the Tkinter main thread to show the window."""
    root.after(0, _show_window)


def _show_window() -> None:
    """Show the phrase selection window."""
    center_window()

    # Show the hidden window.
    root.deiconify()
    # Bring the window to the front.
    root.lift()
    # Keep the window on top of other windows.
    root.attributes("-topmost", True)

    entry.delete(0, tk.END)
    entry.focus_force()


def center_window() -> None:
    """Move the window to the center of the screen."""
    # Apply pending window layout updates.
    root.update_idletasks()

    window_width = root.winfo_width()
    window_height = root.winfo_height()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    root.geometry(f"+{x}+{y}")


# ================================================
#   Escape key
# ================================================
def on_escape(event=None) -> None:
    """Hide the window when Escape is pressed."""
    entry.delete(0, tk.END)
    root.withdraw()


# ================================================
#   Close window
# ================================================
def on_close() -> None:
    """Hide the window instead of closing the application."""
    root.withdraw()


# ================================================
#   Enter key
# ================================================
def on_enter(event=None) -> None:
    """Create and paste the selected phrase."""
    value = entry.get().strip()

    if not value.isdigit():
        return

    # Open phrases.json with Notepad.
    if value == "999":
        entry.delete(0, tk.END)
        root.withdraw()

        subprocess.Popen(
            ["notepad.exe", str(PHRASES_PATH)]
        )
        return

    index = int(value) - 1

    if not 0 <= index < len(PHRASES):
        return

    phrase = PHRASES[index]

    # Generate today's date dynamically.
    if phrase["name"] == "TODAY_YYYY/MM/DD":
        text = datetime.now().strftime("%Y/%m/%d")

    # Generate a folder name using the clipboard text.
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
def hotkey_worker() -> None:
    """
    Monitor Ctrl + Shift + Space.

    Space is blocked before it is pressed so that the Space key
    is not sent to the active application.
    """
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

            # Trigger only once while the hotkey is held down.
            if space and not hotkey_pressed:
                hotkey_pressed = True
                show_window()

            elif not space:
                hotkey_pressed = False

        else:
            hotkey_pressed = False

            # Restore the Space key when Ctrl + Shift are released.
            if space_blocked:
                keyboard.unblock_key("space")
                space_blocked = False

        # Reduce CPU usage while keeping good responsiveness.
        time.sleep(0.01)


# ================================================
#   Tkinter UI
# ================================================
root = tk.Tk()
root.withdraw()

root.title("Text Input Helper")

window_height = (
    BASE_WINDOW_HEIGHT
    + len(PHRASES) * HEIGHT_PER_PHRASE
)
root.geometry(f"{WINDOW_WIDTH}x{window_height}")

root.protocol("WM_DELETE_WINDOW", on_close)

# Title and input area
input_frame = tk.Frame(root)
input_frame.pack(
    fill="x",
    padx=30,
    pady=(20, 10),
)

title_label = tk.Label(
    input_frame,
    text="定型文を選択してください",
    font=("Yu Gothic UI", 14),
)
title_label.pack(side="left")

entry = tk.Entry(
    input_frame,
    font=("Consolas", 14),
    width=4,
    justify="center",
)
entry.pack(
    side="left",
    padx=(15, 0),
)
entry.bind("<Return>", on_enter)
entry.bind("<space>", on_enter)
entry.bind("<Escape>", on_escape)
entry.bind("<Shift_L>", on_shift)
entry.bind("<Control_L>", on_ctrl)



for index, phrase in enumerate(PHRASES, start=1):
    label = tk.Label(
        root,
        text=f'{index}) {phrase["name"]}',
        anchor="w",
        font=("Yu Gothic UI", 11),
    )
    label.pack(fill="x", padx=30, pady=2)






# ================================================
#   Start hotkey worker
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
print("Hotkey: Ctrl + Shift + SPACE")
print()
print("Press the hotkey to open the phrase selection window.")
print()
print("Enter 999 to edit phrases.json.")
print()
print("To exit the application, close this console window.")
print()
print("=" * 50)


# ================================================
#   Main loop
# ================================================
root.mainloop()