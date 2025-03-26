import os
import json
import time
import uuid
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Supabase配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

class DatabaseManager:
    """数据库管理类，负责与Supabase的连接和数据操作"""
    
    def __init__(self):
        """初始化数据库连接"""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("请在.env文件中设置SUPABASE_URL和SUPABASE_KEY")
            
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    # ===== 用户管理相关方法 =====
    
    def register_user(self, email, password, nickname, mac_address):
        """注册新用户
        
        Args:
            email: 用户邮箱
            password: 用户密码
            nickname: 用户昵称
            mac_address: 绑定的MAC地址
            
        Returns:
            dict: 注册结果
        """
        try:
            # 先检查邮箱是否已存在
            existing_user_email = self.supabase.table('users').select('*').eq('email', email).execute()
            if existing_user_email.data:
                return {'success': False, 'message': '该邮箱已被注册'}
            
            # 检查昵称是否已存在（如果昵称需要唯一）
            existing_user_nickname = self.supabase.table('users').select('*').eq('nickname', nickname).execute()
            if existing_user_nickname.data:
                return {'success': False, 'message': '该昵称已被使用'}
            
            # 创建用户认证
            try:
                auth_response = self.supabase.auth.sign_up({
                    'email': email,
                    'password': password
                })
                
                if not auth_response.user:
                    return {'success': False, 'message': '用户认证创建失败'}
                
                # 获取用户ID
                user_id = auth_response.user.id
                
                # 自动确认用户邮箱，绕过邮箱验证
                try:
                    print("尝试自动确认用户邮箱...")
                    # 使用管理员API确认用户邮箱
                    self.supabase.auth.admin.update_user_by_id(
                        user_id,
                        {"email_confirm": True}
                    )
                except Exception as confirm_error:
                    print(f"自动确认邮箱失败: {str(confirm_error)}")
                    # 如果自动确认失败，尝试使用REST API
                    try:
                        import requests
                        
                        admin_url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
                        admin_headers = {
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}",
                            "Content-Type": "application/json"
                        }
                        admin_data = {
                            "email_confirm": True
                        }
                        
                        admin_response = requests.put(admin_url, json=admin_data, headers=admin_headers)
                        if admin_response.status_code >= 300:
                            print(f"REST API确认邮箱失败: {admin_response.text}")
                    except Exception as rest_error:
                        print(f"REST API确认邮箱错误: {str(rest_error)}")
                else:
                    pass  # 添加else子句
                
            except Exception as e:
                print(f"注册用户时发生错误: {str(e)}")
                # 如果发生错误，尝试清理
                if 'user_id' in locals():
                    try:
                        self.supabase.auth.admin.delete_user(user_id)
                    except:
                        pass
                return {'success': False, 'message': f'注册失败: {str(e)}'}
            else:
                pass  # 添加else子句
            
            # 创建用户记录 - 直接插入
            user_data = {
                'id': user_id,
                'email': email,
                'nickname': nickname,
                'mac': mac_address if mac_address else '',
                'role': '1',  # 默认为普通用户
                'activation_status': '未激活',
                'expired_time': (datetime.now() + timedelta(days=30)).isoformat(),
                'create_time': datetime.now().isoformat(),
                'update_time': datetime.now().isoformat()
            }
            
            user_result = self.supabase.table('users').insert(user_data).execute()
            
            if not user_result.data:
                # 如果创建用户记录失败，尝试删除认证用户
                try:
                    self.supabase.auth.admin.delete_user(user_id)
                except:
                    pass
                return {'success': False, 'message': '创建用户记录失败'}
            
            return {
                'success': True, 
                'message': '注册成功',
                'user': user_result.data[0]
            }
            
        except Exception as e:
            print(f"注册用户时发生错误: {str(e)}")
            # 如果发生错误，尝试清理
            if 'user_id' in locals():
                try:
                    self.supabase.auth.admin.delete_user(user_id)
                except:
                    pass
            return {'success': False, 'message': f'注册失败: {str(e)}'}
    
    def register_user_by_admin(self, email, password, nickname, role='1', expired_time=None):
        """管理员创建用户
        
        Args:
            email: 用户邮箱
            password: 用户密码
            nickname: 用户昵称
            role: 用户角色，默认为普通用户
            expired_time: 过期时间，默认为30天后
            
        Returns:
            dict: 注册结果
        """
        try:
            # 先检查邮箱是否已存在于 users 表中
            existing_user_email = self.supabase.table('users').select('*').eq('email', email).execute()
            if existing_user_email.data:
                return {'success': False, 'message': '该邮箱已被注册'}
            
            # 检查昵称是否已存在
            existing_user_nickname = self.supabase.table('users').select('*').eq('nickname', nickname).execute()
            if existing_user_nickname.data:
                return {'success': False, 'message': '该昵称已被使用'}
            
            # 检查 Auth 系统中是否已存在该用户
            try:
                # 尝试通过邮箱查找用户
                auth_users = self.supabase.auth.admin.list_users()
                existing_auth_user = None
                
                for user in auth_users:
                    if user.email == email:
                        existing_auth_user = user
                        break
                
                if existing_auth_user:
                    # Auth 系统中已存在该用户，但 users 表中不存在
                    # 直接使用该用户的 ID 创建 users 表记录
                    user_id = existing_auth_user.id
                    print(f"Auth 系统中已存在该用户，ID: {user_id}")
                else:
                    # 创建用户认证
                    auth_response = self.supabase.auth.admin.create_user({
                        'email': email,
                        'password': password,
                        'email_confirm': True  # 自动确认邮箱
                    })
                    
                    if not auth_response.user:
                        return {'success': False, 'message': '用户认证创建失败'}
                    
                    # 获取用户ID
                    user_id = auth_response.user.id
            except Exception as auth_error:
                print(f"检查或创建 Auth 用户时出错: {str(auth_error)}")
                return {'success': False, 'message': f'用户认证操作失败: {str(auth_error)}'}
            
            # 创建用户记录
            if not expired_time:
                expired_time = (datetime.now() + timedelta(days=30)).isoformat()
            
            user_data = {
                'id': user_id,
                'email': email,
                'nickname': nickname,
                'mac': '',
                'role': role,
                'activation_status': '未激活',
                'expired_time': expired_time,
                'create_time': datetime.now().isoformat(),
                'update_time': datetime.now().isoformat()
            }
            
            user_result = self.supabase.table('users').insert(user_data).execute()
            
            if not user_result.data:
                # 如果创建用户记录失败，尝试删除认证用户
                try:
                    self.supabase.auth.admin.delete_user(user_id)
                except Exception as auth_error:
                    print(f"删除认证用户失败: {str(auth_error)}")
                    # 继续执行，不影响结果
            
                return {'success': False, 'message': '创建用户记录失败'}
            
            return {
                'success': True, 
                'message': '创建用户成功',
                'user': user_result.data[0]
            }
                
        except Exception as e:
            print(f"创建用户时发生错误: {str(e)}")
            return {'success': False, 'message': f'创建用户失败: {str(e)}'}
    
    def login_user(self, email, password):
        """用户登录
        
        Args:
            email: 用户邮箱
            password: 用户密码
            
        Returns:
            dict: 登录结果
        """
        try:
            # 验证用户认证
            auth_response = self.supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })
            
            if not auth_response.user:
                return {'success': False, 'message': '邮箱或密码错误'}
            
            # 获取用户ID
            user_id = auth_response.user.id
            
            # 获取用户信息
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return {'success': False, 'message': '用户数据不存在'}
            
            user = user_result.data[0]
            
            # 检查用户是否过期
            if user.get('expired_time'):
                try:
                    expiry_date = datetime.fromisoformat(user['expired_time'])
                    if expiry_date < datetime.now():
                        return {'success': False, 'message': '账号已过期，请联系管理员'}
                except:
                    pass
            
            # 更新最后登录时间和IP
            try:
                self.supabase.table('users').update({
                    'last_login_time': datetime.now().isoformat(),
                    'last_login_ip': '127.0.0.1'  # 本地登录，使用本地IP
                }).eq('id', user_id).execute()
            except:
                pass
            
            return {
                'success': True,
                'message': '登录成功',
                'user': user
            }
            
        except Exception as e:
            print(f"登录时发生错误: {str(e)}")
            return {'success': False, 'message': f'登录失败: {str(e)}'}
    
    def is_admin(self, user_id):
        """检查用户是否是管理员
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否是管理员
        """
        try:
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return False
            
            user = user_result.data[0]
            
            # 获取用户角色，并转换为字符串进行比较
            role = user.get('role')
            # 打印角色信息，便于调试
            print(f"用户 {user_id} 的角色值: {role}, 类型: {type(role)}")
            
            # 同时处理字符串和数字类型的 role 值
            return str(role) == '0'  # 0表示管理员
            
        except Exception as e:
            print(f"检查管理员权限时出错: {str(e)}")
            return False
    
    def get_users(self, email=None, nickname=None):
        """获取用户列表
        
        Args:
            email: 邮箱筛选条件
            nickname: 昵称筛选条件
            
        Returns:
            dict: 用户列表结果
        """
        try:
            query = self.supabase.table('users').select('*')
            
            if email:
                query = query.ilike('email', f'%{email}%')
            
            if nickname:
                query = query.ilike('nickname', f'%{nickname}%')
            
            result = query.execute()
            
            return {
                'success': True,
                'users': result.data
            }
            
        except Exception as e:
            print(f"获取用户列表时发生错误: {str(e)}")
            return {'success': False, 'message': f'获取用户列表失败: {str(e)}'}
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 用户信息结果
        """
        try:
            result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not result.data:
                return {'success': False, 'message': '用户不存在'}
            
            return {
                'success': True,
                'user': result.data[0]
            }
            
        except Exception as e:
            print(f"获取用户信息时发生错误: {str(e)}")
            return {'success': False, 'message': f'获取用户信息失败: {str(e)}'}
    
    def update_user(self, user_id, nickname=None, password=None, role=None, expired_time=None):
        """更新用户信息
        
        Args:
            user_id: 用户ID
            nickname: 新昵称
            password: 新密码
            role: 新角色
            expired_time: 新过期时间
            
        Returns:
            dict: 更新结果
        """
        try:
            # 先检查用户是否存在
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return {'success': False, 'message': '用户不存在'}
            
            # 如果修改昵称，检查昵称是否已存在
            if nickname and nickname != user_result.data[0].get('nickname'):
                existing_nickname = self.supabase.table('users').select('*').eq('nickname', nickname).execute()
                if existing_nickname.data and existing_nickname.data[0].get('id') != user_id:
                    return {'success': False, 'message': '该昵称已被使用'}
            
            # 更新用户数据
            update_data = {
                'update_time': datetime.now().isoformat()
            }
            
            if nickname:
                update_data['nickname'] = nickname
            
            if role is not None:
                update_data['role'] = role
            
            if expired_time:
                update_data['expired_time'] = expired_time
            
            # 更新用户表
            self.supabase.table('users').update(update_data).eq('id', user_id).execute()
            
            # 如果需要更新密码
            if password:
                try:
                    self.supabase.auth.admin.update_user_by_id(
                        user_id,
                        {"password": password}
                    )
                except Exception as pw_error:
                    print(f"更新密码失败: {str(pw_error)}")
                    return {'success': False, 'message': f'更新密码失败: {str(pw_error)}'}
            
            # 获取更新后的用户信息
            updated_user = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            return {
                'success': True,
                'message': '更新成功',
                'user': updated_user.data[0] if updated_user.data else None
            }
            
        except Exception as e:
            print(f"更新用户信息时发生错误: {str(e)}")
            return {'success': False, 'message': f'更新用户信息失败: {str(e)}'}
    
    def delete_user(self, user_id):
        """删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 删除结果
        """
        try:
            # 先检查用户是否存在
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return {'success': False, 'message': '用户不存在'}
            
            # 删除用户表记录
            self.supabase.table('users').delete().eq('id', user_id).execute()
            
            # 删除认证用户
            try:
                self.supabase.auth.admin.delete_user(user_id)
            except Exception as auth_error:
                print(f"删除认证用户失败: {str(auth_error)}")
                # 继续执行，不影响结果
            
            return {
                'success': True,
                'message': '删除成功'
            }
            
        except Exception as e:
            print(f"删除用户时发生错误: {str(e)}")
            return {'success': False, 'message': f'删除用户失败: {str(e)}'}
    
    def generate_activation_code(self, user_id):
        """为用户生成激活码
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 生成结果
        """
        try:
            # 先检查用户是否存在
            user_result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data:
                return {'success': False, 'message': '用户不存在'}
            
            # 生成激活码
            activation_code = str(uuid.uuid4()).replace('-', '')[:16].upper()
            
            # 更新用户表
            self.supabase.table('users').update({
                'activation_code': activation_code,
                'activation_status': '未激活',
                'update_time': datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            # 创建激活码记录
            code_data = {
                'code': activation_code,
                'user_id': user_id,
                'duration_days': 30,  # 默认30天有效期
                'create_time': datetime.now().isoformat(),
                'used': False
            }
            
            self.supabase.table('activation_codes').insert(code_data).execute()
            
            return {
                'success': True,
                'message': '激活码生成成功',
                'code': activation_code
            }
            
        except Exception as e:
            print(f"生成激活码时发生错误: {str(e)}")
            return {'success': False, 'message': f'生成激活码失败: {str(e)}'}
    
    def create_activation_code(self, duration_days=30):
        """创建通用激活码
        
        Args:
            duration_days: 有效期天数
            
        Returns:
            dict: 创建结果
        """
        try:
            # 生成激活码
            activation_code = str(uuid.uuid4()).replace('-', '')[:16].upper()
            
            # 创建激活码记录
            code_data = {
                'code': activation_code,
                'duration_days': duration_days,
                'create_time': datetime.now().isoformat(),
                'used': False
            }
            
            self.supabase.table('activation_codes').insert(code_data).execute()
            
            return {
                'success': True,
                'message': '激活码创建成功',
                'code': activation_code
            }
            
        except Exception as e:
            print(f"创建激活码时发生错误: {str(e)}")
            return {'success': False, 'message': f'创建激活码失败: {str(e)}'}
    
    def get_activation_codes(self):
        """获取激活码列表
        
        Returns:
            dict: 激活码列表结果
        """
        try:
            result = self.supabase.table('activation_codes').select('*').execute()
            
            return {
                'success': True,
                'codes': result.data
            }
            
        except Exception as e:
            print(f"获取激活码列表时发生错误: {str(e)}")
            return {'success': False, 'message': f'获取激活码列表失败: {str(e)}'}
    
    def activate_user(self, user_id, activation_code, mac_address):
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
            
            # 检查用户是否已激活
            if user.get('activation_status') == '已激活':
                return {'success': False, 'message': '用户已激活'}
            
            # 检查激活码
            code_result = self.supabase.table('activation_codes').select('*').eq('code', activation_code).execute()
            
            if not code_result.data:
                return {'success': False, 'message': '激活码不存在'}
            
            code = code_result.data[0]
            
            # 检查激活码是否已使用
            if code.get('used'):
                return {'success': False, 'message': '激活码已被使用'}
            
            # 检查激活码是否过期
            if code.get('create_time'):
                try:
                    created_at = datetime.fromisoformat(code['create_time'])
                    duration_days = code.get('duration_days', 30)
                    expiry_date = created_at + timedelta(days=duration_days)
                    
                    if expiry_date < datetime.now():
                        return {'success': False, 'message': '激活码已过期'}
                except:
                    pass
            
            # 更新用户表
            expiry_date = datetime.now() + timedelta(days=code.get('duration_days', 30))
            
            self.supabase.table('users').update({
                'activation_code': activation_code,
                'activation_status': '已激活',
                'mac': mac_address,
                'expired_time': expiry_date.isoformat(),
                'update_time': datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            # 更新激活码表
            self.supabase.table('activation_codes').update({
                'used': True,
                'used_by': user_id,
                'used_at': datetime.now().isoformat()
            }).eq('code', activation_code).execute()
            
            return {
                'success': True,
                'message': '激活成功',
                'expired_time': expiry_date.isoformat()
            }
            
        except Exception as e:
            print(f"激活用户时发生错误: {str(e)}")
            return {'success': False, 'message': f'激活失败: {str(e)}'}
    
    # ===== 公众号文章相关方法 =====
    
    def save_article(self, article_data):
        """保存公众号文章
        
        Args:
            article_data: 文章数据字典，包含以下字段：
                - account_name: 公众号名称
                - category: 公众号分类（可选）
                - title: 文章标题
                - content: 文章内容
                - publish_time: 发布时间
                - read_count: 阅读数
                - article_url: 文章链接
                - user_id: 用户ID
                
        Returns:
            dict: 保存结果
        """
        try:
            # 检查文章是否已存在
            existing = self.supabase.table('articles').select('id').eq('article_url', article_data['article_url']).execute()
            
            if existing.data:
                # 更新文章
                article_id = existing.data[0]['id']
                self.supabase.table('articles').update({
                    'title': article_data['title'],
                    'content': article_data['content'],
                    'read_count': article_data['read_count'],
                    'update_time': datetime.now().isoformat()
                }).eq('id', article_id).execute()
                
                return {'success': True, 'message': '文章更新成功', 'article_id': article_id}
            else:
                # 添加文章
                result = self.supabase.table('articles').insert({
                    'account_name': article_data['account_name'],
                    'category': article_data.get('category', '未分类'),
                    'title': article_data['title'],
                    'content': article_data['content'],
                    'publish_time': article_data['publish_time'],
                    'read_count': article_data['read_count'],
                    'article_url': article_data['article_url'],
                    'user_id': article_data['user_id'],
                    'create_time': datetime.now().isoformat(),
                    'update_time': datetime.now().isoformat()
                }).execute()
                
                return {'success': True, 'message': '文章保存成功', 'article_id': result.data[0]['id']}
                
        except Exception as e:
            return {'success': False, 'message': f'保存文章失败: {str(e)}'}
    
    def get_articles(self, user_id, account_name=None, category=None, limit=100, offset=0):
        """获取文章列表
        
        Args:
            user_id: 用户ID
            account_name: 公众号名称（可选）
            category: 公众号分类（可选）
            limit: 返回数量限制
            offset: 分页偏移量
            
        Returns:
            dict: 查询结果
        """
        try:
            query = self.supabase.table('articles').select('*').eq('user_id', user_id)
            
            # 添加过滤条件
            if account_name:
                query = query.eq('account_name', account_name)
            if category:
                query = query.eq('category', category)
                
            # 添加排序和分页
            result = query.order('publish_time', desc=True).range(offset, offset + limit - 1).execute()
            
            return {'success': True, 'articles': result.data}
            
        except Exception as e:
            return {'success': False, 'message': f'获取文章失败: {str(e)}'}
    
    def delete_article(self, article_id, user_id):
        """删除文章
        
        Args:
            article_id: 文章ID
            user_id: 用户ID（用于验证权限）
            
        Returns:
            dict: 删除结果
        """
        try:
            # 验证权限
            article = self.supabase.table('articles').select('user_id').eq('id', article_id).execute()
            
            if not article.data:
                return {'success': False, 'message': '文章不存在'}
                
            if article.data[0]['user_id'] != user_id:
                return {'success': False, 'message': '无权删除此文章'}
                
            # 删除文章
            self.supabase.table('articles').delete().eq('id', article_id).execute()
            
            return {'success': True, 'message': '文章删除成功'}
            
        except Exception as e:
            return {'success': False, 'message': f'删除文章失败: {str(e)}'}
    
    def search_articles(self, user_id, keyword, limit=100, offset=0):
        """搜索文章
        
        Args:
            user_id: 用户ID
            keyword: 搜索关键词
            limit: 返回数量限制
            offset: 分页偏移量
            
        Returns:
            dict: 搜索结果
        """
        try:
            # 使用Supabase的全文搜索功能
            result = self.supabase.table('articles')\
                .select('*')\
                .eq('user_id', user_id)\
                .or_(f"title.ilike.%{keyword}%,content.ilike.%{keyword}%")\
                .order('publish_time', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return {'success': True, 'articles': result.data}
            
        except Exception as e:
            return {'success': False, 'message': f'搜索文章失败: {str(e)}'}
    
    def _get_current_mac(self):
        """获取当前设备的MAC地址
        
        Returns:
            str: MAC地址
        """
        import uuid
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                         for elements in range(0, 8*6, 8)][::-1])
        return mac
        
    def _refresh_supabase_client(self):
        """刷新Supabase客户端连接"""
        print("刷新Supabase客户端连接...")
        try:
            # 确保使用service_role密钥进行客户端初始化
            self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            # 验证密钥类型
            if 'service_role' in SUPABASE_KEY:
                print("使用service_role密钥初始化Supabase客户端")
            else:
                print("警告：未使用service_role密钥，某些管理功能可能受限")
            print("Supabase客户端刷新成功")
            return True
        except Exception as e:
            print(f"Supabase客户端刷新失败: {str(e)}")
            return False