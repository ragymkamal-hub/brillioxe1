import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from database import supabase_db

# إعدادات الصفحة
st.set_page_config(
    page_title="Hunter Pro CRM",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# رابط API
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# ==================== نظام المصادقة ====================
def check_login():
    """التحقق من تسجيل الدخول"""
    if 'logged_in' not in st.session_state:
        st.session_state.update({
            'logged_in': False,
            'user': '',
            'role': '',
            'perms': {}
        })

    if not st.session_state['logged_in']:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h2 style='text-align: center;'>🔐 بوابة Hunter Pro</h2>", unsafe_allow_html=True)
            
            with st.form("login"):
                username = st.text_input("اسم المستخدم", placeholder="admin@example.com")
                password = st.text_input("كلمة المرور", type="password", placeholder="••••••••")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    login_btn = st.form_submit_button("🔑 دخول", use_container_width=True)
                with col_b:
                    if st.form_submit_button("🌐 دخول بـ Google", use_container_width=True):
                        st.info("قريباً...")
                
                if login_btn:
                    if username and password:
                        try:
                            res = requests.post(f"{API_URL}/api/login", json={
                                "email": username,
                                "password": password
                            })
                            
                            if res.status_code == 200:
                                data = res.json()
                                st.session_state['logged_in'] = True
                                st.session_state['user'] = username
                                st.session_state['role'] = 'admin'  # من JWT
                                st.session_state['perms'] = {
                                    'hunt': True,
                                    'campaign': True,
                                    'share': True,
                                    'admin': True
                                }
                                st.success("✅ تم تسجيل الدخول بنجاح!")
                                st.rerun()
                            else:
                                st.error("❌ بيانات الدخول غير صحيحة")
                        except:
                            st.error("❌ خطأ في الاتصال بالخادم")
                    else:
                        st.warning("⚠️ أدخل اسم المستخدم وكلمة المرور")
        return False
    return True

# ==================== الصفحة الرئيسية ====================
def main_dashboard():
    """لوحة التحكم الرئيسية"""
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/1A1F36/00D9FF?text=Hunter+Pro", use_container_width=True)
        st.markdown(f"### مرحباً، {st.session_state['user']} 👋")
        st.markdown(f"**الدور:** {st.session_state['role']}")
        
        st.markdown("---")
        
        page = st.radio(
            "القائمة الرئيسية",
            ["📊 لوحة التحكم", "🔍 البحث", "👥 العملاء", "📤 الحملات", "⚙️ الإعدادات"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
    
    # المحتوى الرئيسي
    if page == "📊 لوحة التحكم":
        show_dashboard()
    elif page == "🔍 البحث":
        show_hunt_page()
    elif page == "👥 العملاء":
        show_leads_page()
    elif page == "📤 الحملات":
        show_campaigns_page()
    elif page == "⚙️ الإعدادات":
        show_settings_page()

# ==================== صفحة لوحة التحكم ====================
def show_dashboard():
    st.title("📊 لوحة التحكم")
    
    # تحميل الإحصائيات
    try:
        res = requests.get(f"{API_URL}/api/admin-stats")
        if res.status_code == 200:
            stats = res.json()
            
            # بطاقات الإحصائيات
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "إجمالي العملاء",
                    stats.get("total_leads", 0),
                    delta="+12 اليوم"
                )
            
            with col2:
                st.metric(
                    "إجمالي المستخدمين",
                    stats.get("total_users", 0)
                )
            
            with col3:
                st.metric(
                    "الرسائل المرسلة",
                    stats.get("total_messages", 0),
                    delta="+25 اليوم"
                )
            
            with col4:
                st.metric(
                    "معدل النجاح",
                    "68%",
                    delta="+5%"
                )
    except:
        st.error("❌ فشل تحميل الإحصائيات")
    
    st.markdown("---")
    
    # آخر الأنشطة
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔔 آخر الأحداث")
        try:
            res = requests.get(f"{API_URL}/api/last-events")
            if res.status_code == 200:
                events = res.json().get("events", [])
                if events:
                    for event in events[:5]:
                        with st.container():
                            st.markdown(f"**{event.get('event')}**")
                            st.caption(f"{event.get('details')} - {event.get('created_at', '')}")
                            st.markdown("---")
                else:
                    st.info("لا توجد أحداث جديدة")
        except:
            st.error("❌ فشل تحميل الأحداث")
    
    with col2:
        st.subheader("📈 إحصائيات سريعة")
        
        # رسم بياني بسيط
        chart_data = pd.DataFrame({
            'الجودة': ['ممتاز 🔥', 'جيد ⭐', 'رفض'],
            'العدد': [150, 320, 80]
        })
        st.bar_chart(chart_data.set_index('الجودة'))

# ==================== صفحة البحث ====================
def show_hunt_page():
    st.title("🔍 البحث عن العملاء")
    
    if not st.session_state['perms'].get('hunt', False):
        st.error("❌ ليس لديك صلاحية البحث")
        return
    
    with st.form("hunt_form"):
        st.subheader("ابدأ بحثاً جديداً")
        
        col1, col2 = st.columns(2)
        
        with col1:
            intent = st.text_input(
                "نية البحث",
                placeholder="مثال: مطلوب شقة في التجمع",
                help="أدخل ما يبحث عنه العملاء"
            )
        
        with col2:
            city = st.selectbox(
                "المدينة",
                ["القاهرة", "الجيزة", "الإسكندرية", "الأقصر", "أسوان"]
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            time_filter = st.selectbox(
                "الفترة الزمنية",
                [
                    ("qdr:d", "آخر 24 ساعة"),
                    ("qdr:w", "آخر أسبوع"),
                    ("qdr:m", "آخر شهر"),
                    ("qdr:y", "آخر سنة")
                ],
                format_func=lambda x: x[1]
            )
        
        with col4:
            max_results = st.number_input(
                "الحد الأقصى للنتائج",
                min_value=10,
                max_value=200,
                value=50,
                step=10
            )
        
        if st.form_submit_button("🚀 بدء البحث", use_container_width=True):
            if intent:
                with st.spinner("جاري البحث..."):
                    try:
                        res = requests.post(f"{API_URL}/hunt", json={
                            "intent_sentence": intent,
                            "city": city,
                            "time_filter": time_filter[0],
                            "user_id": st.session_state['user'],
                            "mode": "general"
                        })
                        
                        if res.status_code == 200:
                            st.success("✅ بدأ البحث بنجاح! ستظهر النتائج قريباً في قائمة العملاء")
                            st.balloons()
                        else:
                            st.error("❌ فشل بدء البحث")
                    except:
                        st.error("❌ خطأ في الاتصال بالخادم")
            else:
                st.warning("⚠️ أدخل نية البحث")

# ==================== صفحة العملاء ====================
def show_leads_page():
    st.title("👥 إدارة العملاء")
    
    # فلاتر
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        quality_filter = st.selectbox(
            "الجودة",
            ["الكل", "ممتاز 🔥", "جيد ⭐", "رفض"]
        )
    
    with col2:
        status_filter = st.selectbox(
            "الحالة",
            ["الكل", "NEW", "CONTACTED", "INTERESTED", "CONVERTED"]
        )
    
    with col3:
        source_filter = st.text_input("المصدر", placeholder="مثال: Facebook")
    
    with col4:
        if st.button("🔄 تحديث", use_container_width=True):
            st.rerun()
    
    # تحميل العملاء
    try:
        params = {"user_id": st.session_state['user']}
        if quality_filter != "الكل":
            params["quality"] = quality_filter
        if status_filter != "الكل":
            params["status"] = status_filter
        
        res = requests.get(f"{API_URL}/api/leads", params=params)
        
        if res.status_code == 200:
            leads = res.json().get("leads", [])
            
            if leads:
                st.info(f"📊 عدد العملاء: {len(leads)}")
                
                # عرض الجدول
                df = pd.DataFrame(leads)
                
                # اختيار الأعمدة المهمة
                columns_to_show = ['phone_number', 'quality', 'status', 'source', 'created_at']
                df_display = df[columns_to_show] if all(col in df.columns for col in columns_to_show) else df
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )
                
                # تصدير
                if st.button("📥 تصدير CSV"):
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "⬇️ تحميل الملف",
                        csv,
                        "leads.csv",
                        "text/csv"
                    )
            else:
                st.info("لا توجد عملاء بعد")
    except:
        st.error("❌ فشل تحميل العملاء")
    
    # إضافة عميل يدوياً
    with st.expander("➕ إضافة عميل يدوياً"):
        with st.form("add_lead_form"):
            phone = st.text_input("رقم الهاتف", placeholder="01012345678")
            name = st.text_input("الاسم", placeholder="أحمد محمد")
            email = st.text_input("البريد الإلكتروني", placeholder="ahmed@example.com")
            quality = st.selectbox("الجودة", ["ممتاز 🔥", "جيد ⭐"])
            notes = st.text_area("ملاحظات", placeholder="أي معلومات إضافية")
            
            if st.form_submit_button("💾 حفظ"):
                if phone:
                    try:
                        res = requests.post(f"{API_URL}/api/add-lead", json={
                            "phone_number": phone,
                            "full_name": name,
                            "email": email,
                            "quality": quality,
                            "notes": notes,
                            "user_id": st.session_state['user'],
                            "source": "Manual"
                        })
                        
                        if res.status_code == 200:
                            st.success("✅ تم إضافة العميل بنجاح!")
                            st.balloons()
                        else:
                            st.error("❌ فشل الحفظ")
                    except:
                        st.error("❌ خطأ في الاتصال")
                else:
                    st.warning("⚠️ أدخل رقم الهاتف")

# ==================== صفحة الحملات ====================
def show_campaigns_page():
    st.title("📤 إدارة الحملات")
    
    if not st.session_state['perms'].get('campaign', False):
        st.error("❌ ليس لديك صلاحية إدارة الحملات")
        return
    
    st.info("🚧 قريباً... صفحة إدارة الحملات الكاملة")

# ==================== صفحة الإعدادات ====================
def show_settings_page():
    st.title("⚙️ الإعدادات")
    
    tabs = st.tabs(["👤 الملف الشخصي", "👥 إدارة المستخدمين", "🔔 الإشعارات"])
    
    with tabs[0]:
        st.subheader("الملف الشخصي")
        st.text_input("اسم المستخدم", value=st.session_state['user'], disabled=True)
        st.text_input("الدور", value=st.session_state['role'], disabled=True)
    
    with tabs[1]:
        if st.session_state['perms'].get('admin', False):
            show_user_management()
        else:
            st.error("❌ ليس لديك صلاحية إدارة المستخدمين")
    
    with tabs[2]:
        st.subheader("إعدادات الإشعارات")
        st.checkbox("تفعيل الإشعارات")
        st.checkbox("إشعارات البريد الإلكتروني")

# ==================== إدارة المستخدمين ====================
def show_user_management():
    st.subheader("👥 إدارة المستخدمين")
    
    # إضافة مستخدم جديد
    with st.expander("➕ إضافة مستخدم جديد"):
        with st.form("add_user_form"):
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            role = st.selectbox("الدور", ["admin", "manager", "user"])
            
            col1, col2 = st.columns(2)
            with col1:
                can_hunt = st.checkbox("يمكنه البحث", value=True)
                can_campaign = st.checkbox("يمكنه الحملات")
            with col2:
                can_share = st.checkbox("يمكنه المشاركة")
                is_admin = st.checkbox("مدير النظام")
            
            if st.form_submit_button("💾 إضافة"):
                if username and password:
                    try:
                        res = requests.post(f"{API_URL}/api/add-user", json={
                            "username": username,
                            "password": password,
                            "role": role,
                            "can_hunt": can_hunt,
                            "can_campaign": can_campaign,
                            "can_share": can_share,
                            "is_admin": is_admin
                        })
                        
                        if res.status_code == 200:
                            st.success(f"✅ تم إضافة المستخدم {username}")
                            st.balloons()
                        else:
                            st.error("❌ فشل الإضافة")
                    except:
                        st.error("❌ خطأ في الاتصال")
                else:
                    st.warning("⚠️ أكمل البيانات")

# ==================== التشغيل الرئيسي ====================
def main():
    if check_login():
        main_dashboard()

if __name__ == "__main__":
    main()
