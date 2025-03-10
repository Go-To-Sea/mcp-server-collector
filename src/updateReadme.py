import base64
import os

import markdown
import requests
import time
from supabase import create_client, Client

# Supabase 配置
SUPABASE_URL = "https://stfkxmxxxvrprkozmywi.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0Zmt4bXh4eHZycHJrb3pteXdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA0OTUwMTksImV4cCI6MjA1NjA3MTAxOX0.c_Sz6sHuPteG9-yIAWFg8x5bwOWGWcoWfbco2n4LK9Y"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub 访问令牌
# 创建 Supabase 客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# 从 Supabase 获取 Projects 表中的 URL
def fetch_github_urls():
    urls = []
    page = 0
    limit = 100  # 每次请求的条目数

    while True:
        # 请求数据，并设置分页参数
        response = supabase.table('projects').select('url').range(page * limit, (page + 1) * limit - 1).execute()

        # 获取数据
        data = response.data

        # 如果返回的数据为空，退出循环
        if not data:
            break

        # 添加当前页的数据
        urls.extend([record['url'] for record in data])

        # 如果返回的数据少于 limit，说明已经是最后一页
        if len(data) < limit:
            break

        # 否则，继续请求下一页
        page += 1

    return urls



# 爬取 GitHub 页面并提取 README 内容（使用公共 API）
def fetch_readme_from_github(url):
    try:
        # 从 URL 中获取 owner 和 repo_name
        owner, repo_name = url.split('/')[-2], url.split('/')[-1]

        # 构建 API 请求 URL
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"

        # 设置认证头
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        }

        # 发送请求获取 README 文件
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            # GitHub 返回的内容是 base64 编码的，需要解码
            readme_content = response.json().get('content')
            # 解码并返回
            return readme_content
        else:
            print(f"无法获取 README 文件: {response.status_code} for {url}")
            return None
    except Exception as e:
        print(f"无法获取 README 文件: {e}")
        return None

# 更新 Supabase 中的 Content 字段
def update_readme_content(url, content):
    response = supabase.table('projects').update({'content': content}).eq('url', url).execute()

def main():
    # 获取所有 GitHub URL
    github_urls = fetch_github_urls()

    print(f'共计：{len(github_urls)}')

    i = 1
    for url in github_urls:
        try:
            # 爬取 README 内容
            readme_content = fetch_readme_from_github(url)
            if readme_content:
                # 解码 Base64 字符串
                decoded_bytes = base64.b64decode(readme_content)
                decoded_str = decoded_bytes.decode('utf-8')
                print(f"正在处理 URL: {url}")

                # 使用 markdown 库将 Markdown 转换为 HTML
                html_content = markdown.markdown(decoded_str)

                # 更新到 Supabase 的 Content 字段
                print(f"开始更新第 {i} 条数据: {url}")
                update_readme_content(url, html_content)
                print(f"第 {i} 条数据更新完成: {url}")

            # 你可以设置一个小的延迟，防止请求过于频繁
            time.sleep(1)  # 延迟 1 秒
            i += 1
        except Exception as e:
            print(f"处理 {url} 时发生错误: {e}")

if __name__ == "__main__":
    main()
