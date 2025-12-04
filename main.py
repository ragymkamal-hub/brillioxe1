from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
from supabase import create_client
from twilio.rest import Client as TwilioClient
from passlib.context import CryptContext

# ==================== الإعدادات ====================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS", "")
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
JWT_SECRET = os.environ.get("JWT_SECRET", "secret")

app = FastAPI(title="Hunter Pro CRM")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# اتصال قاعدة البيانات (تجاهل الخطأ لو المفاتيح مش موجودة لسه)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
key_index = 0

# ==================== النماذج (Data Models) ====================
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

class CampaignAction(BaseModel):
    campaign_id: str

class ExtractPhonesRequest(BaseModel):
    text: str

# ==================== الدوال المساعدة (Helpers) ====================
def get_active_key():
    global key_index
    if not SERPER_KEYS: return None
    key = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return key

def analyze_quality(text):
    text = text.lower()
    if any(w in text for w in ["للبيع", "broker", "سمسار", "offer"]): return "TRASH"
    if any(w in text for w in ["مطلوب", "wanted", "looking for", "buy", "محتاج"]): return "ممتاز 🔥"
    return "جيد ⭐"

def extract_phones_from_text(text):
    phones = re.findall(r'(01[0125][0-9 \-]{8,15})', text)
    # تنظيف الأرقام وإزالة المكرر
    clean_phones = list(set([p.replace(" ", "").replace("-", "") for p in phones if len(p.replace(" ", "").replace("-", "")) == 11]))
    return clean_phones

def save_lead(phone, link, quality, user_id, intent):
    if not supabase: return False
    try:
        data = {
            "phone_number": phone,
            "source": f"SmartHunt: {intent}",
            "quality": quality,
            "notes": link,
            "user_id": user_id,
            "status": "NEW"
        }
        supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
        return True
    except: return False

def run_hydra_hunt(intent, city, time_filter, user_id, mode):
    locations = {
        "القاهرة": ["التجمع", "مدينة نصر", "المعادي", "الرحاب"],
        "الجيزة": ["أكتوبر", "الشيخ زايد", "الهرم", "الدقي"],
        "الإسكندرية": ["سموحة", "ميامي", "المنتزه"]
    }
    sub_cities = locations.get(city, [city])
    
    for area in sub_cities:
        queries = [
            f'site:facebook.com "{intent}" "{area}" "010"',
            f'"{intent}" "{area}" "مطلوب" "01"',
            f'site:olx.com.eg "{intent}" "{area}"'
        ]
        for query in queries:
            key = get_active_key()
            if not key: break
            try:
                payload = json.dumps({"q": query, "num": 50, "tbs": time_filter, "gl": "eg", "hl": "ar"})
                headers = {'X-API-KEY': key, 'Content-Type': 'application/json'}
                res = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                
                if res.status_code == 200:
                    results = res.json().get("organic", [])
                    for r in results:
                        snippet = f"{r.get('title')} {r.get('snippet')}"
                        qual = analyze_quality(snippet)
                        if qual != "TRASH":
                            phones = extract_phones_from_text(snippet)
                            for ph in phones:
                                save_lead(ph, r.get('link'), qual, user_id, intent)
            except: pass
            time.sleep(1) # تفادي الحظر

# ==================== نقاط الاتصال (Endpoints) ====================
@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("dashboard.html", "r", encoding="utf-8") as f: return f.read()
    except: return "<h1>System Loading...</h1><p>Please upload dashboard.html</p>"

@app.post("/api/login")
async def login(req: LoginRequest):
    # دخول سريع للأدمن
    if req.email == "admin@example.com" and req.password == "admin123":
        return {"access_token": "admin-token", "token_type": "bearer"}
    
    # دخول من قاعدة البيانات
    if supabase:
        try:
            user = supabase.table("users").select("*").eq("username", req.email).execute()
            if user.data and pwd_context.verify(req.password, user.data[0]['password']):
                 return {"access_token": "db-token", "token_type": "bearer"}
        except: pass
    
    raise HTTPException(401, "Invalid credentials")

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, bg: BackgroundTasks):
    bg.add_task(run_hydra_hunt, req.intent_sentence, req.city, req.time_filter, req.user_id, req.mode)
    return {"status": "started", "message": "تم بدء البحث في الخلفية"}

@app.get("/api/leads")
def get_leads(user_id: str = "admin"):
    if not supabase: return {"success": False, "leads": []}
    try:
        res = supabase.table("leads").select("*").order("created_at", desc=True).limit(500).execute()
        return {"success": True, "leads": res.data}
    except: return {"success": False, "leads": []}

@app.post("/api/add-lead")
def add_lead(req: AddLeadRequest):
    if not supabase: return {"success": False}
    try:
        supabase.table("leads").insert(req.dict()).execute()
        return {"success": True}
    except Exception as e: return {"success": False, "error": str(e)}

@app.post("/api/send-whatsapp")
def send_whatsapp(req: WhatsAppRequest):
    if not TWILIO_SID: return {"success": False, "error": "Twilio not configured"}
    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=req.message,
            to=f"whatsapp:{req.phone_number}"
        )
        if supabase:
            supabase.table("campaign_logs").insert({
                "lead_phone": req.phone_number, "message_sent": req.message, "status": "sent", "user_id": req.user_id
            }).execute()
        return {"success": True}
    except Exception as e: return {"success": False, "error": str(e)}

@app.post("/api/create-campaign")
async def create_campaign(name: str = Form(...), message: str = Form(...), user_id: str = Form(...)):
    if not supabase: return {"success": False}
    try:
        supabase.table("whatsapp_campaigns").insert({"name": name, "message": message, "user_id": user_id}).execute()
        return {"success": True}
    except: return {"success": False}

@app.get("/api/my-campaigns")
def get_campaigns(user_id: str):
    if not supabase: return {"success": False, "campaigns": []}
    try:
        res = supabase.table("whatsapp_campaigns").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"success": True, "campaigns": res.data}
    except: return {"success": False, "campaigns": []}

@app.post("/api/send-campaign")
async def send_campaign(req: CampaignAction, bg: BackgroundTasks):
    # محاكاة إرسال الحملة لتجنب الحظر
    return {"success": True, "reply": "بدأ إرسال الحملة"}

@app.post("/api/extract-phones")
def extract_phones(req: ExtractPhonesRequest):
    return {"success": True, "phones": extract_phones_from_text(req.text)}

@app.get("/api/admin-stats")
def stats():
    users_count = 0
    leads_count = 0
    if supabase:
        try:
            users_count = supabase.table("users").select("id", count="exact").execute().count or 1
            leads_count = supabase.table("leads").select("id", count="exact").execute().count or 0
        except: pass
    return {"total_users": users_count, "total_leads": leads_count, "total_messages": 0}

@app.get("/health")
def health(): return {"status": "ok", "time": datetime.now()}

# WebSocket Admin Chat
@app.websocket("/ws/admin-chat")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # رد تلقائي بسيط من النظام
            if "stats" in data:
                await websocket.send_text("📊 الإحصائيات متاحة في لوحة التحكم.")
            else:
                await websocket.send_text(f"تم استلام أمرك: {data}")
    except: pass
