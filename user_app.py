import os
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QMessageBox, 
                             QStatusBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QGroupBox, QFormLayout, QFrame,
                             QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap

# 导入现有模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mp_downloader import WechatCollectorUI
from utils.db_article_downloader import DBArticleDownloadManager
from models.user_database import UserDatabaseManager
from models.user_manager import LoginDialog, RegisterDialog

class UserApp(QMainWindow):
    """用户版本的公众号采集助手"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.setWindowTitle("公众号采集与下载助手 (用户版)")
        self.setMinimumSize(1200, 800)
        
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.svg")
        self.setWindowIcon(QIcon(icon_path))
        
        # 创建数据库管理器
        self.db_manager = UserDatabaseManager()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("欢迎使用公众号采集与下载助手")
        
        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 创建公众号采集界面
        self.collector_ui = WechatCollectorUI()
        self.tab_widget.addTab(self.collector_ui, "公众号采集")
        
        # 创建用户中心界面
        self.user_center = UserCenterPanel()
        self.tab_widget.addTab(self.user_center, "用户中心")
        
        # 连接用户登录状态变化信号
        self.user_center.login_status_changed.connect(self.on_login_status_changed)
        
        # 替换下载管理器为支持数据库的版本
        self.setup_db_downloader()
        
        # 检查环境变量
        self.check_environment()
        
        # 默认选择用户中心选项卡并自动弹出登录界面
        self.tab_widget.setCurrentIndex(1)
        QTimer.singleShot(500, self.auto_show_login)
    
    def auto_show_login(self):
        """自动显示登录界面"""
        self.user_center.show_login_dialog()
    
    def setup_db_downloader(self):
        """设置支持数据库的下载管理器"""
        try:
            # 替换原有下载管理器
            if hasattr(self.collector_ui, 'download_manager'):
                # 保存原有设置
                save_dir = self.collector_ui.download_manager.save_dir if hasattr(self.collector_ui.download_manager, 'save_dir') else None
                current_account_name = self.collector_ui.download_manager.current_account_name if hasattr(self.collector_ui.download_manager, 'current_account_name') else None
                
                # 创建新的下载管理器
                self.collector_ui.download_manager = DBArticleDownloadManager(
                    save_to_db=False,
                    user_id=None
                )
                
                # 恢复设置
                if save_dir:
                    self.collector_ui.download_manager.save_dir = save_dir
                if current_account_name:
                    self.collector_ui.download_manager.current_account_name = current_account_name
                    
                # 连接信号
                self.collector_ui.download_manager.download_success.connect(self.collector_ui.on_download_success)
                self.collector_ui.download_manager.download_failed.connect(self.collector_ui.on_download_failed)
                self.collector_ui.download_manager.download_progress.connect(self.collector_ui.on_download_progress)
                self.collector_ui.download_manager.download_complete.connect(self.collector_ui.on_download_complete)
        except Exception as e:
            print(f"设置数据库下载管理器失败: {str(e)}")
    
    def on_login_status_changed(self, is_logged_in, user_info):
        """用户登录状态变化回调"""
        if is_logged_in and user_info:
            # 用户登录成功，可以在这里更新UI或进行其他操作
            print(f"用户登录成功: {user_info.get('nickname', '')}")
            
            # 更新状态栏
            self.statusBar.showMessage(f"用户已登录: {user_info.get('nickname', '')}")
            
            # 更新下载管理器的用户ID
            if hasattr(self.collector_ui, 'download_manager') and isinstance(self.collector_ui.download_manager, DBArticleDownloadManager):
                self.collector_ui.download_manager.set_user_id(user_info.get('id'))
                
                # 如果用户已激活，启用保存到数据库功能
                if user_info.get('activation_status') == '已激活':
                    self.collector_ui.download_manager.set_save_to_db(True)
        else:
            # 用户退出登录
            print("用户已退出登录")
            
            # 更新状态栏
            self.statusBar.showMessage("用户未登录")
            
            # 更新下载管理器
            if hasattr(self.collector_ui, 'download_manager') and isinstance(self.collector_ui.download_manager, DBArticleDownloadManager):
                self.collector_ui.download_manager.set_user_id(None)
                self.collector_ui.download_manager.set_save_to_db(False)
    
    def check_environment(self):
        """检查环境变量"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # 检查Supabase配置
        if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
            QMessageBox.warning(self, "环境配置错误", "请在.env文件中设置SUPABASE_URL和SUPABASE_KEY")


