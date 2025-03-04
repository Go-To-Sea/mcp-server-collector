# 安装必要的依赖
pip install supabase

# 爬取数据并直接导入数据库
cd src/mcp_crawler
python crawl_mcp_data.py

# 只爬取服务器数据
python crawl_mcp_data.py --server-only

# 只爬取客户端数据
python crawl_mcp_data.py --client-only

# 同时导入数据库并导出SQL文件（可选）
python crawl_mcp_data.py --export-sql mcp_data.sql

# 只生成SQL文件，不导入数据库
python crawl_mcp_data.py --no-import --export-sql mcp_data.sql