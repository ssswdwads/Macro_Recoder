from PyQt5.QtWidgets import QStyledItemDelegate, QSpinBox, QDoubleSpinBox
from PyQt5.QtCore import Qt

class SpinBoxDelegate(QStyledItemDelegate):
    """自定义委托用于在树形视图中显示数字输入框"""

    def createEditor(self, parent, option, index):
        if index.column() == 3:  # 重复次数列
            editor = QSpinBox(parent)
            editor.setRange(1, 10000)
            editor.setValue(1)
            return editor
        elif index.column() == 4:  # 延迟时间列
            editor = QDoubleSpinBox(parent)
            editor.setRange(0.0, 3600.0)
            editor.setValue(0.0)
            editor.setSuffix(" 秒")
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole)
        if isinstance(editor, QSpinBox):
            editor.setValue(int(value) if value else 1)
        elif isinstance(editor, QDoubleSpinBox):
            editor.setValue(float(value) if value else 0.0)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QSpinBox):
            model.setData(index, editor.value(), Qt.EditRole)
        elif isinstance(editor, QDoubleSpinBox):
            model.setData(index, editor.value(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)