import os
import sys
import logging
import datetime
from logging.handlers import RotatingFileHandler

class Logger:
    """日志记录器"""
    
    def __init__(self, name="gzh_collector", log_level=logging.DEBUG):
        """初始化日志记录器
        
        Args:
            name: 日志记录器名称
            log_level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # 清除已有的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 获取应用程序根目录
        if getattr(sys, 'frozen', False):
            # 打包后的应用
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建logs目录
        logs_dir = os.path.join(base_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # 日志文件路径
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(logs_dir, f"{name}_{current_date}.log")
        
        # 创建文件处理器 - 10MB大小，最多保留5个备份
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"日志初始化完成，日志文件: {log_file}")
    
    def get_logger(self):
        """获取日志记录器
        
        Returns:
            logging.Logger: 日志记录器
        """
        return self.logger

# 创建全局日志记录器
def get_logger(name="gzh_collector", log_level=logging.DEBUG):
    """获取全局日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别
        
    Returns:
        logging.Logger: 日志记录器
    """
    return Logger(name, log_level).get_logger()
