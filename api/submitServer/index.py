from flask import Flask
from src.submitMcpServer import submitServer

app = Flask(__name__)

@app.route('/submit/server', methods=['GET', 'POST'])
async def handler():
    result = await submitServer()
    return "Server Task Executed", 200

# Vercel要求必须导出名为'app'的WSGI实例
if __name__ == '__main__':
    app.run()
else:
    # 用于Vercel的Serverless环境
    pass