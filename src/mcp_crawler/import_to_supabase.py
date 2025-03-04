import argparse
import logging
import time

from supabase import create_client

from crawler import MCPCrawler

# Supabase 配置
SUPABASE_URL = "https://stfkxmxxxvrprkozmywi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0Zmt4bXh4eHZycHJrb3pteXdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA0OTUwMTksImV4cCI6MjA1NjA3MTAxOX0.c_Sz6sHuPteG9-yIAWFg8x5bwOWGWcoWfbco2n4LK9Y"

def clean_data_for_supabase(data_item):
    """
    清理数据项，确保符合 Supabase 表结构要求
    """
    # 确保 content 字段不会太长，Supabase可能有大小限制
    if "content" in data_item and data_item["content"] and len(data_item["content"]) > 1000000:
        data_item["content"] = data_item["content"][:1000000] + "... (截断)"
    
    # 确保所有必需字段都存在
    required_fields = ["uuid", "name", "title", "type"]
    for field in required_fields:
        if field not in data_item or not data_item[field]:
            if field == "uuid":
                import uuid
                data_item[field] = str(uuid.uuid4())
            elif field in ["name", "title"]:
                data_item[field] = f"unnamed-{time.time()}"
            elif field == "type":
                data_item[field] = "unknown"
    
    return data_item

def record_exists(supabase_client, table_name, record):
    """
    检查记录是否已存在于数据库中
    优先使用 uuid 检查，其次使用 name 和 type 组合检查
    """
    if "uuid" in record and record["uuid"]:
        response = supabase_client.table(table_name).select("id").eq("uuid", record["uuid"]).execute()
        if hasattr(response, 'data') and response.data:
            return True, response.data[0]["id"] if response.data else None
    
    if "name" in record and record["name"] and "type" in record and record["type"]:
        response = supabase_client.table(table_name).select("id").eq("name", record["name"]).eq("type", record["type"]).execute()
        if hasattr(response, 'data') and response.data:
            return True, response.data[0]["id"] if response.data else None
    
    if "url" in record and record["url"]:
        response = supabase_client.table(table_name).select("id").eq("url", record["url"]).execute()
        if hasattr(response, 'data') and response.data:
            return True, response.data[0]["id"] if response.data else None
    
    return False, None

def upsert_data_to_supabase(data_list, supabase_client, table_name="projects"):
    """
    将数据更新或插入 Supabase 数据库，先检查记录是否存在
    """
    total = len(data_list)
    inserted = 0
    updated = 0
    failed = 0
    
    # 逐条处理，因为需要先查询是否存在
    for i, item in enumerate(data_list):
        logging.info(f"处理记录 {i+1}/{total}: {item.get('name', 'unnamed')}")
        
        try:
            # 清洗数据
            clean_item = clean_data_for_supabase(item)
            
            # 检查记录是否已存在
            exists, record_id = record_exists(supabase_client, table_name, clean_item)
            
            if exists:
                # 如果记录存在，则更新
                logging.info(f"记录已存在，进行更新: {clean_item.get('name')}")
                response = supabase_client.table(table_name).update(clean_item).eq("id", record_id).execute()
                if hasattr(response, 'data') and response.data:
                    updated += 1
                    logging.info(f"成功更新记录: {clean_item.get('name')}")
                else:
                    failed += 1
                    logging.error(f"更新记录失败: {clean_item.get('name')}")
            else:
                # 如果记录不存在，则插入
                logging.info(f"记录不存在，进行插入: {clean_item.get('name')}")
                response = supabase_client.table(table_name).insert(clean_item).execute()
                if hasattr(response, 'data') and response.data:
                    inserted += 1
                    logging.info(f"成功插入记录: {clean_item.get('name')}")
                else:
                    failed += 1
                    logging.error(f"插入记录失败: {clean_item.get('name')}")
            
            # 短暂延迟，避免请求过于频繁
            time.sleep(0.5)
                
        except Exception as e:
            failed += 1
            logging.error(f"处理数据时出错 ({item.get('name', 'unnamed')}): {str(e)[:200]}...")
            # 出错后增加延迟，防止连续请求失败
            time.sleep(2)
    
    return inserted, updated, failed

def main():
    parser = argparse.ArgumentParser(description='将MCP.SO网站数据爬取并导入Supabase')
    parser.add_argument('--server-only', action='store_true', help='只处理Server数据')
    parser.add_argument('--client-only', action='store_true', help='只处理Client数据')
    parser.add_argument('--base-url', default='https://mcp.so', help='MCP.SO网站基础URL')
    args = parser.parse_args()
    
    # 初始化爬虫和Supabase客户端
    crawler = MCPCrawler(base_url=args.base_url)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    total_inserted = 0
    total_updated = 0
    total_failed = 0
    
    # 处理服务器数据
    if not args.client_only:
        logging.info("开始爬取MCP Server数据...")
        servers = crawler.get_server_list()
        logging.info(f"爬取到 {len(servers)} 个MCP Server数据")
        
        if servers:
            logging.info("开始导入MCP Server数据到Supabase...")
            inserted, updated, failed = upsert_data_to_supabase(servers, supabase)
            logging.info(f"服务器数据导入完成: 新插入 {inserted} 条，更新 {updated} 条，失败 {failed} 条")
            total_inserted += inserted
            total_updated += updated
            total_failed += failed
    
    # 处理客户端数据
    if not args.server_only:
        logging.info("开始爬取MCP Client数据...")
        clients = crawler.get_client_list()
        logging.info(f"爬取到 {len(clients)} 个MCP Client数据")
        
        if clients:
            logging.info("开始导入MCP Client数据到Supabase...")
            inserted, updated, failed = upsert_data_to_supabase(clients, supabase)
            logging.info(f"客户端数据导入完成: 新插入 {inserted} 条，更新 {updated} 条，失败 {failed} 条")
            total_inserted += inserted
            total_updated += updated
            total_failed += failed
    
    logging.info(f"所有数据导入完成: 新插入 {total_inserted} 条，更新 {total_updated} 条，失败 {total_failed} 条")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main() 