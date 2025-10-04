import time
from typing import Optional, Tuple
import numpy as np
import mss
import pyautogui

Region = Tuple[int, int, int, int]  # left, top, width, height

def grab(region: Optional[Region] = None) -> np.ndarray:
    with mss.mss() as sct:
        if region:
            l, t, w, h = region
            monitor = {"left": l, "top": t, "width": w, "height": h}
        else:
            monitor = sct.monitors[1]
        img = np.asarray(sct.grab(monitor))
    return img[:, :, :3]  # BGRA -> BGR

def to_screen(point: Tuple[int, int], region: Optional[Region]) -> Tuple[int, int]:
    if not region:
        return point
    l, t, _, _ = region
    return (l + point[0], t + point[1])

def move_click(x: int, y: int, button: str = "left", move_duration: float = 0.08):
    pyautogui.moveTo(x, y, duration=move_duration)
    if button == "left":
        pyautogui.click()
    elif button == "right":
        pyautogui.click(button="right")
    elif button == "middle":
        pyautogui.click(button="middle")
    else:
        pyautogui.click()

def scroll(amount: int):
    # pyautogui.scroll: 正=上, 负=下
    pyautogui.scroll(amount)

def key_press(key: str):
    pyautogui.press(key)

def wait(seconds: float):
    if seconds > 0:
        time.sleep(seconds)