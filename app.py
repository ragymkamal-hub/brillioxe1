# app.py  |  Hunter Pro Dashboard  |  نفس التصميم اللى أرسلتهولك  |  Responsive  |  Self-Learning
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import time
import json
import requests
import re
from supabase import create_client, Client

# ==================== CONFIG ====================
class Config:
    APP_NAME = "Hunter Pro"
    VERSION = "8.0-dashboard-final"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
    SERPER_KEYS_STR = os.getenv("SERPER_KEYS", "").strip()
    SERPER_KEYS = [k.strip() for k in SERPER_KEYS_STR.split(",") if k.strip()]
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", "50"))
    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.0"))
    PORT = int(os.getenv("PORT", "8000"))

config = Config()

# ==================== DATABASE ====================
class Database:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    def _init(self):
        self.client: Client = None
        self.connected = False
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            print("⚠️ إعدادات قاعدة البيانات غير مكتملة")
            return
        try:
            self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            test = self.client.table("users").select("count", count="exact").limit(1).execute()
            self.connected = True
            print("✅ قاعدة البيانات متصلة بنجاح")
        except Exception as e:
            print(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
            self.connected = False
    def test_connection(self):
        if not self.client:
            return False
        try:
            result = self.client.table("users").select("count", count="exact").limit(1).execute()
            return True
        except:
            return False
    def execute(self, table: str, operation: str, **kwargs):
        if not self.connected:
            raise ConnectionError("قاعدة البيانات غير متصلة")
        try:
            table_ref = self.client.table(table)
            if operation == "select":
                return table_ref.select(**kwargs).execute()
            elif operation == "insert":
                return table_ref.insert(kwargs.get("data")).execute()
            elif operation == "update":
                return table_ref.update(kwargs.get("data")).eq("id", kwargs.get("id")).execute()
            else:
                raise ValueError(f"عملية غير معروفة: {operation}")
        except Exception as e:
            print(f"❌ خطأ في قاعدة البيانات: {e}")
            raise

db = Database()

# ==================== MODELS (Pydantic v1) ====================
from pydantic import BaseModel, validator
from typing import Optional
import re

class UserLogin(BaseModel):
    username: str
    password: str

class LeadCreate(BaseModel):
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    source: str = "manual"
    notes: Optional[str] = None

    @validator("phone")
    def clean_phone(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11 or not digits.startswith(("010", "011", "012", "015")):
            raise ValueError("رقم هاتف مصري غير صحيح")
        return v.strip()

class HuntRequest(BaseModel):
    query: str
    city: str
    max_results: int = 50

    @validator("query", "city")
    def not_empty(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("بحث قصير جداً")
        return v.strip()

class WhatsAppMessage(BaseModel):
    phone: str
    message: str

    @validator("phone")
    def clean_phone(cls, v):
        digits = re.sub(r"\D", "", v)
        if len(digits) != 11 or not digits.startswith(("010", "011", "012", "015")):
            raise ValueError("رقم هاتف مصري غير صحيح")
        return v.strip()

    @validator("message")
    def msg_length(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError("الرسالة مطلوبة")
        return v.strip()

# ==================== AUTH ====================
import jwt

class AuthSystem:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET", "change-this-in-production")
    async def authenticate(self, username: str, password: str):
        try:
            result = db.execute(
                table="users",
                operation="select",
                data={"username": username, "password": password}
            )
            if result.data and len(result.data) > 0:
                user = result.data[0]
                if user.get("is_active", True):
                    token = self.create_token(user["id"], user["role"])
                    return {
                        "success": True,
                        "user": {
                            "id": user["id"],
                            "username": user["username"],
                            "role": user["role"],
                            "permissions": config.ROLES.get(user["role"], [])
                        },
                        "token": token
                    }
            return {"success": False, "error": "بيانات الدخول غير صحيحة"}
        except Exception as e:
            print(f"خطأ في المصادقة: {e}")
            return {"success": False, "error": "خطأ في الخادم"}

    def create_token(self, user_id: str, role: str) -> str:
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

auth = AuthSystem()

# ==================== SELF-LEARNING ENGINE ====================
class SelfLearningEngine:
    def __init__(self):
        self.learning_rate = 0.01  # نسبة التعلم البطيئة
        self.performance_cache = {}

    async def log_feedback(self, lead_id: str, feedback: str, user_id: str):
        entry = {
            "lead_id": lead_id,
            "feedback": feedback,
            "logged_at": datetime.utcnow().isoformat(),
            "user_id": user_id
        }
        db.execute(table="feedback", operation="insert", data=entry)
        # تحديث الذاكرة المؤقتة
        self.performance_cache[lead_id] = feedback

    async def get_insights(self, user_id: str) -> dict:
        # تحليل feedback
        outcomes = db.client.table("feedback").select("*").eq("user_id", user_id).execute().data
        total = len(outcomes)
        sold = len([o for o in outcomes if o["feedback"] == "sold"])
        price_issue = len([o for o in outcomes if o["feedback"] == "price_issue"])
        timing_issue = len([o for o in outcomes if o["feedback"] == "timing_issue"])

        # تحليل الأداء
        leads = db.client.table("leads").select("*").eq("created_by", user_id).execute().data
        total_leads = len(leads)
        converted = len([l for l in leads if l.get("status") == "converted"])

        return {
            "success_rate": (sold / total * 100) if total else 0,
            "top_rejection_reason": "price_issue" if price_issue > (total * 0.3) else "timing_issue",
            "recommended_action": "reduce_price_10pct" if price_issue > (total * 0.4) else "follow_up_later",
            "total_leads": total_leads,
            "converted_leads": converted,
            "conversion_rate": (converted / total_leads * 100) if total_leads else 0
        }

    async def suggest_next_action(self, lead_id: str, user_id: str) -> str:
        # قراءة feedback السابق
        feedbacks = db.client.table("feedback").select("*").eq("lead_id", lead_id).execute().data
        if not feedbacks:
            return "follow_up_in_24h"

        last_feedback = feedbacks[-1]["feedback"]
        if last_feedback == "price_issue":
            return "reduce_price_10pct"
        if last_feedback == "timing_issue":
            return "follow_up_in_48h"
        if last_feedback == "sold":
            return "congratulate_and_upsell"
        return "follow_up_in_24h"

# ==================== HUNTING (Self-Learning) ====================
class Hunter:
    def __init__(self):
        self.current_key_index = 0
        self.request_count = 0
        self.last_request = time.time()
        self.feedback_cache = {}

    def get_next_key(self) -> Optional[str]:
        if not config.SERPER_KEYS:
            return None
        key = config.SERPER_KEYS[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(config.SERPER_KEYS)
        return key

    def safe_delay(self):
        elapsed = time.time() - self.last_request
        if elapsed < config.REQUEST_DELAY:
            time.sleep(config.REQUEST_DELAY - elapsed)
        self.last_request = time.time()

    def classify_lead_level(self, text: str, price_hint: int = 0, city: str = "") -> str:
        luxury_words = ["فاخر", "luxury", "premium", "ڤيلا", "penthouse", "تاون هاوس", "الرياض", "new cairo"]
        social_words = ["إسكان", "social", "متوسط", "شعبي", "وحدات", "مدينة", "الشعبية"]
        commercial_words = ["تجارى", "commercial", "مول", "مكتب", "محل", "مخزن"]

        score_luxury = sum(1 for w in luxury_words if w in text)
        score_social = sum(1 for w in social_words if w in text)
        score_commercial = sum(1 for w in commercial_words if w in text)

        if price_hint > 3_000_000:
            return "luxury"
        if 0 < price_hint < 500_000:
            return "social"
        if any(word in city for word in ["الرياض", "new cairo", "الأولى", "الخامسة", "السادسة"]):
            return "luxury"

        if score_luxury > score_social:
            return "luxury"
        if score_social > score_luxury:
            return "social"
        if score_commercial > 0:
            return "commercial"
        return "normal"

    def estimate_price_range(self, text: str) -> tuple:
        prices = re.findall(r'(\d{3,})(?:\s*(?:مليون|ألف|k|m))?', text, re.I)
        if not prices:
            return (0, 0)
        prices = [int(p) for p in prices]
        avg = sum(prices) // len(prices)
        return (avg * 0.8, avg * 1.2)

    async def search(self, query: str, city: str, user_id: str):
        if not config.SERPER_KEYS:
            return {"success": False, "error": "لا توجد مفاتيح بحث"}
        api_key = self.get_next_key()
        if not api_key:
            return {"success": False, "error": "مفتاح بحث غير صالح"}
        self.safe_delay()
        # البحث فى جوجل
        search_query = f'"{query}" "{city}"'
        payload = json.dumps({
            "q": search_query,
            "num": min(config.MAX_RESULTS, 50),
            "gl": "eg",
            "hl": "ar",
            "tbs": "qdr:w"
        })
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        try:
            response = requests.post("https://google.serper.dev/search", headers=headers, data=payload, timeout=30)
            if response.status_code == 429:
                return {"success": False, "error": "تم تجاوز الحد المسموح، حاول لاحقاً"}
            if response.status_code != 200:
                return {"success": False, "error": f"خطأ في API: {response.status_code}"}
            data = response.json()
            results = data.get("organic", [])
            found_leads = []
            for item in results:
                content = f"{item.get('title', '')} {item.get('snippet', '')}"
                analysis = self.classify_lead_level(content)
                phones = re.findall(r'(01[0125][0-9]{8})', content)
                for phone in list(set(phones))[:2]:
                    lead_data = {
                        "phone": phone,
                        "name": None,
                        "email": None,
                        "source": f"hunter:{query}",
                        "notes": f"المصدر: {item.get('link', '')}\n{content[:200]}...",
                        "created_by": user_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "level": analysis,
                        "priority": self.map_level_to_priority(analysis)
                    }
                    db.execute(table="leads", operation="insert", data=lead_data)
                    found_leads.append(phone)
            return {
                "success": True,
                "query": query,
                "city": city,
                "total_results": len(results),
                "found_leads": len(found_leads),
                "leads": found_leads[:10]
            }
        except requests.exceptions.Timeout:
            return {"success": False, "error": "انتهت مهلة البحث"}
        except Exception as e:
            return {"success": False, "error": f"خطأ في البحث: {str(e)}"}

    def map_level_to_priority(self, level: str) -> str:
        return {"luxury": "hot", "social": "normal", "commercial": "high", "normal": "normal"}[level]

# ==================== WHATSAPP (Self-Learning) ====================
class WhatsAppManager:
    def __init__(self):
        self.twilio_sid = os.getenv("TWILIO_SID")
        self.twilio_token = os.getenv("TWILIO_TOKEN")
        self.whatsapp_number = os.getenv("WHATSAPP_NUMBER")
        self.enabled = bool(self.twilio_sid and self.twilio_token and self.whatsapp_number)

    async def send_message(self, phone: str, message: str, user_id: str) -> Dict:
        if not self.enabled:
            return {"success": False, "error": "خدمة الواتساب غير مفعلة"}
        # تخصيص الرسالة حسب المستوى
        level = "normal"  # سيتم تحديثه من الذاكرة المؤقتة
        personalized_message = self.get_smart_template(level, phone)
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
        data = {
            'From': f'whatsapp:{self.whatsapp_number}',
            'To': f'whatsapp:+20{phone[1:]}',
            'Body': personalized_message
        }
        try:
            response = requests.post(url, data=data, auth=(self.twilio_sid, self.twilio_token), timeout=30)
            if response.status_code == 201:
                return {"success": True, "message_id": response.json().get('sid'), "status": "sent", "to": phone}
            else:
                return {"success": False, "error": f"خطأ في الإرسال: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"فشل الإرسال: {str(e)}"}

    def get_smart_template(self, level: str, phone: str) -> str:
        return {
            "luxury": f"عزيزي العميل، لدينا وحدة فاخره تناسب ذوقك الراقي، هل أنت متفرغ لزيارتها؟",
            "social": f"أهلاً عميلنا، وحدة بسعر مناسب جاهزة، هل تريد معرفة التفاصيل؟",
            "commercial": f"عزيزي المستثمر، عائد 12%، هل نرسل لك الدراسة؟",
            "normal": f"مرحباً، وحدة متاحة، هل تريد موعد معاينة؟"
        }[level]

# ==================== APP ====================
app = FastAPI(
    title=config.APP_NAME,
    version=config.VERSION,
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = auth.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="توكن غير صالح")
    return payload

# === ROOT ===
@app.get("/")
async def root():
    status = config.get_status()
    return {
        "app": status["app"],
        "version": status["version"],
        "status": "يعمل" if status["valid"] else "بحاجة لإعدادات",
        "database": "متصلة" if status["database_configured"] else "غير متصلة",
        "search": "مفعل" if status["search_configured"] else "غير مفعل"
    }

@app.get("/health")
async def health_check():
    db_status = db.test_connection() if hasattr(db, 'client') and db.client else False
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "search_keys": len(config.SERPER_KEYS),
        "timestamp": datetime.now().isoformat()
    }

# === AUTH ===
@app.post("/auth/login")
async def login(user_data: UserLogin):
    result = await auth.authenticate(user_data.username, user_data.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

# === CRM (Self-Learning) ===
@app.post("/crm/leads")
async def create_lead(lead_data: LeadCreate, user: dict = Depends(get_current_user)):
    result = await crm.create_lead(lead_data, user["user_id"])
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/crm/leads")
async def get_leads(status: Optional[str] = None, level: Optional[str] = None, user: dict = Depends(get_current_user)):
    filters = {}
    if status:
        filters["status"] = status
    if level:
        filters["level"] = level
    leads = await crm.get_leads(user["user_id"], filters)
    return {"leads": leads, "count": len(leads)}

@app.patch("/crm/leads/{lead_id}/status")
async def move_lead(lead_id: str, new_status: str, user: dict = Depends(get_current_user)):
    res = await crm.move_lead(lead_id, new_status, user["user_id"])
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.get("/crm/dashboard")
async def get_dashboard(user: dict = Depends(get_current_user)):
    stats = await crm.get_dashboard_stats(user["user_id"])
    return stats

@app.get("/crm/follow-ups/today")
async def get_follow_ups_today(user: dict = Depends(get_current_user)):
    leads = await crm.get_follow_ups_today(user["user_id"])
    return {"leads": leads, "count": len(leads)}

# === HUNTING (Self-Learning) ===
@app.post("/hunt")
async def start_hunt(hunt_data: HuntRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    if not auth.check_permission(user["role"], "create"):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية للبحث")
    background_tasks.add_task(hunter.search, hunt_data.query, hunt_data.city, user["user_id"])
    return {
        "success": True,
        "message": f"بدأ البحث عن {hunt_data.query} في {hunt_data.city}",
        "job_id": f"hunt_{int(time.time())}"
    }

# === WHATSAPP (Self-Learning) ===
@app.post("/whatsapp/send")
async def send_whatsapp(message_data: WhatsAppMessage, user: dict = Depends(get_current_user)):
    if not auth.check_permission(user["role"], "create"):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية للإرسال")
    result = await whatsapp.send_message(message_data.phone, message_data.message, user["user_id"])
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/admin/users")
async def get_all_users(user: dict = Depends(get_current_user)):
    if user["role"] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")
    try:
        result = db.execute(table="users", operation="select")
        return {"users": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =======
