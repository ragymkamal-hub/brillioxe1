from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os
import re
import json
import requests
from datetime import datetime, timedelta
from supabase import create_client, Client
from twilio.rest import Client as TwilioClient
import jwt
from passlib.context import CryptContext

# ==================== الإعدادات ====================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS", "")
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

# ==================== التهيئة ====================
app = FastAPI(title="Hunter Pro CRM", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
key_index = 0

print("✅ Hunter Pro CRM - System Ready!")

# ==================== النماذج ====================
class LoginRequest(BaseModel):
    email: str
    password: str

class HuntRequest(BaseModel):
    intent_sentence: str
    city: str
    time_filter: str = "qdr:m"
    user_id: str = "admin"
    mode: str = "general"

class WhatsAppRequest(BaseModel):
    phone_number: str
    message: str
    user_id: str

class AddLeadRequest(BaseModel):
    phone_number: str
    full_name: str = ""
    email: str = ""
    source: str = "Manual"
    quality: str = "جيد ⭐"
    notes: str = ""
    user_id: str
    status: str = "NEW"

class ShareRequest(BaseModel):
    phone: str
    shared_with: List[str] = []
    is_public: bool = False
    user_id: str

class CampaignCreate(BaseModel):
    name: str
    message: str
    user_id: str
    target_quality: List[str] = ["ممتاز 🔥", "جيد ⭐"]

class CampaignAction(BaseModel):
    campaign_id: str

class AdminCommand(BaseModel):
    command: str

class AddUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"
    can_hunt: bool = True
    can_campaign: bool = True
    can_share: bool = False
    can_see_all_data: bool = False
    is_admin: bool = False

class UpdatePermissions(BaseModel):
    username: str
    can_hunt: bool
    can_campaign: bool
    can_share: bool
    can_see_all_data: bool
    is_admin: bool

class ExtractPhonesRequest(BaseModel):
    text: str

# ==================== الدوال المساعدة ====================
def get_active_key():
    """إدارة مفاتيح Serper API"""
    global key_index
    if not SERPER_KEYS:
        return None
    key = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return key

def get_sub_locations(city):
    """تقسيم المدن إلى مناطق فرعية"""
    locations = {
        "القاهرة": ["التجمع", "المعادي", "مدينة نصر", "مصر الجديدة", "الزمالك", "الرحاب", "مدينتي", "القاهرة الجديدة"],
        "الجيزة": ["أكتوبر", "الشيخ زايد", "الهرم", "المهندسين", "الدقي", "حدائق الأهرام"],
        "الإسكندرية": ["سموحة", "سيدي جابر", "العجمي", "المنتزه", "ميامي"]
    }
    return locations.get(city, [city])

def analyze_quality(text):
    """تحليل جودة العميل من النص"""
    text = text.lower()
    
    # قائمة سوداء (رفض)
    blacklist = ["للبيع", "for sale", "متاح الان", "احجز الان", "تواصل معنا", 
                 "امتلك", "فرصة", "offer", "discount", "سمسار", "broker", "وكيل"]
    for word in blacklist:
        if word in text:
            return "TRASH"
    
    # قائمة ذهبية (ممتاز)
    excellent = ["مطلوب", "محتاج", "عايز", "أبحث", "شراء", "كاش", "wanted", 
                 "buying", "looking for", "need", "أريد"]
    for word in excellent:
        if word in text:
            return "ممتاز 🔥"
    
    # قائمة جيدة
    good = ["سعر", "تفاصيل", "price", "details", "بكام", "معلومات"]
    for word in good:
        if word in text:
            return "جيد ⭐"
    
    return "TRASH"

def save_lead(phone, email, keyword, link, quality, user_id):
    """حفظ عميل جديد في قاعدة البيانات"""
    if quality == "TRASH":
        print(f"   🗑️ Trash Skipped: {phone}")
        return False
    
    if not phone or len(phone) != 11:
        return False
    
    try:
        data = {
            "phone_number": phone,
            "source": f"SmartHunt: {keyword}",
            "quality": quality,
            "status": "NEW",
            "notes": f"Link: {link}",
            "user_id": user_id
        }
        if email:
            data["email"] = email
        
        supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
        print(f"   💎 SAVED: {phone} ({quality})")
        
        # تسجيل حدث
        supabase.table("events").insert({
            "event": "new_lead",
            "details": f"New lead added: {phone}",
            "user_id": user_id
        }).execute()
        
        return True
    except Exception as e:
        print(f"   ❌ Save Error: {e}")
        return False

def extract_phones_from_text(text):
    """استخراج أرقام الهواتف من النص"""
    phones = re.findall(r'(01[0125][0-9 \-]{8,15})', text)
    clean_phones = []
    for raw in phones:
        clean = raw.replace(" ", "").replace("-", "")
        if len(clean) == 11 and clean not in clean_phones:
            clean_phones.append(clean)
    return clean_phones

def create_jwt_token(email: str):
    """إنشاء JWT Token"""
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str):
    """التحقق من JWT Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except:
        return None

# ==================== محرك البحث ====================
def run_hydra_hunt(intent: str, main_city: str, time_filter: str, user_id: str, mode: str):
    """محرك البحث الذكي - Diamond Hunter"""
    if not SERPER_KEYS:
        print("❌ No Serper API keys configured")
        return
    
    # تحسين جملة البحث
    search_intent = intent
    if "شقة" in intent or "فيلا" in intent or "محل" in intent:
        if "مطلوب" not in intent:
            search_intent = f'مطلوب {intent}'
    
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Quality Hunt Started: {search_intent} in {sub_cities}")
    
    total_found = 0
    start_time = datetime.now()
    
    for area in sub_cities:
        queries = [
            f'site:facebook.com "{search_intent}" "{area}" "010"',
            f'site:olx.com.eg "{search_intent}" "{area}" "010"',
            f'"{search_intent}" "{area}" "مطلوب" "01"',
            f'"{search_intent}" "{area}" "wanted" "01"'
        ]
        
        for query in queries:
            api_key = get_active_key()
            if not api_key:
                break
            
            payload = json.dumps({
                "q": query,
                "num": 100,
                "tbs": time_filter,
                "gl": "eg",
                "hl": "ar"
            })
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
            
            try:
                print(f"🚀 Scanning: {query[:60]}...")
                response = requests.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    data=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    results = response.json().get("organic", [])
                    
                    for res in results:
                        snippet = f"{res.get('title', '')} {res.get('snippet', '')}"
                        quality = analyze_quality(snippet)
                        
                        if quality != "TRASH":
                            phones = extract_phones_from_text(snippet)
                            for phone in phones:
                                if save_lead(phone, None, intent, res.get('link'), quality, user_id):
                                    total_found += 1
                
            except Exception as e:
                print(f"   ⚠️ Error: {e}")
    
    # تسجيل نتائج البحث
    duration = (datetime.now() - start_time).seconds
    try:
        supabase.table("hunt_logs").insert({
            "user_id": user_id,
            "intent": intent,
            "city": main_city,
            "results_count": total_found,
            "duration_seconds": duration,
            "mode": mode
        }).execute()
    except:
        pass
    
    print(f"🏁 Hunt Finished! Found: {total_found} diamonds in {duration}s")

# ==================== Endpoints ====================
@app.get("/", response_class=HTMLResponse)
async def home():
    """صفحة Dashboard الرئيسية"""
    try:
        with open("dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>Hunter Pro CRM</h1><p>Dashboard file not found</p>"

@app.get("/health")
def health_check():
    """فحص صحة النظام"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "serper_keys": len(SERPER_KEYS),
        "twilio_configured": bool(TWILIO_SID and TWILIO_TOKEN)
    }

