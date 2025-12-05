# 📚 Hunter Pro CRM - API Documentation

## Base URL
```
https://your-domain.com
```

---

## 🔐 Authentication

### POST `/api/login`
تسجيل الدخول والحصول على JWT Token

**Request Body:**
```json
{
  "email": "admin@example.com",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Headers للطلبات المصادق عليها:**
```
Authorization: Bearer <your_token>
```

---

## 🔍 Search & Hunting

### POST `/hunt` or `/start_hunt`
بدء عملية بحث عن عملاء جدد

**Request Body:**
```json
{
  "intent_sentence": "مطلوب شقة في التجمع",
  "city": "القاهرة",
  "time_filter": "qdr:m",
  "user_id": "admin",
  "mode": "general"
}
```

**Parameters:**
- `intent_sentence` (string, required): جملة البحث
- `city` (string, required): المدينة
- `time_filter` (string, optional): فلتر الوقت (qdr:m = شهر، qdr:w = أسبوع)
- `user_id` (string, optional): معرف المستخدم
- `mode` (string, optional): نمط البحث

**Response:**
```json
{
  "status": "started",
  "search": "مطلوب شقة في التجمع",
  "city": "القاهرة",
  "message": "بدأ البحث بنجاح"
}
```

---

## 👥 Leads Management

### GET `/leads` or `/api/leads`
جلب قائمة العملاء

**Query Parameters:**
- `user_id` (string, optional): معرف المستخدم

**Response:**
```json
{
  "success": true,
  "leads": [
    {
      "id": "uuid",
      "phone_number": "01012345678",
      "full_name": "أحمد محمد",
      "email": "ahmed@example.com",
      "source": "SmartHunt: شقة",
      "quality": "ممتاز 🔥",
      "status": "NEW",
      "notes": "عميل مهتم",
      "user_id": "admin",
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

### POST `/add-lead` or `/api/add-lead`
إضافة عميل جديد يدوياً

**Request Body:**
```json
{
  "phone_number": "01012345678",
  "full_name": "أحمد محمد",
  "email": "ahmed@example.com",
  "source": "Manual",
  "quality": "جيد ⭐",
  "notes": "تم التواصل معه",
  "user_id": "admin",
  "status": "NEW"
}
```

**Response:**
```json
{
  "success": true,
  "message": "تم إضافة العميل بنجاح"
}
```

---

## 📱 WhatsApp

### POST `/send-whatsapp` or `/api/send-whatsapp`
إرسال رسالة واتساب

**Request Body:**
```json
{
  "phone_number": "+201012345678",
  "message": "مرحباً! لدينا عرض خاص لك",
  "user_id": "admin"
}
```

**Response:**
```json
{
  "success": true,
  "message": "تم إرسال الرسالة",
  "sid": "SM9e5da4c2c3b3b9b3b3b3b3b3b"
}
```

---

## 📤 Campaigns

### POST `/api/create-campaign`
إنشاء حملة جديدة

**Content-Type:** `multipart/form-data`

**Form Data:**
- `name` (string, required): اسم الحملة
- `message` (string, required): نص الرسالة
- `user_id` (string, required): معرف المستخدم
- `media` (file, optional): صورة أو فيديو

**Response:**
```json
{
  "success": true,
  "reply": "تم إنشاء الحملة بنجاح",
  "campaign_id": "uuid"
}
```

### GET `/api/my-campaigns`
جلب حملات المستخدم

**Query Parameters:**
- `user_id` (string, optional): معرف المستخدم

**Response:**
```json
{
  "success": true,
  "campaigns": [
    {
      "id": "uuid",
      "name": "حملة العقارات",
      "message": "مرحباً...",
      "status": "draft",
      "sent_count": 0,
      "delivered_count": 0,
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

### POST `/api/send-campaign`
إرسال الحملة

**Request Body:**
```json
{
  "campaign_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "reply": "تم إرسال 10 رسالة"
}
```

### DELETE `/api/delete-campaign`
حذف حملة

**Request Body:**
```json
{
  "campaign_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "reply": "تم حذف الحملة"
}
```

---

## 🔧 Utilities

### POST `/api/extract-phones`
استخراج أرقام من نص

**Request Body:**
```json
{
  "text": "اتصل على 01012345678 أو 01123456789"
}
```

**Response:**
```json
{
  "success": true,
  "phones": ["01012345678", "01123456789"]
}
```

---

## 🔗 Sharing

### POST `/share-lead` or `/api/share-lead`
مشاركة عميل

**Request Body (مشاركة داخلية):**
```json
{
  "phone": "01012345678",
  "shared_with": ["user1", "user2"],
  "is_public": false,
  "user_id": "admin"
}
```

**Request Body (مشاركة عامة):**
```json
{
  "phone": "01012345678",
  "is_public": true,
  "user_id": "admin"
}
```

**Response (مشاركة عامة):**
```json
{
  "success": true,
  "share_link": "/public/lead/01012345678"
}
```

### GET `/public/lead/{phone}`
عرض عميل مشارك عامياً

**Response:**
```json
{
  "success": true,
  "lead": {
    "phone_number": "01012345678",
    "full_name": "أحمد محمد",
    "quality": "ممتاز 🔥"
  }
}
```

### GET `/api/lead-share-status`
حالة مشاركة العميل

**Query Parameters:**
- `phone` (string, required): رقم الهاتف

**Response:**
```json
{
  "success": true,
  "share_status": "مشارك",
  "share_date": "2024-01-01T12:00:00",
  "share_by": "admin"
}
```

### POST `/api/cancel-share`
إلغاء المشاركة

**Request Body:**
```json
{
  "phone": "01012345678",
  "user_id": "admin"
}
```

**Response:**
```json
{
  "success": true,
  "message": "تم إلغاء المشاركة"
}
```

---

## 📊 Statistics

### GET `/admin-stats` or `/api/admin-stats`
إحصائيات النظام

**Query Parameters:**
- `user_id` (string, optional): معرف المستخدم

**Response:**
```json
{
  "total_users": 10,
  "total_leads": 500,
  "total_messages": 1000
}
```

### GET `/last-events` or `/api/last-events`
آخر الأحداث

**Response:**
```json
{
  "success": true,
  "events": [
    {
      "event": "new_lead",
      "details": "New lead added: 01012345678",
      "timestamp": "2024-01-01T12:00:00"
    }
  ]
}
```

---

## 👤 User Management

### POST `/add-user` or `/api/add-user`
إضافة مستخدم جديد

**Request Body:**
```json
{
  "username": "user1",
  "password": "password123",
  "role": "user",
  "can_hunt": true,
  "can_campaign": true,
  "can_share": false,
  "can_see_all_data": false,
  "is_admin": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "تم إضافة المستخدم"
}
```

### POST `/delete-user` or `/api/delete-user`
حذف مستخدم

**Query Parameters:**
- `username` (string, required): اسم المستخدم

**Response:**
```json
{
  "success": true,
  "message": "تم حذف المستخدم"
}
```

### POST `/update-permissions` or `/api/update-permissions`
تحديث صلاحيات مستخدم

**Request Body:**
```json
{
  "username": "user1",
  "can_hunt": true,
  "can_campaign": true,
  "can_share": true,
  "can_see_all_data": false,
  "is_admin": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "تم تحديث الصلاحيات"
}
```

---

## 💬 Admin Chat

### WebSocket `/ws/admin-chat`
شات الأدمن الفوري

**Connection:**
```javascript
const ws = new WebSocket('wss://your-domain.com/ws/admin-chat');

ws.onopen = () => {
  ws.send('مرحباً!');
};

ws.onmessage = (event) => {
  console.log('Response:', event.data);
};
```

### POST `/api/admin-command`
تنفيذ أوامر الأدمن

**Request Body:**
```json
{
  "command": "/stats"
}
```

**Available Commands:**
- `/stats` - عرض الإحصائيات
- `/help` - عرض المساعدة
- `/users` - قائمة المستخدمين

**Response:**
```json
{
  "reply": "📊 الإحصائيات:\nالمستخدمين: 10\nالعملاء: 500..."
}
```

---

## 🏥 Health Check

### GET `/health`
فحص صحة النظام

**Response:**
```json
{
  "status": "running",
  "timestamp": "2024-01-01T12:00:00",
  "serper_keys": 3,
  "twilio_configured": true
}
```

---

## 🚨 Error Responses

### Standard Error Format
```json
{
  "success": false,
  "error": "Error message here"
}
```

### HTTP Status Codes
- `200 OK` - نجاح الطلب
- `201 Created` - تم الإنشاء بنجاح
- `400 Bad Request` - بيانات غير صحيحة
- `401 Unauthorized` - غير مصرح
- `404 Not Found` - لم يتم العثور على المورد
- `500 Internal Server Error` - خطأ في الخادم

---

## 📝 Notes

1. جميع التواريخ بصيغة ISO 8601
2. أرقام الهواتف يجب أن تبدأ بـ `+20` للأرقام المصرية
3. JWT Token صالح لمدة 7 أيام
4. WebSocket يتطلب اتصال HTTPS في الإنتاج

---

## 🔗 Additional Resources

- [Swagger UI](https://your-domain.com/docs) - واجهة تفاعلية للـ API
- [ReDoc](https://your-domain.com/redoc) - توثيق تفصيلي

---

**Last Updated:** 2024
