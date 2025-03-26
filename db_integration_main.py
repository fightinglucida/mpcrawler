import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# 导入现有模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mp_downloader import WechatCollectorUI
from models.db_integration import DatabaseIntegrationUI
from utils.db_article_downloader import DBArticleDownloadManager
from models.admin_manager import AdminPanel

class IntegratedApp(QMainWindow):
    """集成了数据库功能的公众号采集助手"""
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.setWindowTitle("公众号采集与下载助手 (数据库版)")
        self.setMinimumSize(1200, 800)
        
        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.svg")
        self.setWindowIcon(QIcon(icon_path))
        
        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 创建公众号采集界面
        self.collector_ui = WechatCollectorUI()
        self.tab_widget.addTab(self.collector_ui, "公众号采集")
        
        # 创建数据库界面
        self.db_ui = DatabaseIntegrationUI()
        self.tab_widget.addTab(self.db_ui, "数据库管理")
        
        # 创建管理员界面
        self.admin_ui = AdminPanel()
        self.tab_widget.addTab(self.admin_ui, "账号管理")
        
        # 连接信号
        self.db_ui.login_status_changed.connect(self.on_login_status_changed)
        self.db_ui.article_selected.connect(self.on_article_selected)
        
        # 替换下载管理器为支持数据库的版本
        self.setup_db_downloader()
        
        # 检查环境变量
        self.check_environment()
    
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
                    save_to_db=self.db_ui.is_auto_save_enabled(),
                    user_id=self.db_ui.get_current_user_id()
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
                
                # 连接数据库相关信号
                self.collector_ui.download_manager.db_save_success.connect(self.on_db_save_success)
                self.collector_ui.download_manager.db_save_failed.connect(self.on_db_save_failed)
        except Exception as e:
            print(f"设置数据库下载管理器失败: {str(e)}")
    
    def on_login_status_changed(self, is_logged_in, user_info):
        """登录状态变化回调"""
        if hasattr(self.collector_ui, 'download_manager') and isinstance(self.collector_ui.download_manager, DBArticleDownloadManager):
            if is_logged_in and user_info:
                # 更新下载管理器的用户ID
                self.collector_ui.download_manager.set_user_id(user_info['id'])
                
                # 更新自动保存设置
                self.collector_ui.download_manager.set_save_to_db(self.db_ui.is_auto_save_enabled())
                
                # 显示状态消息
                if hasattr(self.collector_ui, 'statusBar'):
                    self.collector_ui.statusBar.showMessage(f"已登录数据库: {user_info['nickname']}")
            else:
                # 清除用户ID
                self.collector_ui.download_manager.set_user_id(None)
                self.collector_ui.download_manager.set_save_to_db(False)
                
                # 显示状态消息
                if hasattr(self.collector_ui, 'statusBar'):
                    self.collector_ui.statusBar.showMessage("未登录数据库")
    
    def on_article_selected(self, article_data):
        """文章选中回调"""
        # 可以在这里实现查看数据库中的文章内容
        QMessageBox.information(self, "文章详情", f"标题: {article_data['title']}\n公众号: {article_data['account_name']}")
    
    def on_db_save_success(self, result):
        """数据库保存成功回调"""
        if hasattr(self.collector_ui, 'statusBar'):
            self.collector_ui.statusBar.showMessage(f"文章已保存到数据库: {result.get('article_id', '')}")
    
    def on_db_save_failed(self, error_msg):
        """数据库保存失败回调"""
        if hasattr(self.collector_ui, 'statusBar'):
            self.collector_ui.statusBar.showMessage(f"保存到数据库失败: {error_msg}")
    
    def check_environment(self):
        """检查环境变量"""
        from dotenv import load_dotenv
        load_dotenv()
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key or supabase_url == 'your_supabase_url' or supabase_key == 'your_supabase_key':
            QMessageBox.warning(
                self, 
                "环境配置不完整", 
                "请在.env文件中设置正确的SUPABASE_URL和SUPABASE_KEY\n\n" +
                "您可以在Supabase项目设置中获取这些值。"
            )

# 如果直接运行此文件，则启动集成应用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IntegratedApp()
    window.show()
    sys.exit(app.exec())