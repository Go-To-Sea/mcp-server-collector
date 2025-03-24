import asyncio
import json

import aiohttp
import requests
from bs4 import BeautifulSoup

# 目标网站 URL
BASE_URL = 'https://mcp.so/clients'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}
QUERY_URL = "http://localhost:3000/api/get-project"
SUBMIT_URL = "http://localhost:3000/api/submit"


# 获取页面内容
def get_page(url):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.text


# 获取最大页码
def get_max_page_number(url):
    # 获取网页内容
    page_content = get_page(url)

    # 解析 HTML
    soup = BeautifulSoup(page_content, 'html.parser')

    # 查找分页部分
    pagination = soup.find('nav', {'aria-label': 'pagination'})

    # 查找所有的页面链接
    page_links = pagination.find_all('a', class_='inline-flex')

    # 提取最后一页的页码
    last_page = page_links[-2].text.strip()  # 倒数第二个链接通常是最大页码
    return int(last_page)


# 获取服务器页面的所有 GitHub 链接
def get_github_links(page_number):
    url = f'{BASE_URL}?page={page_number}'
    page_content = get_page(url)
    soup = BeautifulSoup(page_content, 'html.parser')

    # 查找所有 GitHub 链接
    github_links = []
    servers = soup.find_all('a', href=True)

    for server in servers:
        # 查找包含 GitHub 链接的部分
        if "github.com" in server.get('href'):
            github_links.append(server['href'])

    return github_links
async def submit_mcp(session, mcp_server):
    """
    异步提交 MCP 服务器数据到指定的 API 端点。
    """
    url = SUBMIT_URL

    try:
        async with session.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(mcp_server)
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"提交成功: {result}")
                return result
            else:
                print(f"提交失败: HTTP {response.status}, 数据: {mcp_server}")
                return None
    except Exception as e:
        print(f"提交失败: {str(e)}")
        return None

# 主函数，获取所有页面的 GitHub 链接
async def main(type):
    # 获取最大页数
    max_page = get_max_page_number(BASE_URL)
    #max_page = 1
    print(f"最大页数是: {max_page}")

    # 遍历所有页面并抓取 GitHub 链接
    all_github_links = []
    for page in range(1, max_page + 1):
        print(f"正在抓取第 {page} 页的 GitHub 链接...")
        github_links = get_github_links(page)
        all_github_links.extend(github_links)

    # 输出所有抓取到的 GitHub 链接
    print(f"共抓取到 {len(all_github_links)} 个 GitHub 链接：")
    async with aiohttp.ClientSession() as session:
        for link in all_github_links:
            result = await submit_mcp(session, {'url' : link,'type':type})
            print(f"服务器 查询结果: {result}")


# 运行主函数
if __name__ == '__main__':
    asyncio.run(main('client'))  # 运行异步任务
