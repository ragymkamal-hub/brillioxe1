from fastapi import FastAPI, WebSocket, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Dict
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

from utils import *
from database import Database
from whatsapp_manager import WhatsAppManager

# ==================== إعداد FastAPI ====================
app = FastAPI(title="Hunter Pro CRM")

# ==================== CORS ====================
origins = [
    "http://localhost",
    "http://localhost:8000"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== إعداد المصادقة ====================
SECRET_KEY = "your-super-secret-jwt-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 أيام

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

db = Database()
whatsapp = WhatsAppManager()

# ==================== JWT Helpers ====================
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user = db.get_user(username)
        if user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ==================== Health Check ====================
@app.get("/health")
def health_check():
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "serper_keys": len(db.get_serper_keys()),
        "twilio_configured": whatsapp.is_configured()
    }

@app.get("/")
def root():
    return {"message": "Hunter Pro CRM API is running"}

# ==================== Authentication ====================
@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.get_user(form_data.username)
    if not user or not verify_password(form_data.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user['username']}, 
                                       expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

# ==================== Leads Management ====================
@app.get("/leads")
@app.get("/api/leads")
def get_leads(user_id: str = None, current_user: dict = Depends(get_current_user)):
    return {"success": True, "leads": db.get_leads(user_id)}

@app.post("/add-lead")
@app.post("/api/add-lead")
def add_lead(lead: Dict, current_user: dict = Depends(get_current_user)):
    db.add_lead(lead)
    return {"success": True, "message": "تم إضافة العميل بنجاح"}

# ==================== WhatsApp ====================
@app.post("/send-whatsapp")
@app.post("/api/send-whatsapp")
def send_whatsapp(data: Dict, current_user: dict = Depends(get_current_user)):
    result = whatsapp.send_message(data['phone_number'], data['message'])
    return {"success": True, "message": "تم إرسال الرسالة", "sid": result}

# ==================== Campaigns ====================
@app.post("/api/create-campaign")
def create_campaign(name: str, message: str, user_id: str, media: UploadFile = File(None), current_user: dict = Depends(get_current_user)):
    campaign_id = db.create_campaign(name, message, user_id, media)
    return {"success": True, "reply": "تم إنشاء الحملة بنجاح", "campaign_id": campaign_id}

@app.get("/api/my-campaigns")
def get_my_campaigns(user_id: str = None, current_user: dict = Depends(get_current_user)):
    return {"success": True, "campaigns": db.get_campaigns(user_id)}

@app.post("/api/send-campaign")
def send_campaign(data: Dict, current_user: dict = Depends(get_current_user)):
    count = whatsapp.send_campaign(data['campaign_id'])
    return {"success": True, "reply": f"تم إرسال {count} رسالة"}

@app.delete("/api/delete-campaign")
def delete_campaign(data: Dict, current_user: dict = Depends(get_current_user)):
    db.delete_campaign(data['campaign_id'])
    return {"success": True, "reply": "تم حذف الحملة"}

# ==================== Utilities ====================
@app.post("/api/extract-phones")
def extract_phones_endpoint(data: Dict, current_user: dict = Depends(get_current_user)):
    phones = extract_phone_numbers(data['text'])
    return {"success": True, "phones": phones}

# ==================== Sharing ====================
@app.post("/share-lead")
def share_lead(data: Dict, current_user: dict = Depends(get_current_user)):
    share_link = db.share_lead(data)
    return {"success": True, "share_link": share_link}

@app.get("/public/lead/{phone}")
def get_public_lead(phone: str):
    lead = db.get_public_lead(phone)
    return {"success": True, "lead": lead}

@app.get("/api/lead-share-status")
def lead_share_status(phone: str):
    status = db.get_lead_share_status(phone)
    return {"success": True, "share_status": status['status'], "share_date": status['date'], "share_by": status['by']}

@app.post("/api/cancel-share")
def cancel_share(data: Dict):
    db.cancel_share(data['phone'], data['user_id'])
    return {"success": True, "message": "تم إلغاء المشاركة"}

# ==================== Statistics ====================
@app.get("/admin-stats")
@app.get("/api/admin-stats")
def admin_stats(user_id: str = None):
    return db.get_admin_stats(user_id)

@app.get("/last-events")
@app.get("/api/last-events")
def last_events():
    return {"success": True, "events": db.get_last_events()}

# ==================== Users ====================
@app.post("/add-user")
@app.post("/api/add-user")
def add_user(data: Dict, current_user: dict = Depends(get_current_user)):
    db.add_user(data)
    return {"success": True, "message": "تم إضافة المستخدم"}

@app.post("/delete-user")
@app.post("/api/delete-user")
def delete_user(data: Dict):
    db.delete_user(data['username'])
    return {"success": True, "message": "تم حذف المستخدم"}

@app.post("/update-permissions")
@app.post("/api/update-permissions")
def update_permissions(data: Dict):
    db.update_user_permissions(data)
    return {"success": True, "message": "تم تحديث الصلاحيات"}

# ==================== Admin Chat ====================
@app.websocket("/ws/admin-chat")
async def admin_chat_ws(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("مرحباً بك في شات الأدمن!")
    while True:
        try:
            msg = await websocket.receive_text()
            # هنا يمكن معالجة الأوامر مثل /stats و /help
            await websocket.send_text(f"تم الاستلام: {msg}")
        except Exception:
            break
