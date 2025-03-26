import os
import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QComboBox, QMessageBox, QGroupBox, QFormLayout,
                             QDialog, QDateTimeEdit, QDialogButtonBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtGui import QFont, QIcon
import uuid

# 导入数据库相关模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import DatabaseManager
from utils.style import get_flat_style

class AdminLoginDialog(QDialog):
    """管理员登录对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.setWindowTitle("管理员登录")
        self.setFixedSize(320, 200)
        
        # 应用扁平化样式
        self.setStyleSheet(get_flat_style())
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 邮箱输入
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入管理员邮箱")
        form_layout.addRow("邮箱:", self.email_input)
        
        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("密码:", self.password_input)
        
        layout.addLayout(form_layout)
        
        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.handle_login)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def handle_login(self):
        """处理登录"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "输入错误", "请输入邮箱和密码")
            return
        
        # 验证登录
        result = self.db_manager.login_user(email, password)
        
        if result['success']:
            user_info = result['user']
            
            # 检查是否是管理员角色
            if not self.db_manager.is_admin(user_info['id']):
                QMessageBox.warning(self, "权限错误", "您的账号不具有管理员权限")
                return
                
            self.user_info = user_info
            self.accept()
        else:
            QMessageBox.warning(self, "登录失败", result['message'])

class UserEditDialog(QDialog):
    """用户编辑对话框"""
    
    def __init__(self, db_manager, user_data=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_data = user_data  # 如果为None，则为新增用户
        self.setWindowTitle("编辑用户" if self.user_data else "新增用户")
        self.setFixedSize(500, 400)
        
        # 应用扁平化样式
        self.setStyleSheet(get_flat_style())
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 邮箱输入
        self.email_input = QLineEdit()
        if self.user_data:
            self.email_input.setText(self.user_data.get('email', ''))
            self.email_input.setReadOnly(True)  # 已存在的用户不允许修改邮箱
        form_layout.addRow("邮箱:", self.email_input)
        
        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("不修改请留空" if self.user_data else "请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("密码:", self.password_input)
        
        # 昵称输入
        self.nickname_input = QLineEdit()
        if self.user_data:
            self.nickname_input.setText(self.user_data.get('nickname', ''))
        form_layout.addRow("昵称:", self.nickname_input)
        
        # 角色选择
        self.role_combo = QComboBox()
        self.role_combo.addItems(["管理员", "普通用户", "付费用户"])
        if self.user_data:
            role = self.user_data.get('role', '1')
            self.role_combo.setCurrentIndex(int(role))
        else:
            self.role_combo.setCurrentIndex(1)  # 默认为普通用户
        form_layout.addRow("角色:", self.role_combo)
        
        # MAC地址显示
        self.mac_label = QLabel(self.user_data.get('mac', '未绑定') if self.user_data else '未绑定')
        form_layout.addRow("MAC地址:", self.mac_label)
        
        # 激活码显示
        self.activation_code_label = QLabel(self.user_data.get('activation_code', '未生成') if self.user_data else '未生成')
        form_layout.addRow("激活码:", self.activation_code_label)
        
        # 激活状态显示
        self.activation_status_label = QLabel(self.user_data.get('activation_status', '未激活') if self.user_data else '未激活')
        form_layout.addRow("激活状态:", self.activation_status_label)
        
        # 过期时间设置
        self.expiry_date_edit = QDateTimeEdit()
        self.expiry_date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.expiry_date_edit.setCalendarPopup(True)
        if self.user_data and self.user_data.get('expired_time'):
            try:
                expiry_date = datetime.fromisoformat(self.user_data['expired_time'])
                self.expiry_date_edit.setDateTime(QDateTime(
                    expiry_date.year, expiry_date.month, expiry_date.day,
                    expiry_date.hour, expiry_date.minute, expiry_date.second
                ))
            except:
                # 默认设置为当前时间+30天
                self.expiry_date_edit.setDateTime(QDateTime.currentDateTime().addDays(30))
        else:
            # 默认设置为当前时间+30天
            self.expiry_date_edit.setDateTime(QDateTime.currentDateTime().addDays(30))
        form_layout.addRow("过期时间:", self.expiry_date_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        if self.user_data:
            # 生成激活码按钮
            self.generate_code_button = QPushButton("生成激活码")
            self.generate_code_button.clicked.connect(self.generate_activation_code)
            button_layout.addWidget(self.generate_code_button)
        
        # 确定取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_user)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def generate_activation_code(self):
        """生成激活码"""
        if not self.user_data or not self.user_data.get('id'):
            QMessageBox.warning(self, "错误", "请先保存用户信息")
            return
            
        result = self.db_manager.generate_activation_code(self.user_data['id'])
        
        if result['success']:
            self.activation_code_label.setText(result['code'])
            QMessageBox.information(self, "成功", f"激活码生成成功: {result['code']}")
        else:
            QMessageBox.warning(self, "失败", result['message'])
    
    def save_user(self):
        """保存用户信息"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        nickname = self.nickname_input.text().strip()
        role = str(self.role_combo.currentIndex())
        
        # 修复 QDateTime 转换为 Python datetime 对象的方法
        qt_datetime = self.expiry_date_edit.dateTime().toPyDateTime()
        expiry_date = qt_datetime.isoformat()
        
        if not email or not nickname:
            QMessageBox.warning(self, "输入错误", "请输入邮箱和昵称")
            return
        
        if not self.user_data and not password:
            QMessageBox.warning(self, "输入错误", "新用户必须设置密码")
            return
        
        try:
            if self.user_data:
                # 更新用户
                result = self.db_manager.update_user(
                    self.user_data['id'],
                    nickname=nickname,
                    password=password if password else None,
                    role=role,
                    expired_time=expiry_date
                )
            else:
                # 创建用户
                result = self.db_manager.register_user_by_admin(
                    email=email,
                    password=password,
                    nickname=nickname,
                    role=role,
                    expired_time=expiry_date
                )
            
            if result['success']:
                self.accept()
            else:
                QMessageBox.warning(self, "保存失败", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")

class AdminPanel(QWidget):
    """管理员面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.admin_info = None
        
        # 应用扁平化样式
        self.setStyleSheet(get_flat_style())
        
        self.setup_ui()
        
        # 尝试自动登录
        self.handle_login()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        # 管理员信息区域
        self.admin_info_widget = self._create_admin_info_widget()
        layout.addWidget(self.admin_info_widget)
        
        # 选项卡区域
        self.tab_widget = QTabWidget()
        
        # 用户管理选项卡
        self.user_tab = self._create_user_tab()
        self.tab_widget.addTab(self.user_tab, "用户管理")
        
        # 激活码管理选项卡
        self.code_tab = self._create_code_tab()
        self.tab_widget.addTab(self.code_tab, "激活码管理")
        
        layout.addWidget(self.tab_widget)
        
        self.setLayout(layout)
        
        # 初始状态下禁用功能
        self.set_ui_enabled(False)
    
    def _create_admin_info_widget(self):
        """创建管理员信息区域"""
        group_box = QGroupBox("管理员信息")
        layout = QHBoxLayout()
        
        # 管理员信息显示
        info_layout = QVBoxLayout()
        self.admin_name_label = QLabel("未登录")
        self.admin_name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        
        self.admin_status_label = QLabel("请登录后使用管理功能")
        self.admin_status_label.setStyleSheet("color: #666666;")
        
        info_layout.addWidget(self.admin_name_label)
        info_layout.addWidget(self.admin_status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.handle_login)
        
        self.logout_button = QPushButton("退出登录")
        self.logout_button.clicked.connect(self.handle_logout)
        self.logout_button.setEnabled(False)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.logout_button)
        
        # 组合布局
        layout.addLayout(info_layout, 2)
        layout.addLayout(button_layout, 1)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_user_tab(self):
        """创建用户管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 搜索区域
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel("邮箱:"))
        self.email_filter = QLineEdit()
        self.email_filter.setPlaceholderText("输入邮箱筛选")
        search_layout.addWidget(self.email_filter)
        
        search_layout.addWidget(QLabel("昵称:"))
        self.nickname_filter = QLineEdit()
        self.nickname_filter.setPlaceholderText("输入昵称筛选")
        search_layout.addWidget(self.nickname_filter)
        
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.search_users)
        search_layout.addWidget(self.search_button)
        
        layout.addLayout(search_layout)
        
        # 用户列表
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(9)
        self.user_table.setHorizontalHeaderLabels([
            "操作", "邮箱", "昵称", "角色", "MAC地址", 
            "激活码", "激活状态", "过期时间", "最后登录时间"
        ])
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.user_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.user_table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.add_user_button = QPushButton("新增用户")
        self.add_user_button.clicked.connect(self.add_user)
        button_layout.addWidget(self.add_user_button)
        
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_users)
        button_layout.addWidget(self.refresh_button)
        
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        return widget
    
    def _create_code_tab(self):
        """创建激活码管理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 激活码列表
        self.code_table = QTableWidget()
        self.code_table.setColumnCount(8)
        self.code_table.setHorizontalHeaderLabels([
            "操作", "激活码", "用户邮箱", "激活状态", "过期时间", "激活时间", "创建时间", "更新时间"
        ])
        
        # 设置列宽
        self.code_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.code_table.setColumnWidth(0, 150)  # 操作列宽度增加
        self.code_table.setColumnWidth(1, 180)  # 激活码列宽度适中
        self.code_table.setColumnWidth(2, 200)  # 用户邮箱
        self.code_table.setColumnWidth(3, 100)  # 激活状态
        self.code_table.setColumnWidth(4, 150)  # 过期时间
        self.code_table.setColumnWidth(5, 150)  # 激活时间
        self.code_table.setColumnWidth(6, 150)  # 创建时间
        self.code_table.setColumnWidth(7, 150)  # 更新时间
        
        # 设置选择行为和编辑触发器
        self.code_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.code_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.code_table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.add_code_button = QPushButton("新增激活码")
        self.add_code_button.clicked.connect(self.generate_code)
        button_layout.addWidget(self.add_code_button)
        
        self.refresh_code_button = QPushButton("刷新")
        self.refresh_code_button.clicked.connect(self.refresh_codes)
        button_layout.addWidget(self.refresh_code_button)
        
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        return widget
    
    def handle_login(self):
        """处理登录"""
        dialog = AdminLoginDialog(self)
        if dialog.exec():
            self.admin_info = dialog.user_info
            self.admin_name_label.setText(f"管理员: {self.admin_info['nickname']}")
            self.admin_status_label.setText("已登录")
            self.login_button.setEnabled(False)
            self.logout_button.setEnabled(True)
            
            # 启用功能
            self.set_ui_enabled(True)
            
            # 加载数据
            self.refresh_users()
            self.refresh_codes()
        
    def handle_logout(self):
        """处理退出登录"""
        self.admin_info = None
        self.admin_name_label.setText("未登录")
        self.admin_status_label.setText("请登录后使用管理功能")
        self.login_button.setEnabled(True)
        self.logout_button.setEnabled(False)
        
        # 禁用功能
        self.set_ui_enabled(False)
        
        # 清空数据
        self.user_table.setRowCount(0)
        self.code_table.setRowCount(0)
    
    def set_ui_enabled(self, enabled):
        """设置界面启用状态"""
        self.tab_widget.setEnabled(enabled)
    
    def search_users(self):
        """搜索用户"""
        email = self.email_filter.text().strip()
        nickname = self.nickname_filter.text().strip()
        
        self.refresh_users(email, nickname)
    
    def refresh_users(self, email=None, nickname=None):
        """刷新用户列表"""
        if not self.admin_info:
            return
            
        try:
            result = self.db_manager.get_users(email, nickname)
            
            if result['success']:
                self.display_users(result['users'])
            else:
                QMessageBox.warning(self, "获取用户失败", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取用户失败: {str(e)}")
    
    def display_users(self, users):
        """显示用户列表"""
        self.user_table.setRowCount(0)
        
        for user in users:
            row = self.user_table.rowCount()
            self.user_table.insertRow(row)
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_button = QPushButton("✎")  # 使用编辑图标
            edit_button.setProperty("user_id", user['id'])
            edit_button.clicked.connect(lambda _, btn=edit_button: self.edit_user(btn.property("user_id")))
            edit_button.setFixedSize(45, 20)  
            edit_button.setFont(QFont("微软雅黑", 8))  
            
            delete_button = QPushButton("✖")  # 使用删除图标
            delete_button.setProperty("user_id", user['id'])
            delete_button.clicked.connect(lambda _, btn=delete_button: self.delete_user(btn.property("user_id")))
            delete_button.setFixedSize(45, 20)  
            delete_button.setFont(QFont("微软雅黑", 8))  
            
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            
            self.user_table.setCellWidget(row, 0, action_widget)
            
            # 用户信息
            self.user_table.setItem(row, 1, QTableWidgetItem(user.get('email', '')))
            self.user_table.setItem(row, 2, QTableWidgetItem(user.get('nickname', '')))
            
            # 角色
            role_map = {"0": "管理员", "1": "普通用户", "2": "付费用户"}
            role = role_map.get(user.get('role', '1'), "普通用户")
            self.user_table.setItem(row, 3, QTableWidgetItem(role))
            
            self.user_table.setItem(row, 4, QTableWidgetItem(user.get('mac', '')))
            self.user_table.setItem(row, 5, QTableWidgetItem(user.get('activation_code', '')))
            self.user_table.setItem(row, 6, QTableWidgetItem(user.get('activation_status', '未激活')))
            
            # 格式化日期
            expiry_date = user.get('expired_time', '')
            if expiry_date:
                try:
                    date_obj = datetime.fromisoformat(expiry_date)
                    expiry_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            self.user_table.setItem(row, 7, QTableWidgetItem(expiry_date))
            
            last_login = user.get('last_login_time', '')
            if last_login:
                try:
                    date_obj = datetime.fromisoformat(last_login)
                    last_login = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            self.user_table.setItem(row, 8, QTableWidgetItem(last_login))
    
    def add_user(self):
        """添加用户"""
        dialog = UserEditDialog(self.db_manager, None, self)
        if dialog.exec():
            self.refresh_users()
    
    def edit_user(self, user_id):
        """编辑用户"""
        try:
            result = self.db_manager.get_user_by_id(user_id)
            
            if result['success']:
                dialog = UserEditDialog(self.db_manager, result['user'], self)
                if dialog.exec():
                    self.refresh_users()
            else:
                QMessageBox.warning(self, "获取用户失败", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取用户失败: {str(e)}")
    
    def delete_user(self, user_id):
        """删除用户"""
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            "确定要删除此用户吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.db_manager.delete_user(user_id)
                
                if result['success']:
                    QMessageBox.information(self, "成功", "用户删除成功")
                    self.refresh_users()
                else:
                    QMessageBox.warning(self, "删除失败", result['message'])
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除用户失败: {str(e)}")
    
    def refresh_codes(self):
        """刷新激活码列表"""
        if not self.admin_info:
            return
            
        try:
            result = self.db_manager.get_activation_codes()
            
            if result['success']:
                self.display_codes(result['codes'])
            else:
                QMessageBox.warning(self, "获取激活码失败", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取激活码失败: {str(e)}")
    
    def display_codes(self, codes):
        """显示激活码列表"""
        self.code_table.setRowCount(0)
        
        for code in codes:
            row = self.code_table.rowCount()
            self.code_table.insertRow(row)
            
            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(5, 2, 5, 2)  
            btn_layout.setSpacing(10)  
            
            edit_btn = QPushButton("✎")  # 使用编辑图标
            edit_btn.setFixedSize(45, 20)  
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 9pt;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            edit_btn.clicked.connect(lambda checked, code_id=code.get('id'): self.edit_code(code_id))
            edit_btn.setFont(QFont("微软雅黑", 8))  
            
            delete_btn = QPushButton("✖")  # 使用删除图标
            delete_btn.setFixedSize(45, 20)  
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 9pt;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            delete_btn.clicked.connect(lambda checked, code_id=code.get('id'): self.delete_code(code_id))
            delete_btn.setFont(QFont("微软雅黑", 8))  
            
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_widget.setLayout(btn_layout)
            
            self.code_table.setCellWidget(row, 0, btn_widget)
            self.code_table.setItem(row, 1, QTableWidgetItem(code.get('code', '')))
            self.code_table.setItem(row, 2, QTableWidgetItem(code.get('user_email', '')))
            self.code_table.setItem(row, 3, QTableWidgetItem(code.get('activation_status', '未激活')))
            
            # 格式化过期时间
            expiry_date = code.get('expiry_date', '')
            if expiry_date:
                try:
                    date_obj = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    expiry_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"日期解析错误: {str(e)}")
            self.code_table.setItem(row, 4, QTableWidgetItem(expiry_date))
            
            # 格式化激活时间
            activation_time = code.get('activation_time', '')
            if activation_time:
                try:
                    date_obj = datetime.fromisoformat(activation_time.replace('Z', '+00:00'))
                    activation_time = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"日期解析错误: {str(e)}")
            self.code_table.setItem(row, 5, QTableWidgetItem(activation_time))
            
            # 格式化创建时间
            create_time = code.get('create_time', '')
            if create_time:
                try:
                    date_obj = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
                    create_time = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"日期解析错误: {str(e)}")
            self.code_table.setItem(row, 6, QTableWidgetItem(create_time))
            
            # 格式化更新时间
            update_time = code.get('update_time', '')
            if update_time:
                try:
                    date_obj = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                    update_time = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"日期解析错误: {str(e)}")
            self.code_table.setItem(row, 7, QTableWidgetItem(update_time))
    
    def generate_code(self):
        """生成激活码"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新增激活码")
        dialog.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        # 激活码自动生成
        activation_code = str(uuid.uuid4()).replace('-', '')[:16].upper()
        code_label = QLabel(activation_code)
        form_layout.addRow("激活码:", code_label)
        
        # 激活状态默认为未激活
        status_label = QLabel("未激活")
        form_layout.addRow("激活状态:", status_label)
        
        # 有效期输入
        duration_input = QLineEdit()
        duration_input.setText("30")
        form_layout.addRow("有效期(天):", duration_input)
        
        layout.addLayout(form_layout)
        
        # 按钮区域
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec():
            try:
                duration = int(duration_input.text())
                if duration <= 0:
                    QMessageBox.warning(self, "输入错误", "有效期必须大于0")
                    return
                    
                result = self.db_manager.create_activation_code(duration)
                
                if result['success']:
                    QMessageBox.information(self, "成功", f"激活码生成成功: {result['code']}")
                    self.refresh_codes()
                else:
                    QMessageBox.warning(self, "生成失败", result['message'])
                    
            except ValueError:
                QMessageBox.warning(self, "输入错误", "有效期必须是数字")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"生成激活码失败: {str(e)}")
    
    def edit_code(self, code_id):
        """编辑激活码"""
        try:
            # 获取激活码信息
            result = self.db_manager.get_activation_code_by_id(code_id)
            
            if not result['success']:
                QMessageBox.warning(self, "获取激活码失败", result['message'])
                return
                
            code_data = result['code']
            
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑激活码")
            dialog.setFixedSize(400, 300)
            
            layout = QVBoxLayout()
            
            form_layout = QFormLayout()
            
            # 激活码（不可修改）
            code_label = QLabel(code_data.get('code', ''))
            form_layout.addRow("激活码:", code_label)
            
            # 用户邮箱（只读）
            email_label = QLabel(code_data.get('user_email', ''))
            form_layout.addRow("用户邮箱:", email_label)
            
            # 激活状态（只读）
            status_label = QLabel(code_data.get('activation_status', '未激活'))
            form_layout.addRow("激活状态:", status_label)
            
            # 过期时间（可修改）
            expiry_date = None
            if code_data.get('expiry_date'):
                try:
                    expiry_date = datetime.fromisoformat(code_data['expiry_date'].replace('Z', '+00:00'))
                except Exception as e:
                    print(f"日期解析错误: {str(e)}")
            
            expiry_date_edit = QDateTimeEdit()
            expiry_date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            expiry_date_edit.setCalendarPopup(True)
            if expiry_date:
                expiry_date_edit.setDateTime(QDateTime(expiry_date.year, expiry_date.month, expiry_date.day, 
                                                      expiry_date.hour, expiry_date.minute, expiry_date.second))
            else:
                expiry_date_edit.setDateTime(QDateTime.currentDateTime().addDays(30))
            form_layout.addRow("过期时间:", expiry_date_edit)
            
            # 激活时间（只读）
            activation_time = ''
            if code_data.get('activation_time'):
                try:
                    date_obj = datetime.fromisoformat(code_data['activation_time'].replace('Z', '+00:00'))
                    activation_time = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"日期解析错误: {str(e)}")
            activation_time_label = QLabel(activation_time)
            form_layout.addRow("激活时间:", activation_time_label)
            
            # 创建时间（只读）
            create_time = ''
            if code_data.get('create_time'):
                try:
                    date_obj = datetime.fromisoformat(code_data['create_time'].replace('Z', '+00:00'))
                    create_time = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"日期解析错误: {str(e)}")
            create_time_label = QLabel(create_time)
            form_layout.addRow("创建时间:", create_time_label)
            
            layout.addLayout(form_layout)
            
            # 按钮区域
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec():
                # 更新过期时间
                qt_datetime = expiry_date_edit.dateTime()
                new_expiry_date = datetime(
                    qt_datetime.date().year(),
                    qt_datetime.date().month(),
                    qt_datetime.date().day(),
                    qt_datetime.time().hour(),
                    qt_datetime.time().minute(),
                    qt_datetime.time().second()
                )
                
                result = self.db_manager.update_activation_code(code_id, expiry_date=new_expiry_date.isoformat())
                
                if result['success']:
                    QMessageBox.information(self, "成功", "激活码更新成功")
                    self.refresh_codes()
                else:
                    QMessageBox.warning(self, "更新失败", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑激活码失败: {str(e)}")
    
    def delete_code(self, code_id):
        """删除激活码"""
        try:
            # 确认是否删除
            confirm = QMessageBox.question(
                self, 
                "确认删除", 
                "确定要删除该激活码吗？如果该激活码已被用户使用，删除后将导致用户无法继续使用。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                result = self.db_manager.delete_activation_code(code_id)
                
                if result['success']:
                    QMessageBox.information(self, "成功", "激活码删除成功")
                    self.refresh_codes()
                else:
                    QMessageBox.warning(self, "删除失败", result['message'])
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除激活码失败: {str(e)}")