class UserCenterPanel(QWidget):
    """用户中心面板"""
    login_status_changed = pyqtSignal(bool, dict)  # 登录状态变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = UserDatabaseManager()
        self.current_user = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 用户信息区域
        self.user_info_group = QGroupBox("用户信息")
        user_info_layout = QGridLayout()
        user_info_layout.setColumnStretch(2, 1)  # 让第三列拉伸
        
        # 用户信息
        self.email_label = QLabel("未登录")
        self.email_label.setFont(QFont("Microsoft YaHei", 10))
        user_info_layout.addWidget(QLabel("邮箱:"), 0, 0)
        user_info_layout.addWidget(self.email_label, 0, 1)
        
        self.nickname_label = QLabel("未登录")
        self.nickname_label.setFont(QFont("Microsoft YaHei", 10))
        user_info_layout.addWidget(QLabel("昵称:"), 1, 0)
        user_info_layout.addWidget(self.nickname_label, 1, 1)
        
        # 登录状态
        self.status_label = QLabel("未登录")
        self.status_label.setStyleSheet("color: red;")
        user_info_layout.addWidget(QLabel("状态:"), 2, 0)
        user_info_layout.addWidget(self.status_label, 2, 1)
        
        # 登录/登出按钮
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton("登录")
        self.login_button.setFixedWidth(100)
        self.login_button.clicked.connect(self.show_login_dialog)
        button_layout.addWidget(self.login_button)
        
        self.logout_button = QPushButton("退出登录")
        self.logout_button.setFixedWidth(100)
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setEnabled(False)
        button_layout.addWidget(self.logout_button)
        
        button_layout.addStretch()
        user_info_layout.addLayout(button_layout, 3, 0, 1, 2)
        
        self.user_info_group.setLayout(user_info_layout)
        main_layout.addWidget(self.user_info_group)
        
        # 激活信息和密码修改区域（放在同一行）
        activation_password_layout = QHBoxLayout()
        
        # 激活信息区域
        self.activation_group = QGroupBox("激活信息")
        activation_layout = QGridLayout()
        activation_layout.setColumnStretch(1, 1)  # 让第二列拉伸
        
        # 激活码信息
        activation_layout.addWidget(QLabel("激活码:"), 0, 0)
        self.activation_code_label = QLabel("未激活")
        activation_layout.addWidget(self.activation_code_label, 0, 1)
        
        activation_layout.addWidget(QLabel("激活状态:"), 1, 0)
        self.activation_status_label = QLabel("未激活")
        activation_layout.addWidget(self.activation_status_label, 1, 1)
        
        activation_layout.addWidget(QLabel("激活时间:"), 2, 0)
        self.activation_time_label = QLabel("未激活")
        activation_layout.addWidget(self.activation_time_label, 2, 1)
        
        activation_layout.addWidget(QLabel("过期时间:"), 3, 0)
        self.expiry_date_label = QLabel("未激活")
        activation_layout.addWidget(self.expiry_date_label, 3, 1)
        
        # 激活码输入区域
        activation_layout.addWidget(QLabel("输入激活码:"), 4, 0)
        self.activation_code_input = QLineEdit()
        self.activation_code_input.setPlaceholderText("请输入激活码")
        activation_layout.addWidget(self.activation_code_input, 4, 1)
        
        self.activate_button = QPushButton("激活")
        self.activate_button.setFixedWidth(80)
        self.activate_button.clicked.connect(self.activate_account)
        self.activate_button.setEnabled(False)
        activation_layout.addWidget(self.activate_button, 5, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        
        self.activation_group.setLayout(activation_layout)
        activation_password_layout.addWidget(self.activation_group)
        
        # 密码修改区域
        self.password_group = QGroupBox("密码修改")
        password_layout = QFormLayout()
        
        self.old_password_input = QLineEdit()
        self.old_password_input.setPlaceholderText("请输入旧密码")
        self.old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addRow("旧密码:", self.old_password_input)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("请输入新密码")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addRow("新密码:", self.new_password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请确认新密码")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addRow("确认密码:", self.confirm_password_input)
        
        self.change_password_button = QPushButton("修改密码")
        self.change_password_button.setFixedWidth(80)
        self.change_password_button.clicked.connect(self.change_password)
        self.change_password_button.setEnabled(False)
        password_layout.addRow("", self.change_password_button)
        
        self.password_group.setLayout(password_layout)
        activation_password_layout.addWidget(self.password_group)
        
        main_layout.addLayout(activation_password_layout)
        
        # 状态信息
        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: blue;")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.message_label)
        
        self.setLayout(main_layout)
    
    def show_login_dialog(self):
        """显示登录对话框"""
        login_dialog = LoginDialog(self)
        login_dialog.login_success.connect(self.on_login_success)
        login_dialog.exec()
    
    def on_login_success(self, user_info):
        """登录成功回调"""
        self.current_user = user_info
        self.update_ui_after_login()
        
        # 获取用户激活信息
        self.get_activation_info()
        
        # 发送登录状态变化信号
        self.login_status_changed.emit(True, user_info)
    
    def update_ui_after_login(self):
        """登录后更新UI"""
        if self.current_user:
            self.email_label.setText(self.current_user.get('email', '未知'))
            self.nickname_label.setText(self.current_user.get('nickname', '未知'))
            
            # 更新状态
            self.status_label.setText('已登录')
            self.status_label.setStyleSheet("color: green;")
            
            # 更新按钮状态
            self.login_button.setEnabled(False)
            self.logout_button.setEnabled(True)
            self.activate_button.setEnabled(True)
            self.change_password_button.setEnabled(True)
            
            # 获取激活信息
            self.user_id = self.current_user.get('id')
            self.get_activation_info()
        else:
            self.reset_ui()
    
    def reset_ui(self):
        """重置UI到未登录状态"""
        self.email_label.setText("未登录")
        self.nickname_label.setText("未登录")
        self.status_label.setText("未登录")
        self.status_label.setStyleSheet("color: red;")
        
        # 重置激活信息
        self.activation_code_label.setText("未激活")
        self.activation_status_label.setText("未激活")
        self.activation_time_label.setText("未激活")
        self.expiry_date_label.setText("未激活")
        
        # 清空输入框
        self.activation_code_input.clear()
        self.old_password_input.clear()
        self.new_password_input.clear()
        self.confirm_password_input.clear()
        
        # 更新按钮状态
        self.login_button.setEnabled(True)
        self.logout_button.setEnabled(False)
        self.activate_button.setEnabled(False)
        self.change_password_button.setEnabled(False)
        
        # 清空用户ID
        self.user_id = None
    
    def logout(self):
        """退出登录"""
        if self.current_user:
            reply = QMessageBox.question(
                self, 
                "确认退出", 
                "确定要退出登录吗？", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.current_user = None
                self.reset_ui()
                self.login_status_changed.emit(False, {})
                self.message_label.setText("已退出登录")
    
    def get_activation_info(self):
        """获取用户激活信息"""
        if not self.user_id:
            return
        
        # 获取激活信息
        result = self.db_manager.get_user_activation_info(self.user_id)
        
        if result['success']:
            data = result['data']
            self.activation_code_label.setText(data.get('code', '未激活'))
            self.activation_status_label.setText(data.get('activation_status', '未激活'))
            
            activation_time = data.get('activation_time', '')
            if activation_time:
                self.activation_time_label.setText(activation_time.split('T')[0])
            else:
                self.activation_time_label.setText('未激活')
            
            expiry_date = data.get('expiry_date', '')
            if expiry_date:
                self.expiry_date_label.setText(expiry_date.split('T')[0])
            else:
                self.expiry_date_label.setText('未激活')
        else:
            self.activation_code_label.setText('未激活')
            self.activation_status_label.setText('未激活')
            self.activation_time_label.setText('未激活')
            self.expiry_date_label.setText('未激活')
    
    def update_activation_info(self):
        """获取激活信息"""
        if not self.user_id:
            return
        
        # 获取激活信息
        result = self.db_manager.get_user_activation_info(self.user_id)
        
        if result['success']:
            data = result['data']
            self.activation_code_label.setText(data.get('code', '未激活'))
            self.activation_status_label.setText(data.get('activation_status', '未激活'))
            
            activation_time = data.get('activation_time', '')
            if activation_time:
                self.activation_time_label.setText(activation_time.split('T')[0])
            else:
                self.activation_time_label.setText('未激活')
            
            expiry_date = data.get('expiry_date', '')
            if expiry_date:
                self.expiry_date_label.setText(expiry_date.split('T')[0])
            else:
                self.expiry_date_label.setText('未激活')
        else:
            self.activation_code_label.setText('未激活')
            self.activation_status_label.setText('未激活')
            self.activation_time_label.setText('未激活')
            self.expiry_date_label.setText('未激活')
    
    def activate_account(self):
        """激活账号"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "请先登录")
            return
        
        activation_code = self.activation_code_input.text().strip()
        if not activation_code:
            QMessageBox.warning(self, "错误", "请输入激活码")
            return
        
        # 获取当前设备MAC地址
        mac_address = self.db_manager._get_current_mac()
        
        # 调用激活方法
        result = self.db_manager.activate_user(self.current_user.get('id'), activation_code, mac_address)
        
        if result['success']:
            QMessageBox.information(self, "成功", "账号激活成功")
            self.activation_code_input.clear()
            
            # 刷新激活信息
            self.get_activation_info()
            
            # 更新用户信息
            updated_user = self.db_manager.get_user_by_id(self.current_user.get('id'))
            if updated_user['success']:
                self.current_user = updated_user['user']
                self.login_status_changed.emit(True, self.current_user)
        else:
            QMessageBox.warning(self, "错误", result['message'])
    
    def change_password(self):
        """修改密码"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "请先登录")
            return
        
        old_password = self.old_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not old_password or not new_password or not confirm_password:
            QMessageBox.warning(self, "错误", "请填写所有密码字段")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "错误", "两次输入的新密码不一致")
            return
        
        # 调用修改密码方法
        result = self.db_manager.change_password(
            self.current_user.get('id'), 
            old_password, 
            new_password
        )
        
        if result['success']:
            QMessageBox.information(self, "成功", "密码修改成功，请重新登录")
            
            # 清空密码输入框
            self.old_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            
            # 退出登录
            self.current_user = None
            self.reset_ui()
            self.login_status_changed.emit(False, {})
        else:
            QMessageBox.warning(self, "错误", result['message'])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserApp()
    window.show()
    sys.exit(app.exec())
