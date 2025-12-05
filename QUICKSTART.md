# 🚀 Hunter Pro CRM - دليل البدء السريع

## ⚡ البدء في 5 دقائق

### 1️⃣ التحضير (دقيقة واحدة)

قم بإنشاء حسابات مجانية على:
- [Supabase](https://supabase.com) - قاعدة البيانات
- [Serper.dev](https://serper.dev) - بحث Google
- [Twilio](https://twilio.com) - واتساب (اختياري)

---

### 2️⃣ إعداد قاعدة البيانات (دقيقتان)

#### افتح Supabase SQL Editor والصق:

```sql
-- جدول المستخدمين
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    is_admin BOOLEAN DEFAULT false,
    can_hunt BOOLEAN DEFAULT true,
    can_campaign BOOLEAN DEFAULT true,
    can_share BOOLEAN DEFAULT false,
    can_see_all_data BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- جدول العملاء
CREATE TABLE leads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    full_name TEXT,
    email TEXT,
    source TEXT,
    quality TEXT,
    status TEXT DEFAULT 'NEW',
    notes TEXT,
    user_id TEXT,
    is_public BOOLEAN DEFAULT false,
    shared_with TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- جدول الحملات
CREATE TABLE whatsapp_campaigns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_name TEXT NOT NULL,
    message_template TEXT NOT NULL,
    target_quality TEXT[],
    user_id TEXT,
    status TEXT DEFAULT 'draft',
    sent_count INTEGER DEFAULT 0,
    delivered_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    media_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- سجلات الحملات
CREATE TABLE campaign_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_id UUID REFERENCES whatsapp_campaigns(id),
    lead_phone TEXT,
    message_sent TEXT,
    status TEXT,
    error_message TEXT,
    response_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- سجلات البحث
CREATE TABLE hunt_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT,
    intent TEXT,
    city TEXT,
    results_count INTEGER,
    duration_seconds INTEGER,
    mode TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- سجل الأحداث
CREATE TABLE events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event TEXT,
    details TEXT,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- إدراج مستخدم أدمن تجريبي
INSERT INTO users (username, password, role, is_admin, can_hunt, can_campaign, can_share, can_see_all_data)
VALUES ('admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7xj7ewqhYK', 'admin', true, true, true, true, true);
-- كلمة المرور: admin123
```

✅ انقر "Run" لتنفيذ الأوامر

---

### 3️⃣ نسخ المشروع (دقيقة واحدة)

```bash
git clone https://github.com/your-username/hunter-pro-crm.git
cd hunter-pro-crm
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### 4️⃣ إعداد المتغيرات البيئية (دقيقة واحدة)

انسخ ملف `.env.example` إلى `.env`:
```bash
cp .env.example .env
```

افتح `.env` وعدّل:

```env
# من Supabase Dashboard -> Settings -> API
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# من Serper.dev Dashboard
SERPER_KEYS=your-key-1,your-key-2

# من Twilio Console (اختياري)
TWILIO_SID=ACxxxxx
TWILIO_TOKEN=xxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886

# أي مفتاح سري طويل
JWT_SECRET=change-this-to-random-string
```

---

### 5️⃣ التشغيل! ⚡

```bash
uvicorn main:app --reload
```

افتح المتصفح:
```
http://localhost:8000
```

---

## 🎯 أول استخدام

### تسجيل الدخول
- **البريد**: `admin@example.com`
- **كلمة السر**: `admin123`

### تجربة البحث
1. انقر "بحث سريع"
2. أدخل: `مطلوب شقة في التجمع`
3. اختر "القاهرة"
4. انقر "بدء البحث"
5. انتظر دقائق... سيتم إضافة العملاء تلقائياً!

---

## 📱 تفعيل واتساب (اختياري)

### الطريقة السريعة - Twilio Sandbox

1. اذهب إلى [Twilio Console](https://console.twilio.com)
2. افتح **Messaging -> Try it out -> Send a WhatsApp message**
3. أرسل رسالة من هاتفك إلى رقم Twilio
4. الصق المفاتيح في `.env`

### الطريقة المتقدمة - رقم حقيقي

1. احصل على **Twilio WhatsApp Business Account**
2. راجع [توثيق Twilio](https://www.twilio.com/docs/whatsapp)

---

## 🚢 النشر على Render.com

### خطوة واحدة فقط!

1. اذهب إلى [Render.com](https://render.com)
2. **New -> Web Service**
3. ربط GitHub repo
4. Render سيكتشف `render.yaml` تلقائياً
5. أضف المتغيرات البيئية
6. انقر **Deploy**

✅ موقعك جاهز في دقائق!

---

## 🐛 حل المشاكل الشائعة

### ❌ خطأ: "Module not found"
```bash
pip install -r requirements.txt
```

### ❌ خطأ: "Supabase connection failed"
- تأكد من `SUPABASE_URL` و `SUPABASE_KEY` صحيحين
- جرب الاتصال يدوياً من [Supabase Dashboard](https://supabase.com)

### ❌ خطأ: "No Serper keys configured"
- أضف على الأقل مفتاح واحد في `SERPER_KEYS`
- احصل على مفتاح مجاني من [Serper.dev](https://serper.dev)

### ❌ البحث لا يعطي نتائج
- تأكد من جملة البحث واضحة (مثال: "مطلوب شقة")
- جرب مدينة مختلفة
- تحقق من أن مفاتيح Serper صالحة

### ❌ واتساب لا يعمل
- تأكد من إعداد Twilio Sandbox صحيح
- تحقق من أن الرقم بصيغة صحيحة (+201234567890)
- راجع [Twilio Console](https://console.twilio.com) للأخطاء

---

## 📚 الخطوات التالية

### تعلم المزيد
- 📖 [README.md](README.md) - الدليل الكامل
- 📚 [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - توثيق API
- 💻 [Swagger UI](http://localhost:8000/docs) - واجهة API تفاعلية

### إضافة ميزات
- 🤖 تفعيل AI Chat Bot
- 📊 تقارير Excel/PDF
- 📧 تكامل البريد الإلكتروني
- 📲 تطبيق موبايل

---

## 💬 الدعم

واجهت مشكلة؟
- 📧 افتح [Issue على GitHub](https://github.com/your-username/hunter-pro-crm/issues)
- 💬 تواصل مع المطور

---

## ✅ Checklist

- [ ] أنشأت قاعدة بيانات Supabase
- [ ] أنشأت حساب Serper.dev
- [ ] نسخت المشروع
- [ ] أضفت المتغيرات البيئية
- [ ] شغلت التطبيق
- [ ] جربت البحث
- [ ] نشرت على Render (اختياري)

---

**🎉 تهانينا! أنت الآن جاهز لاستخدام Hunter Pro CRM**

**صُنع بـ ❤️ في مصر**
