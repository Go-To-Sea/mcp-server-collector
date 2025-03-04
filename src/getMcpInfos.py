import requests
import os
import time
import datetime
import uuid
import re
import random
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub 访问令牌
USE_PROXY = False  # 是否使用代理
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))  # 请求超时时间(秒)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))  # 最大重试次数

# 获取当前年月
current_year = datetime.datetime.now().year
current_month = datetime.datetime.now().month

# 设置查询的年份范围（最近 10 年）
START_YEAR = current_year - 10  # 10 年前
END_YEAR = current_year         # 当前年


def request_with_retry(url, headers, proxies=None, max_retries=MAX_RETRIES, timeout=REQUEST_TIMEOUT):
    """带重试机制的请求函数"""
    for attempt in range(max_retries):
        try:
            # 添加轻微随机延迟避免请求过于集中
            if attempt > 0:
                delay = random.uniform(1, 3) * attempt
                print(f"⏳ 等待 {delay:.2f} 秒后进行第 {attempt+1} 次重试...")
                time.sleep(delay)
                
            kwargs = {
                "headers": headers,
                "timeout": timeout
            }
            if proxies:
                kwargs["proxies"] = proxies
                
            response = requests.get(url, **kwargs)
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"⚠️ 连接超时或错误 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                print(f"❌ 达到最大重试次数，放弃请求: {url}")
                raise
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            raise
    
    return None


