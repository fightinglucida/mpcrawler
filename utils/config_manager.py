import os
import json
import sys
from pathlib import Path

# 导入配置加密工具
try:
    from utils.config_crypto import decrypt_config, encrypt_config
except ImportError:
    # 如果导入失败，尝试添加父目录到路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.config_crypto import decrypt_config, encrypt_config

class ConfigManager:
    """配置管理器，用于读写配置文件"""
    
    def __init__(self):
        """初始化配置管理器"""
        # 获取应用程序所在目录
        if getattr(sys, 'frozen', False):
            # 打包后的应用
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 配置文件路径
        self.config_path = os.path.join(self.base_dir, 'config.json')
        
        # 初始化配置
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件
        
        Returns:
            dict: 配置字典
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    encrypted_config = json.load(f)
                    
                    # 解密需要解密的配置项
                    config = {}
                    for key, value in encrypted_config.items():
                        if key in ['SUPABASE_URL', 'SUPABASE_KEY', 'DATABASE_URL', 'EMAIL', 'PASSWORD']:
                            # 这些项需要解密
                            try:
                                config[key] = decrypt_config({key: value})[key]
                            except Exception as e:
                                print(f"解密配置项 {key} 时出错: {str(e)}")
                                config[key] = value
                        else:
                            # 其他项直接使用
                            config[key] = value
                    
                    return config
            else:
                print(f"配置文件不存在: {self.config_path}")
                return {}
        except Exception as e:
            print(f"加载配置文件时出错: {str(e)}")
            return {}
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 准备要保存的配置
            save_config = {}
            
            # 处理需要加密的配置项
            encrypted_items = {}
            for key in ['SUPABASE_URL', 'SUPABASE_KEY', 'DATABASE_URL', 'EMAIL', 'PASSWORD']:
                if key in self.config and self.config[key]:
                    encrypted_items[key] = self.config[key]
            
            # 加密这些项
            if encrypted_items:
                encrypted_config = encrypt_config(encrypted_items)
                for key, value in encrypted_config.items():
                    save_config[key] = value
            
            # 添加不需要加密的配置项
            for key, value in self.config.items():
                if key not in ['SUPABASE_URL', 'SUPABASE_KEY', 'DATABASE_URL', 'EMAIL', 'PASSWORD']:
                    save_config[key] = value
            
            # 保存到文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, indent=4)
            
            return True
        except Exception as e:
            print(f"保存配置文件时出错: {str(e)}")
            return False
    
    def get(self, key, default=None):
        """获取配置项
        
        Args:
            key: 配置项键名
            default: 默认值
            
        Returns:
            配置项的值
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项
        
        Args:
            key: 配置项键名
            value: 配置项的值
            
        Returns:
            bool: 是否设置成功
        """
        self.config[key] = value
        return True
    
    def save_login_info(self, email, password, remember_password=False, auto_login=False):
        """保存登录信息
        
        Args:
            email: 邮箱
            password: 密码
            remember_password: 是否记住密码
            auto_login: 是否自动登录
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 设置是否记住密码和自动登录
            self.set('REMEMBERPW', remember_password)
            self.set('AUTOLOGIN', auto_login)
            
            # 如果记住密码，则保存邮箱和密码
            if remember_password:
                self.set('EMAIL', email)
                self.set('PASSWORD', password)
            else:
                # 否则清除邮箱和密码
                self.set('EMAIL', '')
                self.set('PASSWORD', '')
            
            # 保存配置
            return self.save_config()
        except Exception as e:
            print(f"保存登录信息时出错: {str(e)}")
            return False
    
    def get_login_info(self):
        """获取登录信息
        
        Returns:
            dict: 登录信息
        """
        return {
            'email': self.get('EMAIL', ''),
            'password': self.get('PASSWORD', ''),
            'remember_password': self.get('REMEMBERPW', False),
            'auto_login': self.get('AUTOLOGIN', False)
        }
