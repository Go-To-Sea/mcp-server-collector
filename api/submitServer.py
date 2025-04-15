from http.server import BaseHTTPRequestHandler
import asyncio
import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入submitServer函数
from src.submitMcpServer import submitServer

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 设置响应头
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        # 初始化loop变量为None
        loop = None
        # 创建新的事件循环并执行submitServer
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(submitServer())
            self.wfile.write('Server task completed successfully'.encode())
        except Exception as e:
            self.wfile.write(f'Error in submitServer: {str(e)}'.encode())
        finally:
            if loop:  # 检查loop是否已定义和绑定
                loop.close()
        
        return