import os, re, jwt, shutil
from fastapi import FastAPI, WebSocket, Request, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from openai import OpenAI
from supabase import create_client

# ====== الإعدادات ======
SECRET_KEY      = os.getenv("SECRET_KEY", "dev-secret-key")
ADMIN_EMAIL     = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD  = os.getenv("ADMIN_PASSWORD", "admin123")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
SUPABASE_URL    = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY    = os.getenv("SUPABASE_KEY", "")
SERPER_KEYS     = [k.strip() for k in os.getenv("SERPER_KEYS", "").split(",") if k.strip()]
TWILIO_SID      = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN    = os.getenv("TWILIO_TOKEN", "")
TWILIO_WHATSAPP = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

client     = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
supabase   = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None
app        = FastAPI(title="Hunter Pro v5", version="5.0")
UPLOAD_DIR = "uploads/campaigns"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== الأمان ======
class LoginRequest(BaseModel):
    email: str
    password: str

def create_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm="HS256")

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub") == ADMIN_EMAIL
    except:
        return False

# ====== المسارات الأساسية ======
@app.post("/api/login")
def login(req: LoginRequest):
    if req.email == ADMIN_EMAIL and req.password == ADMIN_PASSWORD:
        return {"access_token": create_token({"sub": ADMIN_EMAIL}), "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="بيانات خاطئة")

@app.post("/api/extract-phones")
def extract_phones(req: dict, token: str = Depends(lambda r: r.headers.get("authorization").split()[1])):
    if not verify_token(token): raise HTTPException(status_code=403, detail="غير مصرح")
    text = req.get("text", "")
    phones = re.findall(r'01[0125][0-9]{8}', text)
    return {"phones": list(set(phones))}

@app.post("/api/admin-command")
def admin_command(req: dict, token: str = Depends(lambda r: r.headers.get("authorization").split()[1])):
    if not verify_token(token): raise HTTPException(status_code=403, detail="غير مصرح")
    cmd = req.get("command", "").strip()
    parts = cmd.split()

    if parts[0] == "/حذف_عميل":
        phone = parts[1] if len(parts) > 1 else ""
        return {"reply": f"✅ تم حذف العميل {phone} (محاكاة)"}

    elif parts[0] == "/انشئ_حملة":
        name = " ".join(parts[1:]) if len(parts) > 1 else "حملة جديدة"
        return {"reply": f"✅ تم إنشاء الحملة '{name}' (محاكاة)"}

    elif parts[0] == "/احصائيات":
        return {"reply": "📊 إحصائيات سريعة:\n- إجمالي العملاء: 150\n- العملاء الجدد: 25\n- معدل النجاح: 68%"}

    elif parts[0] == "/مسح_الشات":
        return {"reply": "✅ تم مسح سجل المحادثة"}

    else:
        if client:
            try:
                res = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": cmd}],
                    max_tokens=300,
                    temperature=0.3
                )
                return {"reply": res.choices[0].message.content}
            except:
                return {"reply": "❌ خطأ في الـ AI"}
        else:
            return {"reply": "🤖 الأمر غير معروف – جرب:\n/حذف_عميل 010xxxx\n/انشئ_حملة عروض_الصيف\n/احصائيات\n/مسح_الشات"}

# ====== حملات اليوزر العادي (صور + فيديو + إرسال) ======
@app.post("/api/create-campaign")
def create_campaign(
    name: str = Form(...),
    message: str = Form(...),
    user_id: str = Form("user"),
    media: UploadFile = File(None),
    token: str = Depends(lambda r: r.headers.get("authorization").split()[1])
):
    if not verify_token(token): raise HTTPException(status_code=403, detail="غير مصرح")
    file_path = None
    if media:
        file_path = f"{UPLOAD_DIR}/{media.filename}"
        with open(file_path, "wb") as f:
            shutil.copyfileobj(media.file, f)
    # محاكاة حفظ في قاعدة البيانات
    return {"success": True, "reply": f"✅ تم إنشاء الحملة '{name}'"}

@app.get("/api/my-campaigns")
def my_campaigns(user_id: str = "user", token: str = Depends(lambda r: r.headers.get("authorization").split()[1])):
    if not verify_token(token): raise HTTPException(status_code=403, detail="غير مصرح")
    # محاكاة
    campaigns = [
        {"id": "1", "name": "عروض الصيف", "message": "عرض حصري", "status": "draft", "sent_count": 0, "delivered_count": 0},
        {"id": "2", "name": "تخفيضات الشتاء", "message": "خصم 20%", "status": "sent", "sent_count": 45, "delivered_count": 42}
    ]
    return {"success": True, "campaigns": campaigns}

@app.post("/api/send-campaign")
def send_campaign(req: dict, token: str = Depends(lambda r: r.headers.get("authorization").split()[1])):
    if not verify_token(token): raise HTTPException(status_code=403, detail="غير مصرح")
    campaign_id = req.get("campaign_id")
    # محاكاة إرسال واتساب
    return {"success": True, "reply": f"✅ تم إرسال الحملة {campaign_id}"}

@app.delete("/api/delete-campaign")
def delete_campaign(req: dict, token: str = Depends(lambda r: r.headers.get("authorization").split()[1])):
    if not verify_token(token): raise HTTPException(status_code=403, detail="غير مصرح")
    campaign_id = req.get("campaign_id")
    return {"success": True, "reply": f"✅ تم حذف الحملة {campaign_id}"}

# ====== WebSocket شات GPT ======
@app.websocket("/ws/admin-chat")
async def admin_chat_ws(websocket: WebSocket):
    await websocket.accept()
    while True:
        msg = await websocket.receive_text()
        if client:
            try:
                res = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": msg}],
                    max_tokens=300,
                    temperature=0.3
                )
                reply = res.choices[0].message.content
            except:
                reply = "❌ خطأ في الـ AI"
        else:
            reply = "🤖 AI غير مفعل"
        await websocket.send_text(reply)

# ====== SPA Fallback ======
@app.get("/", include_in_schema=False)
def serve_dashboard():
    return FileResponse("dashboard.html")

@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    return FileResponse("dashboard.html")
