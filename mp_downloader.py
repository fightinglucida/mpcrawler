import sys
import os
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QGroupBox, QCheckBox, QDialog, QMessageBox, QFrame, QStatusBar,
                             QSizePolicy, QProgressBar, QScrollArea, QAbstractItemView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QIcon, QFont, QImage
from utils import get_wechat_login
import requests
from utils.search_thread import SearchThread
import pandas as pd
import os.path
from utils.article_downloader import ArticleDownloadManager, WeChatArticleDownloader

class SingleArticleDownloader(QObject):
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    download_progress = pyqtSignal(str)

    def __init__(self, article_url, download_path):
        super().__init__()
        self.article_url = article_url
        self.download_path = download_path

    def download(self):
        try:
            # 创建下载目录
            os.makedirs(self.download_path, exist_ok=True)
            
            # 使用WeChatArticleDownloader下载文章
            self.download_progress.emit("正在下载文章...")
            downloader = WeChatArticleDownloader(self.download_path)
            
            # 下载文章
            success, file_path = downloader.download_article(self.article_url)
            
            if success:
                self.download_complete.emit(file_path)
            else:
                self.download_error.emit("文章下载失败，请检查链接是否正确")
        except Exception as e:
            self.download_error.emit(f"下载出错：{str(e)}")

