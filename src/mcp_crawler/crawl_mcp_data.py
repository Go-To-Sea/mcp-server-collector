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
    db = None if args.no_import else MCPDatabase()
    
    total_processed = 0
    
    # 抓取服务器数据
    if not args.client_only:
        logging.info("开始抓取MCP Server数据")
        server_count = crawler.get_server_list(db)
        logging.info(f"完成抓取 {server_count} 个MCP Server")
        total_processed += server_count
    
    # 抓取客户端数据
    if not args.server_only:
        logging.info("开始抓取MCP Client数据")
        client_count = crawler.get_client_list(db)
        logging.info(f"完成抓取 {client_count} 个MCP Client")
        total_processed += client_count
    
    logging.info(f"数据抓取完成，共处理 {total_processed} 个项目")
    
    # 如果指定了导出SQL文件，则生成SQL
    if args.export_sql and db:
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