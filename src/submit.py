import asyncio
from flask import Flask
from submitMcpServer import submitServer
from submitMcpClient import submitClient

app = Flask(__name__)

@app.route('/submitClient', methods=['GET'])
def submit_client_handler():
    # 显式地创建事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(submitClient())  # 执行客户端任务
    except Exception as e:
        return f"Error in submitClient: {str(e)}", 500

    return "Client task completed"

@app.route('/submitServer', methods=['GET'])
def submit_server_handler():
    # 显式地创建事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(submitServer())  # 执行服务器任务
    except Exception as e:
        return f"Error in submitServer: {str(e)}", 500

    return "Server task completed"

if __name__ == '__main__':
    app.run(debug=True)
