#!/bin/bash

echo "🚀 Building Hunter Pro CRM..."

# تحديث pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# تثبيت المكتبات الأساسية
echo "📚 Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# التحقق من تثبيت المكتبات
echo "✅ Checking installations..."
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import supabase; print('Supabase: OK')"
python -c "import uvicorn; print('Uvicorn: OK')"

# إنشاء مجلدات ضرورية (إن لم تكن موجودة)
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p temp
mkdir -p uploads

# إعداد المتغيرات البيئية
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Please edit .env with your actual credentials"
fi

echo "🎉 Build completed successfully!"
echo "🚀 Run: uvicorn main:app --reload"
