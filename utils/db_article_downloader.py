import os
import sys
from PyQt6.QtCore import QObject, pyqtSignal

# 导入原有的下载器和数据库管理器
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.article_downloader import ArticleDownloadManager, WeChatArticleDownloader
from models.article_manager import ArticleManager

class DBArticleDownloadManager(ArticleDownloadManager):
    """扩展的文章下载管理器，支持将文章保存到数据库"""
    
    # 定义额外的信号
    db_save_success = pyqtSignal(dict)  # 数据库保存成功信号
    db_save_failed = pyqtSignal(str)    # 数据库保存失败信号
    
    def __init__(self, save_to_db=False, user_id=None):
        super().__init__()
        self.save_to_db = save_to_db
        self.article_manager = ArticleManager(user_id)
        
        # 连接信号
        self.article_manager.save_success.connect(self._on_db_save_success)
        self.article_manager.save_failed.connect(self._on_db_save_failed)
    
    def set_user_id(self, user_id):
        """设置当前用户ID"""
        self.article_manager.set_user_id(user_id)
    
    def set_save_to_db(self, save_to_db):
        """设置是否保存到数据库"""
        self.save_to_db = save_to_db
    
    def download_article(self, article_info):
        """下载文章并可选保存到数据库
        
        Args:
            article_info: 文章信息字典
            
        Returns:
            tuple: (是否成功, 文件路径)
        """
        # 调用父类方法下载文章
        success, file_path = super().download_article(article_info)
        
        # 如果下载成功且需要保存到数据库
        if success and self.save_to_db and file_path:
            # 获取公众号名称
            account_name = self.current_account_name
            if not account_name and 'account_name' in article_info:
                account_name = article_info['account_name']
            elif not account_name and '公众号名称' in article_info:
                account_name = article_info['公众号名称']
            
            # 添加公众号名称到文章信息
            if account_name and 'account_name' not in article_info:
                article_info['account_name'] = account_name
            
            # 保存到数据库
            self.article_manager.save_article_to_db(article_info, file_path)
        
        return success, file_path
    
    def _on_db_save_success(self, result):
        """数据库保存成功回调"""
        self.db_save_success.emit(result)
    
    def _on_db_save_failed(self, error_msg):
        """数据库保存失败回调"""
        self.db_save_failed.emit(error_msg)