def get_readme_content(repo_full_name):
    """获取仓库的README内容"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    
    # 设置代理
    proxies = None
    if not USE_PROXY:
        proxies = {"http": None, "https": None}  # 禁用代理
    
    # 尝试获取不同格式的README文件
    readme_formats = ['README.md', 'README', 'readme.md', 'Readme.md']
    for readme_format in readme_formats:
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{readme_format}"
        try:
            response = request_with_retry(url, headers, proxies)
            
            if response and response.status_code == 200:
                data = response.json()
                if 'content' in data and data.get('encoding') == 'base64':
                    import base64
                    content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
                    return content
        except Exception as e:
            print(f"❌ 获取 {repo_full_name} 的 {readme_format} 时出错: {e}")
            continue
    
    return ""  # 如果没有找到README，返回空字符串


def extract_tags_from_text(type, text):
    """从文本中提取关键词作为标签"""
    if not text:
        return []
    
    # 常见的 Minecraft 服务器相关关键词
    keywords = [
        "minecraft", type, "plugin", "mod", "mcp", "forge", "spigot",
        "bukkit", "paper", "velocity", "proxy", "bungee", "waterfall", 
        "fabric", "multiplayer", "smp", "gamemode", "survival", "creative",
        "pvp", "pve", "economy", "permissions", "anti-cheat", "modpack"
    ]
    
    tags = []
    text_lower = text.lower()
    
    for keyword in keywords:
        if keyword in text_lower:
            tags.append(keyword)
    
    return tags


def get_mcp(type):
    all_results = []
    headers = {"Accept": "application/vnd.github.v3+json"}

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    
    # 设置代理
    proxies = None
    if not USE_PROXY:
        proxies = {"http": None, "https": None}  # 禁用代理

    # 倒序遍历每年每月（从最近的时间开始）
    for year in range(END_YEAR, START_YEAR - 1, -1):
        # 确定月份范围
        month_start = 1
        month_end = 12
        
        # 如果是当前年份，则只查询到当前月份
        if year == END_YEAR:
            month_end = current_month
            
        # 倒序遍历月份
        for month in range(month_end, month_start - 1, -1):
            # 计算时间范围（按月）
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"

            print(f"🔍 查询 {start_date} 至 {end_date} 的数据...")

            page = 1
            while True:
                # 构造 GitHub API 查询 URL
                url = f"https://api.github.com/search/repositories?q=MCP+{type}+created:{start_date}..{end_date}&per_page=100&page={page}"
                try:
                    response = request_with_retry(url, headers, proxies)
                    
                    # 如果请求失败则跳过
                    if not response:
                        print(f"⚠️ 无法获取仓库列表，跳过时间段: {start_date} 至 {end_date}")
                        break
                        
                except Exception as e:
                    print(f"❌ 请求仓库列表失败: {e}")
                    # 等待一段时间后再尝试其他月份
                    time.sleep(5)
                    break

                # 处理速率限制
                if response.status_code == 403:
                    retry_after = int(response.headers.get("X-RateLimit-Reset", time.time() + 60)) - int(time.time())
                    print(f"⚠️ 速率限制！等待 {retry_after} 秒后继续...")
                    time.sleep(retry_after)
                    continue

                elif response.status_code == 401:
                    print("❌ GitHub 认证失败，请检查 Token 是否正确。")
                    return all_results

                elif response.status_code != 200:
                    print(f"❌ 请求 GitHub 数据失败，错误代码：{response.status_code}")
                    break

                data = response.json()
                repositories = data.get("items", [])

                if not repositories:
                    print(f"✅ {start_date} ~ {end_date} 的数据获取完毕！")
                    break  # 结束当前月份查询

                # 存储数据
                for repo in repositories:
                    try:
                        # 获取README内容
                        readme_content = get_readme_content(repo["full_name"])
                        
                        # 初始化仓库数据
                        repo_data = {
                            "uuid": str(uuid.uuid4()),  # 生成唯一UUID
                            "name": repo["name"],
                            "title": repo["name"].replace("-", " ").title(),
                            "url": repo["html_url"],
                            "author_name": repo["owner"]["login"],
                            "author_avatar_url": repo["owner"]["avatar_url"],
                            "avatar_url": repo["owner"]["avatar_url"],  # 使用作者头像作为项目头像
                            "type": type,
                            "created_at": repo["created_at"],
                            "updated_at": repo["updated_at"],
                            "status": "created",  # 默认状态
                            "category": "",  # 默认类别
                            "is_featured": True,  # 默认非特色
                            "sort": 0,  # 默认排序
                            "target": "_self",  # 默认目标
                            "content": readme_content,  # README内容
                            "img_url": ""  # 默认无图片URL
                        }
                        
                        # 仅当有描述时添加描述字段
                        if repo["description"]:
                            repo_data["description"] = repo["description"]
                        
                        # 生成简短摘要 - 只有在有内容时才设置
                        if repo["description"]:
                            repo_data["summary"] = repo["description"]
                        
                        # 动态获取标签
                        tags = []
                        
                        # 1. 从仓库主题获取标签
                        if "topics" in repo and repo["topics"]:
                            tags.extend(repo["topics"])
                        
                        # 2. 从描述和README中提取关键词作为标签
                        tags.extend(extract_tags_from_text(type, repo["description"]))
                        tags.extend(extract_tags_from_text(type, readme_content))
                        
                        # 确保至少有基本标签
                        if not tags:
                            tags = ["MCP", type]
                        
                        # 移除重复项，保留唯一标签
                        tags = list(set(tags))
                        
                        # 将标签列表转换为逗号分隔的字符串
                        repo_data["tags"] = ",".join(tags)
                        
                        # 尝试从README中提取图片URL
                        img_matches = re.findall(r'!\[.*?\]\((https?://\S+)\)', readme_content)
                        if img_matches:
                            repo_data["img_url"] = img_matches[0]  # 使用第一个找到的图片URL
                        
                        if repo_data not in all_results:
                            if repo_data['content'] != '':
                                print("111")
                            all_results.append(repo_data)
                            
                    except Exception as e:
                        print(f"❌ 处理仓库 {repo['full_name']} 时出错: {e}")
                        continue
                
                # 等待一小段时间避免触发GitHub的速率限制
                time.sleep(random.uniform(0.5, 1.5))

                if len(repositories) < 100:  # 如果当前页数据少于 100 条，说明已经取完了
                    break

                page += 1
                if page > 10:  # GitHub API 限制每个查询最多 1000 条（10 页）
                    print(f"⚠️ {start_date} ~ {end_date} 达到 1000 条限制，停止查询")
                    break

    return all_results


# 运行
if __name__ == "__main__":
    mcp_servers = get_mcp_servers('client')
    print(f"✅ 共获取 {len(mcp_servers)} 条数据")
