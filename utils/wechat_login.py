import os
import time
import json
import pickle
import requests
from urllib.parse import urlparse, parse_qs
from fake_useragent import UserAgent
from threading import Thread

class QRCodeDisplay(Thread):
    """显示二维码的线程类"""
    def __init__(self, image_content):
        super().__init__()
        self.image_content = image_content
        self.daemon = True  # 设置为守护线程，主线程结束时自动结束
        
    def run(self):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(self.image_content))
            img.show()
        except Exception as e:
            print(f"显示二维码失败: {e}")
            print("请手动保存二维码并扫描")
            with open("qrcode.png", "wb") as f:
                f.write(self.image_content)
            print("二维码已保存为 qrcode.png")

class WeChatLoginAPI:
    """微信公众号登录API"""
    
    def __init__(self, cookie_path=None, cookie_json_path=None):
        """
        初始化微信公众号登录API
        
        Args:
            cookie_path: Cookies文件保存路径
            cookie_json_path: token和cookie信息的JSON文件保存路径
        """
        self.ua = UserAgent()
        self.headers = {
            'User-Agent': self.ua.random, 
            'Referer': "https://mp.weixin.qq.com/", 
            "Host": "mp.weixin.qq.com"
        }
        
        # 创建cookies目录
        cookies_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils', 'cookies')
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir)
            
        # 设置默认路径
        self.cookie_path = cookie_path or os.path.join(cookies_dir, 'gzhcookies.cookie')
        self.cookie_json_path = cookie_json_path or os.path.join(cookies_dir, 'cookie.json')
    
    def is_login(self, session):
        """
        检查当前会话是否已登录
        
        Args:
            session: requests.Session对象
            
        Returns:
            tuple: (session, 是否已登录)
        """
        try:
            session.cookies.load(ignore_discard=True)
        except Exception:
            pass
            
        login_url = session.get(
            "https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1"
        ).json()
        
        if login_url['base_resp']['ret'] == 0:
            print('Cookies值有效，无需扫码登录！')
            return session, True
        else:
            print('Cookies值已经失效，请重新扫码登录！')
            return session, False
    
    def login(self):
        """
        登录微信公众号
        
        Returns:
            dict: 包含token和cookie的字典
        """
        # 创建会话并尝试加载已有cookies
        session = requests.session()
        if not os.path.exists(self.cookie_path):
            # 确保目录存在
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            with open(self.cookie_path, 'wb') as f:
                pickle.dump(session.cookies, f)
        
        # 读取cookies
        session.cookies = pickle.load(open(self.cookie_path, 'rb'))
        session, status = self.is_login(session)
        
        # 如果未登录，则进行扫码登录
        if not status:
            session = requests.session()
            session.get('https://mp.weixin.qq.com/', headers=self.headers)
            session.post(
                'https://mp.weixin.qq.com/cgi-bin/bizlogin?action=startlogin',
                data='userlang=zh_CN&redirect_url=&login_type=3&sessionid={}&token=&lang=zh_CN&f=json&ajax=1'.format(
                    int(time.time() * 1000)
                ), 
                headers=self.headers
            )
            
            # 获取登录二维码
            login_url = session.get(
                'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&random={}'.format(
                    int(time.time() * 1000)
                )
            )
            
            date_url = 'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=ask&token=&lang=zh_CN&f=json&ajax=1'
            
            # 显示二维码
            t = QRCodeDisplay(login_url.content)
            t.start()
            
            # 轮询登录状态
            while True:
                date = session.get(date_url).json()
                if date['status'] == 0:
                    print('二维码未失效，请扫码！')
                elif date['status'] == 6:
                    print('已扫码，请确认！')
                elif date['status'] == 1:
                    print('已确认，登录成功！')
                    url = session.post(
                        'https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login',
                        data='userlang=zh_CN&redirect_url=&cookie_forbidden=0&cookie_cleaned=1&plugin_used=0&login_type=3&token=&lang=zh_CN&f=json&ajax=1',
                        headers=self.headers
                    ).json()
                    
                    # 解析token
                    token = parse_qs(urlparse(url['redirect_url']).query).get('token', [None])[0]
                    session.get('https://mp.weixin.qq.com{}'.format(url['redirect_url']), headers=self.headers)
                    break
                    
                time.sleep(2)
            
            # 保存cookies和token信息
            cookie = '; '.join([f"{name}={value}" for name, value in session.cookies.items()])
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            with open(self.cookie_path, 'wb') as f:
                pickle.dump(session.cookies, f)
                
            login_info = {'token': token, 'cookie': cookie}
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.cookie_json_path), exist_ok=True)
            with open(self.cookie_json_path, 'w') as f:
                json.dump(login_info, f, ensure_ascii=False)
                
            return login_info
        else:
            # 已登录，直接返回保存的信息
            with open(self.cookie_json_path, 'r') as f:
                login_info = json.load(f)
            return login_info
    
    def get_session(self):
        """
        获取已登录的会话对象
        
        Returns:
            requests.Session: 已登录的会话对象
        """
        login_info = self.login()
        session = requests.session()
        
        # 设置cookies
        for cookie_item in login_info['cookie'].split('; '):
            if '=' in cookie_item:
                name, value = cookie_item.split('=', 1)
                session.cookies.set(name, value)
        
        # 设置headers
        session.headers.update(self.headers)
        return session

# 使用示例
def get_wechat_login():
    """
    获取微信公众号登录API实例
    
    Returns:
        WeChatLoginAPI: 微信公众号登录API实例
    """
    return WeChatLoginAPI()