class LoginThread(QThread):
    """登录线程，避免UI卡顿"""
    login_success = pyqtSignal(dict)  # 登录成功信号
    login_failed = pyqtSignal(str)    # 登录失败信号
    qrcode_ready = pyqtSignal(bytes)  # 二维码准备好信号
    status_update = pyqtSignal(str)   # 状态更新信号

    def __init__(self):
        super().__init__()
        self.wechat_api = get_wechat_login()
        
    def run(self):
        try:
            # 检查是否已登录
            session = requests.session()
            cookie_path = self.wechat_api.cookie_path
            
            if os.path.exists(cookie_path):
                self.status_update.emit("检查登录状态...")
                # 尝试使用现有cookie登录
                login_info = self.wechat_api.login()
                self.login_success.emit(login_info)
            else:
                self.status_update.emit("需要扫码登录...")
                # 获取二维码
                session = requests.session()
                session.get('https://mp.weixin.qq.com/', headers=self.wechat_api.headers)
                session.post(
                    'https://mp.weixin.qq.com/cgi-bin/bizlogin?action=startlogin',
                    data='userlang=zh_CN&redirect_url=&login_type=3&sessionid={}&token=&lang=zh_CN&f=json&ajax=1'.format(
                        int(time.time() * 1000)
                    ), 
                    headers=self.wechat_api.headers
                )
                
                # 获取登录二维码
                login_url = session.get(
                    'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={}'.format(
                        int(time.time() * 1000)
                    )
                )
                
                # 发送二维码信号
                self.qrcode_ready.emit(login_url.content)
                
                # 轮询登录状态
                date_url = 'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1'
                while True:
                    date = session.get(date_url).json()
                    if date['status'] == 0:
                        self.status_update.emit('二维码未失效，请扫码！')
                    elif date['status'] == 6:
                        self.status_update.emit('已扫码，请确认！')
                    elif date['status'] == 1:
                        self.status_update.emit('已确认，登录成功！')
                        url = session.post(
                            'https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login',
                            data='userlang=zh_CN&redirect_url=&cookie_forbidden=0&cookie_cleaned=1&plugin_used=0&login_type=3&token=&lang=zh_CN&f=json&ajax=1',
                            headers=self.wechat_api.headers
                        ).json()
                        
                        # 解析token
                        from urllib.parse import urlparse, parse_qs
                        token = parse_qs(urlparse(url['redirect_url']).query).get('token', [None])[0]
                        session.get('https://mp.weixin.qq.com{}'.format(url['redirect_url']), headers=self.wechat_api.headers)
                        
                        # 保存cookies和token信息
                        cookie = '; '.join([f"{name}={value}" for name, value in session.cookies.items()])
                        
                        # 确保目录存在
                        os.makedirs(os.path.dirname(self.wechat_api.cookie_path), exist_ok=True)
                        import pickle
                        with open(self.wechat_api.cookie_path, 'wb') as f:
                            pickle.dump(session.cookies, f)
                            
                        login_info = {'token': token, 'cookie': cookie}
                        
                        # 确保目录存在
                        os.makedirs(os.path.dirname(self.wechat_api.cookie_json_path), exist_ok=True)
                        import json
                        with open(self.wechat_api.cookie_json_path, 'w') as f:
                            json.dump(login_info, f, ensure_ascii=False)
                            
                        self.login_success.emit(login_info)
                        break
                        
                    time.sleep(2)
                    
        except Exception as e:
            self.login_failed.emit(str(e))


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录公众号")
        self.setFixedSize(400, 450)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)  # 设置控件之间的间距
        layout.setContentsMargins(30, 30, 30, 30)  # 设置布局的外边距
        
        # 二维码区域
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(225, 225)  # 调整为原来大小的75%
        self.qr_label.setText("正在加载二维码...")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("border: 1px solid #dcdde1; border-radius: 4px; padding: 10px;")
        
        # 提示文本
        tip_label = QLabel("请使用微信扫描二维码登录公众号")
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_label.setFont(QFont("Microsoft YaHei", 12))
        tip_label.setStyleSheet("color: #333333;")
        
        # 状态信息
        self.status_label = QLabel("等待扫码...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: red;")
        
        # 添加控件并设置边距
        layout.addWidget(self.qr_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setLayout(layout)
        
        # 登录线程
        self.login_thread = None
        
        # 开始登录流程
        self.start_login()
    
    def start_login(self):
        """开始登录流程"""
        if self.login_thread and self.login_thread.isRunning():
            self.login_thread.terminate()
            self.login_thread.wait()
            
        self.login_thread = LoginThread()
        self.login_thread.login_success.connect(self.on_login_success)
        self.login_thread.login_failed.connect(self.on_login_failed)
        self.login_thread.qrcode_ready.connect(self.on_qrcode_ready)
        self.login_thread.status_update.connect(self.on_status_update)
        
        self.status_label.setText("正在登录...")
        self.login_thread.start()
    
    def on_login_success(self, login_info):
        """登录成功回调"""
        self.status_label.setText("登录成功！")
        
        # 保存登录信息以便在主窗口使用
        if hasattr(self.parent(), 'login_info'):
            self.parent().login_info = login_info
            
        self.accept()  # 关闭对话框并返回接受结果
    
    def on_login_failed(self, error_msg):
        """登录失败回调"""
        self.status_label.setText(f"登录失败: {error_msg}")
        QMessageBox.critical(self, "登录失败", f"登录失败: {error_msg}")
    
    def on_qrcode_ready(self, qrcode_data):
        """二维码准备好回调"""
        # 将二维码数据转换为QPixmap并显示
        image = QImage.fromData(qrcode_data)
        pixmap = QPixmap.fromImage(image)
        
        # 调整大小以适应标签
        scaled_pixmap = pixmap.scaled(225, 225, Qt.AspectRatioMode.KeepAspectRatio)
        self.qr_label.setPixmap(scaled_pixmap)
    
    def on_status_update(self, status):
        """状态更新回调"""
        self.status_label.setText(status)
        
    def closeEvent(self, event):
        """重写关闭事件处理"""
        # 终止登录线程
        if self.login_thread and self.login_thread.isRunning():
            self.login_thread.terminate()
            self.login_thread.wait()
        
        # 隐藏对话框而不是退出应用
        self.hide()
        event.ignore()

class WechatCollectorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 全局样式设置
        self.setStyleSheet("""
            QMainWindow {
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
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
                gridline-color: #f0f0f0;
                selection-background-color: #e8f0fe;
                selection-color: #333333;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 5px;
                border: none;
                border-right: 1px solid #e0e0e0;
                border-bottom: 1px solid #e0e0e0;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                color: #333333;
            }
        """)
        
        # 设置窗口标题和大小
        self.setWindowTitle("公众号采集与下载助手")
        self.setMinimumSize(1200, 800)
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.svg")
        self.setWindowIcon(QIcon(icon_path))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)  # 设置主布局边距
        main_layout.setSpacing(5)  # 设置主布局间距
        
        # 创建顶部布局
        top_layout = QHBoxLayout()
        top_layout.setSpacing(5)  # 设置顶部布局间距
        
        # 创建合并的登录状态和账号信息区域
        self.create_login_section(top_layout)
        
        # 创建合并的公众号搜索和信息区域
        self.create_search_account_section(top_layout)
        
        # 将顶部布局添加到主布局
        main_layout.addLayout(top_layout)
        
        # 创建文章列表区域
        self.create_article_list_section(main_layout)
        
        setting_layout = QHBoxLayout()
        setting_layout.setSpacing(5)  # 设置设置布局间距
        

        # 创建导出设置区域
        self.create_export_section(setting_layout)
        
        # 创建合并的下载设置和控制区域
        self.create_download_section(setting_layout)

        main_layout.addLayout(setting_layout)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("欢迎使用公众号采集助手")
        
        # 当前登录状态
        self.is_logged_in = False
        self.login_info = None
        
        # 搜索线程
        self.search_thread = None
        self.searching = False
        
        # 初始状态下禁用所有功能，等待登录检查
        self.disable_all_features()
    
    def create_login_section(self, parent_layout):
        """创建合并的登录状态和账号信息区域"""
        # 统一的样式设置
        GROUP_STYLE = """
            QGroupBox {
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        
        login_group = QGroupBox("登录状态和账号信息")
        login_group.setStyleSheet(GROUP_STYLE)
        login_layout = QVBoxLayout()
        login_layout.setContentsMargins(20, 5, 20, 5)  # 增加内边距
        login_layout.setSpacing(10)  # 增加控件间距

        login_static_layout = QHBoxLayout()
        login_static_layout.setSpacing(10)  # 增加控件间距

        login_info_layout = QHBoxLayout()
        login_info_layout.setSpacing(10)  # 增加控件间距
        
        # 登录状态
        self.login_status_label = QLabel("未登录")
        self.login_status_label.setFont(QFont("Microsoft YaHei", 9))
        self.login_status_label.setStyleSheet("color: #e74c3c;")  # 红色表示未登录
        
        self.login_button = QPushButton("登录")
        self.login_button.setFixedWidth(60)  # 设置固定宽度
        self.login_button.clicked.connect(self.handle_login)
        
        # 账号信息
        self.login_avatar_label = QLabel()
        self.login_avatar_label.setFixedSize(40, 40)
        self.login_avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.login_avatar_label.setFrameShape(QFrame.Shape.Box)
        self.login_avatar_label.setStyleSheet("border: 1px solid #dcdde1; border-radius: 4px;")
        self.login_avatar_label.setText("头像")
        
        self.login_name_label = QLabel("登录公众号名称")
        self.login_name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        
        login_static_layout.addWidget(self.login_status_label)
        login_static_layout.addWidget(self.login_button)

        login_info_layout.addWidget(self.login_avatar_label)
        login_info_layout.addWidget(self.login_name_label)

        
        login_layout.addLayout(login_info_layout)
        login_layout.addLayout(login_static_layout)

        
        login_group.setLayout(login_layout)
        parent_layout.addWidget(login_group)
    
    def create_search_account_section(self, parent_layout):
        """创建合并的公众号搜索和信息区域"""
        # 统一的样式设置
        GROUP_STYLE = """
            QGroupBox {
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        


        search_group = QGroupBox("公众号文章搜索")
        search_group.setStyleSheet(GROUP_STYLE)
        search_layout = QVBoxLayout()
        search_layout.setContentsMargins(10, 15, 10, 10)  # 增加内边距
        search_layout.setSpacing(10)  # 增加控件间距

        article_input_layout = QHBoxLayout()
        article_input_layout.setSpacing(10)  # 增加控件间距

        search_input_layout = QHBoxLayout()
        search_input_layout.setSpacing(10)  # 增加控件间距

        search_result_layout = QHBoxLayout()
        search_result_layout.setSpacing(10)  # 增加控件间距


        # 公众号文章链接
        article_label = QLabel("公众号文章链接:")
        article_label.setFont(QFont("Microsoft YaHei", 9))
        article_input_layout.addWidget(article_label)
        
        self.article_input = QLineEdit()
        self.article_input.setPlaceholderText("请输入要下载的微信公众号文章链接")
        article_input_layout.addWidget(self.article_input)

        self.article_input_button = QPushButton("下载")
        self.article_input_button.clicked.connect(self.download_single_article)
        article_input_layout.addWidget(self.article_input_button)
        
        # 公众号名称
        name_label = QLabel("公众号账号名称:")
        name_label.setFont(QFont("Microsoft YaHei", 9))
        search_input_layout.addWidget(name_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入要搜索的微信公众号")
        search_input_layout.addWidget(self.search_input)
        
        # 文章数量
        count_label = QLabel("文章数量:")
        count_label.setFont(QFont("Microsoft YaHei", 9))
        search_input_layout.addWidget(count_label)
        
        self.search_count_input = QLineEdit("0")  # 默认为0表示搜索全部
        self.search_count_input.setFixedWidth(60)
        self.search_count_input.setToolTip("0表示搜索全部文章")
        search_input_layout.addWidget(self.search_count_input)
        
        # 搜索按钮
        self.search_button = QPushButton("搜索")
        self.search_button.setFixedWidth(80)  # 设置固定宽度
        self.search_button.clicked.connect(self.search_official_account)
        search_input_layout.addWidget(self.search_button)
        
        # 公众号信息
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFrameShape(QFrame.Shape.Box)
        self.avatar_label.setStyleSheet("border: 1px solid #dcdde1; border-radius: 4px;")
        self.avatar_label.setText("头像")
        
        self.account_name_label = QLabel("公众号名称")
        self.account_name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        
        self.article_count_label = QLabel("文章数: 0")
        self.article_count_label.setFont(QFont("Microsoft YaHei", 9))
        self.article_count_label.setStyleSheet("color: #666666;")
        
        search_result_layout.addWidget(self.avatar_label)
        search_result_layout.addWidget(self.account_name_label)
        search_result_layout.addWidget(self.article_count_label)
        
        search_layout.addLayout(article_input_layout)
        search_layout.addLayout(search_input_layout)
        search_layout.addLayout(search_result_layout)
        search_group.setLayout(search_layout)
        parent_layout.addWidget(search_group)
    
    def create_article_list_section(self, parent_layout):
        """创建文章列表区域"""
        # 统一样式设置
        GROUP_STYLE = """
            QGroupBox {
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        
        TABLE_STYLE = """
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
                gridline-color: #f0f0f0;
                selection-background-color: #e8f0fe;
                selection-color: #333333;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 5px;
                border: none;
                border-right: 1px solid #e0e0e0;
                border-bottom: 1px solid #e0e0e0;
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                color: #333333;
            }
        """
        
        # 按钮样式
        SELECT_ALL_BUTTON_STYLE = """
            QPushButton {
                background-color: #4CAF50;
                border: 1px solid #3d8b40;
                border-radius: 4px;
                padding: 2px 8px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #3d8b40;
            }
            QPushButton:pressed {
                background-color: #2d6a30;
            }
        """
        
        DESELECT_ALL_BUTTON_STYLE = """
            QPushButton {
                background-color: #f44336;
                border: 1px solid #d32f2f;
                border-radius: 4px;
                padding: 2px 8px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """
        
        CHECK_BUTTON_STYLE = """
            QPushButton {
                background-color: #2196F3;
                border: 1px solid #1976D2;
                border-radius: 4px;
                padding: 2px 8px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """
        
        UNCHECK_BUTTON_STYLE = """
            QPushButton {
                background-color: #f44336;
                border: 1px solid #d32f2f;
                border-radius: 4px;
                padding: 2px 8px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """
        
        list_group = QGroupBox("文章列表")
        list_group.setStyleSheet(GROUP_STYLE)
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(10, 15, 10, 10)  # 增加内边距
        list_layout.setSpacing(10)  # 增加控件间距
        
        # 创建表格
        self.article_table = QTableWidget()
        self.article_table.setStyleSheet(TABLE_STYLE)
        self.article_table.setColumnCount(7)
        self.article_table.setHorizontalHeaderLabels(["选择", "标题", "发布时间", "阅读数", "链接", "封面图片", "下载状态"])
        self.article_table.setAlternatingRowColors(True)  # 交替行颜色
        self.article_table.setShowGrid(True)  # 显示网格线
        self.article_table.setGridStyle(Qt.PenStyle.SolidLine)  # 实线网格
        
        # 设置表格属性
        self.article_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.article_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.article_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.article_table.setColumnWidth(0, 50)
        self.article_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.article_table.setColumnWidth(1, 240)
        self.article_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.article_table.setColumnWidth(2, 150)
        self.article_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.article_table.setColumnWidth(3, 80)
        self.article_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.article_table.setColumnWidth(4, 200)
        self.article_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.article_table.setColumnWidth(5, 80)
        self.article_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.article_table.setColumnWidth(6, 100)
        
        # 设置表格最小高度，增加文章列表显示空间
        self.article_table.setMinimumHeight(500)  # 进一步增加高度
        
        # 启用滚动条
        self.article_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.article_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 启用鼠标滚轮滚动
        self.article_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.article_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # 设置按钮间距
        
        # 创建按钮，大小为原来的60%
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setStyleSheet(SELECT_ALL_BUTTON_STYLE)
        self.select_all_btn.clicked.connect(self.select_all_articles)
        self.select_all_btn.setFixedWidth(60)  # 设置固定宽度
        
        self.deselect_all_btn = QPushButton("全不选")
        self.deselect_all_btn.setStyleSheet(DESELECT_ALL_BUTTON_STYLE)
        self.deselect_all_btn.clicked.connect(self.deselect_all_articles)
        self.deselect_all_btn.setFixedWidth(60)  # 设置固定宽度
        
        self.check_selected_btn = QPushButton("选中")
        self.check_selected_btn.setStyleSheet(CHECK_BUTTON_STYLE)
        self.check_selected_btn.clicked.connect(self.check_selected_articles)
        self.check_selected_btn.setFixedWidth(60)  # 设置固定宽度
        
        self.uncheck_selected_btn = QPushButton("取消选中")
        self.uncheck_selected_btn.setStyleSheet(UNCHECK_BUTTON_STYLE)
        self.uncheck_selected_btn.clicked.connect(self.uncheck_selected_articles)
        self.uncheck_selected_btn.setFixedWidth(80)  # 设置固定宽度
        
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.deselect_all_btn)
        button_layout.addWidget(self.check_selected_btn)
        button_layout.addWidget(self.uncheck_selected_btn)
        button_layout.addStretch(1)
        
        list_layout.addLayout(button_layout)
        list_layout.addWidget(self.article_table)
        
        list_group.setLayout(list_layout)
        parent_layout.addWidget(list_group)
    
    def create_export_section(self, parent_layout):
        """创建导出设置区域"""
        # 样式设置
        GROUP_STYLE = """
            QGroupBox {
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        
        INPUT_STYLE = """
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 5px;
                background-color: #ffffff;
                font-family: 'Microsoft YaHei';
                min-height: 25px;
            }
        """
        
        BROWSE_BUTTON_STYLE = """
            QPushButton {
                background-color: #607D8B;
                border: 1px solid #455A64;
                border-radius: 4px;
                padding: 3px 10px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
            QPushButton:pressed {
                background-color: #263238;
            }
        """
        
        EXPORT_BUTTON_STYLE = """
            QPushButton {
                background-color: #9C27B0;
                border: 1px solid #7B1FA2;
                border-radius: 4px;
                padding: 3px 10px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #4A148C;
            }
        """
        
        # 创建底部布局
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)  # 设置区域间距
        
        # 导出设置区域
        export_group = QGroupBox("导出设置")
        export_group.setStyleSheet(GROUP_STYLE)
        export_layout = QVBoxLayout()
        export_layout.setContentsMargins(10, 15, 10, 10)  # 增加内边距
        export_layout.setSpacing(10)  # 增加控件间距
        
        # 导出路径设置
        export_path_layout = QHBoxLayout()
        export_path_layout.setSpacing(10)  # 设置控件间距
        
        export_path_label = QLabel("导出路径:")
        export_path_label.setFont(QFont("Microsoft YaHei", 9))
        export_path_layout.addWidget(export_path_label)
        
        self.export_path_input = QLineEdit("./列表导出")
        self.export_path_input.setStyleSheet(INPUT_STYLE)
        self.export_path_input.setMinimumWidth(200)  # 设置最小宽度
        export_path_layout.addWidget(self.export_path_input)
        
        self.export_path_btn = QPushButton("浏览")
        self.export_path_btn.setStyleSheet(BROWSE_BUTTON_STYLE)
        self.export_path_btn.setFixedWidth(60)  # 设置固定宽度
        self.export_path_btn.clicked.connect(self.select_export_path)
        export_path_layout.addWidget(self.export_path_btn)
        
        export_layout.addLayout(export_path_layout)
        
        # 导出按钮
        export_btn_layout = QHBoxLayout()
        export_btn_layout.setSpacing(10)  # 设置控件间距
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.setStyleSheet(EXPORT_BUTTON_STYLE)
        # 缩小导出按钮宽度为原来的三分之一
        self.export_btn.setFixedWidth(100)  # 设置固定宽度
        self.export_btn.clicked.connect(self.export_article_list)
        export_btn_layout.addWidget(self.export_btn)
        export_btn_layout.addStretch(1)  # 添加弹性空间
        
        export_layout.addLayout(export_btn_layout)
        
        export_group.setLayout(export_layout)
        
        parent_layout.addWidget(export_group)
    
    def create_download_section(self, parent_layout):
        """创建合并的下载设置和控制区域"""
        # 样式设置
        GROUP_STYLE = """
            QGroupBox {
                font-family: 'Microsoft YaHei';
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
        
        INPUT_STYLE = """
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 5px;
                background-color: #ffffff;
                font-family: 'Microsoft YaHei';
                min-height: 25px;
            }
        """
        
        BROWSE_BUTTON_STYLE = """
            QPushButton {
                background-color: #607D8B;
                border: 1px solid #455A64;
                border-radius: 4px;
                padding: 3px 10px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
            QPushButton:pressed {
                background-color: #263238;
            }
        """

        
        DOWNLOAD_SELECTED_BUTTON_STYLE = """
            QPushButton {
                background-color: #2196F3;
                border: 1px solid #1976D2;
                border-radius: 4px;
                padding: 3px 10px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """
        
        DOWNLOAD_ALL_BUTTON_STYLE = """
            QPushButton {
                background-color: #4CAF50;
                border: 1px solid #388E3C;
                border-radius: 4px;
                padding: 3px 10px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:pressed {
                background-color: #1B5E20;
            }
        """
        
        STOP_BUTTON_STYLE = """
            QPushButton {
                background-color: #F44336;
                border: 1px solid #D32F2F;
                border-radius: 4px;
                padding: 3px 10px;
                font-family: 'Microsoft YaHei';
                color: white;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:pressed {
                background-color: #B71C1C;
            }
        """
        
        control_group = QGroupBox("下载设置和控制")
        control_group.setStyleSheet(GROUP_STYLE)
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(10, 15, 10, 10)  # 增加内边距
        control_layout.setSpacing(15)  # 增加控件间距
        
        # 下载路径
        download_path_layout = QHBoxLayout()
        download_path_layout.setSpacing(10)  # 设置控件间距
        
        download_path_label = QLabel("下载路径:")
        download_path_label.setFont(QFont("Microsoft YaHei", 9))
        download_path_layout.addWidget(download_path_label)
        
        self.download_path_input = QLineEdit("./文章原文")
        self.download_path_input.setStyleSheet(INPUT_STYLE)
        self.download_path_input.setMinimumWidth(200)  # 设置最小宽度
        download_path_layout.addWidget(self.download_path_input)
        
        self.download_path_btn = QPushButton("浏览")
        self.download_path_btn.setStyleSheet(BROWSE_BUTTON_STYLE)
        self.download_path_btn.setFixedWidth(60)  # 设置固定宽度
        self.download_path_btn.clicked.connect(self.select_download_path)
        download_path_layout.addWidget(self.download_path_btn)
        
        control_layout.addLayout(download_path_layout)
        

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)  # 设置按钮间距
        
        self.download_selected_btn = QPushButton("下载选中文章")
        self.download_selected_btn.setStyleSheet(DOWNLOAD_SELECTED_BUTTON_STYLE)
        self.download_selected_btn.clicked.connect(self.download_selected_articles)
        
        self.download_all_btn = QPushButton("下载全部文章")
        self.download_all_btn.setStyleSheet(DOWNLOAD_ALL_BUTTON_STYLE)
        self.download_all_btn.clicked.connect(self.download_all_articles)
        
        self.stop_download_btn = QPushButton("停止下载")
        self.stop_download_btn.setStyleSheet(STOP_BUTTON_STYLE)
        self.stop_download_btn.clicked.connect(self.stop_download)
        
        button_layout.addWidget(self.download_selected_btn)
        button_layout.addWidget(self.download_all_btn)
        button_layout.addWidget(self.stop_download_btn)
        button_layout.addStretch(1)
        
        # 添加到控制布局
        control_layout.addLayout(button_layout)
        
        control_group.setLayout(control_layout)
        parent_layout.addWidget(control_group)
    
    def check_login_status(self):
        """检查登录状态，如果未登录则显示登录对话框"""
        # 获取微信登录API实例
        wechat_api = get_wechat_login()
        
        # 检查cookie文件是否存在
        if os.path.exists(wechat_api.cookie_path):
            try:
                # 尝试使用现有cookie登录
                login_info = wechat_api.login()
                self.is_logged_in = True
                self.login_info = login_info  # 保存登录信息
                self.login_status_label.setText("已登录")
                self.login_button.setText("注销")
                self.enable_all_features()
                
                # 获取并显示公众号信息
                self.get_account_info()
            except Exception as e:
                self.is_logged_in = False
                self.login_info = None
                self.disable_all_features()
                self.show_login_dialog()
        else:
            self.is_logged_in = False
            self.login_info = None
            self.disable_all_features()
            self.show_login_dialog()
    
    def disable_all_features(self):
        """禁用所有功能"""
        self.search_input.setEnabled(False)
        self.search_count_input.setEnabled(False)
        self.search_button.setEnabled(False)
        self.article_table.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.deselect_all_btn.setEnabled(False)
        self.check_selected_btn.setEnabled(False)
        self.uncheck_selected_btn.setEnabled(False)
        self.export_path_input.setEnabled(False)
        self.export_path_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.download_path_input.setEnabled(False)
        self.download_path_btn.setEnabled(False)
        
        # 检查下载控制按钮是否已创建
        if hasattr(self, 'download_selected_btn'):
            self.download_selected_btn.setEnabled(False)
        if hasattr(self, 'download_all_btn'):
            self.download_all_btn.setEnabled(False)
        if hasattr(self, 'stop_download_btn'):
            self.stop_download_btn.setEnabled(False)
    
    def enable_all_features(self):
        """启用所有功能"""
        self.search_input.setEnabled(True)
        self.search_count_input.setEnabled(True)
        self.search_button.setEnabled(True)
        self.article_table.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)
        self.check_selected_btn.setEnabled(True)
        self.uncheck_selected_btn.setEnabled(True)
        self.export_path_input.setEnabled(True)
        self.export_path_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.download_path_input.setEnabled(True)
        self.download_path_btn.setEnabled(True)
        
        # 检查下载控制按钮是否已创建
        if hasattr(self, 'download_selected_btn'):
            self.download_selected_btn.setEnabled(True)
        if hasattr(self, 'download_all_btn'):
            self.download_all_btn.setEnabled(True)
        if hasattr(self, 'stop_download_btn'):
            self.stop_download_btn.setEnabled(False)  # 初始状态下停止按钮禁用
    
    def show_login_dialog(self):
        """显示登录对话框"""
        login_dialog = LoginDialog(self)
        if login_dialog.exec() == QDialog.DialogCode.Accepted:
            # 登录成功
            self.is_logged_in = True
            self.login_status_label.setText("已登录")
            self.login_button.setText("注销")
            self.enable_all_features()
            
            # 获取并显示公众号信息
            self.get_account_info()

    
    def handle_login(self):
        """处理登录或注销"""
        if self.is_logged_in:
            # 已登录状态，执行注销
            reply = QMessageBox.question(self, "确认注销", 
                                         "确定要注销当前账号吗？",
                                         QMessageBox.StandardButton.Yes | 
                                         QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                # 执行注销操作，删除cookie
                wechat_api = get_wechat_login()
                # 删除cookie文件
                if os.path.exists(wechat_api.cookie_path):
                    os.remove(wechat_api.cookie_path)
                if os.path.exists(wechat_api.cookie_json_path):
                    os.remove(wechat_api.cookie_json_path)
                    
                self.is_logged_in = False
                self.login_info = None
                self.login_status_label.setText("未登录")
                self.login_button.setText("登录")
                
                # 清空登录账号信息显示
                self.login_avatar_label.setText("头像")
                self.login_name_label.setText("登录公众号名称")
                
                # 清空目标公众号信息
                self.avatar_label.setText("头像")
                self.account_name_label.setText("公众号名称")
                self.article_count_label.setText("文章数: 0")
                
                self.disable_all_features()
                self.show_login_dialog()
        else:
            # 未登录状态，执行登录
            self.show_login_dialog()
            
            # 登录成功后获取公众号信息
            if self.is_logged_in:
                self.get_account_info()
            
    def get_account_info(self):
        """获取公众号信息（名称和头像）"""
        try:
            # 获取登录信息
            wechat_api = get_wechat_login()
            login_info = wechat_api.login()
            
            # 保存登录信息供搜索使用
            self.login_info = login_info
            
            # 设置请求头
            headers = {
                'User-Agent': wechat_api.ua.random,
                'Referer': "https://mp.weixin.qq.com/",
                "Host": "mp.weixin.qq.com",
                "Cookie": login_info['cookie']
            }
            
            # 请求公众号首页获取信息
            response = requests.get(
                f'https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={login_info["token"]}', 
                headers=headers
            )
            
            # 解析响应内容
            if response.status_code == 200:
                print("已获取响应内容")
                
                # 使用参考代码中的正则表达式模式
                import re
                content = response.text
                
                # 查找 window.wx.commonData 对象
                match = re.search(r'window\.wx\.commonData\s*=\s*({[\s\S]*?});', content)
                
                if match:
                    # 提取 JavaScript 对象字符串
                    js_obj_str = match.group(1)
                    
                    # 使用正则提取 nick_name
                    nick_name_match = re.search(r'nick_name:\s*"([^"]+)"', js_obj_str)
                    if nick_name_match:
                        gzh_name = nick_name_match.group(1)
                        print(f"成功获取公众号名称: {gzh_name}")
                        
                        # 获取头像URL
                        head_img_match = re.search(r'head_img:\s*\'([^\']+)\'', js_obj_str)
                        if head_img_match:
                            avatar_url = head_img_match.group(1)
                            if not avatar_url.startswith('https://'):
                                avatar_url = avatar_url.replace('http://', 'https://')
                            print(f"获取到头像URL: {avatar_url}")
                            
                            # 下载并显示头像
                            avatar_response = requests.get(avatar_url)
                            if avatar_response.status_code == 200:
                                avatar_image = QImage.fromData(avatar_response.content)
                                avatar_pixmap = QPixmap.fromImage(avatar_image)
                                
                                # 调整头像大小并显示
                                scaled_pixmap = avatar_pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio)
                                self.login_avatar_label.setPixmap(scaled_pixmap)
                                
                                # 显示公众号名称
                                self.login_name_label.setText(gzh_name)
                                
                                # 清空目标公众号信息
                                self.avatar_label.setText("头像")
                                self.account_name_label.setText("公众号名称")
                                self.article_count_label.setText("文章数: 0")
                                
                                return True
                            else:
                                print(f"获取头像失败: HTTP {avatar_response.status_code}")
                        else:
                            print("未找到头像URL，尝试使用默认头像")
                            # 即使没有头像，也显示公众号名称
                            self.account_name_label.setText(gzh_name)
                            return True
                    else:
                        print("未找到公众号名称")
                else:
                    print("未找到 window.wx.commonData 对象")
                    
                    # 尝试其他方式查找公众号名称
                    gzh_name_match = re.search(r'var nickname\s*=\s*"([^"]+)"', content)
                    if gzh_name_match:
                        gzh_name = gzh_name_match.group(1)
                        print(f"通过备用方式找到公众号名称: {gzh_name}")
                        
                        # 查找头像URL
                        head_img_match = re.search(r'var headimg\s*=\s*"([^"]+)"', content)
                        if head_img_match:
                            avatar_url = head_img_match.group(1)
                            if not avatar_url.startswith('https://'):
                                avatar_url = avatar_url.replace('http://', 'https://')
                            
                            # 下载并显示头像
                            avatar_response = requests.get(avatar_url)
                            if avatar_response.status_code == 200:
                                avatar_image = QImage.fromData(avatar_response.content)
                                avatar_pixmap = QPixmap.fromImage(avatar_image)
                                
                                # 调整头像大小并显示
                                scaled_pixmap = avatar_pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio)
                                self.login_avatar_label.setPixmap(scaled_pixmap)
                                
                                # 显示公众号名称
                                self.login_name_label.setText(gzh_name)
                                
                                # 清空目标公众号信息
                                self.avatar_label.setText("头像")
                                self.account_name_label.setText("公众号名称")
                                self.article_count_label.setText("文章数: 0")
                                
                                return True
                            else:
                                print(f"获取头像失败: HTTP {avatar_response.status_code}")
                        else:
                            print("未找到头像URL，尝试使用默认头像")
                            # 即使没有头像，也显示公众号名称
                            self.account_name_label.setText(gzh_name)
                            return True
                    else:
                        print("未找到公众号名称")
            else:
                print(f"获取公众号信息失败: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"获取公众号信息出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
        # 如果获取失败，显示默认信息
        self.avatar_label.setText("头像")
        self.account_name_label.setText("公众号名称")
        
        return False
    
    def search_official_account(self):
        """搜索公众号"""
        # 如果当前正在搜索，则停止搜索
        if self.searching:
            self.stop_search()
            return
            
        account_name = self.search_input.text()
        if not account_name:
            QMessageBox.warning(self, "搜索错误", "请输入公众号名称")
            return
        
        # 获取搜索数量
        try:
            search_count = int(self.search_count_input.text())
            if search_count < 0:
                raise ValueError("搜索数量不能为负数")
        except ValueError as e:
            QMessageBox.warning(self, "搜索错误", f"请输入有效的搜索数量: {str(e)}")
            return
        
        # 清空文章表格
        self.article_table.setRowCount(0)
        
        # 更改按钮状态
        self.search_button.setText("停止搜索")
        self.searching = True
        self.statusBar.showMessage(f"正在搜索公众号: {account_name}")
        
        # 创建并启动搜索线程
        self.search_thread = SearchThread(account_name, self.login_info, search_count)
        self.search_thread.search_success.connect(self.on_article_found)
        self.search_thread.search_failed.connect(self.on_search_failed)
        self.search_thread.search_progress.connect(self.on_search_progress)
        self.search_thread.search_complete.connect(self.on_search_complete)
        self.search_thread.start()
    
    def stop_search(self):
        """停止搜索"""
        if self.search_thread and self.searching:
            self.search_thread.stop_search()
            self.statusBar.showMessage("正在停止搜索，请稍候...")
            self.search_button.setEnabled(False)
    
    def on_article_found(self, articles):
        """当找到文章时的回调"""
        for article in articles:
            row_position = self.article_table.rowCount()
            self.article_table.insertRow(row_position)
            
            # 勾选框
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # 默认选中
            self.article_table.setCellWidget(row_position, 0, checkbox)
            
            # 标题
            self.article_table.setItem(row_position, 1, 
                                      QTableWidgetItem(article['标题']))
            
            # 发布时间
            self.article_table.setItem(row_position, 2, 
                                      QTableWidgetItem(article['发布时间']))
            
            # 阅读数
            self.article_table.setItem(row_position, 3, 
                                      QTableWidgetItem(str(article.get('阅读数', 0))))
            
            # 链接
            self.article_table.setItem(row_position, 4, 
                                      QTableWidgetItem(article['链接']))
            
            # 封面图片链接
            self.article_table.setItem(row_position, 5, 
                                      QTableWidgetItem(article.get('封面', '')))
            
            # 下载状态
            self.article_table.setItem(row_position, 6, 
                                      QTableWidgetItem("等待下载"))
    
    def on_search_failed(self, error_msg):
        """搜索失败回调"""
        QMessageBox.critical(self, "搜索失败", error_msg)
        self.search_button.setText("搜索")
        self.search_button.setEnabled(True)
        self.searching = False
        self.statusBar.showMessage(f"搜索失败: {error_msg}")
    
    def on_search_progress(self, current, total):
        """搜索进度回调"""
        self.statusBar.showMessage(f"已获取 {current}/{total} 篇文章")
        self.article_count_label.setText(f"文章数: {current}")
    
    def on_search_complete(self, total_count):
        """搜索完成回调"""
        self.search_button.setText("搜索")
        self.search_button.setEnabled(True)
        self.searching = False
        self.statusBar.showMessage(f"搜索完成，共获取 {total_count} 篇文章")
        
        # 更新公众号信息
        account_name = self.search_input.text()
        self.account_name_label.setText(account_name)
        self.article_count_label.setText(f"文章数: {total_count}")
        
        # 更新导出和下载路径
        self.update_export_download_paths(account_name)
        
    def update_export_download_paths(self, account_name):
        """更新导出和下载路径"""
        self.export_path_input.setText(f"./列表导出/{account_name}.xlsx")
        self.download_path_input.setText(f"./文章原文/{account_name}/")
    
    def select_all_articles(self):
        """全选文章"""
        for row in range(self.article_table.rowCount()):
            checkbox = self.article_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def deselect_all_articles(self):
        """全不选文章"""
        for row in range(self.article_table.rowCount()):
            checkbox = self.article_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def check_selected_articles(self):
        """勾选选中的文章行"""
        for index in self.article_table.selectedIndexes():
            row = index.row()
            checkbox = self.article_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def uncheck_selected_articles(self):
        """取消勾选选中的文章行"""
        for index in self.article_table.selectedIndexes():
            row = index.row()
            checkbox = self.article_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def select_export_path(self):
        """选择导出路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择导出文件", self.export_path_input.text(),
            "Excel Files (*.xlsx);;All Files (*)"
        )
        if file_path:
            self.export_path_input.setText(file_path)
    
    def select_download_path(self):
        """选择下载路径"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择下载文件夹", self.download_path_input.text()
        )
        if folder_path:
            self.download_path_input.setText(folder_path)
    
    def export_article_list(self):
        """导出文章列表"""
        export_path = self.export_path_input.text()
        if not export_path:
            QMessageBox.warning(self, "导出错误", "请选择导出路径")
            return
        
        # 收集已勾选的文章信息
        articles_to_export = []
        for row in range(self.article_table.rowCount()):
            checkbox = self.article_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                article_data = {
                    '标题': self.article_table.item(row, 1).text(),
                    '发布时间': self.article_table.item(row, 2).text(),
                    '阅读数': self.article_table.item(row, 3).text(),
                    '链接': self.article_table.item(row, 4).text(),
                    '封面图片': self.article_table.item(row, 5).text()
                }
                articles_to_export.append(article_data)
        
        if not articles_to_export:
            QMessageBox.warning(self, "导出错误", "没有选中的文章")
            return
        
        try:
            # 确保导出目录存在
            export_dir = os.path.dirname(export_path)
            if export_dir and not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # 创建DataFrame并导出为Excel
            df = pd.DataFrame(articles_to_export)
            df.to_excel(export_path, index=False, engine='openpyxl')
            
            QMessageBox.information(self, "导出成功", 
                                   f"已将 {len(articles_to_export)} 篇文章的信息导出到 {export_path}")
            
            # 在状态栏显示导出成功信息
            self.statusBar.showMessage(f"导出成功: {len(articles_to_export)} 篇文章已保存到 {export_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出文章列表时出错: {str(e)}")
            self.statusBar.showMessage(f"导出失败: {str(e)}")
    
    def download_articles(self):
        """下载文章"""
        download_path = self.download_path_input.text()
        if not download_path:
            QMessageBox.warning(self, "下载错误", "请选择下载路径")
            return
        
        # 收集已勾选的文章信息
        articles_to_download = []
        for row in range(self.article_table.rowCount()):
            checkbox = self.article_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                article_data = {
                    'title': self.article_table.item(row, 1).text(),
                    'link': self.article_table.item(row, 4).text()
                }
                articles_to_download.append(article_data)
        
        if not articles_to_download:
            QMessageBox.warning(self, "下载错误", "没有选中的文章")
            return
        
        # 确保下载目录存在
        if not os.path.exists(download_path):
            try:
                os.makedirs(download_path)
            except Exception as e:
                QMessageBox.critical(self, "下载错误", f"创建下载目录失败: {str(e)}")
                return
        
        # 确保images目录存在
        images_dir = os.path.join(download_path, "images")
        if not os.path.exists(images_dir):
            try:
                os.makedirs(images_dir)
            except Exception as e:
                QMessageBox.critical(self, "下载错误", f"创建图片目录失败: {str(e)}")
                return
        
        # 初始化下载管理器
        self.download_manager = ArticleDownloadManager(save_dir=download_path)
        
        # 连接信号
        self.download_manager.download_status_changed.connect(self.update_download_status)
        self.download_manager.download_completed.connect(self.on_download_completed)
        
        # 添加文章到下载队列
        for article in articles_to_download:
            self.download_manager.add_article(article)
        
        # 更新UI状态
        self.download_selected_btn.setEnabled(False)
        self.download_all_btn.setEnabled(False)
        self.stop_download_btn.setEnabled(True)
        
        # 开始下载
        self.download_manager.start_download()
        
        # 更新状态栏
        self.statusBar.showMessage(f"开始下载 {len(articles_to_download)} 篇文章...")
    
    def download_selected_articles(self):
        """下载选中的文章"""
        self.download_articles()
    
    def download_all_articles(self):
        """下载全部文章"""
        # 先全选所有文章
        self.select_all_articles()
        # 然后调用下载方法
        self.download_articles()
    
    def stop_download(self):
        """停止下载"""
        if hasattr(self, 'download_manager') and self.download_manager:
            self.download_manager.stop_download()
            self.statusBar.showMessage("下载已停止")
    
    def update_download_status(self, article_link, status_info):
        """更新文章下载状态"""
        # 在文章表格中找到对应的文章并更新状态
        for row in range(self.article_table.rowCount()):
            if self.article_table.item(row, 4).text() == article_link:
                # 更新状态列
                if not self.article_table.item(row, 6):
                    self.article_table.setItem(row, 6, QTableWidgetItem())
                self.article_table.item(row, 6).setText(status_info['status'])
                break
    
    def on_download_completed(self):
        """所有下载完成后的处理"""
        self.download_selected_btn.setEnabled(True)
        self.download_all_btn.setEnabled(True)
        self.stop_download_btn.setEnabled(False)
        
        # 统计下载结果
        success_count = 0
        fail_count = 0
        
        for row in range(self.article_table.rowCount()):
            status_item = self.article_table.item(row, 6)
            if status_item and '成功' in status_item.text():
                success_count += 1
            elif status_item and ('失败' in status_item.text() or '取消' in status_item.text()):
                fail_count += 1
        
        # 更新状态栏
        self.statusBar.showMessage(f"下载完成: {success_count}篇成功, {fail_count}篇失败")
        
        # 显示完成消息
        QMessageBox.information(self, "下载完成", 
                               f"文章下载完成\n成功: {success_count}篇\n失败: {fail_count}篇\n\n文件保存在: {self.download_path_input.text()}")
    
    def download_single_article(self):
        """下载单篇文章"""
        article_url = self.article_input.text().strip()
        if not article_url:
            QMessageBox.warning(self, "提示", "请输入微信公众号文章链接")
            return
        
        # 验证URL格式
        if not article_url.startswith("http"):
            QMessageBox.warning(self, "提示", "请输入有效的微信公众号文章链接")
            return
        
        # 获取下载路径
        download_path = self.download_path_input.text().strip()
        if not download_path:
            download_path = "./文章原文"
        
        # 更新状态栏
        self.statusBar.showMessage("正在准备下载文章...")
        
        # 创建下载线程
        self.single_article_thread = QThread()
        self.single_article_downloader = SingleArticleDownloader(article_url, download_path)
        self.single_article_downloader.moveToThread(self.single_article_thread)
        
        # 连接信号
        self.single_article_thread.started.connect(self.single_article_downloader.download)
        self.single_article_downloader.download_complete.connect(self.on_single_article_download_complete)
        self.single_article_downloader.download_error.connect(self.on_single_article_download_error)
        self.single_article_downloader.download_progress.connect(self.update_status_message)
        
        # 启动线程
        self.single_article_thread.start()
    
    def on_single_article_download_complete(self, file_path):
        """单篇文章下载完成的回调"""
        self.statusBar.showMessage(f"文章下载完成: {file_path}")
        QMessageBox.information(self, "下载成功", f"文章已保存到: {file_path}")
        
        # 清理线程
        self.single_article_thread.quit()
        self.single_article_thread.wait()
    
    def on_single_article_download_error(self, error_message):
        """单篇文章下载出错的回调"""
        self.statusBar.showMessage(f"下载失败: {error_message}")
        QMessageBox.warning(self, "下载失败", error_message)
        
        # 清理线程
        self.single_article_thread.quit()
        self.single_article_thread.wait()
    
    def update_status_message(self, message):
        """更新状态栏消息"""
        self.statusBar.showMessage(message)
    
# 主程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式表，实现扁平化设计
    try:
        # 导入样式文件
        from utils.style import get_flat_style
        
        # 设置Fusion风格
        app.setStyle("Fusion")
        
        # 应用样式表
        app.setStyleSheet(get_flat_style())

    except Exception as e:
        print(f"应用样式失败: {str(e)}")
    
    window = WechatCollectorUI()
    # 先显示主窗口，再检查登录状态
    window.show()
    # 检查登录状态并可能显示登录对话框
    window.check_login_status()
    sys.exit(app.exec())