import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QComboBox, QMessageBox, QGroupBox, QFormLayout,
                             QDialog, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon

# 导入数据库相关模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.user_manager import LoginDialog, ActivationDialog
from models.article_manager import ArticleManager
from models.database import DatabaseManager

class DatabaseIntegrationUI(QWidget):
    """数据库集成界面，提供用户管理和文章数据库功能"""
    
    # 定义信号
    login_status_changed = pyqtSignal(bool, dict)  # 登录状态变化信号
    article_selected = pyqtSignal(dict)           # 文章选中信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_info = None
        self.article_manager = ArticleManager()
        
        # 连接信号
        self.article_manager.save_success.connect(self._on_save_success)
        self.article_manager.save_failed.connect(self._on_save_failed)
        self.article_manager.query_success.connect(self._on_query_success)
        self.article_manager.query_failed.connect(self._on_query_failed)
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 用户信息区域
        self.user_info_widget = self._create_user_info_widget()
        layout.addWidget(self.user_info_widget)
        
        # 选项卡区域
        self.tab_widget = QTabWidget()
        
        # 文章库选项卡
        self.article_tab = self._create_article_tab()
        self.tab_widget.addTab(self.article_tab, "文章库")
        
        # 设置选项卡
        self.settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "设置")
        
        layout.addWidget(self.tab_widget)
        
        self.setLayout(layout)
    
    def _create_user_info_widget(self):
        """创建用户信息区域"""
        group_box = QGroupBox("用户信息")
        layout = QHBoxLayout()
        
        # 用户信息显示
        info_layout = QVBoxLayout()
        self.user_name_label = QLabel("未登录")
        self.user_name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        
        self.user_status_label = QLabel("请登录后使用数据库功能")
        self.user_status_label.setStyleSheet("color: #666666;")
        
        info_layout.addWidget(self.user_name_label)
        info_layout.addWidget(self.user_status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.handle_login)
        
        self.activate_button = QPushButton("激活账号")
        self.activate_button.clicked.connect(self.handle_activate)
        self.activate_button.setEnabled(False)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.activate_button)
        
        # 组合布局
        layout.addLayout(info_layout, 2)
        layout.addLayout(button_layout, 1)
        
        group_box.setLayout(layout)
        return group_box
    
    def _create_article_tab(self):
        """创建文章库选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 搜索区域
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel("公众号:"))
        self.account_filter = QLineEdit()
        self.account_filter.setPlaceholderText("输入公众号名称筛选")
        search_layout.addWidget(self.account_filter)
        
        search_layout.addWidget(QLabel("关键词:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入关键词搜索")
        search_layout.addWidget(self.keyword_input)
        
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.search_articles)
        search_layout.addWidget(self.search_button)
        
        layout.addLayout(search_layout)
        
        # 文章列表
        self.article_table = QTableWidget()
        self.article_table.setColumnCount(5)
        self.article_table.setHorizontalHeaderLabels(["标题", "公众号", "发布时间", "阅读数", "操作"])
        self.article_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.article_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.article_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.article_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.article_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.article_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.article_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.article_table)
        
        # 分页控制
        pagination_layout = QHBoxLayout()
        
        self.prev_page_button = QPushButton("上一页")
        self.prev_page_button.clicked.connect(self.prev_page)
        
        self.page_label = QLabel("第1页")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_page_button = QPushButton("下一页")
        self.next_page_button.clicked.connect(self.next_page)
        
        pagination_layout.addStretch(1)
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)
        pagination_layout.addStretch(1)
        
        layout.addLayout(pagination_layout)
        
        widget.setLayout(layout)
        return widget
    
    def _create_settings_tab(self):
        """创建设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 数据库设置
        db_group = QGroupBox("数据库设置")
        db_layout = QFormLayout()
        
        # 自动保存设置
        self.auto_save_checkbox = QCheckBox("下载文章时自动保存到数据库")
        db_layout.addRow(self.auto_save_checkbox)
        
        # 数据库状态
        db_status_layout = QHBoxLayout()
        db_status_layout.addWidget(QLabel("数据库连接状态:"))
        self.db_status_label = QLabel("未连接")
        self.db_status_label.setStyleSheet("color: red;")
        db_status_layout.addWidget(self.db_status_label)
        
        self.test_connection_button = QPushButton("测试连接")
        self.test_connection_button.clicked.connect(self.test_db_connection)
        db_status_layout.addWidget(self.test_connection_button)
        
        db_layout.addRow(db_status_layout)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # 账号设置
        account_group = QGroupBox("账号设置")
        account_layout = QFormLayout()
        
        # 修改密码
        change_pwd_layout = QHBoxLayout()
        self.change_pwd_button = QPushButton("修改密码")
        self.change_pwd_button.clicked.connect(self.change_password)
        change_pwd_layout.addWidget(self.change_pwd_button)
        account_layout.addRow(change_pwd_layout)
        
        # 退出登录
        logout_layout = QHBoxLayout()
        self.logout_button = QPushButton("退出登录")
        self.logout_button.clicked.connect(self.handle_logout)
        logout_layout.addWidget(self.logout_button)
        account_layout.addRow(logout_layout)
        
        account_group.setLayout(account_layout)
        layout.addWidget(account_group)
        
        layout.addStretch(1)
        
        widget.setLayout(layout)
        return widget
    
    def handle_login(self):
        """处理登录"""
        if self.user_info:  # 已登录状态
            reply = QMessageBox.question(
                self, "确认退出", "确定要退出当前账号吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.handle_logout()
        else:  # 未登录状态
            login_dialog = LoginDialog(self)
            login_dialog.login_success.connect(self._on_login_success)
            login_dialog.exec()
    
    def handle_activate(self):
        """处理账号激活"""
        if not self.user_info:
            QMessageBox.warning(self, "未登录", "请先登录后再激活账号")
            return
            
        activate_dialog = ActivationDialog(self.user_info['id'], self)
        if activate_dialog.exec() == QDialog.DialogCode.Accepted:
            # 刷新用户信息
            self._refresh_user_info()
    
    def handle_logout(self):
        """处理退出登录"""
        self.user_info = None
        self.article_manager.set_user_id(None)
        
        # 更新UI
        self.user_name_label.setText("未登录")
        self.user_status_label.setText("请登录后使用数据库功能")
        self.login_button.setText("登录")
        self.activate_button.setEnabled(False)
        
        # 清空文章列表
        self.article_table.setRowCount(0)
        
        # 发送登录状态变化信号
        self.login_status_changed.emit(False, None)
        
        QMessageBox.information(self, "已退出", "已成功退出登录")
    
    def _on_login_success(self, user_info):
        """登录成功回调"""
        self.user_info = user_info
        self.article_manager.set_user_id(user_info['id'])
        
        # 更新UI
        self.user_name_label.setText(f"用户: {user_info['nickname']}")
        
        if user_info.get('expiry_date'):
            self.user_status_label.setText(f"授权有效期至: {user_info['expiry_date']}")
            self.activate_button.setEnabled(False)
        else:
            self.user_status_label.setText("账号未激活，请激活后使用")
            self.activate_button.setEnabled(True)
            
        self.login_button.setText("退出")
        
        # 加载文章列表
        self.search_articles()
        
        # 发送登录状态变化信号
        self.login_status_changed.emit(True, user_info)
        
        # 测试数据库连接
        self.test_db_connection()
    
    def _refresh_user_info(self):
        """刷新用户信息"""
        if not self.user_info:
            return
            
        try:
            # 获取最新的用户信息
            db_manager = DatabaseManager()
            user_data = db_manager.supabase.table('users').select('*').eq('id', self.user_info['id']).execute()
            
            if user_data.data:
                user = user_data.data[0]
                self.user_info = {
                    'id': user['id'],
                    'email': user['email'],
                    'nickname': user['nickname'],
                    'expiry_date': user.get('expiry_date')
                }
                
                # 更新UI
                if user.get('expiry_date'):
                    self.user_status_label.setText(f"授权有效期至: {user['expiry_date']}")
                    self.activate_button.setEnabled(False)
                else:
                    self.user_status_label.setText("账号未激活，请激活后使用")
                    self.activate_button.setEnabled(True)
                    
                # 发送登录状态变化信号
                self.login_status_changed.emit(True, self.user_info)
                
        except Exception as e:
            QMessageBox.warning(self, "刷新失败", f"刷新用户信息失败: {str(e)}")
    
    def search_articles(self):
        """搜索文章"""
        if not self.user_info:
            QMessageBox.warning(self, "未登录", "请先登录后再搜索文章")
            return
            
        account_name = self.account_filter.text().strip()
        keyword = self.keyword_input.text().strip()
        
        if keyword:
            # 关键词搜索
            self.article_manager.search_articles(keyword)
        else:
            # 按公众号筛选
            self.article_manager.get_articles(account_name if account_name else None)
    
    def _on_query_success(self, articles):
        """查询成功回调"""
        self.article_table.setRowCount(0)
        
        if not articles:
            QMessageBox.information(self, "查询结果", "未找到符合条件的文章")
            return
            
        # 填充表格
        self.article_table.setRowCount(len(articles))
        
        for i, article in enumerate(articles):
            # 标题
            title_item = QTableWidgetItem(article['title'])
            self.article_table.setItem(i, 0, title_item)
            
            # 公众号
            account_item = QTableWidgetItem(article['account_name'])
            self.article_table.setItem(i, 1, account_item)
            
            # 发布时间
            publish_time = article.get('publish_time', '')
            if publish_time and len(publish_time) > 10:
                publish_time = publish_time[:10]  # 只显示日期部分
            time_item = QTableWidgetItem(publish_time)
            self.article_table.setItem(i, 2, time_item)
            
            # 阅读数
            read_count_item = QTableWidgetItem(str(article.get('read_count', 0)))
            self.article_table.setItem(i, 3, read_count_item)
            
            # 操作按钮
            view_button = QPushButton("查看")
            view_button.setProperty("article_id", article['id'])
            view_button.setProperty("article_data", article)
            view_button.clicked.connect(self._on_view_article)
            
            self.article_table.setCellWidget(i, 4, view_button)
    
    def _on_query_failed(self, error_msg):
        """查询失败回调"""
        QMessageBox.warning(self, "查询失败", error_msg)
    
    def _on_save_success(self, result):
        """保存成功回调"""
        QMessageBox.information(self, "保存成功", "文章已成功保存到数据库")
    
    def _on_save_failed(self, error_msg):
        """保存失败回调"""
        QMessageBox.warning(self, "保存失败", error_msg)
    
    def _on_view_article(self):
        """查看文章回调"""
        sender = self.sender()
        article_data = sender.property("article_data")
        
        if article_data:
            self.article_selected.emit(article_data)
    
    def prev_page(self):
        """上一页"""
        # TODO: 实现分页功能
        pass
    
    def next_page(self):
        """下一页"""
        # TODO: 实现分页功能
        pass
    
    def change_password(self):
        """修改密码"""
        # TODO: 实现修改密码功能
        QMessageBox.information(self, "功能开发中", "密码修改功能正在开发中")
    
    def test_db_connection(self):
        """测试数据库连接"""
        try:
            db_manager = DatabaseManager()
            # 简单查询测试连接
            db_manager.supabase.table('users').select('count', count='exact').execute()
            
            self.db_status_label.setText("已连接")
            self.db_status_label.setStyleSheet("color: green;")
            
        except Exception as e:
            self.db_status_label.setText("连接失败")
            self.db_status_label.setStyleSheet("color: red;")
            QMessageBox.warning(self, "连接失败", f"数据库连接失败: {str(e)}")
    
    def is_auto_save_enabled(self):
        """检查是否启用自动保存"""
        return self.auto_save_checkbox.isChecked()
    
    def get_current_user_id(self):
        """获取当前用户ID"""
        if self.user_info:
            return self.user_info['id']
        return None