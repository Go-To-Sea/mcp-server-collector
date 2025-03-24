# check_and_insert_github_url.py
from src.so.supabase import get_supabase_client

def check_and_insert_github_url(github_url: str):
    supabase = get_supabase_client()

    # 查询 `projects` 表中的 `url` 字段
    response = supabase.table('projects').select('url').eq('url', github_url).execute()

    # 如果存在返回
    if response.data:
        print(f'URL 已存在: {github_url}')
        return

    print(f'URL 不存在: {github_url}')

    # 如果 URL 不存在，插入新的记录
    # try:
    #     insert_response = supabase.table('projects').insert({'url': github_url}).execute()
    #     if insert_response.data:
    #         print(f'成功插入新的 URL: {github_url}')
    #     else:
    #         print(f'插入失败: {insert_response.error}')
    # except Exception as e:
    #     print(f'插入过程中发生错误: {str(e)}')
