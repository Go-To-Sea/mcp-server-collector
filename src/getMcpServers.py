import requests
import os
import time
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # 读取 GitHub Token


def get_mcp_servers():
    url = "https://api.github.com/search/repositories?q=MCP+server+in:name&per_page=100"

    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    all_results = []  # 存储所有结果
    page = 1  # 当前页数
    max_pages = 16  # GitHub 限制最多 1600 条
    retry_after = 60  # 默认等待时间（秒）

    while True:
        print(f"🔍 获取第 {page} 页数据...")
        response = requests.get(f"{url}&page={page}", headers=headers)

        # 处理速率限制
        if response.status_code == 403:
            rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", time.time() + retry_after))
            wait_time = max(rate_limit_reset - int(time.time()), retry_after)
            print(f"⚠️ 速率限制！等待 {wait_time} 秒后继续...")
            time.sleep(wait_time)
            continue  # 重新请求

        # 处理认证失败
        elif response.status_code == 401:
            print("❌ GitHub 认证失败，请检查 Token 是否正确。")
            break

        # 其他错误
        elif response.status_code != 200:
            print(f"❌ 请求 GitHub 数据失败，错误代码：{response.status_code}")
            break

        # 解析数据
        data = response.json()
        repositories = data.get("items", [])

        if not repositories:
            print("✅ 所有数据获取完毕！")
            break

        # 存储数据
        all_results.extend([
            {
                "name": repo["name"],
                "title": repo["name"].replace("-", " ").title(),
                "description": repo["description"] if repo["description"] else "暂无描述",
                "url": repo["html_url"],
                "author_name": repo["owner"]["login"],
                "author_avatar_url": repo["owner"]["avatar_url"]
            }
            for repo in repositories
        ])

        # 判断是否获取完所有数据
        if len(all_results) >= data["total_count"]:
            break
        if page >= max_pages:  # 避免 GitHub 1600 条限制
            print("⚠️ 已达到 GitHub API 限制（最多 1600 条数据）")
            break

        page += 1  # 继续下一页

    return all_results


# 运行
if __name__ == "__main__":
    mcp_servers = get_mcp_servers()
    print(f"✅ 共获取 {len(mcp_servers)} 条数据")
