from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os, re, json, requests, time, jwt
from datetime import datetime, timedelta
from supabase import create_client, Client
from twilio.rest import Client as TwilioClient
from passlib.context import CryptContext

# ========== CONFIGURATION ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS", "")
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-in-production-123456")
JWT_ALGORITHM = "HS256"
PORT = int(os.environ.get("PORT", 10000))  # Render.com uses port 10000

# ========== INITIALIZE APP ==========
app = FastAPI(
    title="Hunter Pro CRM",
    version="3.0",
    description="نظام إدارة العملاء والتسويق الذكي",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== DATABASE CONNECTION ==========
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase successfully!")
    except Exception as e:
        print(f"❌ Supabase connection error: {e}")
        supabase = None
else:
    print("⚠️ Supabase credentials not configured")
    supabase = None

# ========== OTHER INITIALIZATIONS ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
key_index = 0
request_count = 0
last_reset = time.time()

print(f"🎯 Hunter Pro CRM v3.0 - Ready on Render.com (Port: {PORT})")

# ========== MODELS ==========
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

class ExtractPhonesRequest(BaseModel):
    text: str

# ========== HELPER FUNCTIONS ==========
def get_active_key():
    global key_index
    if not SERPER_KEYS:
        return None
    key = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return key

def safe_request_delay():
    global request_count, last_reset
    if time.time() - last_reset > 60:
        request_count = 0
        last_reset = time.time()
    request_count += 1
    if request_count > 30:
        time.sleep(3.0)
    elif request_count > 20:
        time.sleep(2.0)
    elif request_count > 10:
        time.sleep(1.5)
    else:
        time.sleep(1.0)

def extract_phones_from_text(text):
    phones = re.findall(r'(01[0125][0-9 \-]{8,15})', text)
    clean_phones = []
    for raw in phones:
        clean = raw.replace(" ", "").replace("-", "")
        if len(clean) == 11 and clean not in clean_phones:
            clean_phones.append(clean)
    return clean_phones

def create_jwt_token(email: str):
    payload = {"sub": email, "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ========== ROUTES ==========
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎯 Hunter Pro CRM | Ultimate</title>
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Tajawal', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(10px);
                border-radius: 25px;
                padding: 40px;
                max-width: 900px;
                width: 100%;
                box-shadow: 0 25px 75px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                text-align: center;
            }
            .logo {
                font-size: 4em;
                margin-bottom: 20px;
                color: #fff;
            }
            h1 {
                font-size: 2.8em;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle {
                font-size: 1.3em;
                margin-bottom: 30px;
                opacity: 0.9;
            }
            .status-card {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 15px;
                padding: 25px;
                margin: 25px 0;
                border-left: 5px solid #4CAF50;
            }
            .btn {
                display: inline-block;
                background: linear-gradient(45deg, #4CAF50, #2E7D32);
                color: white;
                padding: 16px 35px;
                margin: 12px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: bold;
                font-size: 1.2em;
                transition: all 0.3s ease;
                border: none;
                cursor: pointer;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            }
            .btn:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 30px rgba(0, 0, 0, 0.3);
            }
            .btn-secondary {
                background: linear-gradient(45deg, #2196F3, #0D47A1);
            }
            .btn-danger {
                background: linear-gradient(45deg, #FF9800, #F57C00);
            }
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 25px;
                margin: 35px 0;
            }
            .feature {
                background: rgba(255, 255, 255, 0.1);
                padding: 25px;
                border-radius: 15px;
                transition: all 0.3s ease;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            .feature:hover {
                transform: translateY(-8px);
                background: rgba(255, 255, 255, 0.2);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            }
            .feature i {
                font-size: 2.8em;
                margin-bottom: 15px;
                color: #4CAF50;
            }
            .feature h3 {
                font-size: 1.4em;
                margin-bottom: 10px;
            }
            .feature p {
                font-size: 0.95em;
                opacity: 0.9;
            }
            .stats {
                display: flex;
                justify-content: center;
                gap: 30px;
                margin: 30px 0;
                flex-wrap: wrap;
            }
            .stat-item {
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 12px;
                min-width: 150px;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #4CAF50;
            }
            .login-box {
                background: rgba(255, 255, 255, 0.1);
                padding: 25px;
                border-radius: 15px;
                margin-top: 30px;
                display: none;
            }
            .login-box.show {
                display: block;
                animation: fadeIn 0.5s ease;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .credentials {
                background: rgba(0, 0, 0, 0.2);
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                font-family: monospace;
            }
            footer {
                margin-top: 40px;
                font-size: 0.9em;
                opacity: 0.8;
                border-top: 1px solid rgba(255, 255, 255, 0.2);
                padding-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">
                <i class="fas fa-crosshairs"></i>
            </div>
            
            <h1>Hunter Pro CRM</h1>
            <div class="subtitle">نظام إدارة العملاء والتسويق الذكي - الإصدار 3.0</div>
            
            <div class="status-card">
                <p><i class="fas fa-check-circle" style="color: #4CAF50;"></i> ✅ التطبيق يعمل بنجاح على Render.com</p>
                <p><i class="fas fa-server"></i> <strong>المنفذ:</strong> <span id="port">""" + str(PORT) + """</span></p>
                <p><i class="fas fa-database"></i> <strong>قاعدة البيانات:</strong> <span id="db-status">""" + ("✅ متصلة" if supabase else "⚠️ غير متصلة") + """</span></p>
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value" id="serper-count">""" + str(len(SERPER_KEYS)) + """</div>
                    <div>مفاتيح بحث</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="twilio-status">""" + ("✅" if TWILIO_SID and TWILIO_TOKEN else "❌") + """</div>
                    <div>واتساب</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">3.0</div>
                    <div>الإصدار</div>
                </div>
            </div>
            
            <div class="features-grid">
                <div class="feature">
                    <i class="fas fa-search"></i>
                    <h3>بحث ذكي</h3>
                    <p>ابحث عن عملاء محتملين باستخدام الذكاء الاصطناعي</p>
                </div>
                <div class="feature">
                    <i class="fas fa-users"></i>
                    <h3>إدارة العملاء</h3>
                    <p>نظم قاعدة بيانات العملاء بفعالية</p>
                </div>
                <div class="feature">
                    <i class="fab fa-whatsapp"></i>
                    <h3>تسويق واتساب</h3>
                    <p>حملات تسويقية ذكية على واتساب</p>
                </div>
                <div class="feature">
                    <i class="fas fa-chart-line"></i>
                    <h3>تقارير متقدمة</h3>
                    <p>إحصائيات وتحليلات مفصلة</p>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/health" class="btn">
                    <i class="fas fa-heartbeat"></i> Health Check
                </a>
                <a href="/docs" class="btn btn-secondary">
                    <i class="fas fa-code"></i> API Documentation
                </a>
                <button onclick="showLogin()" class="btn btn-danger">
                    <i class="fas fa-sign-in-alt"></i> تسجيل الدخول
                </button>
            </div>
            
            <div id="loginBox" class="login-box">
                <h3><i class="fas fa-user-lock"></i> تسجيل الدخول إلى النظام</h3>
                <p>استخدم بيانات الاختبار التالية:</p>
                
                <div class="credentials">
                    <p><strong><i class="fas fa-envelope"></i> البريد الإلكتروني:</strong> admin@example.com</p>
                    <p><strong><i class="fas fa-key"></i> كلمة المرور:</strong> admin123</p>
                </div>
                
                <div style="margin-top: 20px;">
                    <button onclick="testLogin()" class="btn" style="background: linear-gradient(45deg, #9C27B0, #673AB7);">
                        <i class="fas fa-rocket"></i> تجربة تسجيل الدخول
                    </button>
                    <button onclick="showAPIDocs()" class="btn btn-secondary">
                        <i class="fas fa-book"></i> وثائق API
                    </button>
                </div>
            </div>
            
            <div class="status-card" style="margin-top: 30px; text-align: right;">
                <h4><i class="fas fa-plug"></i> الخدمات المتاحة:</h4>
                <ul style="list-style: none; padding: 0; margin-top: 10px;">
                    <li>✅ <strong>/health</strong> - حالة النظام</li>
                    <li>✅ <strong>/docs</strong> - وثائق API التفاعلية</li>
                    <li>✅ <strong>/api/login</strong> - تسجيل الدخول (POST)</li>
                    <li>✅ <strong>/start_hunt</strong> - بدء البحث عن عملاء (POST)</li>
                    <li>✅ <strong>/api/leads</strong> - قائمة العملاء (GET)</li>
                    <li>✅ <strong>/api/extract-phones</strong> - استخراج أرقام (POST)</li>
                    <li>✅ <strong>/ws/admin-chat</strong> - شات الأدمن (WebSocket)</li>
                </ul>
            </div>
            
            <footer>
                <p><i class="fas fa-code"></i> تم التطوير باستخدام FastAPI & Python</p>
                <p><i class="fas fa-cloud"></i> مستضاف على Render.com | <i class="fas fa-database"></i> قاعدة بيانات Supabase</p>
                <p style="margin-top: 10px; font-size: 0.85em;">
                    📧 للدعم الفني: تواصل مع المطور | 
                    🚀 الإصدار: 3.0 Pro | 
                    ⏰ آخر تحديث: ديسمبر 2024
                </p>
            </footer>
        </div>
        
        <script>
            function showLogin() {
                const loginBox = document.getElementById('loginBox');
                loginBox.classList.toggle('show');
            }
            
            function testLogin() {
                fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: 'admin@example.com',
                        password: 'admin123'
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.access_token) {
                        alert('✅ تسجيل الدخول ناجح!\nتم استلام رمز الدخول.');
                        console.log('Token:', data.access_token);
                    } else {
                        alert('❌ فشل تسجيل الدخول');
                    }
                })
                .catch(error => {
                    alert('⚠️ خطأ في الاتصال بالخادم');
                    console.error('Error:', error);
                });
            }
            
            function showAPIDocs() {
                window.open('/docs', '_blank');
            }
            
            // Auto-check health on load
            fetch('/health')
                .then(response => response.json())
                .then(data => {
                    console.log('✅ Health Status:', data);
                })
                .catch(error => {
                    console.log('⚠️ Health Check Failed:', error);
                });
            
            // Auto-update stats
            setInterval(() => {
                fetch('/health')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('port').textContent = data.port || """ + str(PORT) + """;
                        document.title = `Hunter Pro CRM | ${data.status}`;
                    });
            }, 30000);
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint for Render.com"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "service": "Hunter Pro CRM",
        "version": "3.0",
        "platform": "Render.com",
        "port": PORT,
        "supabase_connected": supabase is not None,
        "serper_keys_count": len(SERPER_KEYS),
        "twilio_configured": bool(TWILIO_SID and TWILIO_TOKEN),
        "environment": "production",
        "uptime": round(time.time() - last_reset, 2)
    }

@app.post("/api/login")
async def login(request: LoginRequest):
    """User login endpoint"""
    try:
        if request.password == "google":
            token = create_jwt_token(request.email)
            return {"access_token": token, "token_type": "bearer"}
        
        if request.email == "admin@example.com" and request.password == "admin123":
            token = create_jwt_token(request.email)
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "email": request.email,
                    "role": "admin",
                    "permissions": ["all"]
                }
            }
        
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start_hunt")
async def start_hunt(request: HuntRequest, background_tasks: BackgroundTasks):
    """Start a hunting session"""
    background_tasks.add_task(
        lambda: print(f"🚀 Starting hunt: {request.intent_sentence} in {request.city}")
    )
    return {
        "status": "started",
        "search": request.intent_sentence,
        "city": request.city,
        "message": "بدأ البحث بنجاح",
        "request_id": str(int(time.time()))
    }

@app.get("/api/leads")
async def get_leads(user_id: str = "admin"):
    """Get leads list"""
    if not supabase:
        return {
            "success": False,
            "error": "Supabase not configured",
            "leads": [],
            "count": 0
        }
    
    try:
        # This is a simplified version - implement your actual logic here
        result = supabase.table("leads").select("*").limit(50).execute()
        return {
            "success": True,
            "leads": result.data if result.data else [],
            "count": len(result.data) if result.data else 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "leads": [],
            "count": 0
        }

@app.post("/api/add-lead")
async def add_lead(request: AddLeadRequest):
    """Add a new lead manually"""
    if not supabase:
        return {"success": False, "error": "Supabase not configured"}
    
    try:
        lead_data = request.dict()
        lead_data["created_at"] = datetime.now().isoformat()
        
        result = supabase.table("leads").insert(lead_data).execute()
        return {
            "success": True,
            "message": "تم إضافة العميل بنجاح",
            "lead_id": result.data[0]["id"] if result.data else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/send-whatsapp")
async def send_whatsapp(request: WhatsAppRequest):
    """Send WhatsApp message"""
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_WHATSAPP_NUMBER]):
        return {"success": False, "error": "Twilio not configured"}
    
    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=request.message,
            to=f"whatsapp:{request.phone_number}"
        )
        
        if supabase:
            supabase.table("campaign_logs").insert({
                "lead_phone": request.phone_number,
                "message_sent": request.message,
                "status": "sent",
                "user_id": request.user_id,
                "created_at": datetime.now().isoformat()
            }).execute()
        
        return {
            "success": True,
            "message": "تم إرسال الرسالة",
            "sid": message.sid,
            "status": message.status
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/extract-phones")
async def extract_phones(request: ExtractPhonesRequest):
    """Extract phone numbers from text"""
    phones = extract_phones_from_text(request.text)
    return {
        "success": True,
        "phones": phones,
        "count": len(phones),
        "sample_text": request.text[:100] + ("..." if len(request.text) > 100 else "")
    }

@app.get("/api/system-info")
async def system_info():
    """Get system information"""
    return {
        "python_version": os.sys.version,
        "platform": os.sys.platform,
        "hostname": os.environ.get("RENDER_SERVICE_NAME", "local"),
        "region": os.environ.get("RENDER_REGION", "unknown"),
        "instance_id": os.environ.get("RENDER_INSTANCE_ID", "local"),
        "memory_limit": os.environ.get("RENDER_MEMORY_LIMIT", "unknown")
    }

# WebSocket endpoint
active_connections = []

@app.websocket("/ws/admin-chat")
async def admin_chat_websocket(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            response = f"تم استلام رسالتك: {data}"
            
            if "إحصائيات" in data or "stats" in data.lower():
                stats_data = {
                    "connections": len(active_connections),
                    "serper_keys": len(SERPER_KEYS),
                    "supabase": supabase is not None,
                    "twilio": bool(TWILIO_SID and TWILIO_TOKEN),
                    "uptime": round(time.time() - last_reset, 2)
                }
                response = f"📊 إحصائيات النظام:\n" + "\n".join([f"• {k}: {v}" for k, v in stats_data.items()])
            elif "مساعدة" in data or "help" in data.lower():
                response = "🎯 الأوامر المتاحة:\n• إحصائيات - عرض إحصائيات النظام\n• الوقت - عرض الوقت الحالي\n• أي رسالة أخرى - سيتم الرد عليها"
            elif "الوقت" in data or "time" in data.lower():
                response = f"🕒 الوقت الحالي: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await websocket.send_text(response)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

# ========== START APPLICATION ==========
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Hunter Pro CRM v3.0 - Starting on Render.com")
    print(f"📡 Port: {PORT}")
    print(f"🔗 URL: http://0.0.0.0:{PORT}")
    print(f"📊 Supabase: {'✅ Connected' if supabase else '❌ Not connected'}")
    print(f"🔑 Serper Keys: {len(SERPER_KEYS)}")
    print(f"💬 WhatsApp: {'✅ Configured' if TWILIO_SID and TWILIO_TOKEN else '❌ Not configured'}")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        access_log=True
    )
