import time
from typing import List, Dict, Any, Optional, Tuple

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox,
    QLineEdit, QGroupBox, QTreeWidget, QTreeWidgetItem, QMessageBox, QFileDialog, QCheckBox
)
from PyQt5.QtGui import QIntValidator, QPalette, QColor, QBrush, QLinearGradient, QFont
from PyQt5.QtCore import Qt

from pynput import keyboard
from pynput.mouse import Listener as MouseListener


class CustomProcessDialog(QDialog):
    """
    自定义过程对话框（最小侵入 + 条件块）
    - 基础动作：鼠标移动/点击/按下/释放、键盘按下/释放、等待
    - 智能动作：OCR 点击、模板点击、滚动直到出现、等待文本、静音
    - 控制结构：条件开始/结束（兼容）、条件块(IF-OCR)（推荐）
    - 导出为“基于时间戳”的事件列表，与录制一致
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomProcessDialog")
        self.setWindowTitle("自定义过程")
        self.resize(960, 660)

        # 背景
        self._apply_ocean_background()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # 预设动作区
        preset_box = QGroupBox("添加动作")
        preset_layout = QHBoxLayout(preset_box)
        preset_layout.setContentsMargins(12, 12, 12, 12)
        preset_layout.setSpacing(8)

        self.action_type = QComboBox()
        self.action_type.addItems([
            "鼠标点击", "鼠标按下", "鼠标释放", "鼠标移动",
            "键盘按下", "键盘释放", "等待",
            # 智能
            "智能点击(OCR)", "智能点击(模板)", "智能滚动直到出现(OCR)", "智能等待文本(OCR)", "设置静音",
            # 控制（兼容旧）
            "条件开始(IF-OCR)", "条件结束(END-IF)",
            # 新：条件块（推荐）
            "条件块(IF-OCR)"
        ])
        preset_layout.addWidget(QLabel("类型"))
        preset_layout.addWidget(self.action_type)

        self.mouse_button = QComboBox()
        self.mouse_button.addItems(["left", "right", "middle"])
        preset_layout.addWidget(QLabel("鼠标键"))
        preset_layout.addWidget(self.mouse_button)

        self.key_line = QLineEdit()
        self.key_line.setPlaceholderText("按下“捕获按键”或直接输入，如 a / enter / esc / f1")
        preset_layout.addWidget(QLabel("键盘键"))
        preset_layout.addWidget(self.key_line)

        self.btn_capture_key = QPushButton("捕获按键")
        self.btn_capture_key.clicked.connect(self.capture_key_once)
        preset_layout.addWidget(self.btn_capture_key)

        # 坐标
        self.x_edit = QLineEdit()
        self.x_edit.setValidator(QIntValidator(0, 999999))
        self.y_edit = QLineEdit()
        self.y_edit.setValidator(QIntValidator(0, 999999))
        self.btn_capture_pos = QPushButton("取坐标")
        self.btn_capture_pos.clicked.connect(self.capture_position_once)

        preset_layout.addWidget(QLabel("X"))
        preset_layout.addWidget(self.x_edit)
        preset_layout.addWidget(QLabel("Y"))
        preset_layout.addWidget(self.y_edit)
        preset_layout.addWidget(self.btn_capture_pos)

        # 间隔与重复
        self.delay_ms = QSpinBox()
        self.delay_ms.setRange(0, 1000000)
        self.delay_ms.setValue(0)
        self.delay_ms.setSuffix(" ms")
        self.repeat = QSpinBox()
        self.repeat.setRange(1, 1000000)
        self.repeat.setValue(1)
        preset_layout.addWidget(QLabel("间隔"))
        preset_layout.addWidget(self.delay_ms)
        preset_layout.addWidget(QLabel("重复"))
        preset_layout.addWidget(self.repeat)

        self.btn_add = QPushButton("添加到序列")
        self.btn_add.clicked.connect(self.add_action_to_list)
        preset_layout.addWidget(self.btn_add)

        main_layout.addWidget(preset_box)

        # 智能参数区（智能类型与 IF-OCR 生效）
        smart_box = QGroupBox("智能动作参数（OCR/模板/等待/滚动/IF）")
        smart_layout = QHBoxLayout(smart_box)
        smart_layout.setContentsMargins(12, 12, 12, 12)
        smart_layout.setSpacing(8)

        self.smart_keywords = QLineEdit()
        self.smart_keywords.setPlaceholderText("关键词，用 | 分隔，如：下一节|Next|下一 / 已完成|完成|Done")
        smart_layout.addWidget(QLabel("关键词"))
        smart_layout.addWidget(self.smart_keywords, 2)

        self.smart_template = QLineEdit()
        self.smart_template.setPlaceholderText("模板图片路径（用于模板匹配）")
        self.smart_btn_template = QPushButton("选择模板")
        self.smart_btn_template.clicked.connect(self._choose_template)
        smart_layout.addWidget(QLabel("模板"))
        smart_layout.addWidget(self.smart_template, 2)
        smart_layout.addWidget(self.smart_btn_template)

        self.region_edit = QLineEdit()
        self.region_edit.setPlaceholderText("搜索区域：left,top,width,height（可留空=全屏）")
        smart_layout.addWidget(QLabel("区域"))
        smart_layout.addWidget(self.region_edit, 2)

        self.smart_timeout_ms = QSpinBox()
        self.smart_timeout_ms.setRange(0, 3_600_000)
        self.smart_timeout_ms.setValue(10000)
        self.smart_timeout_ms.setSuffix(" ms")
        smart_layout.addWidget(QLabel("超时"))
        smart_layout.addWidget(self.smart_timeout_ms)

        self.smart_require_green = QCheckBox("要求绿色命中（仅等待文本）")
        smart_layout.addWidget(self.smart_require_green)

        main_layout.addWidget(smart_box)

        # 列表
        self.tree = QTreeWidget()
        self.tree.setColumnCount(7)
        self.tree.setHeaderLabels(["类型", "按钮/键", "X", "Y", "间隔(ms)", "重复", "详情"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)  # 允许分层
        self.tree.setUniformRowHeights(True)
        self.tree.setColumnWidth(0, 160)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 80)
        self.tree.setColumnWidth(4, 90)
        self.tree.setColumnWidth(5, 70)
        main_layout.addWidget(self.tree, 1)

        # 底部
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.btn_remove = QPushButton("删除选中")
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self.tree.clear)

        bottom_layout.addWidget(self.btn_remove)
        bottom_layout.addWidget(self.btn_clear)
        bottom_layout.addStretch(1)

        self.btn_ok = QPushButton("保存并返回")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)

        bottom_layout.addWidget(self.btn_ok)
        bottom_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(bottom_layout)

        # 状态
        self._pos_listener: Optional[MouseListener] = None

        # 样式
        self._apply_ocean_styles()

        # 事件
        self.action_type.currentTextChanged.connect(self._refresh_inputs)
        self._refresh_inputs()

        # 默认值
        self.smart_keywords.setText("下一节|Next|下一")

    def _apply_ocean_background(self):
        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0, QColor(255, 255, 255))
        gradient.setColorAt(1, QColor(225, 245, 255))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)

    def _apply_ocean_styles(self):
        self.setFont(QFont("Microsoft YaHei UI", 9))
        self.setStyleSheet("""
            QGroupBox {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 10px;
                margin-top: 10px;
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
            QLabel {
                color: #1976d2;
                font-weight: bold;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 6px 8px;
                color: #1976d2;
                min-width: 80px;
            }
            QLineEdit:focus {
                border: 2px solid #42a5f5;
                background-color: #e3f2fd;
            }
            QComboBox {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 4px 8px;
                color: #1976d2;
                min-width: 90px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid #64b5f6;
                selection-background-color: #e3f2fd;
                selection-color: #1976d2;
            }
            QSpinBox {
                background-color: #f0f8ff;
                border: 2px solid #64b5f6;
                border-radius: 10px;
                padding: 4px 6px;
                color: #1976d2;
                min-width: 90px;
                font-weight: bold;
            }
            QSpinBox:focus {
                border: 2px solid #42a5f5;
                background-color: #e3f2fd;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #64b5f6;
                width: 18px;
                border-left: 1px solid #42a5f5;
            }
            QPushButton {
                background-color: #64b5f6;
                color: white;
                border: 2px solid #42a5f5;
                border-radius: 15px;
                padding: 8px 14px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #42a5f5; }
            QPushButton:pressed { background-color: #1976d2; }
            QPushButton:disabled { background-color: #d3d3d3; color: #a0a0a0; }
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
                padding: 6px;
                border: 1px solid #42a5f5;
                border-radius: 5px;
            }
        """)

    def _refresh_inputs(self):
        t = self.action_type.currentText()
        need_button = t in ("鼠标点击", "鼠标按下", "鼠标释放")
        need_key = t in ("键盘按下", "键盘释放")
        need_pos = t in ("鼠标点击", "鼠标按下", "鼠标释放", "鼠标移动")
        is_smart = t in ("智能点击(OCR)", "智能点击(模板)", "智能滚动直到出现(OCR)", "智能等待文本(OCR)", "设置静音",
                         "条件开始(IF-OCR)", "条件块(IF-OCR)")

        self.mouse_button.setEnabled(need_button)
        self.key_line.setEnabled(need_key)
        self.btn_capture_key.setEnabled(need_key)
        self.x_edit.setEnabled(need_pos)
        self.y_edit.setEnabled(need_pos)
        self.btn_capture_pos.setEnabled(need_pos)

        # 智能参数
        self.smart_keywords.setEnabled(is_smart)
        self.smart_template.setEnabled(t == "智能点击(模板)")
        self.smart_btn_template.setEnabled(t == "智能点击(模板)")
        self.region_edit.setEnabled(is_smart)
        self.smart_timeout_ms.setEnabled(t in ("智能点击(OCR)", "智能等待文本(OCR)"))
        self.smart_require_green.setEnabled(t == "智能等待文本(OCR)")

        if t == "等待":
            self.mouse_button.setEnabled(False)
            self.key_line.setEnabled(False)
            self.btn_capture_key.setEnabled(False)
            self.x_edit.setEnabled(False)
            self.y_edit.setEnabled(False)
            self.btn_capture_pos.setEnabled(False)

    def _choose_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模板图片", "", "图片 (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.smart_template.setText(path)

    def _parse_region(self, s: str) -> Optional[List[int]]:
        s = (s or "").strip()
        if not s:
            return None
        try:
            parts = [int(p.strip()) for p in s.split(",")]
            if len(parts) != 4:
                raise ValueError
            return parts
        except Exception:
            QMessageBox.warning(self, "区域格式错误", "区域应为 left,top,width,height（整数）或留空。")
            return None

    def capture_key_once(self):
        self.key_line.setText("")
        key_received = {"done": False, "val": ""}

        def on_press(k):
            if key_received["done"]:
                return False
            try:
                if getattr(k, "char", None):
                    key_received["val"] = k.char
                else:
                    key_received["val"] = k.name
            except Exception:
                key_received["val"] = str(k)
            key_received["done"] = True
            return False

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        QMessageBox.information(self, "捕获按键", "请按下一个按键...")
        listener.join(timeout=5.0)
        if key_received["done"]:
            self.key_line.setText(key_received["val"])
        else:
            QMessageBox.warning(self, "超时", "未捕获到按键")

    def capture_position_once(self):
        if self._pos_listener is not None:
            try:
                self._pos_listener.stop()
            except Exception:
                pass
            self._pos_listener = None

        def on_click(x, y, button, pressed):
            if pressed:
                self.x_edit.setText(str(int(x)))
                self.y_edit.setText(str(int(y)))
                try:
                    if self._pos_listener:
                        self._pos_listener.stop()
                except Exception:
                    pass
                self._pos_listener = None
                return False
            return True

        self._pos_listener = MouseListener(on_click=on_click)
        self._pos_listener.start()
        QMessageBox.information(self, "捕获坐标", "已开始监听。请在目标位置点击一次。")

    def _selected_if_block_parent(self) -> Optional[QTreeWidgetItem]:
        """若当前选中的是“条件块(IF-OCR)”父节点，则返回它；否则 None"""
        sels = self.tree.selectedItems()
        if not sels:
            return None
        it = sels[0]
        act = it.data(0, 0x0100) or {}
        if act.get("type") == "smart_if_block_ocr":
            return it
        return None

    def add_action_to_list(self):
        t = self.action_type.currentText()
        delay_ms = self.delay_ms.value()
        repeat = self.repeat.value()

        btn = self.mouse_button.currentText()
        key = self.key_line.text().strip()
        x = self.x_edit.text().strip()
        y = self.y_edit.text().strip()

        # 智能参数
        keywords = [k.strip() for k in self.smart_keywords.text().split("|") if k.strip()]
        region = self._parse_region(self.region_edit.text())
        timeout_sec = max(0.0, self.smart_timeout_ms.value() / 1000.0)
        require_green = bool(self.smart_require_green.isChecked())
        template_path = self.smart_template.text().strip()

        # 传统校验
        if t in ("键盘按下", "键盘释放") and not key:
            QMessageBox.warning(self, "提示", "请先捕获或输入键盘键")
            return
        if t in ("鼠标点击", "鼠标按下", "鼠标释放", "鼠标移动"):
            if not x or not y:
                QMessageBox.warning(self, "提示", "请先填入或捕获坐标")
                return

        act: Dict[str, Any] = {"delay_ms": delay_ms, "repeat": repeat}
        detail = ""

        # 基础类型
        if t == "等待":
            act["type"] = "wait"
            detail = f"等待 {delay_ms}ms"
        elif t == "鼠标移动":
            act["type"] = "mouse_move"
            act["pos"] = [int(x), int(y)]
            detail = f"移动到({x},{y})"
        elif t == "鼠标点击":
            act["type"] = "mouse_click"
            act["button"] = btn
            act["pos"] = [int(x), int(y)]
            detail = f"{btn} 点击 ({x},{y})"
        elif t == "鼠标按下":
            act["type"] = "mouse_press"
            act["button"] = btn
            act["pos"] = [int(x), int(y)]
            detail = f"{btn} 按下 ({x},{y})"
        elif t == "鼠标释放":
            act["type"] = "mouse_release"
            act["button"] = btn
            act["pos"] = [int(x), int(y)]
            detail = f"{btn} 释放 ({x},{y})"
        elif t == "键盘按下":
            act["type"] = "key_press"
            act["key"] = key
            detail = f"键盘按下 {key}"
        elif t == "键盘释放":
            act["type"] = "key_release"
            act["key"] = key
            detail = f"键盘释放 {key}"

        # 智能类型
        elif t == "智能点击(OCR)":
            if not keywords:
                QMessageBox.warning(self, "提示", "请填写关键词，例如：下一节|Next")
                return
            act["type"] = "smart_click_ocr"
            act["keywords"] = keywords
            if region:
                act["region"] = region
            act["timeout"] = timeout_sec
            act["prefer_area"] = "bottom-right"
            detail = f"OCR点击 关键词={ '|'.join(keywords) } 区域={region or '全屏'} 超时={int(timeout_sec*1000)}ms"
        elif t == "智能点击(模板)":
            if not template_path:
                QMessageBox.warning(self, "提示", "请选择模板图片")
                return
            act["type"] = "smart_click_template"
            act["template_path"] = template_path
            if region:
                act["region"] = region
            act["threshold"] = 0.84
            detail = f"模板点击 模板={template_path} 区域={region or '全屏'} 阈值=0.84"
        elif t == "智能滚动直到出现(OCR)":
            if not keywords:
                QMessageBox.warning(self, "提示", "请填写关键词，例如：下一节|Next")
                return
            act["type"] = "smart_scroll_until_text"
            act["keywords"] = keywords
            act["max_scrolls"] = 8
            act["step"] = -600
            if region:
                act["region"] = region
            act["prefer_area"] = "bottom"
            detail = f"滚动直到出现 关键词={ '|'.join(keywords) } 次数=8 步长=-600"
        elif t == "智能等待文本(OCR)":
            if not keywords:
                QMessageBox.warning(self, "提示", "请填写等待的关键词，例如：已完成|完成")
                return
            act["type"] = "smart_wait_text"
            act["keywords"] = keywords
            if region:
                act["region"] = region
            act["timeout"] = max(1.0, timeout_sec)
            act["require_green"] = require_green
            detail = f"等待文本 关键词={ '|'.join(keywords) } 区域={region or '全屏'} 超时={int(timeout_sec*1000)}ms 绿色={require_green}"
        elif t == "设置静音":
            act["type"] = "smart_mute"
            act["strategy"] = "press_m"
            detail = "静音（按 m）"

        # 兼容：IF 起止（保留）
        elif t == "条件开始(IF-OCR)":
            if not keywords:
                QMessageBox.warning(self, "提示", "请填写关键词（如：下一节|Next|下一）")
                return
            act["type"] = "smart_if_guard_ocr"
            act["keywords"] = keywords
            if region:
                act["region"] = region
            act["interval"] = 0.3
            act["prefer_area"] = "bottom"
            detail = f"IF开始(OCR) 命中即跳出 关键词={ '|'.join(keywords) } 区域={region or '全屏'}"
        elif t == "条件结束(END-IF)":
            act["type"] = "smart_end_guard"
            detail = "END-IF"

        # 新：条件块（父节点，可包含子项）
        elif t == "条件块(IF-OCR)":
            if not keywords:
                QMessageBox.warning(self, "提示", "请填写关键词（如：下一节|Next|下一）")
                return
            act["type"] = "smart_if_block_ocr"
            act["keywords"] = keywords
            if region:
                act["region"] = region
            act["interval"] = 0.3
            act["prefer_area"] = "bottom"
            detail = f"IF块(OCR) 关键词={ '|'.join(keywords) } 区域={region or '全屏'}（在此块下添加子操作）"
        else:
            QMessageBox.warning(self, "错误", "未知类型")
            return

        # 构造树项
        item = QTreeWidgetItem([
            t,
            act.get("button", act.get("key", "")),
            str(act.get("pos", ["", ""])[0] if "pos" in act else ""),
            str(act.get("pos", ["", ""])[1] if "pos" in act else ""),
            str(delay_ms),
            str(repeat),
            detail
        ])
        item.setData(0, 0x0100, act)

        # 插入位置：若选中 IF 块父节点，则作为其子项；否则顶层
        parent_block = self._selected_if_block_parent()
        if parent_block is not None and act.get("type") != "smart_if_block_ocr":
            parent_block.addChild(item)
            parent_block.setExpanded(True)
        else:
            # IF 块自身或普通事件都加到顶层
            self.tree.addTopLevelItem(item)
            # IF 块项高亮显示，便于辨识
            if act.get("type") == "smart_if_block_ocr":
                item.setForeground(0, QBrush(QColor(25, 118, 210)))
                item.setForeground(6, QBrush(QColor(25, 118, 210)))
                font = QFont(self.font()); font.setBold(True)
                item.setFont(0, font)
                item.setExpanded(True)

    def remove_selected(self):
        for it in self.tree.selectedItems():
            # 既支持删除父块（连同子项），也支持删除单个子项
            parent = it.parent()
            if parent is not None:
                parent.removeChild(it)
            else:
                idx = self.tree.indexOfTopLevelItem(it)
                if idx >= 0:
                    self.tree.takeTopLevelItem(idx)

    # 递归导出：遇到 IF-块父节点 -> 输出 start，递归导出子项 -> 输出 end
    def build_recorded_events(self) -> Tuple[List[List[Any]], str]:
        events: List[List[Any]] = []
        t = 0.0
        dt_click = 0.001

        def emit_item(it: QTreeWidgetItem, t_base: float) -> float:
            act = it.data(0, 0x0100) or {}
            typ = act.get("type")
            delay_ms = int(act.get("delay_ms", 0))
            repeat = int(act.get("repeat", 1))

            # 工具函数
            def add_delay(tb: float, ms: int) -> float:
                if ms > 0:
                    tb += ms / 1000.0
                return tb

            # 条件块：父节点
            if typ == "smart_if_block_ocr":
                for _ in range(max(1, repeat)):
                    t1 = add_delay(t_base, delay_ms)
                    payload = {k: act[k] for k in ("keywords", "region", "interval", "prefer_area") if k in act}
                    events.append(["smart_if_guard_ocr", payload, float(t1)])
                    # 子项顺序导出
                    child_count = it.childCount()
                    t_child = t1
                    for ci in range(child_count):
                        t_child = emit_item(it.child(ci), t_child)
                    # 结束守护，时间戳取子项后的当前 t
                    events.append(["smart_end_guard", {}, float(t_child)])
                    t_base = t_child
                return t_base

            # 普通与智能（非块）
            if typ == "wait":
                return add_delay(t_base, delay_ms)

            if typ == "mouse_move":
                pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_move", [int(pos[0]), int(pos[1])], float(t_base)])
                return t_base

            if typ == "mouse_click":
                btn = act.get("button", "left"); pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_press", btn, [int(pos[0]), int(pos[1])], float(t_base)])
                        events.append(["mouse_release", btn, [int(pos[0]), int(pos[1])], float(t_base + dt_click)])
                        t_base += dt_click
                return t_base

            if typ == "mouse_press":
                btn = act.get("button", "left"); pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_press", btn, [int(pos[0]), int(pos[1])], float(t_base)])
                return t_base

            if typ == "mouse_release":
                btn = act.get("button", "left"); pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_release", btn, [int(pos[0]), int(pos[1])], float(t_base)])
                return t_base

            if typ in ("key_press", "key_release"):
                key = act.get("key", "")
                if key:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append([typ, str(key), float(t_base)])
                return t_base

            # 智能与 IF-开始/结束（兼容旧）
            if isinstance(typ, str) and typ.startswith("smart_"):
                payload = {k: act[k] for k in act.keys() if k not in ("type", "delay_ms", "repeat")}
                for _ in range(max(1, repeat)):
                    t_base = add_delay(t_base, delay_ms)
                    events.append([typ, payload, float(t_base)])
                return t_base

            return t_base

        # 顶层逐项导出（支持混合：普通、智能、IF块）
        for i in range(self.tree.topLevelItemCount()):
            t = emit_item(self.tree.topLevelItem(i), t)

        default_name = time.strftime("custom_%Y%m%d_%H%M%S.json")
        return events, default_name