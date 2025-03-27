import os
import uuid
import hashlib
import socket
import getpass
from datetime import datetime, timedelta
import supabase

class UserDatabaseManager:
    """用户版本的数据库管理器，只包含用户相关功能"""
    
    def __init__(self):
        # 从环境变量获取Supabase配置
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        # 初始化Supabase客户端
        self.supabase = supabase.create_client(self.supabase_url, self.supabase_key)
    
    def _hash_password(self, password):
        """对密码进行哈希处理
        
        Args:
            password: 原始密码
            
        Returns:
            str: 哈希后的密码
        """
        salt = uuid.uuid4().hex
        hashed_password = hashlib.sha256(salt.encode() + password.encode()).hexdigest()
        return f"{salt}${hashed_password}"
    
    def _verify_password(self, password, hashed_password):
        """验证密码
        
        Args:
            password: 原始密码
            hashed_password: 哈希后的密码
            
        Returns:
            bool: 密码是否正确
        """
        salt, stored_hash = hashed_password.split('$')
        calculated_hash = hashlib.sha256(salt.encode() + password.encode()).hexdigest()
        return calculated_hash == stored_hash
    
    def _get_current_mac(self):
        """获取当前设备MAC地址
        
        Returns:
            str: MAC地址
        """
        try:
            # 获取主机名
            hostname = socket.gethostname()
            # 获取IP地址
            ip_address = socket.gethostbyname(hostname)
            # 获取用户名
            username = getpass.getuser()
            
            # 组合设备标识
            device_id = f"{hostname}_{ip_address}_{username}"
            
            # 哈希处理
            return hashlib.md5(device_id.encode()).hexdigest()
        except Exception as e:
            print(f"获取MAC地址时发生错误: {str(e)}")
            return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
    
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
            
            return {'success': True, 'message': '登录成功', 'user': user}
            
        except Exception as e:
            print(f"登录时发生错误: {str(e)}")
            return {'success': False, 'message': f'登录失败: {str(e)}', 'user': None}
    
    def register_user(self, email, password, nickname, mac_address=None):
        """注册用户
        
        Args:
            email: 邮箱
            password: 密码
            nickname: 昵称
            mac_address: MAC地址（不使用）
            
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
                'nickname': nickname
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
