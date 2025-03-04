import logging
import time
from supabase import create_client

# Supabase 配置
SUPABASE_URL = "https://stfkxmxxxvrprkozmywi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0Zmt4bXh4eHZycHJrb3pteXdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA0OTUwMTksImV4cCI6MjA1NjA3MTAxOX0.c_Sz6sHuPteG9-yIAWFg8x5bwOWGWcoWfbco2n4LK9Y"

class MCPDatabase:
    def __init__(self):
        self.projects = []
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def add_project(self, project):
        """添加项目到数据库"""
        self.projects.append(project)
    
    def clean_data_for_supabase(self, data_item):
        """清理数据项，确保符合 Supabase 表结构要求"""
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
    
    def record_exists(self, record, table_name="projects"):
        """检查记录是否已存在于数据库中"""
        if "uuid" in record and record["uuid"]:
            response = self.supabase.table(table_name).select("id").eq("uuid", record["uuid"]).execute()
            if hasattr(response, 'data') and response.data:
                return True, response.data[0]["id"] if response.data else None
        
        if "name" in record and record["name"] and "type" in record and record["type"]:
            response = self.supabase.table(table_name).select("id").eq("name", record["name"]).eq("type", record["type"]).execute()
            if hasattr(response, 'data') and response.data:
                return True, response.data[0]["id"] if response.data else None
        
        if "url" in record and record["url"]:
            response = self.supabase.table(table_name).select("id").eq("url", record["url"]).execute()
            if hasattr(response, 'data') and response.data:
                return True, response.data[0]["id"] if response.data else None
        
        return False, None
    
    def import_to_supabase(self, table_name="projects"):
        """将收集的项目导入 Supabase 数据库"""
        total = len(self.projects)
        inserted = 0
        updated = 0
        failed = 0
        
        logging.info(f"开始导入 {total} 条项目数据到 Supabase...")
        
        # 逐条处理项目
        for i, project in enumerate(self.projects):
            logging.info(f"处理项目 {i+1}/{total}: {project.get('name', 'unnamed')}")
            
            try:
                # 清理数据
                clean_project = self.clean_data_for_supabase(project)
                
                # 检查记录是否已存在
                exists, record_id = self.record_exists(clean_project, table_name)
                
                if exists:
                    # 如果记录存在，则更新
                    logging.info(f"记录已存在，进行更新: {clean_project.get('name')}")
                    response = self.supabase.table(table_name).update(clean_project).eq("id", record_id).execute()
                    if hasattr(response, 'data') and response.data:
                        updated += 1
                        logging.info(f"成功更新记录: {clean_project.get('name')}")
                    else:
                        failed += 1
                        logging.error(f"更新记录失败: {clean_project.get('name')}")
                else:
                    # 如果记录不存在，则插入
                    logging.info(f"记录不存在，进行插入: {clean_project.get('name')}")
                    response = self.supabase.table(table_name).insert(clean_project).execute()
                    if hasattr(response, 'data') and response.data:
                        inserted += 1
                        logging.info(f"成功插入记录: {clean_project.get('name')}")
                    else:
                        failed += 1
                        logging.error(f"插入记录失败: {clean_project.get('name')}")
                
                # 短暂延迟，避免请求过于频繁
                time.sleep(0.5)
                
            except Exception as e:
                failed += 1
                logging.error(f"处理数据时出错 ({project.get('name', 'unnamed')}): {str(e)[:200]}...")
                # 出错后增加延迟，防止连续请求失败
                time.sleep(2)
        
        logging.info(f"数据导入完成: 新插入 {inserted} 条，更新 {updated} 条，失败 {failed} 条")
        return inserted, updated, failed 