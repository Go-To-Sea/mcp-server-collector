import logging
import argparse
from crawler import MCPCrawler
from db import MCPDatabase

def main():
    parser = argparse.ArgumentParser(description='MCP.SO网站爬虫')
    parser.add_argument('--server-only', action='store_true', help='只抓取Server数据')
    parser.add_argument('--client-only', action='store_true', help='只抓取Client数据')
    parser.add_argument('--export-sql', help='导出SQL到文件（可选）')
    parser.add_argument('--no-import', action='store_true', help='不导入到数据库，只生成SQL')
    args = parser.parse_args()

    logging.info("开始抓取MCP.SO网站数据")
    
    crawler = MCPCrawler()
    db = MCPDatabase()
    
    # 抓取服务器数据
    if not args.client_only:
        logging.info("开始抓取MCP Server数据")
        servers = crawler.get_server_list()
        logging.info(f"共抓取 {len(servers)} 个MCP Server")
        for server in servers:
            db.add_project(server)
    
    # 抓取客户端数据
    if not args.server_only:
        logging.info("开始抓取MCP Client数据")
        clients = crawler.get_client_list()
        logging.info(f"共抓取 {len(clients)} 个MCP Client")
        for client in clients:
            db.add_project(client)
    
    # 导入数据到数据库
    if not args.no_import:
        logging.info("正在将数据导入到Supabase...")
        inserted, updated, failed = db.import_to_supabase()
        logging.info(f"数据导入完成: 新插入 {inserted} 条，更新 {updated} 条，失败 {failed} 条")
    
    # 如果指定了导出SQL文件，则同时生成SQL
    if args.export_sql:
        logging.info(f"正在生成SQL文件: {args.export_sql}")
        try:
            with open(args.export_sql, 'w', encoding='utf-8') as f:
                sql_statements = []
                for project in db.projects:
                    columns = []
                    values = []
                    
                    for key, value in project.items():
                        if value is not None:
                            columns.append(key)
                            if isinstance(value, bool):
                                values.append(str(value).lower())
                            elif isinstance(value, (int, float)):
                                values.append(str(value))
                            else:
                                values.append(f"'{value.replace('\'', '\'\'')}'" if isinstance(value, str) else f"'{value}'")
                    
                    columns_str = ", ".join(columns)
                    values_str = ", ".join(values)
                    
                    sql = f"INSERT INTO projects ({columns_str}) VALUES ({values_str});"
                    sql_statements.append(sql)
                
                f.write("\n".join(sql_statements))
            logging.info(f"SQL已保存到文件: {args.export_sql}")
        except Exception as e:
            logging.error(f"保存SQL文件失败: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main() 