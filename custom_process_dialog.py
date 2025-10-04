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
    自定义过程（含：鼠标滚轮、智能动作、IF块、WHILE块）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomProcessDialog")
        self.setWindowTitle("自定义过程")
        self.resize(980, 680)

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
            "鼠标滚轮",  # 新增
            "键盘按下", "键盘释放", "等待",
            # 智能
            "智能点击(OCR)", "智能点击(模板)", "智能滚动直到出现(OCR)", "智能等待文本(OCR)",
            # 控制块
            "条件块(IF-OCR)", "条件块结束(END-IF)",
            "条件循环(WHILE-OCR)", "循环块结束(END-WHILE)"
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
        self.x_edit = QLineEdit(); self.x_edit.setValidator(QIntValidator(0, 999999))
        self.y_edit = QLineEdit(); self.y_edit.setValidator(QIntValidator(0, 999999))
        self.btn_capture_pos = QPushButton("取坐标")
        self.btn_capture_pos.clicked.connect(self.capture_position_once)
        preset_layout.addWidget(QLabel("X")); preset_layout.addWidget(self.x_edit)
        preset_layout.addWidget(QLabel("Y")); preset_layout.addWidget(self.y_edit)
        preset_layout.addWidget(self.btn_capture_pos)

        # 新增：滚轮方向/刻度
        self.wheel_dir = QComboBox()
        self.wheel_dir.addItems(["上", "下"])  # 上=dy>0, 下=dy<0
        self.wheel_amount = QSpinBox()
        self.wheel_amount.setRange(1, 1000)
        self.wheel_amount.setValue(1)
        self.wheel_amount.setSuffix(" 刻度")
        preset_layout.addWidget(QLabel("滚轮方向"))
        preset_layout.addWidget(self.wheel_dir)
        preset_layout.addWidget(QLabel("滚动"))
        preset_layout.addWidget(self.wheel_amount)

        # 间隔与重复
        self.delay_ms = QSpinBox(); self.delay_ms.setRange(0, 1000000); self.delay_ms.setValue(0); self.delay_ms.setSuffix(" ms")
        self.repeat = QSpinBox(); self.repeat.setRange(1, 1000000); self.repeat.setValue(1)
        preset_layout.addWidget(QLabel("间隔"))
        preset_layout.addWidget(self.delay_ms)
        preset_layout.addWidget(QLabel("重复"))
        preset_layout.addWidget(self.repeat)

        self.btn_add = QPushButton("添加到序列")
        self.btn_add.clicked.connect(self.add_action_to_list)
        preset_layout.addWidget(self.btn_add)

        main_layout.addWidget(preset_box)

        # 智能参数
        smart_box = QGroupBox("智能动作参数（OCR/模板/等待/滚动/IF/WHILE）")
        smart_layout = QHBoxLayout(smart_box)
        smart_layout.setContentsMargins(12, 12, 12, 12)
        smart_layout.setSpacing(8)

        self.smart_keywords = QLineEdit()
        self.smart_keywords.setPlaceholderText("关键词，用 | 分隔，如：下一节|Next|下一 / 已完成|完成|Done")
        smart_layout.addWidget(QLabel("关键词")); smart_layout.addWidget(self.smart_keywords, 2)

        self.smart_template = QLineEdit()
        self.smart_template.setPlaceholderText("模板图片路径（用于模板匹配）")
        self.smart_btn_template = QPushButton("选择模板")
        self.smart_btn_template.clicked.connect(self._choose_template)
        smart_layout.addWidget(QLabel("模板")); smart_layout.addWidget(self.smart_template, 2); smart_layout.addWidget(self.smart_btn_template)

        self.region_edit = QLineEdit()
        self.region_edit.setPlaceholderText("搜索区域：left,top,width,height（可留空=全屏）")
        smart_layout.addWidget(QLabel("区域")); smart_layout.addWidget(self.region_edit, 2)

        self.smart_timeout_ms = QSpinBox(); self.smart_timeout_ms.setRange(0, 3_600_000); self.smart_timeout_ms.setValue(10000); self.smart_timeout_ms.setSuffix(" ms")
        smart_layout.addWidget(QLabel("超时/最长时长")); smart_layout.addWidget(self.smart_timeout_ms)

        self.smart_require_green = QCheckBox("要求绿色命中（仅等待文本）")
        smart_layout.addWidget(self.smart_require_green)

        main_layout.addWidget(smart_box)

        # 列表
        self.tree = QTreeWidget()
        self.tree.setColumnCount(7)
        self.tree.setHeaderLabels(["类型", "按钮/键", "X", "Y", "间隔(ms)", "重复", "详情"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setColumnWidth(0, 170)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 80)
        self.tree.setColumnWidth(4, 90)
        self.tree.setColumnWidth(5, 70)
        main_layout.addWidget(self.tree, 1)

        # 底部
        bottom_layout = QHBoxLayout(); bottom_layout.setSpacing(10)
        self.btn_remove = QPushButton("删除选中"); self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("清空"); self.btn_clear.clicked.connect(self.tree.clear)
        bottom_layout.addWidget(self.btn_remove); bottom_layout.addWidget(self.btn_clear); bottom_layout.addStretch(1)
        self.btn_ok = QPushButton("保存并返回"); self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消"); self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_ok); bottom_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(bottom_layout)

        # 状态
        self._pos_listener: Optional[MouseListener] = None

        self._apply_ocean_styles()
        self.action_type.currentTextChanged.connect(self._refresh_inputs)
        self._refresh_inputs()

        self.smart_keywords.setText("下一节|Next|下一")

    def _apply_ocean_background(self):
        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0, QColor(255, 255, 255)); gradient.setColorAt(1, QColor(225, 245, 255))
        palette.setBrush(QPalette.Window, QBrush(gradient)); self.setPalette(palette)

    def _apply_ocean_styles(self):
        self.setFont(QFont("Microsoft YaHei UI", 9))
        self.setStyleSheet("""
            QGroupBox { background-color:#f0f8ff; border:2px solid #64b5f6; border-radius:10px; padding:10px; margin-top:10px; font-weight:bold; color:#1976d2; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; background-color:#f0f8ff; border-radius:5px; }
            QLabel { color:#1976d2; font-weight:bold; font-size:12px; }
            QLineEdit, QComboBox, QSpinBox { background-color:#f0f8ff; border:2px solid #64b5f6; border-radius:10px; padding:4px 8px; color:#1976d2; min-width:90px; }
            QPushButton { background-color:#64b5f6; color:white; border:2px solid #42a5f5; border-radius:15px; padding:8px 14px; font-weight:bold; font-size:12px; }
            QPushButton:hover { background:#42a5f5; } QPushButton:pressed { background:#1976d2; }
            QTreeWidget { background-color:#f0f8ff; border:2px solid #64b5f6; border-radius:10px; padding:5px; alternate-background-color:#e3f2fd; }
            QTreeWidget::item { height:28px; border-bottom:1px dashed #64b5f6; }
            QTreeWidget::item:selected { background-color:#e3f2fd; color:#1976d2; }
            QHeaderView::section { background-color:#64b5f6; color:white; font-weight:bold; padding:6px; border:1px solid #42a5f5; border-radius:5px; }
        """)

    def _refresh_inputs(self):
        t = self.action_type.currentText()
        need_button = t in ("鼠标点击", "鼠标按下", "鼠标释放")
        need_key = t in ("键盘按下", "键盘释放")
        need_pos = t in ("鼠标点击", "鼠标按下", "鼠标释放", "鼠标移动", "鼠标滚轮")
        is_smart = t in ("智能点击(OCR)", "智能点击(模板)", "智能滚动直到出现(OCR)", "智能等待文本(OCR)", "条件块(IF-OCR)", "条件循环(WHILE-OCR)")

        self.mouse_button.setEnabled(need_button)
        self.key_line.setEnabled(need_key); self.btn_capture_key.setEnabled(need_key)
        self.x_edit.setEnabled(need_pos); self.y_edit.setEnabled(need_pos); self.btn_capture_pos.setEnabled(need_pos)

        # 滚轮控件
        self.wheel_dir.setEnabled(t == "鼠标滚轮")
        self.wheel_amount.setEnabled(t == "鼠标滚轮")

        # 智能参数
        self.smart_keywords.setEnabled(is_smart)
        self.smart_template.setEnabled(t == "智能点击(模板)")
        self.smart_btn_template.setEnabled(t == "智能点击(模板)")
        self.region_edit.setEnabled(is_smart)
        self.smart_timeout_ms.setEnabled(t in ("智能点击(OCR)", "智能等待文本(OCR)", "条件循环(WHILE-OCR)"))
        self.smart_require_green.setEnabled(t == "智能等待文本(OCR)")

        if t == "等待":
            self.mouse_button.setEnabled(False); self.key_line.setEnabled(False)
            self.btn_capture_key.setEnabled(False); self.x_edit.setEnabled(False)
            self.y_edit.setEnabled(False); self.btn_capture_pos.setEnabled(False)

    def _choose_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模板图片", "", "图片 (*.png *.jpg *.jpeg *.bmp)")
        if path: self.smart_template.setText(path)

    def _parse_region(self, s: str) -> Optional[List[int]]:
        s = (s or "").strip()
        if not s: return None
        try:
            parts = [int(p.strip()) for p in s.split(",")]
            if len(parts) != 4: raise ValueError
            return parts
        except Exception:
            QMessageBox.warning(self, "区域格式错误", "区域应为 left,top,width,height（整数）或留空。")
            return None

    def capture_key_once(self):
        self.key_line.setText("")
        key_received = {"done": False, "val": ""}
        def on_press(k):
            if key_received["done"]: return False
            try:
                if getattr(k, "char", None): key_received["val"] = k.char
                else: key_received["val"] = k.name
            except Exception:
                key_received["val"] = str(k)
            key_received["done"] = True; return False
        listener = keyboard.Listener(on_press=on_press); listener.start()
        QMessageBox.information(self, "捕获按键", "请按下一个按键...")
        listener.join(timeout=5.0)
        if key_received["done"]: self.key_line.setText(key_received["val"])
        else: QMessageBox.warning(self, "超时", "未捕获到按键")

    def capture_position_once(self):
        if self._pos_listener is not None:
            try: self._pos_listener.stop()
            except Exception: pass
            self._pos_listener = None

        def on_click(x, y, button, pressed):
            if pressed:
                self.x_edit.setText(str(int(x))); self.y_edit.setText(str(int(y)))
                try:
                    if self._pos_listener: self._pos_listener.stop()
                except Exception: pass
                self._pos_listener = None; return False
            return True

        self._pos_listener = MouseListener(on_click=on_click); self._pos_listener.start()
        QMessageBox.information(self, "捕获坐标", "已开始监听。请在目标位置点击一次。")

    def _selected_block_parent(self, block_type_key: str) -> Optional[QTreeWidgetItem]:
        sels = self.tree.selectedItems()
        if not sels: return None
        it = sels[0]
        act = it.data(0, 0x0100) or {}
        if act.get("type") == block_type_key:
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
            QMessageBox.warning(self, "提示", "请先捕获或输入键盘键"); return
        if t in ("鼠标点击", "鼠标按下", "鼠标释放", "鼠标移动", "鼠标滚轮"):
            if not x or not y:
                QMessageBox.warning(self, "提示", "请先填入或捕获坐标"); return

        act: Dict[str, Any] = {"delay_ms": delay_ms, "repeat": repeat}
        detail = ""

        # 基础
        if t == "等待":
            act["type"] = "wait"; detail = f"等待 {delay_ms}ms"

        elif t == "鼠标移动":
            act["type"] = "mouse_move"; act["pos"] = [int(x), int(y)]
            detail = f"移动到({x},{y})"

        elif t == "鼠标点击":
            act["type"] = "mouse_click"; act["button"] = btn; act["pos"] = [int(x), int(y)]
            detail = f"{btn} 点击 ({x},{y})"

        elif t == "鼠标按下":
            act["type"] = "mouse_press"; act["button"] = btn; act["pos"] = [int(x), int(y)]
            detail = f"{btn} 按下 ({x},{y})"

        elif t == "鼠标释放":
            act["type"] = "mouse_release"; act["button"] = btn; act["pos"] = [int(x), int(y)]
            detail = f"{btn} 释放 ({x},{y})"

        elif t == "鼠标滚轮":
            # 方向 -> dy；上=正，下=负；dx 一般为 0
            dy = int(self.wheel_amount.value())
            if self.wheel_dir.currentText() == "下":
                dy = -dy
            act["type"] = "mouse_wheel"
            act["pos"] = [int(x), int(y)]
            act["dy"] = dy
            act["dx"] = 0
            detail = f"滚轮 {'上' if dy>0 else '下'} {abs(dy)} 刻度 @({x},{y})"

        elif t == "键盘按下":
            act["type"] = "key_press"; act["key"] = key; detail = f"键盘按下 {key}"

        elif t == "键盘释放":
            act["type"] = "key_release"; act["key"] = key; detail = f"键盘释放 {key}"

        # 智能
        elif t == "智能点击(OCR)":
            if not keywords: QMessageBox.warning(self, "提示", "请填写关键词，例如：下一节|Next"); return
            act["type"] = "smart_click_ocr"; act["keywords"] = keywords
            if region: act["region"] = region
            act["timeout"] = timeout_sec; act["prefer_area"] = "bottom-right"
            detail = f"OCR点击 关键词={ '|'.join(keywords) } 区域={region or '全屏'} 超时={int(timeout_sec*1000)}ms"

        elif t == "智能点击(模板)":
            if not template_path: QMessageBox.warning(self, "提示", "请选择模板图片"); return
            act["type"] = "smart_click_template"; act["template_path"] = template_path
            if region: act["region"] = region
            act["threshold"] = 0.84
            detail = f"模板点击 模板={template_path} 区域={region or '全屏'} 阈值=0.84"

        elif t == "智能滚动直到出现(OCR)":
            if not keywords: QMessageBox.warning(self, "提示", "请填写关键词，例如：下一节|Next"); return
            act["type"] = "smart_scroll_until_text"; act["keywords"] = keywords
            act["max_scrolls"] = 8; act["step"] = -600
            if region: act["region"] = region
            act["prefer_area"] = "bottom"
            detail = f"滚动直到出现 关键词={ '|'.join(keywords) } 次数=8 步长=-600"

        elif t == "智能等待文本(OCR)":
            if not keywords: QMessageBox.warning(self, "提示", "请填写等待的关键词，例如：已完成|完成"); return
            act["type"] = "smart_wait_text"; act["keywords"] = keywords
            if region: act["region"] = region
            act["timeout"] = max(1.0, timeout_sec); act["require_green"] = require_green
            detail = f"等待文本 关键词={ '|'.join(keywords) } 区域={region or '全屏'} 超时={int(timeout_sec*1000)}ms 绿色={require_green}"

        # 控制块：IF
        elif t == "条件块(IF-OCR)":
            if not keywords: QMessageBox.warning(self, "提示", "请填写关键词（如：下一节|Next|下一）"); return
            act["type"] = "smart_if_block_ocr"; act["keywords"] = keywords
            if region: act["region"] = region
            act["interval"] = 0.3; act["prefer_area"] = "bottom"
            detail = f"IF块(OCR) 关键词={ '|'.join(keywords) } 区域={region or '全屏'}（在此块下添加子操作）"

        elif t == "条件块结束(END-IF)":
            act["type"] = "smart_if_block_end"; detail = "IF块结束（标记）"

        # 控制块：WHILE
        elif t == "条件循环(WHILE-OCR)":
            if not keywords: QMessageBox.warning(self, "提示", "请填写关键词（如：下一节|Next|下一）"); return
            act["type"] = "smart_while_block_ocr"; act["keywords"] = keywords
            if region: act["region"] = region
            act["interval"] = 0.3; act["prefer_area"] = "bottom"
            act["max_duration"] = max(0.0, self.smart_timeout_ms.value() / 1000.0)
            act["max_loops"] = repeat
            detail = f"WHILE块(OCR) 直到命中 关键词={ '|'.join(keywords) } 区域={region or '全屏'} 周期=0.3s 最长={int(self.smart_timeout_ms.value())}ms 上限次数={repeat}（在此块下添加子操作）"

        elif t == "循环块结束(END-WHILE)":
            act["type"] = "smart_while_block_end"; detail = "WHILE块结束（标记）"

        else:
            QMessageBox.warning(self, "错误", "未知类型"); return

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

        # 插入到对应父块下
        parent_if = self._selected_block_parent("smart_if_block_ocr")
        parent_while = self._selected_block_parent("smart_while_block_ocr")

        if act.get("type") in ("smart_if_block_end", "smart_while_block_end"):
            parent = parent_if if act.get("type") == "smart_if_block_end" else parent_while
            if parent is None:
                QMessageBox.warning(self, "提示", "请先选中对应的父块，再添加“块结束”标记。")
                return
            parent.addChild(item); parent.setExpanded(True); return

        if parent_if is not None and act.get("type") not in ("smart_if_block_ocr", "smart_while_block_ocr"):
            parent_if.addChild(item); parent_if.setExpanded(True)
        elif parent_while is not None and act.get("type") not in ("smart_if_block_ocr", "smart_while_block_ocr"):
            parent_while.addChild(item); parent_while.setExpanded(True)
        else:
            self.tree.addTopLevelItem(item)
            if act.get("type") in ("smart_if_block_ocr", "smart_while_block_ocr"):
                item.setForeground(0, QBrush(QColor(25, 118, 210)))
                item.setForeground(6, QBrush(QColor(25, 118, 210)))
                font = QFont(self.font()); font.setBold(True)
                item.setFont(0, font)
                item.setExpanded(True)

    def remove_selected(self):
        for it in self.tree.selectedItems():
            parent = it.parent()
            if parent is not None:
                parent.removeChild(it)
            else:
                idx = self.tree.indexOfTopLevelItem(it)
                if idx >= 0:
                    self.tree.takeTopLevelItem(idx)

    # 递归导出
    def build_recorded_events(self) -> Tuple[List[List[Any]], str]:
        events: List[List[Any]] = []
        t = 0.0
        dt_click = 0.001

        def add_delay(tb: float, ms: int) -> float:
            if ms > 0:
                tb += ms / 1000.0
            return tb

        # 导出 WHILE 子事件为相对时序
        def emit_child_rel(it: QTreeWidgetItem, t_rel: float, children_out: List[List[Any]]) -> float:
            act = it.data(0, 0x0100) or {}
            typ = act.get("type")
            delay_ms = int(act.get("delay_ms", 0))
            repeat = int(act.get("repeat", 1))

            if typ in ("smart_if_block_end", "smart_while_block_end"):
                return t_rel

            if typ == "smart_if_block_ocr":
                t_rel = add_delay(t_rel, delay_ms)
                payload = {k: act[k] for k in ("keywords", "region", "interval", "prefer_area") if k in act}
                children_out.append(["smart_if_guard_ocr", payload, float(t_rel)])
                for ci in range(it.childCount()):
                    t_rel = emit_child_rel(it.child(ci), t_rel, children_out)
                children_out.append(["smart_end_guard", {}, float(t_rel)])
                return t_rel

            for _ in range(max(1, repeat)):
                t_rel = add_delay(t_rel, delay_ms)
                if typ == "wait":
                    continue
                elif typ == "mouse_move":
                    pos = act.get("pos")
                    if pos:
                        children_out.append(["mouse_move", [int(pos[0]), int(pos[1])], float(t_rel)])
                elif typ == "mouse_click":
                    btn = act.get("button", "left"); pos = act.get("pos")
                    if pos:
                        children_out.append(["mouse_press", btn, [int(pos[0]), int(pos[1])], float(t_rel)])
                        children_out.append(["mouse_release", btn, [int(pos[0]), int(pos[1])], float(t_rel + dt_click)])
                        t_rel += dt_click
                elif typ == "mouse_press":
                    btn = act.get("button", "left"); pos = act.get("pos")
                    if pos:
                        children_out.append(["mouse_press", btn, [int(pos[0]), int(pos[1])], float(t_rel)])
                elif typ == "mouse_release":
                    btn = act.get("button", "left"); pos = act.get("pos")
                    if pos:
                        children_out.append(["mouse_release", btn, [int(pos[0]), int(pos[1])], float(t_rel)])
                elif typ == "mouse_wheel":
                    pos = act.get("pos"); dx = int(act.get("dx", 0)); dy = int(act.get("dy", 0))
                    if pos:
                        children_out.append(["mouse_scroll", [dx, dy], [int(pos[0]), int(pos[1])], float(t_rel)])
                elif typ in ("key_press", "key_release"):
                    key = act.get("key", "")
                    if key:
                        children_out.append([typ, str(key), float(t_rel)])
                elif isinstance(typ, str) and typ.startswith("smart_"):
                    payload = {k: act[k] for k in act.keys() if k not in ("type", "delay_ms", "repeat")}
                    children_out.append([typ, payload, float(t_rel)])
            return t_rel

        def emit_item(it: QTreeWidgetItem, t_base: float) -> float:
            act = it.data(0, 0x0100) or {}
            typ = act.get("type")
            delay_ms = int(act.get("delay_ms", 0))
            repeat = int(act.get("repeat", 1))

            # IF 块（父）
            if typ == "smart_if_block_ocr":
                for _ in range(max(1, repeat)):
                    t1 = add_delay(t_base, delay_ms)
                    payload = {k: act[k] for k in ("keywords", "region", "interval", "prefer_area") if k in act}
                    events.append(["smart_if_guard_ocr", payload, float(t1)])
                    t_child = t1
                    for ci in range(it.childCount()):
                        c = it.child(ci)
                        if (c.data(0, 0x0100) or {}).get("type") == "smart_if_block_end":
                            continue
                        t_child = emit_item(c, t_child)
                    events.append(["smart_end_guard", {}, float(t_child)])
                    t_base = t_child
                return t_base

            # WHILE 块（父）
            if typ == "smart_while_block_ocr":
                for _ in range(max(1, repeat)):
                    t1 = add_delay(t_base, delay_ms)
                    children_rel: List[List[Any]] = []
                    t_rel = 0.0
                    for ci in range(it.childCount()):
                        c = it.child(ci)
                        if (c.data(0, 0x0100) or {}).get("type") == "smart_while_block_end":
                            continue
                        t_rel = emit_child_rel(c, t_rel, children_rel)
                    payload = {
                        "keywords": act.get("keywords", []),
                        "region": act.get("region"),
                        "interval": float(act.get("interval", 0.3)),
                        "prefer_area": act.get("prefer_area", "bottom"),
                        "max_duration": float(act.get("max_duration", 30.0)),
                        "max_loops": int(act.get("max_loops", 200)),
                        "children": children_rel
                    }
                    events.append(["smart_while_ocr", payload, float(t1)])
                    t_base = t1
                return t_base

            # 结束标记：忽略
            if typ in ("smart_if_block_end", "smart_while_block_end"):
                return t_base

            # 常规与智能（顶层）
            if typ == "wait":
                return add_delay(t_base, delay_ms)
            elif typ == "mouse_move":
                pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_move", [int(pos[0]), int(pos[1])], float(t_base)])
                return t_base
            elif typ == "mouse_click":
                btn = act.get("button", "left"); pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_press", btn, [int(pos[0]), int(pos[1])], float(t_base)])
                        events.append(["mouse_release", btn, [int(pos[0]), int(pos[1])], float(t_base + dt_click)])
                        t_base += dt_click
                return t_base
            elif typ == "mouse_press":
                btn = act.get("button", "left"); pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_press", btn, [int(pos[0]), int(pos[1])], float(t_base)])
                return t_base
            elif typ == "mouse_release":
                btn = act.get("button", "left"); pos = act.get("pos")
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_release", btn, [int(pos[0]), int(pos[1])], float(t_base)])
                return t_base
            elif typ == "mouse_wheel":
                pos = act.get("pos"); dx = int(act.get("dx", 0)); dy = int(act.get("dy", 0))
                if pos:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append(["mouse_scroll", [dx, dy], [int(pos[0]), int(pos[1])], float(t_base)])
                return t_base
            elif typ in ("key_press", "key_release"):
                key = act.get("key", "")
                if key:
                    for _ in range(max(1, repeat)):
                        t_base = add_delay(t_base, delay_ms)
                        events.append([typ, str(key), float(t_base)])
                return t_base
            elif isinstance(typ, str) and typ.startswith("smart_"):
                payload = {k: act[k] for k in act.keys() if k not in ("type", "delay_ms", "repeat")}
                for _ in range(max(1, repeat)):
                    t_base = add_delay(t_base, delay_ms)
                    events.append([typ, payload, float(t_base)])
                return t_base

            return t_base

        for i in range(self.tree.topLevelItemCount()):
            t = emit_item(self.tree.topLevelItem(i), t)

        default_name = time.strftime("custom_%Y%m%d_%H%M%S.json")
        return events, default_name