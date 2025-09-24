import json
import time
import threading
import os
from typing import Dict, Optional
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QLabel, QMessageBox, QFileDialog,
                             QTreeWidget, QTreeWidgetItem, QGroupBox, QSpinBox, QCheckBox,
                             QSplitter, QLineEdit, QComboBox, QInputDialog, QStyledItemDelegate,
                             QDoubleSpinBox, QAbstractItemView, QFrame, QStyle)
from PyQt5.QtCore import Qt, QTimer, QSignalBlocker
from PyQt5.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QBrush, QLinearGradient
from pynput import keyboard

from recorder import KeyMouseRecorder
from models import MacroStep, MacroTask
from delegates import SpinBoxDelegate


class OceanItemDelegate(QStyledItemDelegate):
    """海洋风格的项目委托"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.font = QFont("Arial Rounded MT Bold", 10)
        self.font.setBold(True)

    def paint(self, painter, option, index):
        # 绘制海洋风格的背景
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(230, 245, 255))
        else:
            painter.fillRect(option.rect, QColor(240, 250, 255))

        # 绘制圆角矩形边框
        painter.setPen(QColor(100, 180, 255))
        painter.drawRoundedRect(option.rect.adjusted(1, 1, -1, -1), 8, 8)

        # 绘制文本
        painter.setFont(self.font)
        painter.setPen(QColor(30, 80, 150))
        text = index.data(Qt.DisplayRole)
        painter.drawText(option.rect.adjusted(5, 0, -5, 0), Qt.AlignVCenter | Qt.AlignLeft, text)


class OceanListWidget(QListWidget):
    """海洋风格的列表控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(OceanItemDelegate(self))
        self.setStyleSheet("""
            QListWidget {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 5px;
            }
            QListWidget::item {
                height: 30px;
            }
            QScrollBar:vertical {
                border: none;
                background: #e3f2fd;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #64b5f6;
                min-height: 20px;
                border-radius: 5px;
            }
        """)


class OceanTreeWidget(QTreeWidget):
    """海洋风格的树控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 5px;
                alternate-background-color: #e3f2fd;
            }
            QTreeWidget::item {
                height: 28px;
                border-bottom: 1px dashed #64b5f6;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #64b5f6;
                color: white;
                font-weight: bold;
                padding: 4px;
                border: 1px solid #42a5f5;
                border-radius: 5px;
            }
            QScrollBar:vertical {
                border: none;
                background: #e3f2fd;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #64b5f6;
                min-height: 20px;
                border-radius: 5px;
            }
        """)


class OceanButton(QPushButton):
    """海洋风格的按钮"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #64b5f6;
                color: white;
                border: 2px solid #42a5f5;
                border-radius: 15px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #42a5f5;
            }
            QPushButton:pressed {
                background-color: #1976d2;
            }
            QPushButton:disabled {
                background-color: #d3d3d3;
                color: #a0a0a0;
            }
        """)


class OceanGroupBox(QGroupBox):
    """海洋风格的分组框"""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 10px;
                margin-top: 20px;
                font-weight: bold;
                color: #1976d2;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #f0f8ff;
                border-radius: 5px;
            }
        """)


class OceanLineEdit(QLineEdit):
    """海洋风格的输入框"""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 8px;
                color: #1976d2;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid #1976d2;
            }
        """)


class OceanSpinBox(QSpinBox):
    """海洋风格的数值输入框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QSpinBox {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 5px;
                color: #1976d2;
                font-weight: bold;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #64b5f6;
                border-bottom: 1px solid #64b5f6;
                border-top-right-radius: 10px;
                background-color: #64b5f6;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid #64b5f6;
                border-top: 1px solid #64b5f6;
                border-bottom-right-radius: 10px;
                background-color: #64b5f6;
            }
            QSpinBox::up-arrow {
                image: url(icons/up_arrow.png);
                width: 10px;
                height: 10px;
            }
            QSpinBox::down-arrow {
                image: url(icons/down_arrow.png);
                width: 10px;
                height: 10px;
            }
        """)


class OceanDoubleSpinBox(QDoubleSpinBox):
    """海洋风格的浮点数输入框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 5px;
                color: #1976d2;
                font-weight: bold;
            }
            QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #64b5f6;
                border-bottom: 1px solid #64b5f6;
                border-top-right-radius: 10px;
                background-color: #64b5f6;
            }
            QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid #64b5f6;
                border-top: 1px solid #64b5f6;
                border-bottom-right-radius: 10px;
                background-color: #64b5f6;
            }
            QDoubleSpinBox::up-arrow {
                image: url(icons/up_arrow.png);
                width: 10px;
                height: 10px;
            }
            QDoubleSpinBox::down-arrow {
                image: url(icons/down_arrow.png);
                width: 10px;
                height: 10px;
            }
        """)


class OceanLabel(QLabel):
    """海洋风格的标签"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                color: #1976d2;
                font-weight: bold;
                font-size: 12px;
            }
        """)


# ===== 延迟单位工具与委托（内联） =====

def _format_duration_seconds(seconds: float) -> str:
    """将秒的浮点值格式化为 毫秒/秒/分钟 文本"""
    try:
        s = float(seconds)
    except Exception:
        s = 0.0

    if s < 1.0:
        ms = int(round(s * 1000.0))
        return f"{ms} 毫秒"
    if s >= 60.0:
        mins = s / 60.0
        if abs(mins - round(mins)) < 1e-3:
            return f"{int(round(mins))} 分钟"
    text = f"{s:.3f}".rstrip("0").rstrip(".")
    return f"{text} 秒"


