import os
import argparse
import logging
from supabase import create_client

# Supabase 配置
SUPABASE_URL = "https://stfkxmxxxvrprkozmywi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0Zmt4bXh4eHZycHJrb3pteXdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA0OTUwMTksImV4cCI6MjA1NjA3MTAxOX0.c_Sz6sHuPteG9-yIAWFg8x5bwOWGWcoWfbco2n4LK9Y"

def execute_sql_file(filename, supabase_client):
    """执行SQL文件中的查询"""
    
    try:
        # 读取SQL文件
        with open(filename, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 拆分SQL语句（假设每个语句以分号结束）
        statements = sql_content.split(';')
        total = len(statements)
        success = 0
        failed = 0
        
        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement:  # 跳过空语句
                continue
                
            try:
                logging.info(f"执行第 {i+1}/{total} 条SQL语句")
                # 执行SQL语句
                response = supabase_client.rpc('exec_sql', {'sql_query': statement}).execute()
                success += 1
            except Exception as e:
                failed += 1
                logging.error(f"执行SQL语句失败: {e}")
                
        logging.info(f"SQL执行完成: 成功 {success} 条，失败 {failed} 条")
        return success, failed
            
    except Exception as e:
        logging.error(f"读取或执行SQL文件失败: {e}")
        return 0, 0

def main():
    parser = argparse.ArgumentParser(description='执行SQL文件并将数据导入Supabase')
    parser.add_argument('--file', required=True, help='SQL文件路径')
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        logging.error(f"SQL文件不存在: {args.file}")
        return
    
    # 初始化Supabase客户端
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logging.info(f"开始执行SQL文件: {args.file}")
    success, failed = execute_sql_file(args.file, supabase)
    
    if success > 0:
        logging.info(f"成功执行 {success} 条SQL语句")
    
    if failed > 0:
        logging.warning(f"失败 {failed} 条SQL语句")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main() 