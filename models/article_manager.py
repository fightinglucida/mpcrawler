import os
import sys
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

# 导入数据库管理器
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import DatabaseManager

class ArticleManager(QObject):
    """文章数据管理类，负责文章的保存、查询和管理"""
    
    # 定义信号
    save_success = pyqtSignal(dict)  # 保存成功信号
    save_failed = pyqtSignal(str)    # 保存失败信号
    query_success = pyqtSignal(list) # 查询成功信号
    query_failed = pyqtSignal(str)   # 查询失败信号
    
    def __init__(self, user_id=None):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.user_id = user_id
    
    def set_user_id(self, user_id):
        """设置当前用户ID"""
        self.user_id = user_id
    
    def save_article_to_db(self, article_data, local_file_path=None):
        """保存文章到数据库
        
        Args:
            article_data: 文章数据字典，包含标题、链接等信息
            local_file_path: 本地文件路径，用于读取文章内容
            
        Returns:
            bool: 是否保存成功
        """
        if not self.user_id:
            self.save_failed.emit("未登录，无法保存文章")
            return False
        
        try:
            # 读取文章内容
            content = ""
            if local_file_path and os.path.exists(local_file_path):
                with open(local_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # 准备文章数据
            db_article_data = {
                'account_name': article_data.get('公众号名称', article_data.get('account_name', '')),
                'category': article_data.get('分类', article_data.get('category', '未分类')),
                'title': article_data.get('标题', article_data.get('title', '')),
                'content': content,
                'publish_time': article_data.get('发布时间', article_data.get('publish_time', datetime.now().isoformat())),
                'read_count': article_data.get('阅读数', article_data.get('read_count', 0)),
                'article_url': article_data.get('链接', article_data.get('article_url', '')),
                'user_id': self.user_id
            }
            
            # 保存到数据库
            result = self.db_manager.save_article(db_article_data)
            
            if result['success']:
                self.save_success.emit(result)
                return True
            else:
                self.save_failed.emit(result['message'])
                return False
                
        except Exception as e:
            self.save_failed.emit(f"保存文章失败: {str(e)}")
            return False
    
    def get_articles(self, account_name=None, category=None, limit=100, offset=0):
        """获取文章列表
        
        Args:
            account_name: 公众号名称（可选）
            category: 公众号分类（可选）
            limit: 返回数量限制
            offset: 分页偏移量
            
        Returns:
            list: 文章列表
        """
        if not self.user_id:
            self.query_failed.emit("未登录，无法获取文章")
            return []
        
        try:
            result = self.db_manager.get_articles(
                self.user_id, account_name, category, limit, offset
            )
            
            if result['success']:
                self.query_success.emit(result['articles'])
                return result['articles']
            else:
                self.query_failed.emit(result['message'])
                return []
                
        except Exception as e:
            self.query_failed.emit(f"获取文章失败: {str(e)}")
            return []
    
    def search_articles(self, keyword, limit=100, offset=0):
        """搜索文章
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            offset: 分页偏移量
            
        Returns:
            list: 文章列表
        """
        if not self.user_id:
            self.query_failed.emit("未登录，无法搜索文章")
            return []
        
        try:
            result = self.db_manager.search_articles(
                self.user_id, keyword, limit, offset
            )
            
            if result['success']:
                self.query_success.emit(result['articles'])
                return result['articles']
            else:
                self.query_failed.emit(result['message'])
                return []
                
        except Exception as e:
            self.query_failed.emit(f"搜索文章失败: {str(e)}")
            return []
    
    def delete_article(self, article_id):
        """删除文章
        
        Args:
            article_id: 文章ID
            
        Returns:
            bool: 是否删除成功
        """
        if not self.user_id:
            self.save_failed.emit("未登录，无法删除文章")
            return False
        
        try:
            result = self.db_manager.delete_article(article_id, self.user_id)
            
            if result['success']:
                return True
            else:
                self.save_failed.emit(result['message'])
                return False
                
        except Exception as e:
            self.save_failed.emit(f"删除文章失败: {str(e)}")
            return False