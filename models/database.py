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
                
                # 创建用户记录 - 尝试使用RPC调用
                try:
                    print("尝试使用RPC调用创建用户记录...")
                    # 方法1: 使用RPC调用
                    result = self.supabase.rpc(
                        'create_user_record',
                        {
                            'user_id': user_id,
                            'user_email': email,
                            'user_nickname': nickname,
                            'user_mac': mac_address,
                            'created_at_time': datetime.now().isoformat()
                        }
                    ).execute()
                    
                    if result.data:
                        return {'success': True, 'message': '注册成功', 'user_id': user_id}
                    else:
                        print(f"RPC调用失败: {result.error}")
                        
                        # 方法2: 尝试使用SQL插入
                        print("尝试使用SQL插入...")
                        sql = """
                        INSERT INTO users (id, email, nickname, mac_address, created_at)
                        VALUES ('{}', '{}', '{}', '{}', '{}')
                        """.format(
                            user_id, 
                            email.replace("'", "''"), 
                            nickname.replace("'", "''"), 
                            mac_address.replace("'", "''"),
                            datetime.now().isoformat()
                        )
                        
                        sql_result = self.supabase.sql(sql).execute()
                        if not sql_result.error:
                            return {'success': True, 'message': '注册成功', 'user_id': user_id}
                        else:
                            print(f"SQL插入失败: {sql_result.error}")
                            
                            # 方法3: 尝试使用REST API
                            print("尝试使用REST API插入...")
                            import requests
                            
                            # 确保使用service_role密钥
                            headers = {
                                "apikey": SUPABASE_KEY,
                                "Authorization": f"Bearer {SUPABASE_KEY}",
                                "Content-Type": "application/json",
                                "Prefer": "return=minimal"
                            }
                            
                            url = f"{SUPABASE_URL}/rest/v1/users"
                            data = {
                                'id': user_id,
                                'email': email,
                                'nickname': nickname,
                                'mac_address': mac_address,
                                'created_at': datetime.now().isoformat()
                            }
                            
                            response = requests.post(url, json=data, headers=headers)
                            if response.status_code < 300:
                                return {'success': True, 'message': '注册成功', 'user_id': user_id}
                            else:
                                print(f"REST API插入失败: {response.text}")
                                
                                # 如果所有方法都失败，删除认证用户
                                try:
                                    self.supabase.auth.admin.delete_user(user_id)
                                except:
                                    pass
                                return {'success': False, 'message': '注册失败: 无法创建用户记录，请联系管理员'}
                
                except Exception as db_error:
                    # 如果创建用户记录失败，删除认证用户
                    try:
                        self.supabase.auth.admin.delete_user(user_id)
                    except:
                        pass
                    
                    # 输出详细错误信息
                    error_str = str(db_error)
                    print(f"数据库错误详情: {error_str}")
                    return {'success': False, 'message': f'创建用户记录失败: {error_str}'}
                    
            except Exception as auth_error:
                return {'success': False, 'message': f'用户认证创建失败: {str(auth_error)}'}
                
        except Exception as e:
            return {'success': False, 'message': f'注册失败: {str(e)}'}
    
    def login_user(self, email, password):
        """用户登录
        
        Args:
            email: 用户邮箱
            password: 用户密码
            
        Returns:
            dict: 登录结果
        """
        # 尝试刷新Supabase客户端，确保连接是最新的
        self._refresh_supabase_client()
        
        try:
            # 登录验证
            print(f"尝试登录用户: {email}")
            # 确保邮箱格式正确（去除可能的空格）
            email = email.strip().lower()
            print(f"处理后的邮箱: {email}")
            
            # 检查用户是否存在
            try:
                users = self.supabase.auth.admin.list_users()
                user_exists = False
                for user in users:
                    if hasattr(user, 'email') and user.email and user.email.lower() == email.lower():
                        user_exists = True
                        print(f"用户存在于认证系统中，用户ID: {user.id}")
                        break
                
                if not user_exists:
                    print(f"用户 {email} 不存在于认证系统中")
                    return {'success': False, 'message': '该邮箱未注册，请先注册账号'}
            except Exception as check_error:
                print(f"检查用户存在性失败: {str(check_error)}")
                # 继续尝试登录，因为list_users可能没有权限
            
            try:
                print(f"开始验证登录凭据，邮箱: {email}")
                # 检查Supabase配置
                print(f"Supabase URL: {SUPABASE_URL[:20]}...")
                print(f"Supabase KEY类型: {'service_role' if 'service_role' in SUPABASE_KEY else 'anon'}")
                
                try:
                    response = self.supabase.auth.sign_in_with_password({
                        'email': email,
                        'password': password
                    })
                    print("登录凭据验证成功")
                except Exception as sign_in_error:
                    error_msg = str(sign_in_error)
                    print(f"登录验证详细错误: {error_msg}")
                    
                    # 检查是否是JWT过期错误
                    if "JWT expired" in error_msg or "token is expired" in error_msg:
                        print("检测到JWT令牌过期错误，尝试重新初始化Supabase客户端...")
                        # 重新初始化Supabase客户端
                        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                        # 重试登录
                        response = self.supabase.auth.sign_in_with_password({
                            'email': email,
                            'password': password
                        })
                        print("重新初始化后登录成功")
                    else:
                        # 重新抛出异常，让外层捕获
                        raise
                
                # 获取用户信息
                user_id = response.user.id
                print(f"登录成功，用户ID: {user_id}")
                
                user_data = self.supabase.table('users').select('*').eq('id', user_id).execute()
                
                if not user_data.data:
                    print(f"用户ID {user_id} 在users表中不存在")
                    # 尝试自动创建用户记录
                    try:
                        print("尝试自动创建用户记录...")
                        user_record = {
                            'id': user_id,
                            'email': email,
                            'nickname': email.split('@')[0],  # 使用邮箱前缀作为默认昵称
                            'mac_address': self._get_current_mac(),
                            'created_at': datetime.now().isoformat()
                        }
                        
                        self.supabase.table('users').insert(user_record).execute()
                        user_data = self.supabase.table('users').select('*').eq('id', user_id).execute()
                        
                        if not user_data.data:
                            return {'success': False, 'message': '用户数据不存在，自动创建失败'}
                    except Exception as create_error:
                        print(f"自动创建用户记录失败: {str(create_error)}")
                        return {'success': False, 'message': '用户数据不存在，请联系管理员'}
                
                user = user_data.data[0]
                print(f"获取到用户数据: {user}")
                
                # 检查授权是否过期
                if user.get('expiry_date'):
                    expiry_date = datetime.fromisoformat(user['expiry_date'])
                    if expiry_date < datetime.now():
                        print(f"用户授权已过期，过期时间: {expiry_date}")
                        return {'success': False, 'message': '授权已过期，请续费'}
                
                # 检查MAC地址
                current_mac = self._get_current_mac()
                if user.get('mac_address') and user['mac_address'] != current_mac:
                    print(f"MAC地址不匹配，用户MAC: {user['mac_address']}，当前MAC: {current_mac}")
                    return {'success': False, 'message': '设备不匹配，请联系管理员'}
                
                return {
                    'success': True, 
                    'message': '登录成功', 
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'nickname': user['nickname'],
                        'expiry_date': user.get('expiry_date')
                    }
                }
            
            except Exception as auth_error:
                error_str = str(auth_error)
                print(f"登录验证失败: {error_str}")
                
                # 检查是否是邮箱未验证的错误
                if "Email not confirmed" in error_str:
                    # 尝试查找用户并自动确认邮箱
                    try:
                        print("检测到邮箱未验证错误，尝试自动确认...")
                        # 查找用户
                        users = self.supabase.auth.admin.list_users()
                        target_user = None
                        for user in users:
                            if user.email == email:
                                target_user = user
                                break
                        
                        if target_user:
                            # 自动确认邮箱
                            self.supabase.auth.admin.update_user_by_id(
                                target_user.id,
                                {"email_confirm": True}
                            )
                            
                            # 再次尝试登录
                            print("邮箱已确认，再次尝试登录...")
                            return self.login_user(email, password)
                        else:
                            print(f"未找到邮箱为 {email} 的用户")
                    except Exception as confirm_error:
                        print(f"自动确认邮箱失败: {str(confirm_error)}")
                
                # 根据错误类型返回不同的错误消息
                if "Invalid login credentials" in error_str:
                    print(f"登录凭据无效，详细错误: {error_str}")
                    
                    # 尝试查找用户是否存在
                    try:
                        users = self.supabase.auth.admin.list_users()
                        user_exists = False
                        for user in users:
                            if user.email.lower() == email.lower():
                                user_exists = True
                                print(f"用户存在于认证系统中，用户ID: {user.id}")
                                break
                        
                        if not user_exists:
                            print(f"用户 {email} 不存在于认证系统中")
                            return {'success': False, 'message': '该邮箱未注册，请先注册账号'}
                        else:
                            # 用户存在但密码错误
                            return {'success': False, 'message': '密码错误，请确认密码是否正确。如忘记密码，请联系管理员重置'}
                    except Exception as check_error:
                        print(f"检查用户存在性失败: {str(check_error)}")
                        return {'success': False, 'message': '邮箱或密码错误，请确认邮箱拼写和密码是否正确'}
                elif "Email not confirmed" in error_str:
                    return {'success': False, 'message': '邮箱未验证，请查收验证邮件或联系管理员'}
                else:
                    print(f"未知登录错误: {error_str}")
                    return {'success': False, 'message': f'登录失败: {error_str}'}
                
        except Exception as e:
            print(f"登录过程中发生异常: {str(e)}")
            return {'success': False, 'message': f'登录失败: {str(e)}'}
    
    def activate_user(self, user_id, activation_code):
        """激活用户账号
        
        Args:
            user_id: 用户ID
            activation_code: 激活码
            
        Returns:
            dict: 激活结果
        """
        try:
            # 验证激活码
            code_data = self.supabase.table('activation_codes').select('*').eq('code', activation_code).execute()
            
            if not code_data.data:
                return {'success': False, 'message': '无效的激活码'}
                
            code_info = code_data.data[0]
            
            # 检查激活码是否已使用
            if code_info.get('used'):
                return {'success': False, 'message': '该激活码已被使用'}
                
            # 计算过期时间
            duration_days = code_info.get('duration_days', 30)  # 默认30天
            expiry_date = datetime.now() + timedelta(days=duration_days)
            
            # 更新用户信息
            self.supabase.table('users').update({
                'activation_code': activation_code,
                'expiry_date': expiry_date.isoformat()
            }).eq('id', user_id).execute()
            
            # 标记激活码为已使用
            self.supabase.table('activation_codes').update({
                'used': True,
                'used_by': user_id,
                'used_at': datetime.now().isoformat()
            }).eq('id', code_info['id']).execute()
            
            return {
                'success': True, 
                'message': '激活成功', 
                'expiry_date': expiry_date.isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'message': f'激活失败: {str(e)}'}
    
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
                    'updated_at': datetime.now().isoformat()
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
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
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