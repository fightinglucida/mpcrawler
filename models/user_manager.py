import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# 导入数据库管理器
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import DatabaseManager

class LoginDialog(QDialog):
    """用户登录对话框"""
    login_success = pyqtSignal(dict)  # 登录成功信号，传递用户信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户登录")
        self.setFixedSize(400, 300)
        self.db_manager = DatabaseManager()
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("用户登录")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 登录表单
        form_group = QGroupBox()
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱")
        form_layout.addRow("邮箱:", self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("密码:", self.password_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.handle_login)
        
        self.register_button = QPushButton("注册")
        self.register_button.clicked.connect(self.show_register_dialog)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.register_button)
        
        layout.addLayout(button_layout)
        
        # 状态信息
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def handle_login(self):
        """处理登录"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            self.status_label.setText("请输入邮箱和密码")
            return
        
        # 调用数据库登录方法
        result = self.db_manager.login_user(email, password)
        
        if result['success']:
            self.login_success.emit(result['user'])
            self.accept()
        else:
            self.status_label.setText(result['message'])
    
    def show_register_dialog(self):
        """显示注册对话框"""
        register_dialog = RegisterDialog(self)
        if register_dialog.exec() == QDialog.DialogCode.Accepted:
            # 注册成功后自动填充邮箱
            self.email_input.setText(register_dialog.email_input.text())
            self.status_label.setText("注册成功，请登录")


class RegisterDialog(QDialog):
    """用户注册对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户注册")
        self.setFixedSize(400, 350)
        self.db_manager = DatabaseManager()
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("用户注册")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 注册表单
        form_group = QGroupBox()
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱")
        form_layout.addRow("邮箱:", self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("密码:", self.password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请再次输入密码")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("确认密码:", self.confirm_password_input)
        
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("请输入昵称")
        form_layout.addRow("昵称:", self.nickname_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.register_button = QPushButton("注册")
        self.register_button.clicked.connect(self.handle_register)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.register_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 状态信息
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def handle_register(self):
        """处理注册"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        nickname = self.nickname_input.text().strip()
        
        # 验证输入
        if not email or not password or not confirm_password or not nickname:
            self.status_label.setText("请填写所有字段")
            return
        
        if password != confirm_password:
            self.status_label.setText("两次输入的密码不一致")
            return
        
        # 获取当前设备MAC地址
        mac_address = self.db_manager._get_current_mac()
        
        # 调用数据库注册方法
        result = self.db_manager.register_user(email, password, nickname, mac_address)
        
        if result['success']:
            QMessageBox.information(self, "注册成功", "注册成功，请登录并激活账号")
            self.accept()
        else:
            self.status_label.setText(result['message'])


class ActivationDialog(QDialog):
    """账号激活对话框"""
    
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("账号激活")
        self.setFixedSize(400, 200)
        self.user_id = user_id
        self.db_manager = DatabaseManager()
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("账号激活")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 激活码输入
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("激活码:"))
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("请输入激活码")
        form_layout.addWidget(self.code_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.activate_button = QPushButton("激活")
        self.activate_button.clicked.connect(self.handle_activation)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.activate_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 状态信息
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def handle_activation(self):
        """处理激活"""
        activation_code = self.code_input.text().strip()
        
        if not activation_code:
            self.status_label.setText("请输入激活码")
            return
        
        # 调用数据库激活方法
        result = self.db_manager.activate_user(self.user_id, activation_code)
        
        if result['success']:
            QMessageBox.information(self, "激活成功", f"账号已激活，有效期至: {result['expiry_date']}")
            self.accept()
        else:
            self.status_label.setText(result['message'])