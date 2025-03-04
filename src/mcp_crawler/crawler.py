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
    
    def get_server_list(self, db=None):
        """获取MCP Server列表"""
        logging.info("开始从网页抓取 MCP Server 列表")
        html = self.get_page(f"{self.base_url}/servers")
        if not html:
            logging.error("获取服务器列表页面失败")
            return []
        
        return self._parse_project_list(html, "server", db)
    
    def get_client_list(self, db=None):
        """获取MCP Client列表"""
        logging.info("开始从网页抓取 MCP Client 列表")
        html = self.get_page(f"{self.base_url}/clients")
        if not html:
            logging.error("获取客户端列表页面失败")
            return []
        
        return self._parse_project_list(html, "client", db)
    
    def _ensure_absolute_url(self, url):
        """确保URL是绝对路径，并处理特殊的URL替换规则"""
        if not url:
            return url
            
        # 特殊URL替换规则
        if url == "https://mcp.so/logo.png":
            return "https://mcp.ad/logo.png"
            
        if not url.startswith(('http://', 'https://')):
            if url.startswith('//'):
                return 'https:' + url
            elif url.startswith('/'):
                return self.base_url + url
            else:
                return self.base_url + '/' + url
        return url
    
    def _parse_project_detail(self, soup, project_type):
        """解析项目详情页面"""
        # 基本信息
        project = {
            "uuid": str(uuid.uuid4()),
            "type": project_type,
            "target": "_self",
            "status": "created",
            "is_featured": True,
            "sort": 0,
            "category": "",
        }
        
        # 获取项目名称和标题
        name_elem = soup.select_one('h1')
        if name_elem:
            project["name"] = name_elem.text.strip()
            project["title"] = project["name"]  # 默认使用name作为title
        else:
            # 如果没找到标题，从URL生成一个
            project["name"] = soup.title.string.strip() if soup.title else "untitled"
            project["title"] = project["name"]
        
        # 如果title为空，使用name
        if not project.get("title"):
            project["title"] = project["name"]
        
        # 获取项目logo/avatar（必须要有）
        logo_elem = soup.select_one('img.w-10.h-10.rounded-full')
        if logo_elem and logo_elem.get('src'):
            project["avatar_url"] = self._ensure_absolute_url(logo_elem['src'])
        else:
            # 如果找不到，使用一个默认的头像
            project["avatar_url"] = "https://mcp.so/default-avatar.png"
        
        # 获取作者信息（必须要有）
        # 首先找到包含 "created by" 的容器
        author_section = soup.select_one('div.flex.items-center.gap-2.py-2')
        if author_section and "created by" in author_section.text:
            # 在这个容器中找到作者信息的div
            author_info = author_section.select_one('div.flex.items-center.gap-2')
            if author_info:
                # 获取作者头像
                author_img = author_info.select_one('img.w-4.h-4.rounded-full')
                if author_img and author_img.get('src'):
                    project["author_avatar_url"] = self._ensure_absolute_url(author_img['src'])
                else:
                    project["author_avatar_url"] = ""
                
                # 获取作者名称（在img后面的span中）
                author_name = author_info.select_one('span.text-sm.font-medium')
                if author_name:
                    project["author_name"] = author_name.text.strip()
                else:
                    project["author_name"] = ""
            else:
                project["author_name"] = ""
                project["author_avatar_url"] = ""
        else:
            # 如果找不到作者信息，使用空值
            project["author_name"] = ""
            project["author_avatar_url"] = ""
        
        # 获取项目描述（Information部分）
        content_elem = soup.select_one('div.max-w-full.overflow-x-auto.markdown')
        if content_elem:
            project["content"] = content_elem.decode_contents().strip()
        
        # 获取标签（从页面上获取）
        tags = []
        tag_elems = soup.select('div > div')  # 选择所有可能的标签容器
        for tag_elem in tag_elems:
            if tag_elem.text.strip().startswith('#'):
                tag_text = tag_elem.text.strip().replace('#', '').strip()
                if tag_text:
                    tags.append(tag_text)
        project["tags"] = ",".join(tags) if tags else ""  # 如果没有标签则设为空字符串
        
        # 获取GitHub URL
        github_link = soup.select_one('a[href*="github.com"]')
        if github_link and github_link.get('href'):
            project["url"] = github_link['href']
        
        # 获取分类（如果有）
        category_elem = soup.select_one('div.category')
        if category_elem:
            project["category"] = category_elem.text.strip()
        
        # 获取描述
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
        
        # 确保有描述字段
        if "description" not in project:
            project["description"] = project["title"]
            project["summary"] = project["title"]
        
        # 设置时间字段
        current_time = datetime.now().isoformat()
        project["created_at"] = current_time
        project["updated_at"] = current_time
        
        return project
    
    def _parse_project_list(self, html, project_type, db=None):
        """从HTML中解析项目列表"""
        processed_urls = set()  # 用于记录已处理的URL
        processed_count = 0  # 处理计数
        page = 1
        max_pages = 100  # 设置一个合理的最大页数限制
        
        while page <= max_pages:
            logging.info(f"正在处理第 {page} 页...")
            
            # 构造分页URL
            page_url = f"{self.base_url}/{project_type}s"
            if page > 1:
                page_url += f"?page={page}"
            
            # 获取页面内容
            if page == 1:
                current_html = html  # 使用已经获取的第一页内容
            else:
                current_html = self.get_page(page_url)
                if not current_html:
                    logging.error(f"获取第 {page} 页失败")
                    break
            
            soup = BeautifulSoup(current_html, 'html.parser')
            
            # 查找当前页面的所有项目链接
            project_links = []
            all_links = soup.find_all('a')
            
            for link in all_links:
                href = link.get('href', '')
                if f"/{project_type}/" in href:
                    project_links.append(href)
            
            if not project_links:
                logging.info(f"第 {page} 页没有找到项目链接，可能已经到达最后一页")
                break
            
            logging.info(f"第 {page} 页找到 {len(project_links)} 个{project_type}项目链接")
            
            # 访问每个项目的详情页面
            for link in project_links:
                full_url = self._ensure_absolute_url(link)
                
                # 检查是否已经处理过这个URL
                if full_url in processed_urls:
                    continue
                
                processed_urls.add(full_url)
                
                detail_html = self.get_page(full_url)
                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, 'html.parser')
                    project = self._parse_project_detail(detail_soup, project_type)
                    if project:
                        processed_count += 1
                        if db:
                            try:
                                # 尝试导入到数据库
                                db.add_project(project)
                                inserted, updated, failed = db.import_to_supabase()
                                status = "更新" if updated > 0 else "新增" if inserted > 0 else "失败"
                                logging.info(f"项目 {project.get('name', 'unnamed')} {status}成功 (总计处理: {processed_count})")
                            except Exception as e:
                                logging.error(f"导入项目 {project.get('name', 'unnamed')} 失败: {str(e)}")
                        else:
                            logging.info(f"已处理项目 {project.get('name', 'unnamed')} (总计: {processed_count})")
                
                # 添加延迟避免请求过于频繁
                time.sleep(1.5)
            
            # 检查是否有下一页
            pagination = soup.select('button[aria-label="Next"]')
            if not pagination:
                logging.info("没有找到分页按钮，已到达最后一页")
                break
            
            page += 1
            
            # 每处理完一页添加一个较长的延迟
            time.sleep(3)
        
        logging.info(f"共处理 {processed_count} 个{project_type}项目")
        return processed_count
    
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