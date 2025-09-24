import sys
from PyQt5.QtWidgets import QApplication
from main_window import MacroRecorderApp
from custom_process_integration import install_custom_process_feature

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion主题

    # 设置应用程序样式
    app.setStyleSheet("""
        QPushButton {
            padding: 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        QListWidget, QTreeWidget {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 5px;
        }
        QLabel {
            padding: 5px;
        }
        QGroupBox {
            border: 1px solid #aaa;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
        }
        QTreeWidget::item {
            height: 25px;
        }
    """)

    try:
        window = MacroRecorderApp()
        # 最小侵入式安装“自定义过程”功能（新增“工具->自定义过程...”菜单项）
        install_custom_process_feature(window)

        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"启动失败: {e}")