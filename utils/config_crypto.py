import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ConfigCrypto:
    """配置文件加密解密工具"""
    
    def __init__(self, secret_key=None):
        """初始化加密工具
        
        Args:
            secret_key: 自定义密钥，如果不提供则使用内置密钥
        """
        # 使用硬编码的密钥（在实际应用中，这个密钥应该更复杂并且隐藏在代码中）
        self._base_key = secret_key or "gzh_collector_2025_secure_key_do_not_share"
        # 使用应用程序特定信息作为盐值
        self._salt = b'gzh_collector_salt_value_2025'
        # 生成加密密钥
        self._key = self._generate_key()
        # 创建加密器
        self._fernet = Fernet(self._key)
    
    def _generate_key(self):
        """生成加密密钥"""
        # 使用PBKDF2派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._base_key.encode()))
        return key
    
    def encrypt(self, data):
        """加密数据
        
        Args:
            data: 要加密的字符串
            
        Returns:
            加密后的字符串
        """
        if not data:
            return ""
        
        encrypted = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data):
        """解密数据
        
        Args:
            encrypted_data: 加密后的字符串
            
        Returns:
            解密后的原始字符串
        """
        if not encrypted_data:
            return ""
        
        try:
            # 解码base64
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            # 解密
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            print(f"解密失败: {str(e)}")
            return ""

# 创建一个默认的加密工具实例
default_crypto = ConfigCrypto()

def encrypt_config(config):
    """加密配置字典
    
    Args:
        config: 包含配置项的字典
        
    Returns:
        加密后的配置字典
    """
    encrypted_config = {}
    for key, value in config.items():
        if isinstance(value, str):
            encrypted_config[key] = default_crypto.encrypt(value)
        else:
            encrypted_config[key] = value
    return encrypted_config

def decrypt_config(encrypted_config):
    """解密配置字典
    
    Args:
        encrypted_config: 加密后的配置字典
        
    Returns:
        解密后的配置字典
    """
    decrypted_config = {}
    for key, value in encrypted_config.items():
        if isinstance(value, str):
            decrypted_config[key] = default_crypto.decrypt(value)
        else:
            decrypted_config[key] = value
    return decrypted_config

if __name__ == "__main__":
    # 测试加密解密
    original = "test_secret_value"
    crypto = ConfigCrypto()
    encrypted = crypto.encrypt(original)
    decrypted = crypto.decrypt(encrypted)
    print(f"原始: {original}")
    print(f"加密: {encrypted}")
    print(f"解密: {decrypted}")
    
    # 测试配置加密
    test_config = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "very_secret_key_value",
        "VERSION": 1.0
    }
    
    encrypted_config = encrypt_config(test_config)
    print("\n加密后的配置:")
    for k, v in encrypted_config.items():
        print(f"{k}: {v}")
    
    decrypted_config = decrypt_config(encrypted_config)
    print("\n解密后的配置:")
    for k, v in decrypted_config.items():
        print(f"{k}: {v}")
