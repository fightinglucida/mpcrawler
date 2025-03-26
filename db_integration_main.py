import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# 导入现有模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mp_downloader import WechatCollectorUI
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
        
        # 创建管理员界面
        self.admin_ui = AdminPanel()
        self.tab_widget.addTab(self.admin_ui, "账号管理")
        
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