import json
import time
from typing import List, Tuple, Union, Optional
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

# 智能执行器（可选）
try:
    from smart.runtime import SmartExecutor  # type: ignore
except Exception:
    SmartExecutor = None


class KeyMouseRecorder:
    """键盘鼠标操作记录器类，实现录制和回放功能"""

    def __init__(self):
        self.recorded_events: List[Tuple] = []
        self.start_time: Optional[float] = None
        self.is_recording: bool = False
        self.is_playing: bool = False
        self.keyboard_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None
        self.stop_playback_flag = False

    def on_press(self, key: Union[Key, KeyCode, None]) -> None:
        if not self.is_recording or key is None:
            return
        timestamp = time.time() - self.start_time  # type: ignore
        if isinstance(key, KeyCode):
            self.recorded_events.append(('key_press', key.char, timestamp))
        elif isinstance(key, Key):
            self.recorded_events.append(('key_press', key.name, timestamp))

    def on_release(self, key: Union[Key, KeyCode, None]) -> None:
        if not self.is_recording or key is None:
            return
        timestamp = time.time() - self.start_time  # type: ignore
        if isinstance(key, KeyCode):
            self.recorded_events.append(('key_release', key.char, timestamp))
        elif isinstance(key, Key):
            self.recorded_events.append(('key_release', key.name, timestamp))

    def on_move(self, x: int, y: int) -> None:
        if not self.is_recording:
            return
        timestamp = time.time() - self.start_time  # type: ignore
        self.recorded_events.append(('mouse_move', (x, y), timestamp))

    def on_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        if not self.is_recording:
            return
        timestamp = time.time() - self.start_time  # type: ignore
        action = 'mouse_press' if pressed else 'mouse_release'
        self.recorded_events.append((action, button.name, (x, y), timestamp))

    def start_recording(self) -> None:
        self.recorded_events = []
        self.is_recording = True
        self.start_time = time.time()
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release); self.keyboard_listener.start()
        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click); self.mouse_listener.start()

    def stop_recording(self) -> None:
        self.is_recording = False
        if self.keyboard_listener: self.keyboard_listener.stop()
        if self.mouse_listener: self.mouse_listener.stop()

    def save_recording(self, filename: str) -> None:
        with open(filename, 'w') as f:
            json.dump(self.recorded_events, f)

    def load_recording(self, filename: str) -> None:
        with open(filename, 'r') as f:
            self.recorded_events = json.load(f)

    # —— 内部工具 ——
    def _exec_event_immediate(self, ev, keyboard_ctrl, mouse_ctrl, smart) -> None:
        """立即执行一条事件，不基于全局时间轴延迟（延迟由调用方控制）"""
        et = ev[0]
        if smart is not None and isinstance(et, str) and et.startswith("smart_") and et not in ("smart_if_guard_ocr", "smart_end_guard", "smart_while_ocr"):
            try:
                smart.handle(list(ev))
            except Exception:
                pass
            return

        if et == 'key_press':
            key = ev[1]
            try: key_obj = getattr(Key, key)
            except AttributeError: key_obj = key
            keyboard_ctrl.press(key_obj)
        elif et == 'key_release':
            key = ev[1]
            try: key_obj = getattr(Key, key)
            except AttributeError: key_obj = key
            keyboard_ctrl.release(key_obj)
        elif et == 'mouse_move':
            x, y = ev[1]
            mouse_ctrl.position = (x, y)
        elif et == 'mouse_press':
            button = getattr(Button, ev[1]); x, y = ev[2]
            mouse_ctrl.position = (x, y); mouse_ctrl.press(button)
        elif et == 'mouse_release':
            button = getattr(Button, ev[1]); x, y = ev[2]
            mouse_ctrl.position = (x, y); mouse_ctrl.release(button)
        # IF/END 标记在这里不做动作

    def _run_while_block(self, payload: dict, keyboard_ctrl, mouse_ctrl, smart, speed: float = 1.0) -> None:
        """
        执行 while 块:
          - payload: {
              keywords, region, interval, prefer_area,
              max_duration, max_loops,
              children: [ [event,..., t_rel], ... ]
            }
          - 按 children 内的相对时间执行一轮；轮与轮之间立即衔接
          - 在执行中每 interval 秒检查一次条件；命中即结束
        """
        if smart is None:
            return
        cond_payload = {
            "keywords": payload.get("keywords", []),
            "region": payload.get("region"),
            "prefer_area": payload.get("prefer_area", "bottom"),
            "require_green": bool(payload.get("require_green", False)),
        }
        interval = float(payload.get("interval", 0.3))
        max_duration = float(payload.get("max_duration", 30.0))
        max_loops = int(payload.get("max_loops", 200))
        children = payload.get("children", [])

        start_time = time.time()
        next_check = 0.0
        loops = 0

        # 若一开始就满足条件，直接返回
        try:
            if smart.condition_met(cond_payload):
                return
        except Exception:
            pass

        while True:
            if self.stop_playback_flag:
                break
            now = time.time()
            if max_duration > 0 and (now - start_time) >= max_duration:
                break
            if loops >= max_loops:
                break

            prev_t = None
            for ev in children:
                if self.stop_playback_flag:
                    break

                # 条件周期检查
                if time.time() >= next_check:
                    try:
                        if smart.condition_met(cond_payload):
                            return
                    except Exception:
                        pass
                    next_check = time.time() + interval

                # 相对延迟
                t_rel = float(ev[-1])
                if prev_t is None:
                    delay = t_rel / max(speed, 1e-6)
                else:
                    delay = (t_rel - prev_t) / max(speed, 1e-6)
                if delay > 0:
                    time.sleep(delay)
                prev_t = t_rel

                # 执行事件本体
                self._exec_event_immediate(ev, keyboard_ctrl, mouse_ctrl, smart)

            # 轮结束后再检查一次
            try:
                if smart.condition_met(cond_payload):
                    return
            except Exception:
                pass

            loops += 1

    # —— IF 配对查找（已存在） ——
    def _find_matching_end_guard(self, start_index: int) -> Optional[int]:
        depth = 1; i = start_index + 1; n = len(self.recorded_events)
        while i < n:
            ev = self.recorded_events[i]
            et = ev[0] if isinstance(ev, (list, tuple)) and ev else None
            if et == "smart_if_guard_ocr":
                depth += 1
            elif et == "smart_end_guard":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return None

    def play_recording(self, speed: float = 1.0) -> None:
        if not self.recorded_events:
            return

        self.is_playing = True
        self.stop_playback_flag = False

        keyboard_ctrl = KeyboardController()
        mouse_ctrl = MouseController()

        smart = SmartExecutor() if SmartExecutor is not None else None

        i = 0; n = len(self.recorded_events)
        last_timestamp = 0.0
        active_guard = None  # IF 区间守护

        while i < n:
            if self.stop_playback_flag:
                break
            event = self.recorded_events[i]
            if not isinstance(event, (list, tuple)) or not event:
                i += 1; continue

            etype = event[0]
            current_timestamp = event[-1]

            # IF 区间内周期判断
            if active_guard and i < active_guard["end_index"]:
                if smart is not None and time.time() >= active_guard["next_check"]:
                    if smart.condition_met(active_guard["payload"]):
                        jump_to = active_guard["end_index"]
                        if jump_to < n:
                            last_timestamp = self.recorded_events[jump_to][-1]
                        i = jump_to; active_guard = None; continue
                    else:
                        active_guard["next_check"] = time.time() + active_guard["interval"]
            else:
                active_guard = None

            # 常规基于时间轴的延迟
            delay = (current_timestamp - last_timestamp) / max(speed, 1e-6)
            if delay > 0:
                time.sleep(delay)
            last_timestamp = current_timestamp

            # IF 守护开始
            if etype == "smart_if_guard_ocr":
                if smart is not None and isinstance(event[1], dict):
                    end_index = self._find_matching_end_guard(i)
                    if end_index is not None:
                        payload = dict(event[1])
                        interval = float(payload.get("interval", 0.3))
                        active_guard = {"end_index": end_index, "next_check": 0.0, "interval": interval, "payload": payload}
                i += 1; continue

            # IF 守护结束
            if etype == "smart_end_guard":
                active_guard = None; i += 1; continue

            # WHILE 块执行（新）
            if etype == "smart_while_ocr":
                if smart is not None and isinstance(event[1], dict):
                    try:
                        self._run_while_block(event[1], keyboard_ctrl, mouse_ctrl, smart, speed)
                    except Exception:
                        pass
                i += 1; continue

            # 其它 smart_* 事件
            if smart is not None and isinstance(etype, str) and etype.startswith("smart_"):
                try:
                    smart.handle(list(event))
                except Exception:
                    pass
                i += 1; continue

            # 原有事件
            if etype == 'key_press':
                key = event[1]
                try: key_obj = getattr(Key, key)
                except AttributeError: key_obj = key
                keyboard_ctrl.press(key_obj)
            elif etype == 'key_release':
                key = event[1]
                try: key_obj = getattr(Key, key)
                except AttributeError: key_obj = key
                keyboard_ctrl.release(key_obj)
            elif etype == 'mouse_move':
                x, y = event[1]; mouse_ctrl.position = (x, y)
            elif etype == 'mouse_press':
                button = getattr(Button, event[1]); x, y = event[2]
                mouse_ctrl.position = (x, y); mouse_ctrl.press(button)
            elif etype == 'mouse_release':
                button = getattr(Button, event[1]); x, y = event[2]
                mouse_ctrl.position = (x, y); mouse_ctrl.release(button)

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