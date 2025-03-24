from supafunc import create_client

def get_supabase_client():
    SUPABASE_URL = "https://stfkxmxxxvrprkozmywi.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0Zmt4bXh4eHZycHJrb3pteXdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA0OTUwMTksImV4cCI6MjA1NjA3MTAxOX0.c_Sz6sHuPteG9-yIAWFg8x5bwOWGWcoWfbco2n4LK9Y"

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY, is_async=False)  # is_async参数设置为False表示同步
        return client
    except Exception as e:
        raise Exception(f"Failed to create Supabase client: {str(e)}")
