import json
import time
from typing import List, Tuple, Union, Optional
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

# 新增：智能执行器（加法扩展，不影响原逻辑）
try:
    from smart.runtime import SmartExecutor  # type: ignore
except Exception:
    SmartExecutor = None  # 允许未安装时仍可运行传统功能


class KeyMouseRecorder:
    """键盘鼠标操作记录器类，实现录制和回放功能"""

    def __init__(self):
        self.recorded_events: List[Tuple] = []  # 存储记录的事件列表
        self.start_time: Optional[float] = None  # 记录开始的时间戳
        self.is_recording: bool = False  # 记录状态标志
        self.is_playing: bool = False  # 回放状态标志
        self.keyboard_listener: Optional[keyboard.Listener] = None  # 键盘监听器
        self.mouse_listener: Optional[mouse.Listener] = None  # 鼠标监听器
        self.stop_playback_flag = False  # 停止回放标志

    def on_press(self, key: Union[Key, KeyCode, None]) -> None:
        """键盘按键按下事件处理"""
        if not self.is_recording or key is None:
            return

        timestamp = time.time() - self.start_time  # type: ignore

        if isinstance(key, KeyCode):
            self.recorded_events.append(('key_press', key.char, timestamp))
        elif isinstance(key, Key):
            self.recorded_events.append(('key_press', key.name, timestamp))

    def on_release(self, key: Union[Key, KeyCode, None]) -> None:
        """键盘按键释放事件处理"""
        if not self.is_record录 or key is None:
            return

        timestamp = time.time() - self.start_time  # type: ignore

        if isinstance(key, KeyCode):
            self.recorded_events.append(('key_release', key.char, timestamp))
        elif isinstance(key, Key):
            self.recorded_events.append(('key_release', key.name, timestamp))

    def on_move(self, x: int, y: int) -> None:
        """鼠标移动事件处理"""
        if not self.is_recording:
            return

        timestamp = time.time() - self.start_time  # type: ignore
        self.recorded_events.append(('mouse_move', (x, y), timestamp))

    def on_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        """鼠标点击事件处理"""
        if not self.is_recording:
            return

        timestamp = time.time() - self.start_time  # type: ignore
        action = 'mouse_press' if pressed else 'mouse_release'
        self.recorded_events.append((action, button.name, (x, y), timestamp))

    def start_recording(self) -> None:
        """开始记录键盘鼠标操作"""
        self.recorded_events = []
        self.is_recording = True
        self.start_time = time.time()

        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.keyboard_listener.start()

        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click)
        self.mouse_listener.start()

    def stop_recording(self) -> None:
        """停止记录操作"""
        self.is_recording = False
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

    def save_recording(self, filename: str) -> None:
        with open(filename, 'w') as f:
            json.dump(self.recorded_events, f)

    def load_recording(self, filename: str) -> None:
        with open(filename, 'r') as f:
            self.recorded_events = json.load(f)

    def _find_matching_end_guard(self, start_index: int) -> Optional[int]:
        """
        从 start_index 之后寻找与之配对的 smart_end_guard 的下标（支持嵌套）。
        返回“end_guard 的下一个事件 index”（跳转点）。找不到则返回 None。
        """
        depth = 1
        i = start_index + 1
        n = len(self.recorded_events)
        while i < n:
            ev = self.recorded_events[i]
            et = ev[0] if isinstance(ev, (list, tuple)) and ev else None
            if et == "smart_if_guard_ocr":
                depth += 1
            elif et == "smart_end_guard":
                depth -= 1
                if depth == 0:
                    return i + 1  # 跳到 end_guard 的后一个事件
            i += 1
        return None

    def play_recording(self, speed: float = 1.0) -> None:
        """回放记录的操作（支持 smart_* 与 IF 守护）"""
        if not self.recorded_events:
            return

        self.is_playing = True
        self.stop_playback_flag = False

        keyboard_ctrl = KeyboardController()
        mouse_ctrl = MouseController()

        smart = SmartExecutor() if SmartExecutor is not None else None

        # 改为索引式循环，便于“跳过一段”
        i = 0
        n = len(self.recorded_events)
        last_timestamp = 0.0

        # 活动的 IF 守护（最多一个即可满足当前需求；若需多层可扩展为栈）
        active_guard = None  # dict: {"end_index": int, "next_check": float, "interval": float, "payload": dict}

        while i < n:
            if self.stop_playback_flag:
                break

            event = self.recorded_events[i]
            if not isinstance(event, (list, tuple)) or not event:
                i += 1
                continue

            etype = event[0]
            current_timestamp = event[-1]
            # 守护在区间内：按 interval 周期评估，一旦命中就直接跳转
            if active_guard and i < active_guard["end_index"]:
                if smart is not None and time.time() >= active_guard["next_check"]:
                    if smart.condition_met(active_guard["payload"]):
                        # 跳到 end_guard 之后，并把 last_timestamp 对齐到跳转点，避免额外等待
                        jump_to = active_guard["end_index"]
                        if jump_to < n:
                            last_timestamp = self.recorded_events[jump_to][-1]
                        i = jump_to
                        active_guard = None
                        continue
                    else:
                        active_guard["next_check"] = time.time() + active_guard["interval"]
                # 没命中就继续照常执行当前事件
            else:
                # 已经离开守护区间
                active_guard = None

            # 常规“按时间轴”延迟（保证原有时序）
            delay = (current_timestamp - last_timestamp) / speed
            if delay > 0:
                time.sleep(delay)
            last_timestamp = current_timestamp

            # IF 守护起点：记录区间与条件，不阻塞执行
            if etype == "smart_if_guard_ocr":
                if smart is not None and isinstance(event[1], dict):
                    end_index = self._find_matching_end_guard(i)
                    if end_index is not None:
                        payload = dict(event[1])
                        interval = float(payload.get("interval", 0.3))
                        active_guard = {
                            "end_index": end_index,
                            "next_check": 0.0,
                            "interval": interval,
                            "payload": payload
                        }
                i += 1
                continue

            # IF 守护终点：占位事件，不做动作
            if etype == "smart_end_guard":
                active_guard = None
                i += 1
                continue

            # 智能事件：以 smart_ 开头，交给 SmartExecutor 处理
            if smart is not None and isinstance(etype, str) and etype.startswith("smart_") and etype not in ("smart_if_guard_ocr",):
                try:
                    smart.handle(list(event))
                except Exception:
                    pass
                i += 1
                continue

            # 以下为原有坐标/键盘事件，保持不变
            if etype == 'key_press':
                key = event[1]
                try:
                    key_obj = getattr(Key, key)
                except AttributeError:
                    key_obj = key
                keyboard_ctrl.press(key_obj)

            elif etype == 'key_release':
                key = event[1]
                try:
                    key_obj = getattr(Key, key)
                except AttributeError:
                    key_obj = key
                keyboard_ctrl.release(key_obj)

            elif etype == 'mouse_move':
                x, y = event[1]
                mouse_ctrl.position = (x, y)

            elif etype == 'mouse_press':
                button = getattr(Button, event[1])
                x, y = event[2]
                mouse_ctrl.position = (x, y)
                mouse_ctrl.press(button)

            elif etype == 'mouse_release':
                button = getattr(Button, event[1])
                x, y = event[2]
                mouse_ctrl.position = (x, y)
                mouse_ctrl.release(button)

            i += 1

        self.is_playing = False

    def stop_playback(self) -> None:
        self.stop_playback_flag = True
        self.is_playing = False

    def clear_recording(self) -> None:
        self.recorded_events = []
        self.stop_playback_flag = True
        self.is_playing = False
        self.is_recording = False