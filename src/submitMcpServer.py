import json
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

from src.getMcpInfos import get_mcp

# 加载环境变量
load_dotenv()

async def submit_mcp_server(session, mcp_server):
    """
    异步提交 MCP 服务器数据到指定的 API 端点。
    """
    url = os.getenv("MCP_SERVER_SUBMIT_URL")  # 获取提交 URL
    if not url:
        print("错误: MCP_SERVER_SUBMIT_URL 环境变量未设置！")
        return None

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

async def main():
    """
    获取 MCP 服务器数据，并按顺序逐个提交到 API。
    """
    mcp_servers = get_mcp("server")  # 获取 MCP 服务器列表

    if not mcp_servers:
        print("未找到 MCP 服务器，任务终止。")
        return

    async with aiohttp.ClientSession() as session:
        for server in mcp_servers:
            result = await submit_mcp_server(session, server)  # 逐个提交
            print(f"服务器 {server} 提交结果: {result}")

if __name__ == "__main__":
    asyncio.run(main())  # 运行异步任务