def _parse_display_to_seconds(text: str) -> float:
    """从显示文本解析“秒”的浮点值，支持 毫秒/秒/分钟 或纯数字（默认秒）"""
    if text is None:
        return 0.0
    s = str(text).strip().lower()

    # 尝试直接转秒（纯数字）
    try:
        return max(0.0, float(s))
    except Exception:
        pass

    num = ""
    for ch in s:
        if ch.isdigit() or ch in ".-":
            num += ch
        elif ch == ",":
            num += "."
    if num in ("", ".", "-"):
        num_val = 0.0
    else:
        try:
            num_val = float(num)
        except Exception:
            num_val = 0.0

    if "毫秒" in s or "ms" in s:
        return max(0.0, num_val / 1000.0)
    if "分钟" in s or "分" in s or "min" in s:
        return max(0.0, num_val * 60.0)
    # 默认当秒
    return max(0.0, num_val)


class _DelayUnitEditor(QWidget):
    """组合编辑器：数值 + 单位（毫秒 / 秒 / 分钟），对外以秒浮点值进行读写（0ms~60min）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spin = QDoubleSpinBox(self)
        self.spin.setDecimals(3)
        self.spin.setMinimum(0.0)
        self.spin.setSingleStep(1.0)

        self.unit = QComboBox(self)
        self.unit.addItems(["毫秒", "秒", "分钟"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.spin)
        layout.addWidget(self.unit)
        self.setLayout(layout)

        self.unit.currentIndexChanged.connect(self._on_unit_changed)
        self._on_unit_changed()

    def _on_unit_changed(self):
        u = self.unit.currentText()
        # 将当前值先换算为秒，再切换单位与范围
        sec = self.seconds()
        if u == "毫秒":
            self.spin.setDecimals(0)
            self.spin.setRange(0, 3_600_000)  # 0ms~60min
            self.spin.setSuffix(" 毫秒")
            self.spin.setValue(int(round(sec * 1000.0)))
        elif u == "秒":
            self.spin.setDecimals(3)
            self.spin.setRange(0.0, 3600.0)  # 0s~60min
            self.spin.setSuffix(" 秒")
            self.spin.setValue(sec)
        else:
            self.spin.setDecimals(3)
            self.spin.setRange(0.0, 60.0)  # 0min~60min
            self.spin.setSuffix(" 分钟")
            self.spin.setValue(sec / 60.0)

    def set_seconds(self, seconds: float):
        try:
            s = float(seconds)
        except Exception:
            s = 0.0
        # 选个合适的单位
        if s < 1.0:
            self.unit.setCurrentText("毫秒")
            self.spin.setValue(int(round(s * 1000.0)))
        elif s >= 60.0 and abs((s / 60.0) - round(s / 60.0)) < 1e-3:
            self.unit.setCurrentText("分钟")
            self.spin.setValue(s / 60.0)
        else:
            self.unit.setCurrentText("秒")
            self.spin.setValue(s)

    def seconds(self) -> float:
        u = self.unit.currentText()
        v = self.spin.value()
        if u == "毫秒":
            return float(v) / 1000.0
        if u == "分钟":
            return float(v) * 60.0
        return float(v)


class DelayUnitDelegate(QStyledItemDelegate):
    """步骤延迟委托（第4列）：毫秒/秒/分钟 输入，写回为“秒”的浮点值，并设置友好显示文本"""

    def createEditor(self, parent, option, index):
        return _DelayUnitEditor(parent)

    def setEditorData(self, editor, index):
        # 优先从 UserRole 拿秒值
        user_seconds = index.model().data(index, Qt.UserRole)
        if user_seconds is None:
            # 解析显示文本
            value = index.model().data(index, Qt.DisplayRole)
            seconds = _parse_display_to_seconds(value)
        else:
            try:
                seconds = float(user_seconds)
            except Exception:
                seconds = 0.0
        editor.set_seconds(seconds)

    def setModelData(self, editor, model, index):
        seconds = max(0.0, float(editor.seconds()))
        # 编辑值（用于 item.text / 可编辑）
        model.setData(index, seconds, Qt.EditRole)
        # 格式化显示
        model.setData(index, _format_duration_seconds(seconds), Qt.DisplayRole)
        # 也写入 UserRole，便于下次编辑直接读取
        model.setData(index, seconds, Qt.UserRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class MacroRecorderApp(QMainWindow):
    """主应用程序窗口 - 蓝白海洋风格"""

    def __init__(self):
        super().__init__()

        self.recorder = KeyMouseRecorder()  # 创建记录器实例
        self.recordings: Dict[str, str] = {}  # 保存的录制: {名称: 文件路径}
        self.tasks: Dict[str, MacroTask] = {}  # 保存的任务
        self.current_task: Optional[MacroTask] = None  # 当前编辑的任务

        self.init_ui()
        self.setup_hotkeys()

        # 更新状态的定时器
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(100)  # 每100ms更新一次状态

    def init_ui(self):
        """初始化用户界面 - 蓝白海洋风格"""
        self.setWindowTitle("Macro Recorder")
        self.setGeometry(300, 300, 1000, 700)

        # 使用用户指定的图标
        icon_path = r"C:\Users\ASUS\Desktop\study\Keyboard\Macro_Recoder\icon.jpg"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"图标文件不存在: {icon_path}")

        # 设置主窗口背景 - 蓝白渐变
        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0, QColor(255, 255, 255))
        gradient.setColorAt(1, QColor(225, 245, 255))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)

        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 标题标签
        title_label = QLabel("Macro Recorder")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #1976d2;
                font-weight: bold;
                font-size: 24px;
                background-color: rgba(240, 248, 255, 200);
                border: 2px solid #64b5f6;
                border-radius: 15px;
                padding: 10px;
            }
        """)
        main_layout.addWidget(title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("background-color: transparent;")
        main_layout.addWidget(splitter, 1)

        # 左侧面板 - 录制和任务列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(15)
        left_panel.setStyleSheet("""
            background-color: rgba(240, 248, 255, 200);
            border: 2px solid #64b5f6;
            border-radius: 15px;
        """)

        # 状态标签
        self.status_label = QLabel("状态: 空闲")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #1976d2;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #64b5f6;
                border-radius: 15px;
            }
        """)
        left_layout.addWidget(self.status_label)

        # 录制信息标签
        self.info_label = QLabel("录制事件数: 0")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("""
            QLabel {
                color: #1976d2;
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #64b5f6;
                border-radius: 15px;
            }
        """)
        left_layout.addWidget(self.info_label)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 录制按钮
        self.record_button = OceanButton("开始录制")
        self.record_button.setStyleSheet("background-color: #4caf50;")  # 绿色
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)

        # 停止录制按钮
        self.stop_record_button = OceanButton("停止录制")
        self.stop_record_button.setEnabled(False)
        self.stop_record_button.setStyleSheet("background-color: #f44336;")  # 红色
        self.stop_record_button.clicked.connect(self.stop_recording)
        button_layout.addWidget(self.stop_record_button)

        # 回放按钮
        self.play_button = OceanButton("回放")
        self.play_button.setStyleSheet("background-color: #2196f3;")  # 蓝色
        self.play_button.clicked.connect(self.play_recording)
        button_layout.addWidget(self.play_button)

        # 停止回放按钮
        self.stop_play_button = OceanButton("停止回放")
        self.stop_play_button.setEnabled(False)
        self.stop_play_button.setStyleSheet("background-color: #ff9800;")  # 橙色
        self.stop_play_button.clicked.connect(self.stop_playback)
        button_layout.addWidget(self.stop_play_button)

        left_layout.addLayout(button_layout)

        # 录制列表
        left_layout.addWidget(OceanLabel("录制列表:"))
        self.recording_list_widget = OceanListWidget()
        self.recording_list_widget.itemDoubleClicked.connect(self.load_selected_recording)
        left_layout.addWidget(self.recording_list_widget, 1)

        # 任务列表
        left_layout.addWidget(OceanLabel("任务列表:"))
        self.task_list_widget = OceanListWidget()
        self.task_list_widget.itemDoubleClicked.connect(self.load_task)
        left_layout.addWidget(self.task_list_widget, 1)

        # 任务管理按钮
        task_btn_layout = QHBoxLayout()
        task_btn_layout.setSpacing(10)

        self.new_task_btn = OceanButton("新建任务")
        self.new_task_btn.clicked.connect(self.create_new_task)
        task_btn_layout.addWidget(self.new_task_btn)

        self.save_task_btn = OceanButton("保存任务")
        self.save_task_btn.clicked.connect(self.save_task)
        task_btn_layout.addWidget(self.save_task_btn)

        self.delete_task_btn = OceanButton("删除任务")
        self.delete_task_btn.setStyleSheet("background-color: #f44336;")
        self.delete_task_btn.clicked.connect(self.delete_task)
        task_btn_layout.addWidget(self.delete_task_btn)

        left_layout.addLayout(task_btn_layout)

        # 右侧面板 - 任务编辑
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(15)
        right_panel.setStyleSheet("""
            background-color: rgba(240, 248, 255, 200);
            border: 2px solid #64b5f6;
            border-radius: 15px;
        """)

        # 任务信息
        self.task_info_group = OceanGroupBox("任务信息")
        task_info_layout = QVBoxLayout(self.task_info_group)
        task_info_layout.setSpacing(10)

        task_info_layout.addWidget(OceanLabel("任务名称:"))
        self.task_name_edit = OceanLineEdit("任务名称")
        task_info_layout.addWidget(self.task_name_edit)

        loop_layout = QHBoxLayout()
        loop_layout.setSpacing(10)

        loop_layout.addWidget(OceanLabel("循环次数 (0=无限):"))

        self.loop_spin = OceanSpinBox()
        self.loop_spin.setRange(0, 10000)
        self.loop_spin.setValue(1)
        loop_layout.addWidget(self.loop_spin, 1)

        loop_layout.addWidget(OceanLabel("循环间隔:"))

        # 新的循环间隔输入（数值 + 单位）
        self.loop_delay_spin = OceanDoubleSpinBox()
        self.loop_delay_spin.setDecimals(3)
        self.loop_delay_unit = QComboBox()
        self.loop_delay_unit.addItems(["毫秒", "秒", "分钟"])

        # 记录上一次单位，避免用新单位误读旧值
        self.loop_delay_prev_unit = "秒"

        def _on_loop_unit_change():
            # 用“旧单位”解释当前值 -> 秒
            prev = self.loop_delay_prev_unit
            new = self.loop_delay_unit.currentText()
            v = self.loop_delay_spin.value()

            if prev == "毫秒":
                seconds = float(v) / 1000.0
            elif prev == "分钟":
                seconds = float(v) * 60.0
            else:  # 秒
                seconds = float(v)

            # 配置新单位的范围/后缀，并将秒值转换为新单位值写回
            if new == "毫秒":
                self.loop_delay_spin.setDecimals(0)
                self.loop_delay_spin.setRange(0, 3_600_000)  # 0ms ~ 60min
                self.loop_delay_spin.setSuffix(" 毫秒")
                self.loop_delay_spin.setValue(int(round(seconds * 1000.0)))
            elif new == "秒":
                self.loop_delay_spin.setDecimals(3)
                self.loop_delay_spin.setRange(0.0, 3600.0)  # 0s ~ 60min
                self.loop_delay_spin.setSuffix(" 秒")
                self.loop_delay_spin.setValue(seconds)
            else:  # 分钟
                self.loop_delay_spin.setDecimals(3)
                self.loop_delay_spin.setRange(0.0, 60.0)  # 0min ~ 60min
                self.loop_delay_spin.setSuffix(" 分钟")
                self.loop_delay_spin.setValue(seconds / 60.0)

            self.loop_delay_prev_unit = new

        self.loop_delay_unit.currentIndexChanged.connect(_on_loop_unit_change)
        # 初始化（默认秒）
        self.loop_delay_unit.setCurrentText("秒")
        self.loop_delay_prev_unit = "秒"
        _on_loop_unit_change()

        loop_layout.addWidget(self.loop_delay_spin, 1)
        loop_layout.addWidget(self.loop_delay_unit)

        task_info_layout.addLayout(loop_layout)

        right_layout.addWidget(self.task_info_group)

        # 任务步骤
        self.task_steps_group = OceanGroupBox("任务步骤")
        task_steps_layout = QVBoxLayout(self.task_steps_group)
        task_steps_layout.setSpacing(10)

        self.steps_tree = OceanTreeWidget()
        self.steps_tree.setHeaderLabels(["启用", "步骤名称", "录制文件", "重复次数", "延迟"])
        self.steps_tree.setColumnWidth(0, 60)
        self.steps_tree.setColumnWidth(1, 150)
        self.steps_tree.setColumnWidth(2, 200)
        self.steps_tree.setColumnWidth(3, 100)
        self.steps_tree.setColumnWidth(4, 140)

        # 设置委托以允许编辑
        # 第3列（重复次数）用原有 SpinBoxDelegate
        self.steps_tree.setItemDelegateForColumn(3, SpinBoxDelegate(self.steps_tree))
        # 第4列（延迟）用新的 DelayUnitDelegate
        self.steps_tree.setItemDelegateForColumn(4, DelayUnitDelegate(self.steps_tree))

        # 启用双击编辑
        self.steps_tree.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)

        task_steps_layout.addWidget(self.steps_tree, 1)

        # 步骤操作按钮
        step_btn_layout = QHBoxLayout()
        step_btn_layout.setSpacing(10)

        self.add_step_btn = OceanButton("添加步骤")
        self.add_step_btn.clicked.connect(self.add_step)
        step_btn_layout.addWidget(self.add_step_btn)

        self.remove_step_btn = OceanButton("移除步骤")
        self.remove_step_btn.clicked.connect(self.remove_step)
        step_btn_layout.addWidget(self.remove_step_btn)

        self.move_up_btn = OceanButton("上移")
        self.move_up_btn.clicked.connect(lambda: self.move_step(-1))
        step_btn_layout.addWidget(self.move_up_btn)

        self.move_down_btn = OceanButton("下移")
        self.move_down_btn.clicked.connect(lambda: self.move_step(1))
        step_btn_layout.addWidget(self.move_down_btn)

        task_steps_layout.addLayout(step_btn_layout)

        right_layout.addWidget(self.task_steps_group, 1)

        # 任务执行按钮
        task_exec_layout = QHBoxLayout()
        task_exec_layout.setSpacing(10)

        self.run_task_btn = OceanButton("执行任务")
        self.run_task_btn.setStyleSheet("""
            background-color: #2196f3;
            font-weight: bold;
            font-size: 14px;
            padding: 10px 20px;
        """)
        self.run_task_btn.clicked.connect(self.run_task)
        task_exec_layout.addWidget(self.run_task_btn)

        self.stop_task_btn = OceanButton("停止任务")
        self.stop_task_btn.setStyleSheet("""
            background-color: #f44336;
            padding: 10px 20px;
        """)
        self.stop_task_btn.setEnabled(False)
        self.stop_task_btn.clicked.connect(self.stop_task)
        task_exec_layout.addWidget(self.stop_task_btn)

        right_layout.addLayout(task_exec_layout)

        # 添加左右面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 650])

        # 热键提示
        hotkey_label = QLabel("热键: F9 - 开始/停止录制 | F10 - 停止回放 | F11 - 开始任务 | F12 - 停止任务")
        hotkey_label.setAlignment(Qt.AlignCenter)
        hotkey_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #1976d2;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #64b5f6;
                border-radius: 15px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        main_layout.addWidget(hotkey_label)

        # 初始化任务编辑区
        self.disable_task_editing()

        # 加载保存的录制和任务
        self.load_saved_recordings()
        self.load_saved_tasks()

        # 连接信号
        self.steps_tree.itemChanged.connect(self.update_step_parameters)

    def setup_hotkeys(self):
        """设置全局热键监听"""
        self.hotkey_listener = keyboard.GlobalHotKeys({
            '<f9>': lambda: QTimer.singleShot(0, self.toggle_recording),
            '<f10>': lambda: QTimer.singleShot(0, self.stop_playback),
            '<f11>': lambda: QTimer.singleShot(0, self.run_task),
            '<f12>': lambda: QTimer.singleShot(0, self.stop_task)
        })
        self.hotkey_listener.start()

    def toggle_recording(self):
        """切换录制状态"""
        if not self.isVisible():
            return

        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """开始录制"""
        if self.recorder.is_playing:
            QMessageBox.warning(self, "警告", "请先停止回放")
            return

        self.recorder.start_recording()
        self.status_label.setText("状态: 录制中...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #f44336;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #f44336;
                border-radius: 15px;
            }
        """)
        self.record_button.setText("停止录制")
        self.record_button.setStyleSheet("background-color: #f44336;")
        self.stop_record_button.setEnabled(True)

    def stop_recording(self):
        """停止录制"""
        self.recorder.stop_recording()
        self.status_label.setText("状态: 录制完成")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4caf50;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #4caf50;
                border-radius: 15px;
            }
        """)
        self.record_button.setText("开始录制")
        self.record_button.setStyleSheet("background-color: #4caf50;")
        self.stop_record_button.setEnabled(False)

        # 提示保存录制
        self.prompt_save_recording()

    def play_recording(self):
        """回放录制"""
        if not self.recorder.recorded_events:
            QMessageBox.warning(self, "警告", "没有可回放的录制内容")
            return

        if self.recorder.is_recording:
            QMessageBox.warning(self, "警告", "请先停止录制")
            return

        # 在单独的线程中回放
        self.play_button.setEnabled(False)
        self.stop_play_button.setEnabled(True)
        self.status_label.setText("状态: 回放中...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2196f3;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #2196f3;
                border-radius: 15px;
            }
        """)

        playback_thread = threading.Thread(target=self.recorder.play_recording)
        playback_thread.daemon = True
        playback_thread.start()

    def stop_playback(self):
        """停止回放"""
        if self.recorder.is_playing:
            self.recorder.stop_playback()
            self.status_label.setText("状态: 回放已停止")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 10px;
                    background-color: rgba(230, 245, 255, 200);
                    border: 2px solid #ff9800;
                    border-radius: 15px;
                }
            """)
            self.play_button.setEnabled(True)
            self.stop_play_button.setEnabled(False)

    def save_recording(self, name: str):
        """保存录制到文件"""
        if not self.recorder.recorded_events:
            QMessageBox.warning(self, "警告", "没有可保存的录制内容")
            return

        # 创建录制目录
        recordings_dir = os.path.join(os.path.dirname(__file__), "recordings")
        if not os.path.exists(recordings_dir):
            os.makedirs(recordings_dir)

        file_path = os.path.join(recordings_dir, f"{name}.json")
        self.recorder.save_recording(file_path)

        # 添加到录制列表
        self.recordings[name] = file_path
        self.recording_list_widget.addItem(name)

        QMessageBox.information(self, "成功", f"录制 '{name}' 已保存")

    def load_recording(self, name: str):
        """从文件加载录制"""
        if name in self.recordings:
            try:
                self.recorder.load_recording(self.recordings[name])
                event_count = len(self.recorder.recorded_events)
                self.info_label.setText(f"录制事件数: {event_count}")
                QMessageBox.information(self, "成功", f"录制 '{name}' 已加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")

    def load_selected_recording(self, item):
        """加载选中的录制"""
        name = item.text()
        self.load_recording(name)

    def delete_recording(self):
        """删除选中的录制"""
        current_item = self.recording_list_widget.currentItem()
        if current_item:
            name = current_item.text()
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除录制 '{name}' 吗?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 从列表中移除
                row = self.recording_list_widget.row(current_item)
                self.recording_list_widget.takeItem(row)

                # 删除文件
                if name in self.recordings:
                    try:
                        os.remove(self.recordings[name])
                        del self.recordings[name]
                    except Exception as e:
                        QMessageBox.warning(self, "警告", f"删除文件失败: {str(e)}")

                # 如果删除的是当前录制，则清空录制内容
                if self.recording_list_widget.count() == 0:
                    self.recorder.clear_recording()
                    self.info_label.setText("录制事件数: 0")

    def clear_recording(self):
        """清空当前录制内容"""
        if not self.recorder.recorded_events:
            return

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空当前录制内容吗?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.recorder.clear_recording()
            self.info_label.setText("录制事件数: 0")
            self.status_label.setText("状态: 空闲")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #1976d2;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 10px;
                    background-color: rgba(230, 245, 255, 200);
                    border: 2px solid #64b5f6;
                    border-radius: 15px;
                }
            """)

    def update_status(self):
        """更新状态信息"""
        # 更新录制事件数
        event_count = len(self.recorder.recorded_events)
        self.info_label.setText(f"录制事件数: {event_count}")

        # 如果回放结束，更新按钮状态
        if not self.recorder.is_playing and self.stop_play_button.isEnabled():
            self.play_button.setEnabled(True)
            self.stop_play_button.setEnabled(False)
            self.status_label.setText("状态: 回放完成")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #4caf50;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 10px;
                    background-color: rgba(230, 245, 255, 200);
                    border: 2px solid #4caf50;
                    border-radius: 15px;
                }
            """)

    def closeEvent(self, event):
        """关闭应用程序事件处理"""
        # 停止所有活动
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        if self.recorder.is_playing:
            self.recorder.stop_playback()

        # 停止热键监听
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener.running:
            self.hotkey_listener.stop()

        # 保存任务
        self.save_tasks_to_file()

        event.accept()

    # ======================== 任务管理功能 ========================

    def disable_task_editing(self):
        """禁用任务编辑区"""
        self.task_info_group.setEnabled(False)
        self.task_steps_group.setEnabled(False)
        self.run_task_btn.setEnabled(False)
        self.stop_task_btn.setEnabled(False)

    def enable_task_editing(self):
        """启用任务编辑区"""
        self.task_info_group.setEnabled(True)
        self.task_steps_group.setEnabled(True)
        self.run_task_btn.setEnabled(True)
        self.stop_task_btn.setEnabled(False)

    def create_new_task(self):
        """创建新任务"""
        name, ok = QInputDialog.getText(self, "新建任务", "请输入任务名称:")
        if ok and name:
            if name in self.tasks:
                QMessageBox.warning(self, "警告", f"任务 '{name}' 已存在!")
                return

            self.current_task = MacroTask(name)
            self.tasks[name] = self.current_task
            self.task_list_widget.addItem(name)

            # 更新UI
            self.task_name_edit.setText(name)
            self.loop_spin.setValue(1)
            self._set_loop_delay_seconds_to_widgets(0.0)
            self.steps_tree.clear()

            self.enable_task_editing()

    def load_task(self, item):
        """加载选中的任务"""
        task_name = item.text()
        if task_name in self.tasks:
            self.current_task = self.tasks[task_name]

            # 更新UI
            self.task_name_edit.setText(self.current_task.name)
            self.loop_spin.setValue(self.current_task.loop_count)
            self._set_loop_delay_seconds_to_widgets(self.current_task.loop_delay)

            # 加载步骤
            self.steps_tree.clear()
            for step in self.current_task.steps:
                self.add_step_to_tree(step)

            self.enable_task_editing()

    def save_task(self):
        """保存当前任务"""
        if not self.current_task:
            QMessageBox.warning(self, "警告", "没有正在编辑的任务!")
            return

        # 更新任务信息
        self.current_task.name = self.task_name_edit.text()
        self.current_task.loop_count = self.loop_spin.value()
        self.current_task.loop_delay = self._get_loop_delay_seconds_from_widgets()

        # 更新任务列表
        for i in range(self.task_list_widget.count()):
            if self.task_list_widget.item(i).text() == self.current_task.name:
                self.task_list_widget.item(i).setText(self.current_task.name)
                break

        # 保存到文件
        self.save_tasks_to_file()

        QMessageBox.information(self, "成功", f"任务 '{self.current_task.name}' 已保存")

    def delete_task(self):
        """删除选中的任务"""
        current_item = self.task_list_widget.currentItem()
        if current_item:
            task_name = current_item.text()
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除任务 '{task_name}' 吗?",
                QMessageBox.Yes | QMessageBox.No
            )

        if current_item and reply == QMessageBox.Yes:
            # 从列表中移除
            row = self.task_list_widget.row(current_item)
            self.task_list_widget.takeItem(row)

            # 从内存中删除
            if task_name in self.tasks:
                del self.tasks[task_name]

            # 如果是当前任务，清空编辑区
            if self.current_task and self.current_task.name == task_name:
                self.current_task = None
                self.disable_task_editing()
                self.task_name_edit.clear()
                self.steps_tree.clear()

    def add_step(self):
        """添加新步骤到当前任务"""
        if not self.current_task:
            QMessageBox.warning(self, "警告", "没有正在编辑的任务!")
            return

        # 获取选中的录制
        recording_item = self.recording_list_widget.currentItem()
        if not recording_item:
            QMessageBox.warning(self, "警告", "请先在录制列表中选择一个录制!")
            return

        recording_name = recording_item.text()

        # 创建新步骤
        step = MacroStep(
            name=f"{recording_name} 步骤",
            file_path=self.recordings[recording_name],
            repeat=1,
            delay=0.0
        )

        # 添加到任务
        self.current_task.add_step(step)

        # 添加到树形视图
        self.add_step_to_tree(step)

    def add_step_to_tree(self, step: MacroStep):
        """将步骤添加到树形视图"""
        item = QTreeWidgetItem(self.steps_tree)

        # 保存步骤对象到item
        item.setData(0, Qt.UserRole, step)

        # 设置项目可编辑
        item.setFlags(item.flags() | Qt.ItemIsEditable)

        # 设置列数据
        item.setText(1, step.name)
        item.setText(2, os.path.basename(step.file_path))
        item.setText(3, str(step.repeat))

        # 延迟列：显示格式化文本，同时保存秒到 UserRole
        item.setText(4, _format_duration_seconds(step.delay))
        item.setData(4, Qt.UserRole, float(step.delay))

        # 添加启用复选框
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #64b5f6;
                border-radius: 5px;
                background: #f0f8ff;
            }
            QCheckBox::indicator:checked {
                background-color: #1976d2;
                image: url(icons/check.png);
            }
            QCheckBox::indicator:unchecked {
                background-color: #f0f8ff;
            }
        """)
        checkbox.setChecked(step.enabled)
        checkbox.stateChanged.connect(lambda state, s=step: self.toggle_step_enabled(s, state))
        self.steps_tree.setItemWidget(item, 0, checkbox)

    def toggle_step_enabled(self, step: MacroStep, state: int):
        """切换步骤启用状态"""
        step.enabled = (state == Qt.Checked)

    def remove_step(self):
        """移除选中的步骤"""
        if not self.current_task:
            return

        selected_items = self.steps_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        index = self.steps_tree.indexOfTopLevelItem(item)

        if 0 <= index < len(self.current_task.steps):
            self.current_task.remove_step(index)
            self.steps_tree.takeTopLevelItem(index)

    def move_step(self, direction: int):
        """移动步骤位置"""
        if not self.current_task:
            return

        selected_items = self.steps_tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        current_index = self.steps_tree.indexOfTopLevelItem(item)
        new_index = current_index + direction

        if 0 <= new_index < len(self.current_task.steps):
            # 移动任务中的步骤
            if direction < 0:
                self.current_task.move_step_up(current_index)
            else:
                self.current_task.move_step_down(current_index)

            # 移动树形视图中的项目
            item = self.steps_tree.takeTopLevelItem(current_index)
            self.steps_tree.insertTopLevelItem(new_index, item)
            self.steps_tree.setCurrentItem(item)

    def run_task(self):
        """执行当前任务"""
        if not self.current_task or not self.current_task.steps:
            QMessageBox.warning(self, "警告", "任务中没有可执行的步骤!")
            return

        # 启动前，同步当前 UI 的循环次数与循环间隔（秒）
        self.current_task.loop_count = self.loop_spin.value()
        self.current_task.loop_delay = self._get_loop_delay_seconds_from_widgets()

        # 禁用运行按钮，启用停止按钮
        self.run_task_btn.setEnabled(False)
        self.stop_task_btn.setEnabled(True)
        self.status_label.setText("状态: 任务执行中...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2196f3;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #2196f3;
                border-radius: 15px;
            }
        """)

        # 在单独线程中执行任务
        self.task_thread = threading.Thread(target=self.execute_task)
        self.task_thread.daemon = True
        self.task_thread.start()

    def execute_task(self):
        """执行任务的线程函数（循环间隔为“结束到开始”的固定间隔）"""
        try:
            self.current_task.is_running = True
            self.current_task.should_stop = False

            loop_count = self.current_task.loop_count
            loop_delay = float(self.current_task.loop_delay)

            # 无限循环或有限循环
            current_loop = 0
            while (loop_count == 0 or current_loop < loop_count) and not self.current_task.should_stop:
                # 执行所有步骤
                for step in self.current_task.steps:
                    if self.current_task.should_stop:
                        break

                    if not step.enabled:
                        continue

                    # 加载录制
                    self.recorder.load_recording(step.file_path)

                    # 执行步骤指定次数
                    for i in range(step.repeat):
                        if self.current_task.should_stop:
                            break

                        # 执行录制
                        self.recorder.play_recording()

                        # 执行后延迟（仅在重复之间）
                        if step.delay > 0 and i < step.repeat - 1:
                            time.sleep(step.delay)

                # 循环间延迟（结束到开始：每轮执行完后，再等待完整的 loop_delay）
                if loop_delay > 0 and (loop_count == 0 or current_loop < loop_count - 1):
                    # 精确睡眠（抗抖动），但不扣除执行耗时
                    target = time.monotonic() + loop_delay
                    while not self.current_task.should_stop:
                        remain = target - time.monotonic()
                        if remain <= 0:
                            break
                        time.sleep(min(0.2, max(0.0, remain)))

                current_loop += 1

            # 任务完成
            self.current_task.is_running = False
            # 修复：使用线程安全方式更新UI
            QTimer.singleShot(0, self.on_task_finished)

        except Exception as e:
            # 修复：捕获并报告异常
            error_msg = f"任务执行错误: {str(e)}"
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "错误", error_msg))
            QTimer.singleShot(0, self.on_task_finished)

    def stop_task(self):
        """停止当前任务"""
        if self.current_task and self.current_task.is_running:
            self.current_task.should_stop = True
            self.recorder.stop_playback()
            self.stop_task_btn.setEnabled(False)
            self.status_label.setText("状态: 任务已停止")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #ff9800;
                    font-weight: bold;
                    font-size: 16px;
                    padding: 10px;
                    background-color: rgba(230, 245, 255, 200);
                    border: 2px solid #ff9800;
                    border-radius: 15px;
                }
            """)

            # 更新UI状态
            QTimer.singleShot(0, lambda: self.run_task_btn.setEnabled(True))

    def prompt_save_recording(self):
        """提示用户保存录制"""
        name, ok = QInputDialog.getText(
            self,
            "保存录制",
            "请输入录制名称:",
            text=f"录制_{time.strftime('%Y%m%d_%H%M%S')}"
        )

    def on_task_finished(self):
        """任务完成后的UI更新"""
        self.status_label.setText("状态: 任务完成")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #4caf50;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                background-color: rgba(230, 245, 255, 200);
                border: 2px solid #4caf50;
                border-radius: 15px;
            }
        """)
        self.run_task_btn.setEnabled(True)
        self.stop_task_btn.setEnabled(False)

    def closeEvent(self, event):
        """关闭应用程序事件处理"""
        # 停止所有活动
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        if self.recorder.is_playing:
            self.recorder.stop_playback()

        # 停止任务
        if self.current_task and self.current_task.is_running:
            self.current_task.should_stop = True

        # 等待任务停止
        if hasattr(self, 'task_thread') and self.task_thread.is_alive():
            self.task_thread.join(1.0)  # 最多等待1秒

        # 停止热键监听
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener.running:
            self.hotkey_listener.stop()

        # 保存任务
        self.save_tasks_to_file()

        event.accept()

    def load_saved_recordings(self):
        """加载保存的录制"""
        recordings_dir = os.path.join(os.path.dirname(__file__), "recordings")
        if not os.path.exists(recordings_dir):
            return

        # 清空列表
        self.recording_list_widget.clear()
        self.recordings.clear()

        # 加载所有JSON文件
        for filename in os.listdir(recordings_dir):
            if filename.endswith(".json"):
                name = os.path.splitext(filename)[0]
                file_path = os.path.join(recordings_dir, filename)
                self.recordings[name] = file_path
                self.recording_list_widget.addItem(name)

    def load_saved_tasks(self):
        """加载保存的任务"""
        tasks_file = os.path.join(os.path.dirname(__file__), "tasks.json")
        if not os.path.exists(tasks_file):
            return

        try:
            with open(tasks_file, 'r') as f:
                tasks_data = json.load(f)

            for task_data in tasks_data:
                task = MacroTask.from_dict(task_data)
                self.tasks[task.name] = task
                self.task_list_widget.addItem(task.name)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载任务失败: {str(e)}")

    def save_tasks_to_file(self):
        """保存所有任务到文件"""
        tasks_file = os.path.join(os.path.dirname(__file__), "tasks.json")

        try:
            tasks_data = [task.to_dict() for task in self.tasks.values()]
            with open(tasks_file, 'w') as f:
                json.dump(tasks_data, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"保存任务失败: {str(e)}")

    def update_step_parameters(self, item, column):
        """当步骤参数被修改时更新"""
        if not self.current_task:
            return

        # 只处理重复次数和延迟时间列
        if column != 3 and column != 4:
            return

        step = item.data(0, Qt.UserRole)
        if not step:
            return

        if column == 3:  # 重复次数
            try:
                new_repeat = int(item.text(3))
                step.repeat = new_repeat
            except ValueError:
                # 恢复原值
                item.setText(3, str(step.repeat))
        elif column == 4:  # 延迟时间（优先读 UserRole 的秒值）
            seconds = item.data(4, Qt.UserRole)
            if seconds is None:
                seconds = _parse_display_to_seconds(item.text(4))
            try:
                seconds = float(seconds)
            except Exception:
                seconds = step.delay  # fallback
            seconds = max(0.0, seconds)
            step.delay = seconds
            # 确保显示与 UserRole 同步（防止外部直接编辑文本产生歧义）
            item.setText(4, _format_duration_seconds(seconds))
            item.setData(4, Qt.UserRole, seconds)

    # ===== 工具：循环间隔 组合输入的换算 =====

    def _get_loop_delay_seconds_from_widgets(self) -> float:
        if not hasattr(self, "loop_delay_spin") or not hasattr(self, "loop_delay_unit"):
            return 0.0
        u = self.loop_delay_unit.currentText()
        v = self.loop_delay_spin.value()
        if u == "毫秒":
            return float(v) / 1000.0
        if u == "分钟":
            return float(v) * 60.0
        return float(v)

    def _set_loop_delay_seconds_to_widgets(self, seconds: float):
        try:
            s = float(seconds)
        except Exception:
            s = 0.0

        # 选择合适的显示单位
        if s < 1.0:
            unit = "毫秒"
        elif s >= 60.0 and abs((s / 60.0) - round(s / 60.0)) < 1e-3:
            unit = "分钟"
        else:
            unit = "秒"

        # 阻断单位切换信号，避免在设置 currentText 时触发 _on_loop_unit_change 造成二次换算
        with QSignalBlocker(self.loop_delay_unit):
            self.loop_delay_unit.setCurrentText(unit)
            self.loop_delay_prev_unit = unit  # 同步“上一次单位”

        # 直接按目标单位配置范围/后缀并设置对应值
        if unit == "毫秒":
            self.loop_delay_spin.setDecimals(0)
            self.loop_delay_spin.setRange(0, 3_600_000)
            self.loop_delay_spin.setSuffix(" 毫秒")
            self.loop_delay_spin.setValue(int(round(s * 1000.0)))
        elif unit == "秒":
            self.loop_delay_spin.setDecimals(3)
            self.loop_delay_spin.setRange(0.0, 3600.0)
            self.loop_delay_spin.setSuffix(" 秒")
            self.loop_delay_spin.setValue(s)
        else:
            self.loop_delay_spin.setDecimals(3)
            self.loop_delay_spin.setRange(0.0, 60.0)
            self.loop_delay_spin.setSuffix(" 分钟")
            self.loop_delay_spin.setValue(s / 60.0)


if __name__ == "__main__":
    app = QApplication([])
    window = MacroRecorderApp()
    window.show()
    app.exec_()