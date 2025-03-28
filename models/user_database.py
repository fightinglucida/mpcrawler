import uuid
import bcrypt
import getpass
import platform
import uuid
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import supabase
from dotenv import load_dotenv

# 导入配置加密工具
try:
    from utils.config_crypto import decrypt_config
except ImportError:
    # 如果导入失败，尝试添加父目录到路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.config_crypto import decrypt_config

class UserDatabaseManager:
    """用户数据库管理器"""
    
    def __init__(self, show_errors=False):
        """初始化
        
        Args:
            show_errors: 是否显示错误信息，默认为False
        """
        # 初始化配置变量
        self.supabase_url = None
        self.supabase_key = None
        self.database_url = None
        self.config_error = False
        
        try:
            # 获取应用程序所在目录
            if getattr(sys, 'frozen', False):
                # 打包后的应用
                base_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 加载config.json配置文件（唯一配置来源）
            config_path = os.path.join(base_dir, 'config.json')
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        encrypted_config = json.load(f)
                        # 解密配置
                        config = decrypt_config(encrypted_config)
                        self.supabase_url = config.get('SUPABASE_URL')
                        self.supabase_key = config.get('SUPABASE_KEY')
                        self.database_url = config.get('DATABASE_URL')
                    if show_errors:
                        print("已从config.json加载并解密配置")
                except Exception as e:
                    if show_errors:
                        print(f"读取或解密config.json出错: {str(e)}")
                    self.config_error = True
            else:
                if show_errors:
                    print(f"配置文件不存在: {config_path}")
                self.config_error = True
            
            # 如果仍然没有配置，使用默认值
            if not self.supabase_url or not self.supabase_key:
                if show_errors:
                    print("警告: 未找到有效的Supabase配置")
                    print("请在应用程序目录下创建config.json文件，包含加密后的配置")
                
                # 标记配置错误
                self.config_error = True
                
                # 使用默认值（这些值不会实际工作，但可以让应用程序启动）
                self.supabase_url = "https://your-project-url.supabase.co"
                self.supabase_key = "your-supabase-key"
        
        except Exception as e:
            if show_errors:
                print(f"加载配置时出错: {str(e)}")
            
            # 标记配置错误
            self.config_error = True
            
            self.supabase_url = "https://your-project-url.supabase.co"
            self.supabase_key = "your-supabase-key"
        
        # 初始化Supabase客户端
        try:
            self.supabase = supabase.create_client(self.supabase_url, self.supabase_key)
            if show_errors:
                print("Supabase客户端初始化成功")
        except Exception as e:
            if show_errors:
                print(f"Supabase客户端初始化失败: {str(e)}")
            
            # 标记配置错误
            self.config_error = True
            
            # 创建一个空的客户端对象，避免程序崩溃
            self.supabase = None
        
        # MAC地址存储路径
        self.mac_store_path = os.path.join(os.path.expanduser("~"), ".gzh_mac_store.json")
    
    def has_config_error(self):
        """检查是否存在配置错误
        
        Returns:
            bool: 是否存在配置错误
        """
        return self.config_error
    
    def get_database_url(self):
        """获取数据库URL
        
        Returns:
            str: 数据库URL，如果不存在则返回None
        """
        return self.database_url
    
    def _hash_password(self, password):
        """对密码进行哈希处理
        
        Args:
            password: 原始密码
            
        Returns:
            str: 哈希后的密码
        """
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode(), salt)
        return hashed_password.decode()
    
    def _verify_password(self, password, hashed_password):
        """验证密码
        
        Args:
            password: 原始密码
            hashed_password: 哈希后的密码
            
        Returns:
            bool: 密码是否正确
        """
        return bcrypt.checkpw(password.encode(), hashed_password.encode())
    
    def _get_current_mac(self):
        """获取当前MAC地址"""
        try:
            if platform.system() == 'Windows':
                for line in os.popen("getmac /fo csv /nh"):
                    mac = line.split(',')[0].strip('"')
                    return mac
            elif platform.system() == 'Darwin':  # macOS
                for line in os.popen("ifconfig en0 | grep ether"):
                    return line.strip().split()[1]
            elif platform.system() == 'Linux':
                for line in os.popen("ip link show | grep link/ether"):
                    return line.strip().split()[1]
            return "unknown"
        except Exception as e:
            print(f"获取MAC地址时发生错误: {str(e)}")
            return "unknown"
    
    def _save_mac_for_user(self, user_id, mac_address):
        """保存用户的MAC地址到本地
        
        Args:
            user_id: 用户ID
            mac_address: MAC地址
        """
        try:
            mac_data = {}
            if os.path.exists(self.mac_store_path):
                with open(self.mac_store_path, 'r') as f:
                    mac_data = json.load(f)
            
            mac_data[user_id] = mac_address
            
            with open(self.mac_store_path, 'w') as f:
                json.dump(mac_data, f)
                
            return True
        except Exception as e:
            print(f"保存MAC地址时发生错误: {str(e)}")
            return False
    
    def _get_mac_for_user(self, user_id):
        """获取用户的MAC地址
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: MAC地址
        """
        try:
            if os.path.exists(self.mac_store_path):
                with open(self.mac_store_path, 'r') as f:
                    mac_data = json.load(f)
                    return mac_data.get(user_id)
            return None
        except Exception as e:
            print(f"获取MAC地址时发生错误: {str(e)}")
            return None
    
    # ===== 用户相关方法 =====
    
    def login(self, email, password):
        """用户登录
        
        Args:
            email: 邮箱
            password: 密码
            
        Returns:
            dict: 登录结果
        """
        try:
            # 查询用户
            result = self.supabase.table('users').select('*').eq('email', email).execute()
            
            if not result.data:
                return {'success': False, 'message': '用户不存在', 'user': None}
            
            user = result.data[0]
            
            # 验证密码
            if not self._verify_password(password, user.get('password', '')):
                return {'success': False, 'message': '密码错误', 'user': None}
            
            # 获取当前MAC地址
            current_mac = self._get_current_mac()
            user_id = user.get('id')
            
            # 检查用户是否有MAC地址
            user_mac = user.get('mac')
            if not user_mac:
                # 首次登录，更新MAC地址
                self.supabase.table('users').update({
                    'mac': current_mac,
                    'last_login_time': datetime.now().isoformat(),
                    'last_login_ip': self._get_ip_address()
                }).eq('id', user_id).execute()
                
                # 重新获取用户信息
                result = self.supabase.table('users').select('*').eq('id', user_id).execute()
                if result.data:
                    user = result.data[0]
            else:
                # 验证MAC地址
                if user_mac != current_mac:
                    return {'success': False, 'message': '登录失败，请不要更换设备使用', 'user': None}
                
                # 更新登录时间和IP
                self.supabase.table('users').update({
                    'last_login_time': datetime.now().isoformat(),
                    'last_login_ip': self._get_ip_address()
                }).eq('id', user_id).execute()
            
            return {'success': True, 'message': '登录成功', 'user': user}
            
        except Exception as e:
            print(f"登录时发生错误: {str(e)}")
            return {'success': False, 'message': f'登录失败: {str(e)}', 'user': None}
    
    def register_user(self, email, password, nickname):
        """注册用户
        
        Args:
            email: 邮箱
            password: 密码
            nickname: 昵称
            
        Returns:
            dict: 注册结果
        """
        try:
            # 检查邮箱是否已存在
            existing_user_email = self.supabase.table('users').select('*').eq('email', email).execute()
            
            if existing_user_email.data:
                return {'success': False, 'message': '该邮箱已被注册'}
            
            # 检查昵称是否已存在
            existing_user_nickname = self.supabase.table('users').select('*').eq('nickname', nickname).execute()
            
            if existing_user_nickname.data:
                return {'success': False, 'message': '该昵称已被使用'}
            
            # 哈希密码
            hashed_password = self._hash_password(password)
            
            # 创建用户
            user_id = str(uuid.uuid4())
            
            self.supabase.table('users').insert({
                'id': user_id,
                'email': email,
                'password': hashed_password,
                'nickname': nickname,
                'role': '1'  # 普通用户角色
            }).execute()
            
            return {'success': True, 'message': '注册成功'}
            
        except Exception as e:
            print(f"注册用户时发生错误: {str(e)}")
            return {'success': False, 'message': f'注册失败: {str(e)}'}
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 用户信息
        """
        try:
            result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not result.data:
                return {'success': False, 'message': '用户不存在', 'user': {}}
            
            return {'success': True, 'message': '获取成功', 'user': result.data[0]}
            
        except Exception as e:
            print(f"获取用户信息时发生错误: {str(e)}")
            return {'success': False, 'message': f'获取失败: {str(e)}', 'user': {}}
    
    def get_user_activation_info(self, user_id):
        """获取用户激活信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 激活信息结果
        """
        try:
            # 先检查用户是否存在
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return {'success': False, 'message': '用户不存在', 'data': {}}
            
            user = user_result.data[0]
            
            # 检查用户是否有激活码
            activation_code = user.get('activation_code')
            if not activation_code:
                return {'success': True, 'message': '用户未激活', 'data': {
                    'activation_status': '未激活',
                    'code': '',
                    'activation_time': '',
                    'expiry_date': ''
                }}
            
            # 查询激活码信息
            code_result = self.supabase.table('activation_codes').select('*').eq('code', activation_code).execute()
            
            if not code_result.data:
                return {'success': True, 'message': '激活码不存在', 'data': {
                    'activation_status': '未知',
                    'code': activation_code,
                    'activation_time': '',
                    'expiry_date': user.get('expired_time', '')
                }}
            
            # 返回激活码信息
            code = code_result.data[0]
            
            return {
                'success': True,
                'message': '获取成功',
                'data': {
                    'code': activation_code,
                    'activation_status': code.get('activation_status', '未激活'),
                    'activation_time': code.get('activation_time', ''),
                    'expiry_date': code.get('expiry_date', '') or user.get('expired_time', '')
                }
            }
            
        except Exception as e:
            print(f"获取用户激活信息时发生错误: {str(e)}")
            return {'success': False, 'message': f'获取失败: {str(e)}', 'data': {}}
    
    def activate_user(self, user_id, activation_code, mac_address=None):
        """激活用户
        
        Args:
            user_id: 用户ID
            activation_code: 激活码
            mac_address: MAC地址
            
        Returns:
            dict: 激活结果
        """
        try:
            # 先检查用户是否存在
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return {'success': False, 'message': '用户不存在'}
            
            user = user_result.data[0]
            user_email = user.get('email')
            
            # 检查激活码是否存在
            code_result = self.supabase.table('activation_codes').select('*').eq('code', activation_code).execute()
            
            if not code_result.data:
                return {'success': False, 'message': '激活码不存在'}
            
            code = code_result.data[0]
            
            # 检查激活码状态
            activation_status = code.get('activation_status', '')
            if activation_status != '未激活' and activation_status != '':
                if activation_status == '已激活':
                    return {'success': False, 'message': '激活码已被使用'}
                elif activation_status == '已过期':
                    return {'success': False, 'message': '激活码已过期'}
                else:
                    return {'success': False, 'message': f'激活码状态异常: {activation_status}'}
            
            # 检查激活码是否已过期
            expiry_date = code.get('expiry_date', '')
            if expiry_date:
                try:
                    # 处理不同格式的日期字符串
                    if 'T' in expiry_date:
                        # 处理带时区的ISO格式
                        if '+' in expiry_date:
                            expiry_date = expiry_date.split('+')[0]
                        # 处理带毫秒的格式
                        if '.' in expiry_date:
                            expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M:%S.%f')
                        else:
                            expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%dT%H:%M:%S')
                    else:
                        expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d')
                    
                    # 获取当前时间
                    current_datetime = datetime.now()
                    
                    # 检查是否过期
                    if current_datetime > expiry_datetime:
                        # 更新激活码状态为已过期
                        self.supabase.table('activation_codes').update({
                            'activation_status': '已过期',
                            'update_time': current_datetime.isoformat()
                        }).eq('id', code.get('id')).execute()
                        
                        return {'success': False, 'message': '激活码已过期'}
                except Exception as e:
                    print(f"检查激活码过期时间时发生错误: {str(e)}")
            
            # 获取当前时间
            current_time = datetime.now()
            
            # 从激活码获取有效天数，默认为30天
            valid_days = int(code.get('valid_days', 30))
            
            # 计算过期时间
            expiry_date = (current_time + timedelta(days=valid_days)).isoformat()
            
            print(f"激活用户 {user_id}，激活码 {activation_code}，有效天数 {valid_days}，激活时间 {current_time.isoformat()}，过期时间 {expiry_date}")
            
            # 更新激活码信息
            self.supabase.table('activation_codes').update({
                'user_email': user_email,
                'activation_status': '已激活',
                'activation_time': current_time.isoformat(),
                'expiry_date': expiry_date,
                'update_time': current_time.isoformat()
            }).eq('id', code.get('id')).execute()
            
            # 更新用户信息
            self.supabase.table('users').update({
                'activation_code': activation_code,
                'activation_status': '已激活',
                'expired_time': expiry_date
            }).eq('id', user_id).execute()
            
            return {'success': True, 'message': '激活成功', 'expiry_date': expiry_date}
            
        except Exception as e:
            print(f"激活用户时发生错误: {str(e)}")
            return {'success': False, 'message': f'激活失败: {str(e)}'}
    
    def change_password(self, user_id, old_password, new_password):
        """修改用户密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            dict: 修改结果
        """
        try:
            # 先检查用户是否存在
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return {'success': False, 'message': '用户不存在'}
            
            user = user_result.data[0]
            
            # 验证旧密码
            if not self._verify_password(old_password, user.get('password', '')):
                return {'success': False, 'message': '旧密码不正确'}
            
            # 加密新密码
            hashed_password = self._hash_password(new_password)
            
            # 更新密码
            self.supabase.table('users').update({
                'password': hashed_password
            }).eq('id', user_id).execute()
            
            return {'success': True, 'message': '密码修改成功'}
            
        except Exception as e:
            print(f"修改密码时发生错误: {str(e)}")
            return {'success': False, 'message': f'修改失败: {str(e)}'}
    
    def auto_login_by_mac(self):
        """通过MAC地址自动登录
        
        Returns:
            dict: 登录结果
        """
        try:
            # 获取当前MAC地址
            current_mac = self._get_current_mac()
            
            # 查询用户
            result = self.supabase.table('users').select('*').eq('mac', current_mac).execute()
            
            if not result.data:
                return {'success': False, 'message': '未找到匹配的设备', 'user': None}
            
            user = result.data[0]
            
            # 更新登录时间和IP
            self.supabase.table('users').update({
                'last_login_time': datetime.now().isoformat(),
                'last_login_ip': self._get_ip_address()
            }).eq('id', user.get('id')).execute()
            
            return {'success': True, 'message': '自动登录成功', 'user': user}
            
        except Exception as e:
            print(f"自动登录时发生错误: {str(e)}")
            return {'success': False, 'message': f'自动登录失败: {str(e)}', 'user': None}
    
    def _get_ip_address(self):
        """获取当前IP地址"""
        try:
            import socket
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            return ip_address
        except Exception as e:
            print(f"获取IP地址时发生错误: {str(e)}")
            return "unknown"
    
    def update_activation_status(self, user_id, activation_code, status):
        """更新激活状态
        
        Args:
            user_id: 用户ID
            activation_code: 激活码
            status: 激活状态（未激活/已激活/已过期）
            
        Returns:
            dict: 更新结果
        """
        try:
            current_time = datetime.now().isoformat()
            
            # 更新用户表中的激活状态
            self.supabase.table('users').update({
                'activation_status': status,
                'update_time': current_time
            }).eq('id', user_id).execute()
            
            # 如果有激活码，也更新激活码表中的状态
            if activation_code:
                self.supabase.table('activation_codes').update({
                    'activation_status': status,
                    'update_time': current_time
                }).eq('code', activation_code).execute()
            
            return {'success': True, 'message': '激活状态更新成功'}
            
        except Exception as e:
            print(f"更新激活状态时发生错误: {str(e)}")
            return {'success': False, 'message': f'更新失败: {str(e)}'}
