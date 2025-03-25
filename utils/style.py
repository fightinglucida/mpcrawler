"""
扁平化风格的样式表定义
"""

def get_flat_style():
    """返回扁平化风格的样式表"""
    return """
    QMainWindow, QDialog {
        background-color: #f5f5f5;
    }
    
    QLabel {
        color: #333333;
        font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
    }
    
    QPushButton {
        background-color: #2196F3;
        color: white;
        border: none;
        padding: 5px 15px;
        border-radius: 3px;
        font-weight: bold;
        font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
    }
    
    QPushButton:hover {
        background-color: #1976D2;
    }
    
    QPushButton:pressed {
        background-color: #0D47A1;
    }
    
    QPushButton:disabled {
        background-color: #BDBDBD;
        color: #757575;
    }
    
    QLineEdit, QComboBox, QSpinBox {
        border: 1px solid #BDBDBD;
        border-radius: 3px;
        padding: 4px;
        background-color: white;
        selection-background-color: #2196F3;
    }
    
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
        border: 1px solid #2196F3;
    }
    
    QTableWidget {
        border: 1px solid #BDBDBD;
        background-color: white;
        gridline-color: #E0E0E0;
        selection-background-color: #E3F2FD;
        selection-color: #212121;
    }
    
    QTableWidget::item {
        padding: 4px;
        border-bottom: 1px solid #E0E0E0;
    }
    
    QTableWidget::item:selected {
        background-color: #E3F2FD;
        color: #212121;
    }
    
    QHeaderView::section {
        background-color: #F5F5F5;
        color: #424242;
        padding: 4px;
        border: none;
        border-bottom: 1px solid #BDBDBD;
        font-weight: bold;
    }
    
    QScrollBar:vertical {
        border: none;
        background: #F5F5F5;
        width: 10px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background: #BDBDBD;
        min-height: 20px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #9E9E9E;
    }
    
    QScrollBar:horizontal {
        border: none;
        background: #F5F5F5;
        height: 10px;
        margin: 0px;
    }
    
    QScrollBar::handle:horizontal {
        background: #BDBDBD;
        min-width: 20px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background: #9E9E9E;
    }
    
    QGroupBox {
        border: 1px solid #BDBDBD;
        border-radius: 3px;
        margin-top: 1ex;
        font-weight: bold;
        color: #424242;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 3px;
    }
    
    QCheckBox {
        spacing: 5px;
        font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
    }
    
    QCheckBox::indicator {
        width: 15px;
        height: 15px;
    }
    
    QCheckBox::indicator:unchecked {
        border: 1px solid #BDBDBD;
        background-color: white;
        border-radius: 2px;
    }
    
    QCheckBox::indicator:checked {
        border: 1px solid #2196F3;
        background-color: #2196F3;
        border-radius: 2px;
    }
    
    QProgressBar {
        border: none;
        background-color: #E0E0E0;
        text-align: center;
        color: white;
        border-radius: 3px;
    }
    
    QProgressBar::chunk {
        background-color: #2196F3;
        border-radius: 3px;
    }
    
    QStatusBar {
        background-color: #F5F5F5;
        color: #424242;
    }
    
    QMenuBar {
        background-color: #F5F5F5;
        color: #424242;
    }
    
    QMenuBar::item {
        padding: 5px 10px;
        background: transparent;
    }
    
    QMenuBar::item:selected {
        background-color: #E3F2FD;
    }
    
    QMenu {
        background-color: white;
        border: 1px solid #BDBDBD;
    }
    
    QMenu::item {
        padding: 5px 20px 5px 20px;
    }
    
    QMenu::item:selected {
        background-color: #E3F2FD;
    }
    """
