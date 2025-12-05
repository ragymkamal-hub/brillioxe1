import os
from supabase import create_client, Client
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")

class Database:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ==================== Users ====================
    def get_user(self, username: str):
        res = self.client.table("users").select("*").eq("username", username).execute()
        if res.data:
            return res.data[0]
        return None

    def add_user(self, data: dict):
        self.client.table("users").insert([data]).execute()

    def delete_user(self, username: str):
        self.client.table("users").delete().eq("username", username).execute()

    def update_user_permissions(self, data: dict):
        username = data.pop("username")
        self.client.table("users").update(data).eq("username", username).execute()

    def get_serper_keys(self):
        # Example: return number of Serper API keys
        return ["key1", "key2", "key3"]

    # ==================== Leads ====================
    def get_leads(self, user_id: str = None):
        query = self.client.table("leads").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        return query.execute().data

    def add_lead(self, lead: dict):
        lead["created_at"] = datetime.now().isoformat()
        self.client.table("leads").insert([lead]).execute()

    # ==================== Campaigns ====================
    def create_campaign(self, name: str, message: str, user_id: str, media):
        campaign_data = {
            "name": name,
            "message": message,
            "user_id": user_id,
            "status": "draft",
            "sent_count": 0,
            "delivered_count": 0,
            "created_at": datetime.now().isoformat()
        }
        res = self.client.table("whatsapp_campaigns").insert([campaign_data]).execute()
        return res.data[0]['id']

    def get_campaigns(self, user_id: str = None):
        query = self.client.table("whatsapp_campaigns").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        return query.execute().data

    def delete_campaign(self, campaign_id: str):
        self.client.table("whatsapp_campaigns").delete().eq("id", campaign_id).execute()

    # ==================== Lead Sharing ====================
    def share_lead(self, data: dict):
        phone = data['phone']
        is_public = data.get('is_public', False)
        shared_with = data.get('shared_with', [])
        user_id = data.get('user_id')

        share_data = {
            "phone": phone,
            "shared_with": shared_with,
            "is_public": is_public,
            "shared_by": user_id,
            "share_date": datetime.now().isoformat()
        }
        self.client.table("lead_shares").insert([share_data]).execute()
        if is_public:
            return f"/public/lead/{phone}"
        return "تم مشاركة العميل داخلياً"

    def get_public_lead(self, phone: str):
        res = self.client.table("leads").select("*").eq("phone_number", phone).execute()
        if res.data:
            lead = res.data[0]
            return {
                "phone_number": lead['phone_number'],
                "full_name": lead['full_name'],
                "quality": lead.get('quality', '')
            }
        return None

    def get_lead_share_status(self, phone: str):
        res = self.client.table("lead_shares").select("*").eq("phone", phone).execute()
        if res.data:
            share = res.data[0]
            return {"status": "مشارك", "date": share['share_date'], "by": share['shared_by']}
        return {"status": "غير مشارك", "date": None, "by": None}

    def cancel_share(self, phone: str, user_id: str):
        self.client.table("lead_shares").delete().eq("phone", phone).eq("shared_by", user_id).execute()

    # ==================== Statistics & Events ====================
    def get_admin_stats(self, user_id: str = None):
        total_users = len(self.client.table("users").select("*").execute().data)
        total_leads = len(self.client.table("leads").select("*").execute().data)
        total_messages = len(self.client.table("campaign_logs").select("*").execute().data)
        return {"total_users": total_users, "total_leads": total_leads, "total_messages": total_messages}

    def get_last_events(self):
        res = self.client.table("events").select("*").order("timestamp", desc=True).limit(20).execute()
        return res.data
