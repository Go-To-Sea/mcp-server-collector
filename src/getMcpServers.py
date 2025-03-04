import requests
import os
import time
import datetime
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # GitHub 访问令牌

# 获取当前年月
current_year = datetime.datetime.now().year
current_month = datetime.datetime.now().month

# 设置查询的年份范围（最近 10 年）
START_YEAR = current_year - 10  # 10 年前
END_YEAR = current_year         # 当前年


def get_mcp_servers():
    all_results = []
    headers = {"Accept": "application/vnd.github.v3+json"}

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    # 遍历每年每月
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            if year == END_YEAR and month > current_month:  # 只查询到当前月份
                break

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
                url = f"https://api.github.com/search/repositories?q=MCP+server+created:{start_date}..{end_date}&per_page=100&page={page}"
                response = requests.get(url, headers=headers)

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
                    repo_data = {
                        "name": repo["name"],
                        "title": repo["name"].replace("-", " ").title(),
                        "description": repo["description"] if repo["description"] else "",
                        "url": repo["html_url"],
                        "author_name": repo["owner"]["login"],
                        "author_avatar_url": repo["owner"]["avatar_url"],
                        "type": "server"
                    }
                    if repo_data not in all_results:
                        all_results.append(repo_data)

                if len(repositories) < 100:  # 如果当前页数据少于 100 条，说明已经取完了
                    break

                page += 1
                if page > 10:  # GitHub API 限制每个查询最多 1000 条（10 页）
                    print(f"⚠️ {start_date} ~ {end_date} 达到 1000 条限制，停止查询")
                    break

    return all_results


# 运行
if __name__ == "__main__":
    mcp_servers = get_mcp_servers()
    print(f"✅ 共获取 {len(mcp_servers)} 条数据")
