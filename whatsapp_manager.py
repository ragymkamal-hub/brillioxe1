import os
from twilio.rest import Client
from datetime import datetime
from utils import generate_campaign_message, format_phone_display
from database import Database

TWILIO_SID = os.getenv("TWILIO_SID", "your-twilio-sid")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "your-twilio-token")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886")

class WhatsAppManager:
    def __init__(self):
        self.client = Client(TWILIO_SID, TWILIO_TOKEN)
        self.db = Database()

    # ==================== إرسال رسالة فردية ====================
    def send_message(self, phone_number: str, message: str, media_url: str = None, user_id: str = None):
        phone_number = format_phone_display(phone_number)
        try:
            msg = self.client.messages.create(
                body=message,
                from_=f'whatsapp:{TWILIO_WHATSAPP_NUMBER}',
                to=f'whatsapp:{phone_number}',
                media_url=media_url if media_url else None
            )
            # سجل الرسالة في قاعدة البيانات
            if user_id:
                log_data = {
                    "campaign_id": None,
                    "lead_phone": phone_number,
                    "message_sent": message,
                    "status": "sent",
                    "error_message": "",
                    "response_text": str(msg.sid),
                    "created_at": datetime.now().isoformat()
                }
                self.db.client.table("campaign_logs").insert([log_data]).execute()
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== إرسال رسائل جماعية ====================
    def send_bulk(self, leads: list, message_template: str, variables_list: list = None, media_url: str = None, user_id: str = None):
        results = []
        for idx, lead in enumerate(leads):
            variables = variables_list[idx] if variables_list else {}
            msg_text = generate_campaign_message(message_template, variables)
            res = self.send_message(lead['phone_number'], msg_text, media_url, user_id)
            results.append({"lead": lead['phone_number'], "result": res})
        return results

    # ==================== إدارة الحملات ====================
    def create_campaign(self, name: str, message: str, user_id: str, media_url: str = None):
        campaign_id = self.db.create_campaign(name, message, user_id, media_url)
        return campaign_id

    def send_campaign(self, campaign_id: str):
        # جلب بيانات الحملة
        campaign = self.db.client.table("whatsapp_campaigns").select("*").eq("id", campaign_id).execute().data[0]
        # جلب العملاء المناسبين
        target_quality = campaign.get("target_quality", [])
        leads = self.db.client.table("leads").select("*").execute().data
        if target_quality:
            leads = [l for l in leads if l.get("quality") in target_quality]
        message = campaign.get("message", "")
        media_url = campaign.get("media_url", None)
        user_id = campaign.get("user_id", None)

        # إرسال الرسائل
        results = self.send_bulk(leads, message, media_url=media_url, user_id=user_id)

        # تحديث إحصائيات الحملة
        sent_count = sum(1 for r in results if r['result']['success'])
        failed_count = sum(1 for r in results if not r['result']['success'])

        self.db.client.table("whatsapp_campaigns").update({
            "status": "sent",
            "sent_count": sent_count,
            "failed_count": failed_count
        }).eq("id", campaign_id).execute()

        return {"success": True, "sent_count": sent_count, "failed_count": failed_count}

    # ==================== استخراج الرسائل المخصصة ====================
    def generate_message(self, template: str, variables: dict):
        return generate_campaign_message(template, variables)
