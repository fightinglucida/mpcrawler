import os
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QMessageBox, 
                             QStatusBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QGroupBox, QFormLayout, QFrame,
                             QGridLayout, QDialog, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap
from datetime import datetime

# 导入现有模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mp_downloader import WechatCollectorUI
from utils.db_article_downloader import DBArticleDownloadManager
from models.user_database import UserDatabaseManager
from models.user_manager import RegisterDialog
from utils.config_manager import ConfigManager

class UserApp(QMainWindow):
    """用户版本的公众号采集助手"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.setWindowTitle("公众号采集与下载助手 V1.0 ")
        self.setMinimumSize(1200, 900)
        
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.svg")
        self.setWindowIcon(QIcon(icon_path))
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建数据库管理器
        self.db_manager = UserDatabaseManager()
        
        # 创建配置管理器
        self.config_manager = ConfigManager()
        
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
        # self.check_environment()
        
        # 默认选择用户中心选项卡并自动弹出登录界面
        self.tab_widget.setCurrentIndex(1)
        QTimer.singleShot(200, self.auto_show_login)
        
        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def auto_show_login(self):
        """自动显示登录界面或尝试自动登录"""
        # 检查是否配置了自动登录
        login_info = self.config_manager.get_login_info()
        
        if login_info.get('auto_login') and login_info.get('email') and login_info.get('password'):
            print("检测到自动登录配置，准备自动登录...")
            # 显示登录对话框，并在其中执行自动登录
            login_dialog = self.user_center.show_login_dialog()
            
            # 确保登录对话框显示出来，然后才执行自动登录
            QTimer.singleShot(100, lambda: print("登录对话框已显示，准备执行自动登录"))
            
            # 在登录成功后，对话框会自动关闭，并触发 login_success 信号
            # 该信号会调用 on_login_status_changed 方法，在其中处理激活状态
            # 这里不需要额外处理
        else:
            # 没有配置自动登录，直接显示登录对话框
            self.user_center.show_login_dialog()
    
    def on_login_status_changed(self, is_logged_in, user_info):
        """用户登录状态变化回调"""
        if is_logged_in and user_info:
            # 用户登录成功，可以在这里更新UI或进行其他操作
            print(f"用户登录成功: {user_info.get('nickname', '')}")
            print(f"用户信息: {user_info}")
            print(f"激活状态: {user_info.get('activation_status')}")
            
            # 更新状态栏
            self.status_bar.showMessage(f"用户已登录: {user_info.get('nickname', '')}")
            
            # 更新下载管理器的用户ID
            if hasattr(self.collector_ui, 'download_manager') and isinstance(self.collector_ui.download_manager, DBArticleDownloadManager):
                self.collector_ui.download_manager.set_user_id(user_info.get('id'))
                print(f"更新下载管理器的用户ID: {user_info.get('id')}")
                # 如果用户已激活，启用保存到数据库功能
                if user_info.get('activation_status') == '已激活':
                    self.collector_ui.download_manager.set_save_to_db(True)
                    self.enable_collector_features()
                    # 启用公众号采集页面并自动切换
                    self.switch_to_collector(True)
                    print("用户已激活，启用公众号采集，并切换到公众号采集页面")
                else:
                    # 未激活状态，禁用公众号采集页面
                    self.disable_collector_features()
                    print(f"用户未激活，禁用公众号采集页面，激活状态: {user_info.get('activation_status')}")
        else:
            # 用户退出登录
            print("用户已退出登录")
            
            # 更新状态栏
            self.status_bar.showMessage("用户未登录")
            
            # 更新下载管理器
            if hasattr(self.collector_ui, 'download_manager') and isinstance(self.collector_ui.download_manager, DBArticleDownloadManager):
                self.collector_ui.download_manager.set_user_id(None)
                self.collector_ui.download_manager.set_save_to_db(False)
            
            # 禁用公众号采集页面
            self.disable_collector_features()
    
    def switch_to_collector(self, check_wechat_login=False):
        """切换到公众号采集页面并根据需要检查微信登录状态"""
        # 切换到公众号采集页面
        self.tab_widget.setCurrentIndex(0)
        
        # 启用公众号采集页面的所有功能
        self.enable_collector_features()
        
        # 如果需要，检查微信登录状态
        if check_wechat_login:
            QTimer.singleShot(500, self.check_wechat_login)
    
    def check_wechat_login(self):
        """检查微信登录状态，自动登录或显示扫码登录"""
        try:
            # 调用公众号采集界面的登录状态检查
            self.collector_ui.check_login_status()
        except Exception as e:
            print(f"检查微信登录状态出错: {str(e)}")
    
    def enable_collector_features(self):
        """启用公众号采集页面的所有功能"""
        try:
            # 启用公众号采集页面的所有功能
            self.collector_ui.enable_all_features()
            # 更新标签页状态
            self.tab_widget.setTabEnabled(0, True)
        except Exception as e:
            print(f"启用公众号采集页面功能出错: {str(e)}")
    
    def disable_collector_features(self):
        """禁用公众号采集页面的所有功能"""
        try:
            # 禁用公众号采集页面的所有功能
            self.collector_ui.disable_all_features()
            # 更新标签页状态
            self.tab_widget.setTabEnabled(0, False)
        except Exception as e:
            print(f"禁用公众号采集页面功能出错: {str(e)}")
    
    def on_tab_changed(self, index):
        """标签页切换事件处理"""
        if index == 0:  # 切换到公众号采集页面
            # 获取当前用户信息
            user_info = self.user_center.current_user if hasattr(self.user_center, 'current_user') else None
            
            # 检查用户是否已登录且已激活
            if user_info and user_info.get('activation_status') == '已激活':
                # 已激活状态，启用功能
                self.enable_collector_features()
                
                # 只有在公众号采集界面未登录状态下才检查微信登录
                if not self.collector_ui.is_logged_in:
                    self.check_wechat_login()
            else:
                # 未登录或未激活状态，禁用功能并切换回用户中心
                self.disable_collector_features()
                self.status_bar.showMessage("请先登录并激活账号", 5000)
                QTimer.singleShot(100, lambda: self.tab_widget.setCurrentIndex(1))
    
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
    
    def check_environment(self):
        """检查环境变量"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # 检查Supabase配置
        if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
            QMessageBox.warning(self, "环境配置错误", "请在.env文件中设置SUPABASE_URL和SUPABASE_KEY")


