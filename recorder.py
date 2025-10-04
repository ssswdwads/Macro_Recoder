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
    """键盘鼠标操作记录器类，实现录制和回放功能（含滚轮/IF/WHILE/智能识别）"""

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

    # 新增：滚轮事件
    def on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """
        记录滚轮滚动；dy>0 表示向上，dy<0 表示向下（pynput 约定）
        事件格式（保存为 list 时）统一在回放前转换，这里保持 tuple 兼容：
          ('mouse_scroll', (dx, dy), (x, y), t)
        """
        if not self.is_recording:
            return
        timestamp = time.time() - self.start_time  # type: ignore
        self.recorded_events.append(('mouse_scroll', (int(dx), int(dy)), (x, y), timestamp))

    def start_recording(self) -> None:
        self.recorded_events = []
        self.is_recording = True
        self.start_time = time.time()
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.keyboard_listener.start()
        # 监听滚轮 on_scroll
        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll)
        self.mouse_listener.start()

    def stop_recording(self) -> None:
        self.is_recording = False
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

    def save_recording(self, filename: str) -> None:
        # 将 tuple 统一转换为 list，便于 JSON 序列化
        serializable = []
        for e in self.recorded_events:
            if isinstance(e, tuple):
                serializable.append(list(e))
            else:
                serializable.append(e)
        with open(filename, 'w') as f:
            json.dump(serializable, f)

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
            try:
                key_obj = getattr(Key, key)
            except AttributeError:
                key_obj = key
            keyboard_ctrl.press(key_obj)

        elif et == 'key_release':
            key = ev[1]
            try:
                key_obj = getattr(Key, key)
            except AttributeError:
                key_obj = key
            keyboard_ctrl.release(key_obj)

        elif et == 'mouse_move':
            x, y = ev[1]
            mouse_ctrl.position = (x, y)

        elif et == 'mouse_press':
            button = getattr(Button, ev[1])
            x, y = ev[2]
            mouse_ctrl.position = (x, y)
            mouse_ctrl.press(button)

        elif et == 'mouse_release':
            button = getattr(Button, ev[1])
            x, y = ev[2]
            mouse_ctrl.position = (x, y)
            mouse_ctrl.release(button)

        elif et == 'mouse_scroll':
            # ev: ["mouse_scroll", [dx, dy], [x, y], t]
            dx, dy = ev[1]
            x, y = ev[2]
            # 大多数网页不要求定位，但为兼容某些控件，这里先移动到位置再滚动
            mouse_ctrl.position = (x, y)
            try:
                mouse_ctrl.scroll(int(dx), int(dy))
            except Exception:
                # 某些平台 dx 不支持，保底只滚动垂直
                mouse_ctrl.scroll(0, int(dy))

    def _run_while_block(self, payload: dict, keyboard_ctrl, mouse_ctrl, smart, speed: float = 1.0) -> None:
        """
        执行 while 块:
          - payload: {
              keywords, region, interval, prefer_area,
              max_duration, max_loops,
              children: [ [event,..., t_rel], ... ]
            }
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

        # 首次检查
        try:
            if smart.condition_met(cond_payload):
                return
        except Exception:
            pass

        while True:
            if self.stop_playback_flag:
                break
            if max_duration > 0 and (time.time() - start_time) >= max_duration:
                break
            if loops >= max_loops:
                break

            prev_t = None
            for ev in children:
                if self.stop_playback_flag:
                    break

                if time.time() >= next_check:
                    try:
                        if smart.condition_met(cond_payload):
                            return
                    except Exception:
                        pass
                    next_check = time.time() + interval

                t_rel = float(ev[-1])
                if prev_t is None:
                    delay = t_rel / max(speed, 1e-6)
                else:
                    delay = (t_rel - prev_t) / max(speed, 1e-6)
                if delay > 0:
                    time.sleep(delay)
                prev_t = t_rel

                self._exec_event_immediate(ev, keyboard_ctrl, mouse_ctrl, smart)

            try:
                if smart.condition_met(cond_payload):
                    return
            except Exception:
                pass

            loops += 1

    # —— IF 配对查找 ——
    def _find_matching_end_guard(self, start_index: int) -> Optional[int]:
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

        i = 0
        n = len(self.recorded_events)
        last_timestamp = 0.0
        active_guard = None  # IF 区间守护

        while i < n:
            if self.stop_playback_flag:
                break
            event = self.recorded_events[i]
            if not isinstance(event, (list, tuple)) or not event:
                i += 1
                continue

            etype = event[0]
            current_timestamp = event[-1]

            # IF 区间内周期判断
            if active_guard and i < active_guard["end_index"]:
                if smart is not None and time.time() >= active_guard["next_check"]:
                    if smart.condition_met(active_guard["payload"]):
                        jump_to = active_guard["end_index"]
                        if jump_to < n:
                            last_timestamp = self.recorded_events[jump_to][-1]
                        i = jump_to
                        active_guard = None
                        continue
                    else:
                        active_guard["next_check"] = time.time() + active_guard["interval"]
            else:
                active_guard = None

            # 按时间轴延迟
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
                i += 1
                continue

            # IF 守护结束
            if etype == "smart_end_guard":
                active_guard = None
                i += 1
                continue

            # WHILE 块
            if etype == "smart_while_ocr":
                if smart is not None and isinstance(event[1], dict):
                    try:
                        self._run_while_block(event[1], keyboard_ctrl, mouse_ctrl, smart, speed)
                    except Exception:
                        pass
                i += 1
                continue

            # 其它 smart_* 事件
            if smart is not None and isinstance(etype, str) and etype.startswith("smart_"):
                try:
                    smart.handle(list(event))
                except Exception:
                    pass
                i += 1
                continue

            # 原有事件 + 滚轮事件
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

            elif etype == 'mouse_scroll':
                dx, dy = event[1]
                x, y = event[2]
                mouse_ctrl.position = (x, y)
                try:
                    mouse_ctrl.scroll(int(dx), int(dy))
                except Exception:
                    mouse_ctrl.scroll(0, int(dy))

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