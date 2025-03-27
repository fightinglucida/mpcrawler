import os
import uuid
import bcrypt
import getpass
import platform
import uuid
import json
from pathlib import Path
from datetime import datetime, timedelta
import supabase

class UserDatabaseManager:
    """用户数据库管理器"""
    
    def __init__(self):
        """初始化"""
        # 从环境变量获取Supabase配置
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        # 初始化Supabase客户端
        self.supabase = supabase.create_client(self.supabase_url, self.supabase_key)
        
        # MAC地址存储路径
        self.mac_store_path = os.path.join(os.path.expanduser("~"), ".gzh_mac_store.json")
    
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
                    'expiry_date': user.get('expiry_date', '')
                }}
            
            # 返回激活码信息
            code = code_result.data[0]
            
            activation_status = '已激活' if code.get('used') else '未激活'
            
            return {
                'success': True,
                'message': '获取成功',
                'data': {
                    'code': activation_code,
                    'activation_status': activation_status,
                    'activation_time': code.get('used_at', ''),
                    'expiry_date': user.get('expiry_date', '')
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
            
            # 检查激活码是否存在
            code_result = self.supabase.table('activation_codes').select('*').eq('code', activation_code).execute()
            
            if not code_result.data:
                return {'success': False, 'message': '激活码不存在'}
            
            code = code_result.data[0]
            
            # 检查激活码状态
            if code.get('used') == True:
                return {'success': False, 'message': '激活码已被使用'}
            
            # 计算过期时间
            duration_days = code.get('duration_days', 30)
            expiry_date = (datetime.now() + timedelta(days=duration_days)).isoformat()
            
            # 更新激活码信息
            self.supabase.table('activation_codes').update({
                'used': True,
                'used_by': user_id,
                'used_at': datetime.now().isoformat()
            }).eq('id', code.get('id')).execute()
            
            # 更新用户信息
            self.supabase.table('users').update({
                'activation_code': activation_code,
                'expiry_date': expiry_date
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