class UserCenterPanel(QWidget):
    """用户中心面板"""
    login_status_changed = pyqtSignal(bool, object)  # 登录状态变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = UserDatabaseManager()
        self.current_user = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        # 设置全局样式
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei';
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 3px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 3px 10px;  
                font-family: 'Microsoft YaHei';
                color: #333333;
                min-height: 24px;  
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                border: 1px solid #9E9E9E;
                color: #757575;
            }
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 5px;
                background-color: #ffffff;
                font-family: 'Microsoft YaHei';
                min-height: 25px;
            }
            QLabel {
                font-family: 'Microsoft YaHei';
                color: #333333;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 用户信息区域
        self.user_info_group = QGroupBox("用户信息")
        user_info_layout = QGridLayout()
        user_info_layout.setColumnStretch(2, 1)  # 让第三列拉伸
        user_info_layout.setSpacing(8)  # 设置控件间距
        
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
        self.status_label.setStyleSheet("color: #e74c3c;")
        user_info_layout.addWidget(QLabel("状态:"), 2, 0)
        user_info_layout.addWidget(self.status_label, 2, 1)
        
        # 登录/登出按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.login_button = QPushButton("登录")
        self.login_button.setFixedWidth(100)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
        """)
        self.login_button.clicked.connect(self.show_login_dialog)
        button_layout.addWidget(self.login_button)
        
        self.logout_button = QPushButton("退出登录")
        self.logout_button.setFixedWidth(100)
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: 1px solid #D32F2F;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:pressed {
                background-color: #C62828;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                border: 1px solid #9E9E9E;
                color: #757575;
            }
        """)
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setEnabled(False)
        button_layout.addWidget(self.logout_button)
        
        button_layout.addStretch()
        user_info_layout.addLayout(button_layout, 3, 0, 1, 2)
        
        self.user_info_group.setLayout(user_info_layout)
        main_layout.addWidget(self.user_info_group)
        
        # 激活信息和密码修改区域（放在同一行）
        activation_password_layout = QHBoxLayout()
        activation_password_layout.setSpacing(10)
        
        # 激活信息区域
        self.activation_group = QGroupBox("激活信息")
        activation_layout = QGridLayout()
        activation_layout.setColumnStretch(1, 1)  # 让第二列拉伸
        activation_layout.setSpacing(8)  # 设置控件间距
        
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
        self.activate_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                border: 1px solid #9E9E9E;
                color: #757575;
            }
        """)
        self.activate_button.clicked.connect(self.activate_account)
        self.activate_button.setEnabled(False)
        activation_layout.addWidget(self.activate_button, 5, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        
        self.activation_group.setLayout(activation_layout)
        activation_password_layout.addWidget(self.activation_group)
        
        # 密码修改区域
        self.password_group = QGroupBox("密码修改")
        password_layout = QGridLayout()
        password_layout.setSpacing(8)  # 设置控件间距
        
        password_layout.addWidget(QLabel("旧密码:"), 0, 0)
        self.old_password_input = QLineEdit()
        self.old_password_input.setPlaceholderText("请输入旧密码")
        self.old_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.old_password_input, 0, 1)
        
        password_layout.addWidget(QLabel("新密码:"), 1, 0)
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("请输入新密码")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.new_password_input, 1, 1)
        
        password_layout.addWidget(QLabel("确认密码:"), 2, 0)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请确认新密码")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addWidget(self.confirm_password_input, 2, 1)
        
        self.change_password_button = QPushButton("修改密码")
        self.change_password_button.setFixedWidth(80)
        self.change_password_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: 1px solid #F57C00;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                border: 1px solid #9E9E9E;
                color: #757575;
            }
        """)
        self.change_password_button.clicked.connect(self.change_password)
        self.change_password_button.setEnabled(False)
        password_layout.addWidget(self.change_password_button, 3, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        
        self.password_group.setLayout(password_layout)
        activation_password_layout.addWidget(self.password_group)
        
        main_layout.addLayout(activation_password_layout)
        
        # 状态信息
        self.message_label = QLabel("")
        self.message_label.setStyleSheet("color: #3498db; font-weight: bold;")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.message_label)
        
        # 添加底部间距
        main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def try_auto_login(self):
        """尝试通过MAC地址自动登录"""
        result = self.db_manager.auto_login_by_mac()
        
        if result['success']:
            # 自动登录成功
            self.current_user = result['user']
            self.update_ui_after_login()
            
            # 发送登录状态变化信号
            self.login_status_changed.emit(True, result['user'])
            
            # 显示提示信息
            QMessageBox.information(self, "自动登录", "已通过设备识别自动登录")
        else:
            # 自动登录失败，显示登录对话框
            self.show_login_dialog()
    
    def show_login_dialog(self):
        """显示登录对话框"""
        login_dialog = LoginDialog(self)
        login_dialog.login_success.connect(self.on_login_success)
        login_dialog.exec()
        return login_dialog
    
    def on_login_success(self, user_info):
        """登录成功回调"""
        self.current_user = user_info
        self.user_id = user_info.get('id')
        
        # 检查激活状态和过期时间
        self.check_activation_status()
        
        # 更新UI
        self.update_ui_after_login()
        
        # 发送登录状态变化信号
        self.login_status_changed.emit(True, user_info)
    
    def check_activation_status(self):
        """检查激活状态和过期时间"""
        if not self.current_user:
            return
            
        # 获取用户激活信息
        activation_code = self.current_user.get('activation_code', '')
        if not activation_code:
            return
            
        result = self.db_manager.get_user_activation_info(self.user_id)
        
        if result['success']:
            data = result['data']
            activation_status = data.get('activation_status', '')
            expiry_date = data.get('expiry_date', '')
            
            # 如果已经是过期状态，不需要再检查
            if activation_status == '已过期':
                return
                
            # 只有已激活状态才需要检查是否过期
            if activation_status == '已激活' and expiry_date:
                # 将过期时间转换为datetime对象
                try:
                    # 处理不同格式的日期字符串
                    if 'T' in expiry_date:
                        # 处理带时区的ISO格式
                        if '+' in expiry_date:
                            expiry_date = expiry_date.split('+')[0]
                        # 处理带毫秒的格式
                        if '.' in expiry_date:
                            expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M:%S.%f')
                        else:
                            expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M:%S')
                    else:
                        expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d')
                        
                    # 获取当前时间
                    current_datetime = datetime.now()
                    
                    # 检查是否过期
                    if current_datetime > expiry_datetime:
                        # 已过期，更新激活状态
                        update_result = self.db_manager.update_activation_status(
                            self.user_id, 
                            activation_code, 
                            '已过期'
                        )
                        
                        if update_result['success']:
                            # 在状态栏显示提示
                            self.parent().status_bar.showMessage("您的激活码已过期，请重新激活", 5000)
                        
                        # 重新获取用户信息
                        updated_user = self.db_manager.get_user_by_id(self.user_id)
                        if updated_user['success']:
                            self.current_user = updated_user['user']
                            # 更新UI
                            self.update_ui_after_login()
                except Exception as e:
                    print(f"检查激活状态时发生错误: {str(e)}")
    
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
            # 格式化过期时间显示
            expiry_date = result.get('expiry_date', '')
            expiry_display = ''
            if expiry_date:
                try:
                    # 处理不同格式的日期字符串
                    if 'T' in expiry_date:
                        # 处理带时区的ISO格式
                        if '+' in expiry_date:
                            expiry_date = expiry_date.split('+')[0]
                        # 处理带毫秒的格式
                        if '.' in expiry_date:
                            expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M:%S.%f')
                        else:
                            expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M:%S')
                    else:
                        expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d')
                        
                    # 获取当前时间
                    current_datetime = datetime.now()
                    
                    # 检查是否过期
                    if current_datetime > expiry_datetime:
                        # 已过期，更新激活状态
                        update_result = self.db_manager.update_activation_status(
                            self.user_id, 
                            activation_code, 
                            '已过期'
                        )
                        
                        if update_result['success']:
                            # 在状态栏显示提示
                            self.parent().status_bar.showMessage("您的激活码已过期，请重新激活", 5000)
                        
                        # 重新获取用户信息
                        updated_user = self.db_manager.get_user_by_id(self.user_id)
                        if updated_user['success']:
                            self.current_user = updated_user['user']
                            # 更新UI
                            self.update_ui_after_login()
                except Exception as e:
                    print(f"格式化过期时间出错: {str(e)}")
            
            # 显示成功信息，包含过期时间
            success_message = f"账号激活成功！\n\n激活时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n过期时间: {expiry_display}"
            QMessageBox.information(self, "激活成功", success_message)
            
            self.activation_code_input.clear()
            
            # 刷新激活信息
            self.get_activation_info()
            
            # 更新用户信息
            updated_user = self.db_manager.get_user_by_id(self.current_user.get('id'))
            if updated_user['success']:
                self.current_user = updated_user['user']
                self.login_status_changed.emit(True, self.current_user)
                
            # 启用公众号采集页面的功能
            try:
                main_window = self.parent().parent()  # 获取主窗口 UserApp 实例
                if hasattr(main_window, 'enable_collector_features'):
                    main_window.enable_collector_features()
            except Exception as e:
                print(f"启用公众号采集功能出错: {str(e)}")
                
            # 在消息标签中显示激活成功信息
            self.message_label.setText(f"激活成功，账号有效期至: {expiry_display}")
            self.message_label.setStyleSheet("color: green;")
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