# ==================== المصادقة ====================
@app.post("/api/login")
async def login(req: LoginRequest):
    """تسجيل الدخول"""
    try:
        # محاكاة دخول Google
        if req.password == "google":
            token = create_jwt_token(req.email)
            return {"access_token": token, "token_type": "bearer"}
        
        # دخول عادي (للمستقبل: التحقق من قاعدة البيانات)
        if req.email == "admin@example.com" and req.password == "admin123":
            token = create_jwt_token(req.email)
            return {"access_token": token, "token_type": "bearer"}
        
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== البحث ====================
@app.post("/start_hunt")
@app.post("/hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    """بدء عملية البحث"""
    background_tasks.add_task(
        run_hydra_hunt,
        req.intent_sentence,
        req.city,
        req.time_filter,
        req.user_id,
        req.mode
    )
    return {
        "status": "started",
        "search": req.intent_sentence,
        "city": req.city,
        "message": "بدأ البحث بنجاح"
    }

# ==================== العملاء ====================
@app.get("/leads")
@app.get("/api/leads")
def get_leads(user_id: str = "admin"):
    """جلب قائمة العملاء"""
    try:
        # التحقق من صلاحيات المستخدم
        user = supabase.table("users").select("can_see_all_data, is_admin").eq("username", user_id).execute()
        
        if user.data and (user.data[0].get("can_see_all_data") or user.data[0].get("is_admin")):
            rows = supabase.table("leads").select("*").order("created_at", desc=True).limit(500).execute()
        else:
            rows = supabase.table("leads").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(500).execute()
        
        return {"success": True, "leads": rows.data}
    except Exception as e:
        return {"success": False, "error": str(e), "leads": []}

@app.post("/add-lead")
@app.post("/api/add-lead")
def add_lead(req: AddLeadRequest):
    """إضافة عميل يدوياً"""
    try:
        supabase.table("leads").insert(req.dict()).execute()
        
        # تسجيل حدث
        supabase.table("events").insert({
            "event": "manual_lead_added",
            "details": f"Manual lead: {req.phone_number}",
            "user_id": req.user_id
        }).execute()
        
        return {"success": True, "message": "تم إضافة العميل بنجاح"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== واتساب ====================
@app.post("/send-whatsapp")
@app.post("/api/send-whatsapp")
async def send_whatsapp(req: WhatsAppRequest):
    """إرسال رسالة واتساب"""
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_WHATSAPP_NUMBER]):
        return {"success": False, "error": "Twilio not configured"}
    
    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=req.message,
            to=f"whatsapp:{req.phone_number}"
        )
        
        # تسجيل الرسالة
        supabase.table("campaign_logs").insert({
            "lead_phone": req.phone_number,
            "message_sent": req.message,
            "status": "sent",
            "user_id": req.user_id
        }).execute()
        
        return {
            "success": True,
            "message": "تم إرسال الرسالة",
            "sid": message.sid
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== الحملات ====================
@app.post("/api/create-campaign")
async def create_campaign(
    name: str = Form(...),
    message: str = Form(...),
    user_id: str = Form(...),
    media: Optional[UploadFile] = File(None)
):
    """إنشاء حملة جديدة"""
    try:
        campaign_data = {
            "name": name,
            "message": message,
            "user_id": user_id,
            "status": "draft",
            "sent_count": 0,
            "delivered_count": 0
        }
        
        if media:
            # حفظ الملف (للمستقبل)
            campaign_data["media_url"] = f"/media/{media.filename}"
        
        result = supabase.table("whatsapp_campaigns").insert(campaign_data).execute()
        
        return {"success": True, "reply": "تم إنشاء الحملة بنجاح", "campaign_id": result.data[0]["id"]}
    except Exception as e:
        return {"success": False, "reply": f"خطأ: {str(e)}"}

@app.get("/api/my-campaigns")
def get_my_campaigns(user_id: str = "admin"):
    """جلب حملات المستخدم"""
    try:
        result = supabase.table("whatsapp_campaigns").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"success": True, "campaigns": result.data}
    except Exception as e:
        return {"success": False, "campaigns": [], "error": str(e)}

@app.post("/api/send-campaign")
async def send_campaign(req: CampaignAction, background_tasks: BackgroundTasks):
    """إرسال الحملة"""
    try:
        # جلب بيانات الحملة
        campaign = supabase.table("whatsapp_campaigns").select("*").eq("id", req.campaign_id).execute()
        if not campaign.data:
            return {"success": False, "reply": "الحملة غير موجودة"}
        
        campaign_data = campaign.data[0]
        
        # جلب العملاء
        leads = supabase.table("leads").select("phone_number").eq("user_id", campaign_data["user_id"]).execute()
        
        # إرسال في الخلفية
        sent_count = 0
        for lead in leads.data[:10]:  # حد أقصى 10 لكل مرة
            try:
                client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
                client.messages.create(
                    from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
                    body=campaign_data["message"],
                    to=f"whatsapp:{lead['phone_number']}"
                )
                sent_count += 1
            except:
                pass
        
        # تحديث الحملة
        supabase.table("whatsapp_campaigns").update({
            "status": "sent",
            "sent_count": sent_count
        }).eq("id", req.campaign_id).execute()
        
        return {"success": True, "reply": f"تم إرسال {sent_count} رسالة"}
    except Exception as e:
        return {"success": False, "reply": f"خطأ: {str(e)}"}

@app.delete("/api/delete-campaign")
async def delete_campaign(req: CampaignAction):
    """حذف حملة"""
    try:
        supabase.table("whatsapp_campaigns").delete().eq("id", req.campaign_id).execute()
        return {"success": True, "reply": "تم حذف الحملة"}
    except Exception as e:
        return {"success": False, "reply": f"خطأ: {str(e)}"}

# ==================== المشاركة ====================
@app.post("/share-lead")
@app.post("/api/share-lead")
def share_lead(req: ShareRequest):
    """مشاركة عميل"""
    try:
        if req.is_public:
            share_link = f"/public/lead/{req.phone}"
            supabase.table("leads").update({
                "is_public": True
            }).eq("phone_number", req.phone).eq("user_id", req.user_id).execute()
            return {"success": True, "share_link": share_link}
        
        supabase.table("leads").update({
            "shared_with": req.shared_with
        }).eq("phone_number", req.phone).eq("user_id", req.user_id).execute()
        
        return {"success": True, "message": f"تمت المشاركة مع {', '.join(req.shared_with)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/public/lead/{phone}")
def get_public_lead(phone: str):
    """عرض عميل عام"""
    try:
        row = supabase.table("leads").select("*").eq("phone_number", phone).eq("is_public", True).execute()
        if row.data:
            return {"success": True, "lead": row.data[0]}
        return {"success": False, "message": "غير مسموح بالمشاهدة"}
    except:
        return {"success": False, "message": "خطأ في البيانات"}

@app.get("/api/lead-share-status")
def lead_share_status(phone: str):
    """حالة مشاركة العميل"""
    try:
        row = supabase.table("leads").select("shared_with, is_public, created_at, user_id").eq("phone_number", phone).execute()
        if row.data:
            data = row.data[0]
            return {
                "success": True,
                "share_status": "مشارك عام" if data.get("is_public") else ("مشارك" if data.get("shared_with") else "غير مشارك"),
                "share_date": data.get("created_at"),
                "share_by": data.get("user_id")
            }
        return {"success": False}
    except:
        return {"success": False}

@app.post("/api/cancel-share")
def cancel_share(req: dict):
    """إلغاء المشاركة"""
    try:
        supabase.table("leads").update({
            "shared_with": [],
            "is_public": False
        }).eq("phone_number", req["phone"]).eq("user_id", req["user_id"]).execute()
        return {"success": True, "message": "تم إلغاء المشاركة"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== استخراج الأرقام ====================
@app.post("/api/extract-phones")
def extract_phones(req: ExtractPhonesRequest):
    """استخراج أرقام من نص"""
    phones = extract_phones_from_text(req.text)
    return {"success": True, "phones": phones}

# ==================== إدارة المستخدمين ====================
@app.get("/admin-stats")
@app.get("/api/admin-stats")
def admin_stats(user_id: str = "admin"):
    """إحصائيات النظام"""
    try:
        total_users = supabase.table("users").select("id", count="exact").execute().count or 0
        total_leads = supabase.table("leads").select("id", count="exact").execute().count or 0
        total_messages = supabase.table("campaign_logs").select("id", count="exact").execute().count or 0
        
        return {
            "total_users": total_users,
            "total_leads": total_leads,
            "total_messages": total_messages
        }
    except
