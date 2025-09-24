from PyQt5.QtWidgets import (
    QStyledItemDelegate,
    QSpinBox,
    QDoubleSpinBox,
    QWidget,
    QComboBox,
    QHBoxLayout,
)
from PyQt5.QtCore import Qt, QModelIndex


def _format_duration_seconds(seconds: float) -> str:
    """
    将秒的浮点值格式化成最合适的单位字符串（毫秒/秒/分钟）
    规则：
    - < 1s 使用 毫秒 显示（取整到毫秒）
    - >= 60s 且是整数分钟（或接近）优先显示 分钟
    - 其他使用 秒，保留最多 3 位小数（去掉尾部无意义的 0）
    """
    if seconds is None:
        return "0 毫秒"
    try:
        s = float(seconds)
    except Exception:
        s = 0.0

    if s < 1.0:
        ms = int(round(s * 1000.0))
        return f"{ms} 毫秒"
    if s >= 60.0:
        mins = s / 60.0
        # 若接近整数分钟（容差 0.001）
        if abs(mins - round(mins)) < 1e-3:
            return f"{int(round(mins))} 分钟"
    # 以秒显示，最多 3 位小数
    text = f"{s:.3f}".rstrip("0").rstrip(".")
    return f"{text} 秒"


def _parse_display_to_seconds(text: str):
    """
    尝试从显示文本中解析出“秒”的浮点值。
    支持：
    - "123" / "123.45"（默认按秒）
    - "500 毫秒" / "500ms"
    - "1.5 秒" / "1.5s"
    - "2 分钟" / "2min" / "2 分"
    """
    if text is None:
        return 0.0
    s = str(text).strip().lower()
    try:
        # 纯数字（默认秒）
        return float(s)
    except Exception:
        pass

    # 单位解析
    num = ""
    for ch in s:
        if ch.isdigit() or ch in ".-":
            num += ch
        elif ch == ",":
            # 容错：逗号作为小数点
            num += "."
        else:
            # 跳过其它
            pass
    if num == "" or num == "." or num == "-":
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
    # 默认按秒
    return max(0.0, num_val)


class _DelayUnitEditor(QWidget):
    """
    组合编辑器：数值 + 单位选择（毫秒/秒/分钟）
    对外以“秒”为单位的浮点值进行 get/set。
    限制范围：0ms – 60min
    """
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
        if u == "毫秒":
            self.spin.setDecimals(0)
            self.spin.setRange(0, 3_600_000)  # 0ms ~ 60min
            self.spin.setSuffix(" 毫秒")
            if self.spin.value() < 1 and self.spin.value() != 0:
                # 之前是秒的小数，切换成毫秒时避免显示 0
                self.spin.setValue(max(1, int(round(self.spin.value() * 1000.0))))
        elif u == "秒":
            self.spin.setDecimals(3)
            self.spin.setRange(0.0, 3600.0)  # 0s ~ 60min
            self.spin.setSuffix(" 秒")
        else:  # 分钟
            self.spin.setDecimals(3)
            self.spin.setRange(0.0, 60.0)  # 0min ~ 60min
            self.spin.setSuffix(" 分钟")

    def set_seconds(self, seconds: float):
        try:
            s = float(seconds)
        except Exception:
            s = 0.0
        # 选择一个合适的显示单位
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


class SpinBoxDelegate(QStyledItemDelegate):
    """
    表格编辑委托：
    - 第3列（重复次数）：QSpinBox
    - 第4列（延迟）：_DelayUnitEditor（毫秒/秒/分钟），写回为“秒”的浮点值
    其它列沿用默认。
    """
    def createEditor(self, parent, option, index: QModelIndex):
        if index.column() == 3:
            editor = QSpinBox(parent)
            editor.setRange(1, 10000)
            editor.setValue(1)
            return editor
        elif index.column() == 4:
            return _DelayUnitEditor(parent)
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index: QModelIndex):
        value = index.model().data(index, Qt.DisplayRole)
        # 重复次数
        if isinstance(editor, QSpinBox):
            try:
                editor.setValue(int(value) if value not in (None, "") else 1)
            except Exception:
                editor.setValue(1)
            return

        # 延迟（以秒为内部基准）
        if isinstance(editor, _DelayUnitEditor):
            # 优先从 UserRole 读“秒”，没有再解析显示文本
            user_seconds = index.model().data(index, Qt.UserRole)
            if user_seconds is not None:
                try:
                    s = float(user_seconds)
                except Exception:
                    s = 0.0
            else:
                s = _parse_display_to_seconds(str(value) if value is not None else "0")
            editor.set_seconds(s)
            return

        # 默认
        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index: QModelIndex):
        # 重复次数
        if isinstance(editor, QSpinBox):
            model.setData(index, editor.value(), Qt.EditRole)
            return

        # 延迟（回写为“秒”的浮点值，同时设置友好显示文本和 UserRole）
        if isinstance(editor, _DelayUnitEditor):
            seconds = max(0.0, float(editor.seconds()))
            model.setData(index, seconds, Qt.EditRole)  # 存“秒”作为可编辑值
            model.setData(index, _format_duration_seconds(seconds), Qt.DisplayRole)
            model.setData(index, seconds, Qt.UserRole)  # 存“秒”方便下次读取
            return

        # 默认
        super().setModelData(editor, model, index)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)