class LoginDialog(QDialog):
    """登录对话框"""
    
    login_success = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = UserDatabaseManager()
        
        # 导入配置管理器
        self.config_manager = ConfigManager()
        
        self.setup_ui()
        
        # 加载保存的登录信息
        self.load_login_info()
        
        # 如果配置了自动登录，则自动执行登录
        if self.auto_login_checkbox.isChecked() and self.email_input.text() and self.password_input.text():
            # 显示正在登录的提示
            self.status_label.setText("正在自动登录中...")
            # 禁用登录和注册按钮
            self.login_button.setEnabled(False)
            self.register_button.setEnabled(False)
            # 延迟执行登录，以便用户可以看到登录界面
            QTimer.singleShot(1500, self.login)
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("用户登录")
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QWidget {
                font-family: 'Microsoft YaHei';
            }
            QGroupBox {
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 3px;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 3px 10px;  
                font-family: 'Microsoft YaHei';
                color: #333333;
                min-height: 24px;  
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 5px;
                background-color: #ffffff;
                font-family: 'Microsoft YaHei';
                min-height: 25px;
            }
            QLabel {
                font-family: 'Microsoft YaHei';
                color: #333333;
            }
            QCheckBox {
                font-family: 'Microsoft YaHei';
                color: #333333;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("用户登录")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 表单布局
        form_layout = QGridLayout()
        form_layout.setSpacing(10)
        
        # 邮箱输入
        form_layout.addWidget(QLabel("邮箱:"), 0, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱")
        form_layout.addWidget(self.email_input, 0, 1)
        
        # 密码输入
        form_layout.addWidget(QLabel("密码:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.password_input, 1, 1)
        
        # 添加自动登录和记住密码选项
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(10)
        
        self.remember_password_checkbox = QCheckBox("记住密码")
        self.auto_login_checkbox = QCheckBox("自动登录")
        
        # 自动登录依赖于记住密码，当记住密码取消选中时，自动登录也应该取消选中
        self.remember_password_checkbox.stateChanged.connect(self.on_remember_password_changed)
        
        checkbox_layout.addWidget(self.remember_password_checkbox)
        checkbox_layout.addWidget(self.auto_login_checkbox)
        checkbox_layout.addStretch()
        
        layout.addLayout(form_layout)
        layout.addLayout(checkbox_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.login_button = QPushButton("登录")
        self.login_button.setFixedWidth(100)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #2E7D32;
            }
        """)
        self.login_button.clicked.connect(self.login)
        
        self.register_button = QPushButton("注册")
        self.register_button.setFixedWidth(100)
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 1px solid #1976D2;
                border-radius: 4px;
                padding: 3px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.register_button.clicked.connect(self.show_register_dialog)
        
        button_layout.addStretch()
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.register_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 状态信息
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #e74c3c;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def on_remember_password_changed(self, state):
        """记住密码选项变化时的处理"""
        # 如果取消选中记住密码，则自动登录也取消选中
        if state == 0:  # Qt.Unchecked
            self.auto_login_checkbox.setChecked(False)
            self.auto_login_checkbox.setEnabled(False)
        else:
            self.auto_login_checkbox.setEnabled(True)
    
    def load_login_info(self):
        """加载保存的登录信息"""
        try:
            login_info = self.config_manager.get_login_info()
            
            # 设置记住密码和自动登录选项
            self.remember_password_checkbox.setChecked(login_info['remember_password'])
            self.auto_login_checkbox.setChecked(login_info['auto_login'])
            
            # 如果记住密码，则填充邮箱和密码
            if login_info['remember_password']:
                self.email_input.setText(login_info['email'])
                self.password_input.setText(login_info['password'])
                
                # 如果没有选中自动登录，则禁用自动登录选项
                if not login_info['auto_login']:
                    self.auto_login_checkbox.setEnabled(True)
                else:
                    self.auto_login_checkbox.setEnabled(True)
            else:
                # 如果没有记住密码，则禁用自动登录选项
                self.auto_login_checkbox.setEnabled(False)
        except Exception as e:
            print(f"加载登录信息时出错: {str(e)}")
    
    def login(self):
        """登录"""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email:
            QMessageBox.warning(self, "提示", "请输入邮箱")
            return
        
        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return
        
        # 更新状态
        self.status_label.setText("正在登录，请稍候...")
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)
        
        # 登录
        result = self.db_manager.login(email, password)
        
        # 恢复按钮状态
        self.login_button.setEnabled(True)
        self.register_button.setEnabled(True)
        
        if result['success']:
            # 保存登录信息
            remember_password = self.remember_password_checkbox.isChecked()
            auto_login = self.auto_login_checkbox.isChecked()
            
            self.config_manager.save_login_info(
                email=email,
                password=password,
                remember_password=remember_password,
                auto_login=auto_login
            )
            
            # 登录成功
            self.status_label.setText("登录成功！")
            
            # 获取用户信息，确保包含最新的激活状态
            user_info = result['user']
            print(f"登录成功，用户信息: {user_info}")
            print(f"激活状态: {user_info.get('activation_status')}")
            
            # 发送登录成功信号
            self.login_success.emit(user_info)
            
            # 检查用户激活状态
            if user_info.get('activation_status') == '已激活':
                print("用户已激活，准备启用公众号采集页面")
                # 如果已激活，延迟关闭登录对话框并切换到公众号采集页面
                QTimer.singleShot(500, self.accept)
                
                # 获取主窗口并切换到公众号采集页面
                try:
                    main_window = self.parent().parent()
                    if hasattr(main_window, 'enable_collector_features'):
                        # 先启用公众号采集页面功能
                        main_window.enable_collector_features()
                        print("已调用 enable_collector_features 方法")
                    
                    if hasattr(main_window, 'switch_to_collector'):
                        # 然后切换到公众号采集页面
                        QTimer.singleShot(1000, lambda: main_window.switch_to_collector(True))
                        print("已设置延时调用 switch_to_collector 方法")
                except Exception as e:
                    print(f"切换到公众号采集页面出错: {str(e)}")
            else:
                # 如果未激活，直接关闭登录对话框
                self.accept()
                print("用户未激活，不启用公众号采集页面")
        else:
            self.status_label.setText("登录失败")
            QMessageBox.warning(self, "登录失败", result['message'])
    
    def show_register_dialog(self):
        """显示注册对话框"""
        register_dialog = RegisterDialog(self)
        register_dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserApp()
    window.show()
    sys.exit(app.exec())
