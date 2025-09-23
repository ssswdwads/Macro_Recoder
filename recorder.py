import json
import time
from typing import List, Tuple, Union, Optional
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController

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
            # 对于普通按键（可打印字符），记录字符
            self.recorded_events.append(('key_press', key.char, timestamp))
        elif isinstance(key, Key):
            # 对于特殊按键（如Ctrl、Shift等），记录键名
            self.recorded_events.append(('key_press', key.name, timestamp))

    def on_release(self, key: Union[Key, KeyCode, None]) -> None:
        """键盘按键释放事件处理"""
        if not self.is_recording or key is None:
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
        # 记录鼠标移动事件，包含坐标位置
        self.recorded_events.append(('mouse_move', (x, y), timestamp))

    def on_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        """鼠标点击事件处理"""
        if not self.is_recording:
            return

        timestamp = time.time() - self.start_time  # type: ignore
        # 根据是按下还是释放确定事件类型
        action = 'mouse_press' if pressed else 'mouse_release'
        # 记录鼠标点击事件，包含按钮类型和位置
        self.recorded_events.append((action, button.name, (x, y), timestamp))

    def start_recording(self) -> None:
        """开始记录键盘鼠标操作"""
        self.recorded_events = []  # 清空之前记录
        self.is_recording = True  # 设置记录状态
        self.start_time = time.time()  # 记录开始时间

        # 创建并启动键盘监听器
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.keyboard_listener.start()

        # 创建并启动鼠标监听器
        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click)
        self.mouse_listener.start()

    def stop_recording(self) -> None:
        """停止记录操作"""
        self.is_recording = False  # 清除记录状态
        # 停止监听器
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

    def save_recording(self, filename: str) -> None:
        """将记录的操作保存到文件"""
        with open(filename, 'w') as f:
            # 使用JSON格式保存记录的事件列表
            json.dump(self.recorded_events, f)

    def load_recording(self, filename: str) -> None:
        """从文件加载记录的操作"""
        with open(filename, 'r') as f:
            # 从JSON文件读取记录的事件列表
            self.recorded_events = json.load(f)

    def play_recording(self, speed: float = 1.0) -> None:
        """回放记录的操作"""
        if not self.recorded_events:
            return

        self.is_playing = True
        self.stop_playback_flag = False  # 重置停止标志

        # 创建键盘和鼠标控制器
        keyboard_ctrl = KeyboardController()
        mouse_ctrl = MouseController()

        last_timestamp = 0  # 上一个事件的时间戳

        # 遍历所有记录的事件
        for event in self.recorded_events:
            if self.stop_playback_flag:  # 使用正确的标志名
                break

            # 计算当前事件相对于开始的时间偏移
            current_timestamp = event[-1]
            # 计算与上一个事件的延迟时间（考虑回放速度）
            delay = (current_timestamp - last_timestamp) / speed
            if delay > 0:
                time.sleep(delay)  # 等待适当的时间
            last_timestamp = current_timestamp

            # 根据事件类型执行相应操作

            # 键盘按下事件
            if event[0] == 'key_press':
                key = event[1]
                try:
                    # 尝试将字符串转换为特殊键对象
                    key_obj = getattr(Key, key)
                except AttributeError:
                    # 普通字符键
                    key_obj = key
                keyboard_ctrl.press(key_obj)  # 模拟按键按下

            # 键盘释放事件
            elif event[0] == 'key_release':
                key = event[1]
                try:
                    key_obj = getattr(Key, key)
                except AttributeError:
                    key_obj = key
                keyboard_ctrl.release(key_obj)  # 模拟按键释放

            # 鼠标移动事件
            elif event[0] == 'mouse_move':
                x, y = event[1]  # 获取坐标
                mouse_ctrl.position = (x, y)  # 移动鼠标到指定位置

            # 鼠标按下事件
            elif event[0] == 'mouse_press':
                button = getattr(Button, event[1])  # 获取按钮类型
                x, y = event[2]  # 获取坐标
                mouse_ctrl.position = (x, y)  # 移动鼠标到位置
                mouse_ctrl.press(button)  # 模拟鼠标按下

            # 鼠标释放事件
            elif event[0] == 'mouse_release':
                button = getattr(Button, event[1])
                x, y = event[2]
                mouse_ctrl.position = (x, y)
                mouse_ctrl.release(button)  # 模拟鼠标释放

        self.is_playing = False

    def stop_playback(self) -> None:
        """停止回放"""
        self.stop_playback_flag = True
        self.is_playing = False

    def clear_recording(self) -> None:
        """清除录制内容"""
        self.recorded_events = []
        self.stop_playback_flag = True
        self.is_playing = False
        self.is_recording = False