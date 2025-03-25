import time
import random
import threading
import queue
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class SearchThread(QThread):
    """搜索线程，避免UI卡顿"""
    search_success = pyqtSignal(list)  # 搜索成功信号，传递文章列表
    search_failed = pyqtSignal(str)    # 搜索失败信号
    search_progress = pyqtSignal(int, int)  # 搜索进度信号，当前数量和总数量
    search_complete = pyqtSignal(int)  # 搜索完成信号，传递总文章数
    
    def __init__(self, gzh_name, login_info, article_limit=0):
        super().__init__()
        self.gzh_name = gzh_name
        self.login_info = login_info
        self.article_limit = article_limit
        self.searching = True
        self.articles_queue = queue.Queue()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': "https://mp.weixin.qq.com/",
            "Host": "mp.weixin.qq.com",
            "Cookie": self.login_info['cookie']
        }
        
    def run(self):
        try:
            # 搜索公众号fakeid
            fakeid = self.search_gzh(self.gzh_name)
            if not fakeid:
                self.search_failed.emit(f"未找到 {self.gzh_name} 的公众号信息")
                return
                
            # 获取文章总数
            first_page = requests.get(
                f'https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&begin=0&count=5&fakeid={fakeid}&type=9&query=&token={self.login_info["token"]}&lang=zh_CN&f=json&ajax=1',
                headers=self.headers
            ).json()
            
            if first_page.get('app_msg_cnt'):
                total_articles = first_page['app_msg_cnt']
                total_pages = (total_articles - 1) // 5 + 1
                
                # 处理文章数量限制
                if self.article_limit > 0 and self.article_limit < total_articles:
                    total_articles = self.article_limit
                    total_pages = (total_articles - 1) // 5 + 1
                
                articles_count = 0
                
                # 开始抓取文章
                for batch_start in range(0, total_pages, 10):
                    if not self.searching:
                        break
                        
                    threads = []
                    batch_end = min(batch_start + 10, total_pages)
                    
                    for page in range(batch_start, batch_end):
                        if not self.searching:
                            break
                        offset = page * 5
                        t = threading.Thread(target=self.fetch_page, args=(offset, fakeid))
                        t.daemon = True
                        threads.append(t)
                        t.start()
                    
                    # 等待当前批次完成，但设置超时时间
                    for t in threads:
                        t.join(timeout=15)
                    
                    # 处理队列中的文章
                    while not self.articles_queue.empty():
                        articles = self.articles_queue.get()
                        for article in articles:
                            articles_count += 1
                            self.search_progress.emit(articles_count, total_articles)
                            self.search_success.emit([article])
                            
                            # 检查是否达到限制数量
                            if self.article_limit > 0 and articles_count >= self.article_limit:
                                self.searching = False
                                break
                    
                    # 批次间延时，避免被封
                    if batch_end < total_pages and self.searching:
                        delay = random.randint(3, 5)
                        time.sleep(delay)
                
                self.search_complete.emit(articles_count)
            else:
                self.search_failed.emit("获取文章列表失败")
                
        except Exception as e:
            self.search_failed.emit(f"搜索过程出错: {str(e)}")
    
    def stop_search(self):
        """停止搜索"""
        self.searching = False
    
    def search_gzh(self, gzh_name):
        """搜索公众号fakeid"""
        search_url = f'https://mp.weixin.qq.com/cgi-bin/searchbiz?action=search_biz&token={self.login_info["token"]}&lang=zh_CN&f=json&ajax=1&random={time.time()}&query={gzh_name}&begin=0&count=5'
        response = requests.get(search_url, headers=self.headers)
        data = response.json()
        if data.get('list'):
            return data['list'][0]['fakeid']
        return None
    
    def fetch_page(self, offset, fakeid):
        """抓取单个页面的文章"""
        if not self.searching:
            return
            
        try:
            article_url = f'https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&begin={offset}&count=5&fakeid={fakeid}&type=9&query=&token={self.login_info["token"]}&lang=zh_CN&f=json&ajax=1'
            response = requests.get(article_url, headers=self.headers, timeout=10)
            data = response.json()
            
            if not self.searching:
                return
                
            if data.get('app_msg_list'):
                new_articles = []
                for a in data['app_msg_list']:
                    article = {
                        '标题': a['title'],
                        '链接': a['link'],
                        '发布时间': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(a.get('create_time', 0))),
                        '阅读数': a.get('read_num', 0),
                        '封面': a.get('cover', '')
                    }
                    new_articles.append(article)
                
                if self.searching:
                    self.articles_queue.put(new_articles)
        except Exception as e:
            print(f"抓取页面出错 (offset={offset}): {str(e)}")
