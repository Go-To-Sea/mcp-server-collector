import requests
import logging
import time
import uuid
import re
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MCPCrawler:
    def __init__(self, base_url="https://mcp.so"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
    
    def get_page(self, url, retry=3):
        """获取页面内容，带重试"""
        for attempt in range(retry):
            try:
                logging.info(f"获取页面: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # 记录实际响应内容的前100个字符用于调试
                content_preview = response.text[:100] if response.text else "空内容"
                logging.info(f"页面响应内容预览: {content_preview}...")
                
                return response.text
            except requests.RequestException as e:
                logging.error(f"请求失败 ({attempt+1}/{retry}): {e}")
                if attempt < retry - 1:
                    wait_time = 2 ** attempt
                    logging.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"获取页面失败: {url}")
                    return None
    
    def get_server_list(self):
        """获取MCP Server列表"""
        logging.info("开始从网页抓取 MCP Server 列表")
        # 假设服务器列表页面是 /servers
        html = self.get_page(f"{self.base_url}/servers")
        if not html:
            logging.error("获取服务器列表页面失败")
            return []
        
        return self._parse_project_list(html, "server")
    
    def get_client_list(self):
        """获取MCP Client列表"""
        logging.info("开始从网页抓取 MCP Client 列表")
        # 假设客户端列表页面是 /clients
        html = self.get_page(f"{self.base_url}/clients")
        if not html:
            logging.error("获取客户端列表页面失败")
            return []
        
        return self._parse_project_list(html, "client")
    
    def _parse_project_list(self, html, project_type):
        """从HTML中解析项目列表"""
        soup = BeautifulSoup(html, 'html.parser')
        projects = []
        
        # 记录HTML结构以便调试
        logging.info(f"页面标题: {soup.title.string if soup.title else '无标题'}")
        
        # 尝试找到项目列表容器
        # 这里的选择器需要根据实际网页结构调整
        project_cards = soup.select('.project-card, .card, .item, article, .project-item')
        logging.info(f"找到 {len(project_cards)} 个可能的项目卡片")
        
        if not project_cards:
            # 如果没有找到项目卡片，记录页面结构以供调试
            logging.warning("未找到项目卡片，可能需要调整选择器")
            logging.debug(f"页面结构预览: {soup.prettify()[:500]}...")
            
            # 尝试查找所有链接，可能指向详情页
            all_links = soup.find_all('a')
            project_links = []
            
            for link in all_links:
                href = link.get('href', '')
                # 假设项目链接包含 /server/ 或 /client/
                if f"/{project_type}/" in href:
                    project_links.append(href)
            
            logging.info(f"通过链接搜索找到 {len(project_links)} 个可能的{project_type}项目")
            
            for link in project_links:
                full_url = self._ensure_absolute_url(link)
                project = self.get_project_detail(full_url, project_type)
                if project:
                    projects.append(project)
                # 添加延迟避免请求过于频繁
                time.sleep(1.5)
        else:
            for card in project_cards:
                # 尝试从卡片中提取链接
                link_elem = card.select_one('a')
                if link_elem and link_elem.get('href'):
                    project_url = self._ensure_absolute_url(link_elem['href'])
                    logging.info(f"正在获取项目详情: {project_url}")
                    
                    # 添加延迟避免请求过于频繁
                    time.sleep(1.5)
                    
                    project = self.get_project_detail(project_url, project_type)
                    if project:
                        projects.append(project)
        
        return projects
    
    def get_project_detail(self, project_url, project_type):
        """获取项目详细信息"""
        html = self.get_page(project_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 记录HTML结构以便调试
        logging.info(f"项目页面标题: {soup.title.string if soup.title else '无标题'}")
        
        # 基本信息
        project = {
            "uuid": str(uuid.uuid4()),
            "type": project_type,
            "url": project_url,
            "target": "_self",
            "status": "created",  # 与您之前的代码保持一致
            "is_featured": True,  # 与您之前的代码保持一致
            "sort": 0,
            "category": "",  # 与您之前的代码保持一致
        }
        
        # 尝试不同的选择器找到标题
        title_selectors = ['h1', 'h1.title', '.project-title', '.title', 'header h1', '.project-header h1']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                project["title"] = title_elem.text.strip()
                project["name"] = self._sanitize_name(project["title"])
                break
        
        if "title" not in project:
            # 尝试使用页面标题
            if soup.title:
                project["title"] = soup.title.string.strip()
                project["name"] = self._sanitize_name(project["title"])
            else:
                # 如果没找到标题，从URL生成一个
                project["name"] = project_url.split('/')[-1]
                project["title"] = project["name"].replace('-', ' ').title()
        
        # 寻找描述元素
        description_selectors = ['.description', '.project-description', 'meta[name="description"]', '.summary', 'p.lead']
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                if selector.startswith('meta'):
                    project["description"] = desc_elem.get('content', '')
                else:
                    project["description"] = desc_elem.text.strip()
                project["summary"] = project["description"]
                break
        
        # 寻找作者信息
        author_selectors = ['.author', '.creator', '.owner', '.user-info', '.profile']
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                # 尝试找作者名
                author_name = author_elem.select_one('a, .name, .username, .author-name')
                if author_name:
                    project["author_name"] = author_name.text.strip()
                
                # 尝试找作者头像
                author_img = author_elem.select_one('img')
                if author_img and author_img.get('src'):
                    project["author_avatar_url"] = self._ensure_absolute_url(author_img['src'])
                    project["avatar_url"] = project["author_avatar_url"]
                break
        
        # 如果找不到特定的作者信息，尝试从整个页面找
        if "author_name" not in project:
            author_anywhere = soup.select_one('.author-name, .username, .creator-name')
            if author_anywhere:
                project["author_name"] = author_anywhere.text.strip()
        
        # 尝试找时间信息
        date_selectors = ['.date', '.time', '.created-at', '.updated-at', '.timestamp', 'time']
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get('datetime') or date_elem.text.strip()
                try:
                    dt = self._parse_time(date_text)
                    project["created_at"] = dt
                    project["updated_at"] = dt
                except:
                    pass
                break
        
        # 确保有日期字段
        if "created_at" not in project:
            project["created_at"] = datetime.now().isoformat()
        if "updated_at" not in project:
            project["updated_at"] = project["created_at"]
        
        # 尝试找标签
        tags = []
        tag_selectors = ['.tags .tag', '.tag', '.label', '.chip', '.badge', '.category']
        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            if tag_elems:
                for tag in tag_elems:
                    tag_text = tag.text.strip()
                    if tag_text and len(tag_text) < 30:  # 避免获取太长的文本
                        tags.append(tag_text)
        
        # 确保有标签
        if not tags:
            tags = ["MCP", project_type]
        
        # 确保MCP标签在最前面
        if "MCP" in tags:
            tags.remove("MCP")
            tags = ["MCP"] + tags
        elif "mcp" in tags:
            tags.remove("mcp")
            tags = ["MCP"] + tags
        else:
            tags = ["MCP"] + tags
            
        project["tags"] = ",".join(tags)
        
        # 尝试找内容
        content_selectors = ['.content', '.project-content', '.description', 'article', '.text', '.body', 'main']
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                project["content"] = str(content_elem)
                break
        
        if "content" not in project:
            # 如果找不到内容，使用整个body内容
            body = soup.find('body')
            if body:
                project["content"] = str(body)
            else:
                project["content"] = str(soup)
        
        # 尝试找图片
        img_elems = soup.select('img')
        for img in img_elems:
            src = img.get('src')
            if src and not src.endswith(('.ico', '.svg')) and 'avatar' not in src and 'logo' not in src:
                project["img_url"] = self._ensure_absolute_url(src)
                break
        
        if "img_url" not in project:
            project["img_url"] = ""
        
        return project
    
    def _sanitize_name(self, title):
        """将标题转换为有效的名称"""
        name = re.sub(r'[^a-zA-Z0-9]', '-', title.lower())
        name = re.sub(r'-+', '-', name)
        name = name.strip('-')
        if not name:
            name = f"project-{uuid.uuid4().hex[:8]}"
        return name
    
    def _ensure_absolute_url(self, url):
        """确保URL是绝对路径"""
        if not url:
            return ""
        if url.startswith('http'):
            return url
        return f"{self.base_url}{url if url.startswith('/') else '/' + url}"
    
    def _parse_time(self, time_str):
        """解析时间字符串"""
        formats = [
            "%Y-%m-%d %H:%M:%S", 
            "%Y-%m-%d", 
            "%B %d, %Y",
            "%d %B %Y",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%m/%d/%Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        
        return datetime.now().isoformat() 