import asyncio

import aiohttp
from dotenv import load_dotenv

from src.getMcpInfos import get_mcp
from src.getMcpInfos import submit_mcp

# 加载环境变量
load_dotenv()
async def submitServer():
    """
    获取 MCP 服务器数据，并按顺序逐个提交到 API。
    """
    mcp_servers = get_mcp("server")  # 获取 MCP 服务器列表

    if not mcp_servers:
        print("未找到 MCP 服务器，任务终止。")
        return

    async with aiohttp.ClientSession() as session:
        for server in mcp_servers:
            result = await submit_mcp(session, {'url': server, 'type': 'server'})
            print(f"提交结果: {result}")

if __name__ == "__main__":
    asyncio.run(submitServer())  # 运行异步任务
