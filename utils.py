"""
أدوات مساعدة عامة للنظام
"""
import re
from typing import List, Optional, Dict
from datetime import datetime, timedelta

# ==================== معالجة أرقام الهواتف ====================

def clean_phone_number(phone: str) -> str:
    """تنظيف رقم الهاتف من الرموز والمسافات"""
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    if cleaned.startswith('01') and len(cleaned) == 11:
        cleaned = '+2' + cleaned
    elif cleaned.startswith('1') and len(cleaned) == 10:
        cleaned = '+201' + cleaned
    elif not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    
    return cleaned

def validate_egyptian_phone(phone: str) -> bool:
    """التحقق من صحة رقم هاتف مصري"""
    cleaned = clean_phone_number(phone)
    pattern = r'^\+2001[0125]\d{8}$'
    return bool(re.match(pattern, cleaned))

def extract_phone_numbers(text: str) -> List[str]:
    """استخراج جميع أرقام الهواتف من نص"""
    pattern = r'(01[0125][0-9 \-]{8,15})'
    phones = re.findall(pattern, text)
    
    cleaned_phones = []
    for phone in phones:
        clean = phone.replace(' ', '').replace('-', '')
        if len(clean) == 11 and clean not in cleaned_phones:
            cleaned_phones.append(clean)
    
    return cleaned_phones

# ==================== معالجة التواريخ ====================

def format_datetime(dt: datetime, format_type: str = 'full') -> str:
    formats = {
        'full': '%Y-%m-%d %H:%M:%S',
        'date': '%Y-%m-%d',
        'time': '%H:%M:%S',
        'arabic': '%d/%m/%Y %I:%M %p',
        'short': '%d/%m %H:%M'
    }
    return dt.strftime(formats.get(format_type, formats['full']))

def get_time_ago(dt: datetime) -> str:
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"منذ {years} سنة" if years == 1 else f"منذ {years} سنوات"
    elif diff.days > 30:
        months = diff.days // 30
        return f"منذ {months} شهر" if months == 1 else f"منذ {months} شهور"
    elif diff.days > 0:
        return f"منذ {diff.days} يوم" if diff.days == 1 else f"منذ {diff.days} أيام"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"منذ {hours} ساعة" if hours == 1 else f"منذ {hours} ساعات"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"منذ {minutes} دقيقة" if minutes == 1 else f"منذ {minutes} دقائق"
    else:
        return "الآن"

# ==================== تحليل النصوص ====================

def analyze_intent(text: str) -> Dict:
    text_lower = text.lower()
    
    real_estate_keywords = ['شقة', 'فيلا', 'عمارة', 'أرض', 'محل', 'apartment', 'villa', 'land']
    car_keywords = ['سيارة', 'عربية', 'car', 'vehicle', 'bmw', 'mercedes', 'toyota']
    demand_keywords = ['مطلوب', 'محتاج', 'عايز', 'أبحث', 'wanted', 'looking', 'need']
    supply_keywords = ['للبيع', 'متاح', 'available', 'for sale']
    
    intent = {
        'category': 'general',
        'type': 'unknown',
        'quality_score': 0
    }
    
    if any(kw in text_lower for kw in real_estate_keywords):
        intent['category'] = 'real_estate'
    elif any(kw in text_lower for kw in car_keywords):
        intent['category'] = 'cars'
    
    if any(kw in text_lower for kw in demand_keywords):
        intent['type'] = 'demand'
        intent['quality_score'] = 10
    elif any(kw in text_lower for kw in supply_keywords):
        intent['type'] = 'supply'
        intent['quality_score'] = 1
    
    return intent

def extract_city(text: str) -> Optional[str]:
    cities = {
        'القاهرة': ['القاهرة', 'cairo', 'التجمع', 'المعادي', 'مدينة نصر', 'مصر الجديدة'],
        'الجيزة': ['الجيزة', 'giza', 'أكتوبر', 'الشيخ زايد', 'الهرم', 'المهندسين'],
        'الإسكندرية': ['الإسكندرية', 'alexandria', 'اسكندرية', 'سموحة']
    }
    
    text_lower = text.lower()
    for city, keywords in cities.items():
        if any(kw in text_lower for kw in keywords):
            return city
    
    return None

# ==================== معالجة النصوص ====================

def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def sanitize_input(text: str) -> str:
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`']
    for char in dangerous_chars:
        text = text.replace(char, '')
    return text.strip()

def format_phone_display(phone: str) -> str:
    if phone.startswith('+20'):
        phone = phone[3:]
        return f"+20 {phone[:3]} {phone[3:6]} {phone[6:]}"
    return phone

# ==================== التحقق من الصلاحيات ====================

def check_permission(user_permissions: Dict, required_permission: str) -> bool:
    if user_permissions.get('is_admin', False):
        return True
    return user_permissions.get(required_permission, False)

# ==================== معالجة الإحصائيات ====================

def calculate_percentage(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)

def calculate_growth(current: int, previous: int) -> Dict:
    if previous == 0:
        return {'value': current, 'growth': 100.0, 'direction': 'up'}
    growth = ((current - previous) / previous) * 100
    direction = 'up' if growth > 0 else 'down' if growth < 0 else 'stable'
    return {
        'value': current,
        'growth': round(abs(growth), 2),
        'direction': direction
    }

# ==================== توليد العبارات ====================

def generate_campaign_message(template: str, variables: Dict) -> str:
    message = template
    for key, value in variables.items():
        placeholder = f"{{{key}}}"
        message = message.replace(placeholder, str(value))
    return message

def get_greeting() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "صباح الخير"
    elif 12 <= hour < 17:
        return "مساء الخير"
    elif 17 <= hour < 21:
        return "مساء الخير"
    else:
        return "مساء الخير"

# ==================== التحقق من الصحة ====================

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_url(url: str) -> bool:
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    return bool(re.match(pattern, url))

# ==================== الألوان والرموز ====================

QUALITY_COLORS = {
    'ممتاز 🔥': '#FF6B6B',
    'جيد ⭐': '#4ECDC4',
    'TRASH': '#95A5A6'
}

STATUS_COLORS = {
    'NEW': '#3498DB',
    'CONTACTED': '#F39C12',
    'INTERESTED': '#2ECC71',
    'NOT_INTERESTED': '#E74C3C',
    'CONVERTED': '#9B59B6'
}

def get_quality_emoji(quality: str) -> str:
    emojis = {
        'ممتاز': '🔥',
        'جيد': '⭐',
        'TRASH': '🗑️'
    }
    for key, emoji in emojis.items():
        if key in quality:
            return emoji
    return '❓'

def get_status_emoji(status: str) -> str:
    emojis = {
        'NEW': '🆕',
        'CONTACTED': '📞',
        'INTERESTED': '✅',
        'NOT_INTERESTED': '❌',
        'CONVERTED': '🎉'
    }
    return emojis.get(status, '❓')

# ==================== Export ====================
__all__ = [
    'clean_phone_number',
    'validate_egyptian_phone',
    'extract_phone_numbers',
    'format_datetime',
    'get_time_ago',
    'analyze_intent',
    'extract_city',
    'truncate_text',
    'sanitize_input',
    'format_phone_display',
    'check_permission',
    'calculate_percentage',
    'calculate_growth',
    'generate_campaign_message',
    'get_greeting',
    'validate_email',
    'validate_url',
    'get_quality_emoji',
    'get_status_emoji',
    'QUALITY_COLORS',
    'STATUS_COLORS'
]
