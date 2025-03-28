import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.config_crypto import encrypt_config

def generate_encrypted_config():
    """从.env文件生成加密的config.json文件"""
    print("开始生成加密的配置文件...")
    
    # 加载.env文件
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_path):
        print(f"错误: 未找到.env文件: {env_path}")
        return False
    
    load_dotenv(env_path)
    
    # 获取环境变量
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    database_url = os.getenv('DATABASE_URL')
    
    if not supabase_url or not supabase_key:
        print("错误: .env文件中未找到SUPABASE_URL或SUPABASE_KEY")
        return False
    
    # 创建配置字典
    config = {
        "SUPABASE_URL": supabase_url,
        "SUPABASE_KEY": supabase_key
    }
    
    # 如果存在DATABASE_URL，也添加到配置中
    if database_url:
        config["DATABASE_URL"] = database_url
        print(f"已添加DATABASE_URL到配置中")
    else:
        print("警告: 未找到DATABASE_URL，将不会包含在配置中")
    
    # 加密配置
    encrypted_config = encrypt_config(config)
    
    # 保存到config.json
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(encrypted_config, f, indent=4)
    
    print(f"加密的配置文件已保存到: {config_path}")
    print("原始配置:")
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_KEY: {supabase_key[:5]}...{supabase_key[-5:]}")
    if database_url:
        print(f"DATABASE_URL: {database_url[:10]}...{database_url[-10:] if len(database_url) > 20 else database_url}")
    
    print("\n加密后的配置:")
    print(f"SUPABASE_URL: {encrypted_config['SUPABASE_URL'][:10]}...{encrypted_config['SUPABASE_URL'][-10:]}")
    print(f"SUPABASE_KEY: {encrypted_config['SUPABASE_KEY'][:10]}...{encrypted_config['SUPABASE_KEY'][-10:]}")
    if 'DATABASE_URL' in encrypted_config:
        print(f"DATABASE_URL: {encrypted_config['DATABASE_URL'][:10]}...{encrypted_config['DATABASE_URL'][-10:]}")
    
    return True

if __name__ == "__main__":
    if generate_encrypted_config():
        print("配置文件加密成功！")
        print("注意: 现在应用程序将只从config.json加载配置，不再使用.env文件")
        print("      请确保将加密后的config.json文件与应用程序一起分发")
    else:
        print("配置文件加密失败！")
