FROM python:3.11-slim

# تحديث النظام وتثبيت اعتماديات النظام
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ ملف المتطلبات أولاً لتحسين caching
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# نسخ جميع ملفات التطبيق
COPY . .

# إنشاء مجلد للوسائط
RUN mkdir -p /app/media

# المنفذ الذي يعمل عليه التطبيق
EXPOSE 8080

# أمر التشغيل
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
