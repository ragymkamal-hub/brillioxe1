from fastapi import FastAPI,BackgroundTasks,HTTPException,WebSocket,WebSocketDisconnect,UploadFile,File,Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional,List,Dict,Any
import os,re,json,requests,time,jwt
from datetime import datetime,timedelta
from supabase import create_client,Client
from twilio.rest import Client as TwilioClient
from passlib.context import CryptContext

SUPABASE_URL=os.environ.get("SUPABASE_URL")
SUPABASE_KEY=os.environ.get("SUPABASE_KEY")
SERPER_KEYS_RAW=os.environ.get("SERPER_KEYS","")
SERPER_KEYS=[k.strip().replace('"','') for k in SERPER_KEYS_RAW.split(',') if k.strip()]
TWILIO_SID=os.environ.get("TWILIO_SID")
TWILIO_TOKEN=os.environ.get("TWILIO_TOKEN")
TWILIO_WHATSAPP_NUMBER=os.environ.get("TWILIO_WHATSAPP_NUMBER")
JWT_SECRET=os.environ.get("JWT_SECRET","change-in-production")
JWT_ALGORITHM="HS256"

app=FastAPI(title="Hunter Pro CRM",version="2.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

# تهيئة قاعدة البيانات (إذا كانت المتغيرات موجودة)
if SUPABASE_URL and SUPABASE_KEY:
    supabase=create_client(SUPABASE_URL,SUPABASE_KEY)
    print("✅ Connected to Supabase")
else:
    supabase=None
    print("⚠️ Supabase not configured")

pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")
key_index=0
request_count=0
last_reset=time.time()
print("✅ Hunter Pro CRM - System Ready!")

class LoginRequest(BaseModel):
 email:str
 password:str

class HuntRequest(BaseModel):
 intent_sentence:str
 city:str
 time_filter:str="qdr:m"
 user_id:str="admin"
 mode:str="general"

class WhatsAppRequest(BaseModel):
 phone_number:str
 message:str
 user_id:str

class AddLeadRequest(BaseModel):
 phone_number:str
 full_name:str=""
 email:str=""
 source:str="Manual"
 quality:str="جيد ⭐"
 notes:str=""
 user_id:str
 status:str="NEW"

class ShareRequest(BaseModel):
 phone:str
 shared_with:List[str]=[]
 is_public:bool=False
 user_id:str

class CampaignCreate(BaseModel):
 name:str
 message:str
 user_id:str
 target_quality:List[str]=["ممتاز 🔥","جيد ⭐"]

class CampaignAction(BaseModel):
 campaign_id:str

class AdminCommand(BaseModel):
 command:str

class AddUserRequest(BaseModel):
 username:str
 password:str
 role:str="user"
 can_hunt:bool=True
 can_campaign:bool=True
 can_share:bool=False
 can_see_all_data:bool=False
 is_admin:bool=False

class UpdatePermissions(BaseModel):
 username:str
 can_hunt:bool
 can_campaign:bool
 can_share:bool
 can_see_all_data:bool
 is_admin:bool

class ExtractPhonesRequest(BaseModel):
 text:str

def get_active_key():
 global key_index
 if not SERPER_KEYS:return None
 key=SERPER_KEYS[key_index]
 key_index=(key_index+1)%len(SERPER_KEYS)
 return key

def safe_request_delay():
 global request_count,last_reset
 if time.time()-last_reset>60:
  request_count=0
  last_reset=time.time()
 request_count+=1
 if request_count>30:time.sleep(3.0)
 elif request_count>20:time.sleep(2.0)
 elif request_count>10:time.sleep(1.5)
 else:time.sleep(1.0)

def get_sub_locations(city):
 locations={"القاهرة":["التجمع","المعادي","مدينة نصر","مصر الجديدة","الزمالك","الرحاب","مدينتي","القاهرة الجديدة"],"الجيزة":["أكتوبر","الشيخ زايد","الهرم","المهندسين","الدقي","حدائق الأهرام"],"الإسكندرية":["سموحة","سيدي جابر","العجمي","المنتزه","ميامي"]}
 return locations.get(city,[city])

def analyze_quality(text):
 text=text.lower()
 blacklist=["للبيع","for sale","متاح الان","احجز الان","تواصل معنا","امتلك","فرصة","offer","discount","سمسار","broker","وكيل"]
 for word in blacklist:
  if word in text:return "TRASH"
 excellent=["مطلوب","محتاج","عايز","أبحث","شراء","كاش","wanted","buying","looking for","need","أريد"]
 for word in excellent:
  if word in text:return "ممتاز 🔥"
 good=["سعر","تفاصيل","price","details","بكام","معلومات"]
 for word in good:
  if word in text:return "جيد ⭐"
 return "TRASH"

def extract_phones_from_text(text):
 phones=re.findall(r'(01[0125][0-9 \-]{8,15})',text)
 clean_phones=[]
 for raw in phones:
  clean=raw.replace(" ","").replace("-","")
  if len(clean)==11 and clean not in clean_phones:clean_phones.append(clean)
 return clean_phones

def save_lead(phone,email,keyword,link,quality,user_id):
 if quality=="TRASH":
  print(f"   🗑️ Trash Skipped: {phone}")
  return False
 if not phone or len(phone)!=11:return False
 try:
  data={"phone_number":phone,"source":f"SmartHunt: {keyword}","quality":quality,"status":"NEW","notes":f"Link: {link}","user_id":user_id}
  if email:data["email"]=email
  if supabase:
      supabase.table("leads").upsert(data,on_conflict="phone_number").execute()
      print(f"   💎 SAVED: {phone} ({quality})")
      supabase.table("events").insert({"event":"new_lead","details":f"New lead added: {phone}","user_id":user_id}).execute()
      return True
  else:
      print(f"   ⚠️ No Supabase: {phone} ({quality})")
      return False
 except Exception as e:
  print(f"   ❌ Save Error: {e}")
  return False

def create_jwt_token(email:str):
 payload={"sub":email,"exp":datetime.utcnow()+timedelta(days=7)}
 return jwt.encode(payload,JWT_SECRET,algorithm=JWT_ALGORITHM)

def verify_jwt_token(token:str):
 try:
  payload=jwt.decode(token,JWT_SECRET,algorithms=[JWT_ALGORITHM])
  return payload.get("sub")
 except:return None

def run_hydra_hunt(intent:str,main_city:str,time_filter:str,user_id:str,mode:str):
 if not SERPER_KEYS:
  print("❌ No Serper API keys configured")
  return
 search_intent=intent
 if "شقة" in intent or "فيلا" in intent or "محل" in intent:
  if "مطلوب" not in intent:search_intent=f'مطلوب {intent}'
 sub_cities=get_sub_locations(main_city)
 print(f"🌍 Quality Hunt Started: {search_intent} in {sub_cities}")
 total_found=0
 domains_checked=0
 start_time=datetime.now()
 for area in sub_cities:
  queries=[f'site:facebook.com "{search_intent}" "{area}" "010"',f'site:facebook.com "{search_intent}" "{area}" "011"',f'site:facebook.com "{search_intent}" "{area}" "012"',f'site:facebook.com "{search_intent}" "{area}" "015"',f'site:olx.com.eg "{search_intent}" "{area}" "010"',f'"{search_intent}" "{area}" "مطلوب" "01"',f'"{search_intent}" "{area}" "wanted" "01"']
  for query in queries:
   api_key=get_active_key()
   if not api_key:break
   safe_request_delay()
   payload=json.dumps({"q":query,"num":100,"tbs":time_filter,"gl":"eg","hl":"ar"})
   headers={'X-API-KEY':api_key,'Content-Type':'application/json','User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
   try:
    print(f"🚀 Scanning: {query[:60]}...")
    response=requests.post("https://google.serper.dev/search",headers=headers,data=payload,timeout=30)
    if response.status_code==429:
     print("⚠️ Rate limit hit - waiting 10 seconds...")
     time.sleep(10)
     continue
    elif response.status_code!=200:
     print(f"❌ API Error: {response.status_code}")
     continue
    if response.status_code==200:
     results=response.json().get("organic",[])
     domains_checked+=len(results)
     for res in results:
      snippet=f"{res.get('title','')} {res.get('snippet','')}"
      quality=analyze_quality(snippet)
      if quality!="TRASH":
       phones=extract_phones_from_text(snippet)
       for phone in phones:
        if save_lead(phone,None,intent,res.get('link'),quality,user_id):total_found+=1
   except requests.exceptions.Timeout:
    print("⏰ Request timeout - continuing...")
    continue
   except Exception as e:
    print(f"   ⚠️ Error: {e}")
 duration=(datetime.now()-start_time).seconds
 try:
  if supabase:
      supabase.table("hunt_logs").insert({"user_id":user_id,"intent":intent,"city":main_city,"results_count":total_found,"domains_checked":domains_checked,"duration_seconds":duration,"mode":mode}).execute()
 except:pass
 print(f"🏁 Hunt Finished! Found: {total_found} diamonds | Checked: {domains_checked} domains | Time: {duration}s")

# ========== ROUTES ==========
@app.get("/",response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hunter Pro CRM | Ultimate</title>
        <style>
            body {
                font-family: 'Tajawal', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                text-align: center;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                max-width: 800px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            h1 {
                font-size: 3em;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle {
                font-size: 1.2em;
                margin-bottom: 30px;
                opacity: 0.9;
            }
            .status {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }
            .btn {
                display: inline-block;
                background: linear-gradient(45deg, #4CAF50, #2E7D32);
                color: white;
                padding: 15px 30px;
                margin: 10px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: bold;
                font-size: 1.1em;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
            }
            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
            }
            .btn-secondary {
                background: linear-gradient(45deg, #2196F3, #0D47A1);
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .feature {
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 10px;
                transition: transform 0.3s;
            }
            .feature:hover {
                transform: translateY(-5px);
                background: rgba(255, 255, 255, 0.2);
            }
            .icon {
                font-size: 2.5em;
                margin-bottom: 10px;
            }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        <div class="container">
            <div class="icon">
                <i class="fas fa-crosshairs"></i>
            </div>
            <h1>🎯 Hunter Pro CRM</h1>
            <div class="subtitle">نظام إدارة العملاء والتسويق الذكي</div>
            
            <div class="status">
                <p><i class="fas fa-check-circle" style="color: #4CAF50;"></i> ✅ التطبيق يعمل بنجاح على Fly.io</p>
                <p><i class="fas fa-server"></i> السيرفر: <strong>brillioxe1.fly.dev</strong></p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <div class="icon"><i class="fas fa-search"></i></div>
                    <h3>بحث ذكي</h3>
                    <p>ابحث عن عملاء محتملين باستخدام الذكاء الاصطناعي</p>
                </div>
                <div class="feature">
                    <div class="icon"><i class="fas fa-users"></i></div>
                    <h3>إدارة العملاء</h3>
                    <p>نظم قاعدة بيانات العملاء بفعالية</p>
                </div>
                <div class="feature">
                    <div class="icon"><i class="fab fa-whatsapp"></i></div>
                    <h3>تسويق واتساب</h3>
                    <p>حملات تسويقية ذكية على واتساب</p>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/health" class="btn">
                    <i class="fas fa-heartbeat"></i> Health Check
                </a>
                <a href="/docs" class="btn btn-secondary">
                    <i class="fas fa-code"></i> API Documentation
                </a>
                <button onclick="showLogin()" class="btn" style="background: linear-gradient(45deg, #FF9800, #F57C00);">
                    <i class="fas fa-sign-in-alt"></i> تسجيل الدخول
                </button>
            </div>
            
            <div id="loginForm" style="display: none; margin-top: 30px; background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px;">
                <h3><i class="fas fa-user-lock"></i> تسجيل الدخول</h3>
                <p>استخدم بيانات الاختبار:</p>
                <p><strong>البريد:</strong> admin@example.com</p>
                <p><strong>كلمة السر:</strong> admin123</p>
                <button onclick="window.location.href='/docs#/default/login_api_login_post'" class="btn" style="margin-top: 15px;">
                    <i class="fas fa-rocket"></i> الدخول إلى لوحة التحكم
                </button>
            </div>
            
            <div style="margin-top: 40px; font-size: 0.9em; opacity: 0.8;">
                <p>📞 للدعم: تواصل مع المطور | 📧 الإصدار: 3.0 Pro</p>
            </div>
        </div>
        
        <script>
            function showLogin() {
                document.getElementById('loginForm').style.display = 'block';
            }
            
            // Auto-check health
            fetch('/health')
                .then(response => response.json())
                .then(data => {
                    console.log('Health Status:', data);
                })
                .catch(error => {
                    console.log('Health Check Failed:', error);
                });
        </script>
    </body>
    </html>
    """

@app.get("/health")
def health_check():
    supabase_status = "connected" if supabase else "not_configured"
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "app": "Hunter Pro CRM",
        "version": "3.0",
        "supabase": supabase_status,
        "serper_keys": len(SERPER_KEYS),
        "twilio_configured": bool(TWILIO_SID and TWILIO_TOKEN),
        "environment": "production",
        "url": "https://brillioxe1.fly.dev"
    }

@app.post("/api/login")
async def login(req:LoginRequest):
 try:
  if req.password=="google":
   token=create_jwt_token(req.email)
   return {"access_token":token,"token_type":"bearer"}
  if req.email=="admin@example.com" and req.password=="admin123":
   token=create_jwt_token(req.email)
   return {"access_token":token,"token_type":"bearer"}
  raise HTTPException(status_code=401,detail="Invalid credentials")
 except HTTPException:raise
 except Exception as e:raise HTTPException(status_code=500,detail=str(e))

@app.post("/start_hunt")
@app.post("/hunt")
async def start_hunt(req:HuntRequest,background_tasks:BackgroundTasks):
 background_tasks.add_task(run_hydra_hunt,req.intent_sentence,req.city,req.time_filter,req.user_id,req.mode)
 return {"status":"started","search":req.intent_sentence,"city":req.city,"message":"بدأ البحث بنجاح"}

@app.get("/leads")
@app.get("/api/leads")
def get_leads(user_id:str="admin"):
 if not supabase:
     return {"success":False,"error":"Supabase not configured","leads":[]}
 try:
  user=supabase.table("users").select("can_see_all_data, is_admin").eq("username",user_id).execute()
  if user.data and(user.data[0].get("can_see_all_data")or user.data[0].get("is_admin")):
   rows=supabase.table("leads").select("*").order("created_at",desc=True).limit(500).execute()
  else:rows=supabase.table("leads").select("*").eq("user_id",user_id).order("created_at",desc=True).limit(500).execute()
  return {"success":True,"leads":rows.data}
 except Exception as e:return {"success":False,"error":str(e),"leads":[]}

@app.post("/add-lead")
@app.post("/api/add-lead")
def add_lead(req:AddLeadRequest):
 if not supabase:
     return {"success":False,"error":"Supabase not configured"}
 try:
  supabase.table("leads").insert(req.dict()).execute()
  supabase.table("events").insert({"event":"manual_lead_added","details":f"Manual lead: {req.phone_number}","user_id":req.user_id}).execute()
  return {"success":True,"message":"تم إضافة العميل بنجاح"}
 except Exception as e:return {"success":False,"error":str(e)}

@app.post("/send-whatsapp")
@app.post("/api/send-whatsapp")
async def send_whatsapp(req:WhatsAppRequest):
 if not all([TWILIO_SID,TWILIO_TOKEN,TWILIO_WHATSAPP_NUMBER]):return {"success":False,"error":"Twilio not configured"}
 try:
  client=TwilioClient(TWILIO_SID,TWILIO_TOKEN)
  message=client.messages.create(from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",body=req.message,to=f"whatsapp:{req.phone_number}")
  if supabase:
      supabase.table("campaign_logs").insert({"lead_phone":req.phone_number,"message_sent":req.message,"status":"sent","user_id":req.user_id}).execute()
  return {"success":True,"message":"تم إرسال الرسالة","sid":message.sid}
 except Exception as e:return {"success":False,"error":str(e)}

@app.post("/api/create-campaign")
async def create_campaign(name:str=Form(...),message:str=Form(...),user_id:str=Form(...),media:Optional[UploadFile]=File(None)):
 if not supabase:
     return {"success":False,"reply":"Supabase not configured"}
 try:
  campaign_data={"name":name,"message":message,"user_id":user_id,"status":"draft","sent_count":0,"delivered_count":0}
  if media:campaign_data["media_url"]=f"/media/{media.filename}"
  result=supabase.table("whatsapp_campaigns").insert(campaign_data).execute()
  return {"success":True,"reply":"تم إنشاء الحملة بنجاح","campaign_id":result.data[0]["id"]}
 except Exception as e:return {"success":False,"reply":f"خطأ: {str(e)}"}

@app.get("/api/my-campaigns")
def get_my_campaigns(user_id:str="admin"):
 if not supabase:
     return {"success":False,"campaigns":[],"error":"Supabase not configured"}
 try:
  result=supabase.table("whatsapp_campaigns").select("*").eq("user_id",user_id).order("created_at",desc=True).execute()
  return {"success":True,"campaigns":result.data}
 except Exception as e:return {"success":False,"campaigns":[],"error":str(e)}

@app.post("/api/send-campaign")
async def send_campaign(req:CampaignAction,background_tasks:BackgroundTasks):
 if not supabase:
     return {"success":False,"reply":"Supabase not configured"}
 try:
  campaign=supabase.table("whatsapp_campaigns").select("*").eq("id",req.campaign_id).execute()
  if not campaign.data:return {"success":False,"reply":"الحملة غير موجودة"}
  campaign_data=campaign.data[0]
  leads=supabase.table("leads").select("phone_number").eq("user_id",campaign_data["user_id"]).execute()
  sent_count=0
  for lead in leads.data[:10]:
   try:
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_WHATSAPP_NUMBER:
        client=TwilioClient(TWILIO_SID,TWILIO_TOKEN)
        client.messages.create(from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",body=campaign_data["message"],to=f"whatsapp:{lead['phone_number']}")
        sent_count+=1
   except:pass
  supabase.table("whatsapp_campaigns").update({"status":"sent","sent_count":sent_count}).eq("id",req.campaign_id).execute()
  return {"success":True,"reply":f"تم إرسال {sent_count} رسالة"}
 except Exception as e:return {"success":False,"reply":f"خطأ: {str(e)}"}

@app.delete("/api/delete-campaign")
async def delete_campaign(req:CampaignAction):
 if not supabase:
     return {"success":False,"reply":"Supabase not configured"}
 try:
  supabase.table("whatsapp_campaigns").delete().eq("id",req.campaign_id).execute()
  return {"success":True,"reply":"تم حذف الحملة"}
 except Exception as e:return {"success":False,"reply":f"خطأ: {str(e)}"}

@app.post("/share-lead")
@app.post("/api/share-lead")
def share_lead(req:ShareRequest):
 if not supabase:
     return {"success":False,"error":"Supabase not configured"}
 try:
  if req.is_public:
   share_link=f"/public/lead/{req.phone}"
   supabase.table("leads").update({"is_public":True}).eq("phone_number",req.phone).eq("user_id",req.user_id).execute()
   return {"success":True,"share_link":share_link}
  supabase.table("leads").update({"shared_with":req.shared_with}).eq("phone_number",req.phone).eq("user_id",req.user_id).execute()
  return {"success":True,"message":f"تمت المشاركة مع {', '.join(req.shared_with)}"}
 except Exception as e:return {"success":False,"error":str(e)}

@app.get("/public/lead/{phone}")
def get_public_lead(phone:str):
 if not supabase:
     return {"success":False,"message":"Database not configured"}
 try:
  row=supabase.table("leads").select("*").eq("phone_number",phone).eq("is_public",True).execute()
  if row.data:return {"success":True,"lead":row.data[0]}
  return {"success":False,"message":"غير مسموح بالمشاهدة"}
 except:return {"success":False,"message":"خطأ في البيانات"}

@app.get("/api/lead-share-status")
def lead_share_status(phone:str):
 if not supabase:
     return {"success":False}
 try:
  row=supabase.table("leads").select("shared_with, is_public, created_at, user_id").eq("phone_number",phone).execute()
  if row.data:
   data=row.data[0]
   return {"success":True,"share_status":"مشارك عام" if data.get("is_public")else("مشارك" if data.get("shared_with")else "غير مشارك"),"share_date":data.get("created_at"),"share_by":data.get("user_id")}
  return {"success":False}
 except:return {"success":False}

@app.post("/api/cancel-share")
def cancel_share(req:dict):
 if not supabase:
     return {"success":False,"error":"Supabase not configured"}
 try:
  supabase.table("leads").update({"shared_with":[],"is_public":False}).eq("phone_number",req["phone"]).eq("user_id",req["user_id"]).execute()
  return {"success":True,"message":"تم إلغاء المشاركة"}
 except Exception as e:return {"success":False,"error":str(e)}

@app.post("/api/extract-phones")
def extract_phones(req:ExtractPhonesRequest):
 phones=extract_phones_from_text(req.text)
 return {"success":True,"phones":phones}

@app.get("/admin-stats")
@app.get("/api/admin-stats")
def admin_stats(user_id:str="admin"):
 if not supabase:
     return {"total_users":0,"total_leads":0,"total_messages":0}
 try:
  total_users=supabase.table("users").select("id",count="exact").execute().count or 0
  total_leads=supabase.table("leads").select("id",count="exact").execute().count or 0
  total_messages=supabase.table("campaign_logs").select("id",count="exact").execute().count or 0
  return {"total_users":total_users,"total_leads":total_leads,"total_messages":total_messages}
 except:return {"total_users":0,"total_leads":0,"total_messages":0}

@app.get("/last-events")
@app.get("/api/last-events")
def last_events():
 if not supabase:
     return {"success":False,"events":[]}
 try:
  events=supabase.table("events").select("*").order("created_at",desc=True).limit(10).execute()
  return {"success":True,"events":events.data}
 except:return {"success":False,"events":[]}

@app.post("/add-user")
@app.post("/api/add-user")
def add_user(req:AddUserRequest):
 if not supabase:
     return {"success":False,"error":"Supabase not configured"}
 try:
  hashed_password=pwd_context.hash(req.password)
  user_data=req.dict()
  user_data["password"]=hashed_password
  supabase.table("users").insert(user_data).execute()
  return {"success":True,"message":"تم إضافة المستخدم"}
 except Exception as e:return {"success":False,"error":str(e)}

@app.post("/delete-user")
@app.post("/api/delete-user")
def delete_user(username:str):
 if not supabase:
     return {"success":False,"error":"Supabase not configured"}
 try:
  supabase.table("users").delete().eq("username",username).execute()
  return {"success":True,"message":"تم حذف المستخدم"}
 except Exception as e:return {"success":False,"error":str(e)}

@app.post("/update-permissions")
@app.post("/api/update-permissions")
def update_permissions(req:UpdatePermissions):
 if not supabase:
     return {"success":False,"error":"Supabase not configured"}
 try:
  supabase.table("users").update({"can_hunt":req.can_hunt,"can_campaign":req.can_campaign,"can_share":req.can_share,"can_see_all_data":req.can_see_all_data,"is_admin":req.is_admin}).eq("username",req.username).execute()
  return {"success":True,"message":"تم تحديث الصلاحيات"}
 except Exception as e:return {"success":False,"error":str(e)}

active_connections:List[WebSocket]=[]
@app.websocket("/ws/admin-chat")
async def admin_chat_websocket(websocket:WebSocket):
 await websocket.accept()
 active_connections.append(websocket)
 try:
  while True:
   data=await websocket.receive_text()
   response=f"تم استلام رسالتك: {data}"
   if "إحصائيات" in data or "stats" in data.lower():
    stats=admin_stats()
    response=f"📊 إحصائيات النظام:\n• إجمالي المستخدمين: {stats['total_users']}\n• إجمالي العملاء: {stats['total_leads']}\n• إجمالي الرسائل: {stats['total_messages']}"
   await websocket.send_text(response)
 except WebSocketDisconnect:active_connections.remove(websocket)

@app.post("/api/admin-command")
async def admin_command(req:AdminCommand):
 try:
  command=req.command.lower()
  if command.startswith('/stats'):
   stats=admin_stats()
   return {"reply":f"📊 الإحصائيات:\nالمستخدمين: {stats['total_users']}\nالعملاء: {stats['total_leads']}\nالرسائل: {stats['total_messages']}"}
  elif command.startswith('/help'):return {"reply":"🎯 الأوامر المتاحة:\n/stats - عرض الإحصائيات\n/help - عرض المساعدة\n/users - قائمة المستخدمين"}
  elif command.startswith('/users'):
   if supabase:
       users=supabase.table("users").select("username, role").execute()
       user_list="\n".join([f"• {u['username']} ({u['role']})" for u in users.data])
       return {"reply":f"👥 المستخدمين:\n{user_list}"}
   else:
       return {"reply": "❌ قاعدة البيانات غير متصلة"}
  else:return {"reply":"❌ أمر غير معروف. استخدم /help لعرض الأوامر المتاحة"}
 except Exception as e:return {"reply":f"❌ خطأ: {str(e)}"}

if __name__=="__main__":
 import uvicorn
 uvicorn.run(app,host="0.0.0.0",port=8080)
