from typing import List
from PyQt5.QtWidgets import QMainWindow, QAction, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from custom_process_dialog import CustomProcessDialog


def install_custom_process_feature(window: QMainWindow):
    """
    将“自定义过程”功能以最小侵入方式集成到主窗口：
    - 在菜单栏新增“工具”菜单 -> “自定义过程…”
    - 打开对话框构建事件后，直接写入 window.recorder.recorded_events
    - 更新状态与事件数显示，并可选择保存
    依赖主窗口具备以下属性：
      - recorder: 含 recorded_events 列表
      - info_label: QLabel，用于显示“录制事件数: N”
      - status_label: QLabel，用于显示状态
      - save_recording(name: str): 保存录制的方法（已有）
      - prompt_save_recording(): 触发保存提示的方法（已有，若无则用 save_recording 替代）
    """
    # 获取或创建“工具”菜单
    menubar = window.menuBar()
    tools_menu = None
    for a in menubar.actions():
        if a.text().replace("&", "") == "工具":
            tools_menu = a.menu()
            break
    if tools_menu is None:
        tools_menu = menubar.addMenu("工具")

    # 新增“自定义过程...”菜单项
    action = QAction(QIcon(), "自定义过程...", window)
    action.setShortcutVisibleInContextMenu(True)
    action.setShortcut("Ctrl+Alt+C")

    def on_trigger():
        dlg = CustomProcessDialog(window)
        if dlg.exec_() == dlg.Accepted:
            events, default_name = dlg.build_recorded_events()

            # 将事件直接放入当前录制缓冲
            try:
                # 对事件按时间戳排序（稳妥起见）
                def _t(e):
                    # e 结构可能是:
                    #   ["key_press", key, t]
                    #   ["key_release", key, t]
                    #   ["mouse_move", [x,y], t]
                    #   ["mouse_press", btn, [x,y], t]
                    #   ["mouse_release", btn, [x,y], t]
                    return float(e[-1])
                events_sorted: List[list] = sorted(events, key=_t)
            except Exception:
                events_sorted = events

            # 写入主程序的 recorder
            if hasattr(window, "recorder"):
                window.recorder.recorded_events = events_sorted

            # 更新UI状态（不改变原有样式，仅设置文本）
            if hasattr(window, "info_label"):
                try:
                    window.info_label.setText(f"录制事件数: {len(events_sorted)}")
                except Exception:
                    pass
            if hasattr(window, "status_label"):
                try:
                    window.status_label.setText("状态: 已载入自定义过程")
                except Exception:
                    pass

            # 询问是否立即保存
            ret = QMessageBox.question(
                window,
                "保存自定义过程",
                "是否将当前自定义过程保存为录制文件？",
                QMessageBox.Yes | QMessageBox.No
            )
            if ret == QMessageBox.Yes:
                # 优先调用已有的保存流程以保持一致体验
                if hasattr(window, "prompt_save_recording"):
                    try:
                        window.prompt_save_recording()
                        return
                    except Exception:
                        pass
                if hasattr(window, "save_recording"):
                    try:
                        window.save_recording(default_name)
                    except Exception as e:
                        QMessageBox.warning(window, "保存失败", f"保存时出现错误: {e}")

    action.triggered.connect(on_trigger)
    tools_menu.addAction(action)