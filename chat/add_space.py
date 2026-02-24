from googleapiclient.discovery import build
# نفترض أن لديك دالة get_credentials جاهزة كما في الأمثلة السابقة
from manage_chats import authenticate as get_credentials 

def create_google_chat_space():
    creds = get_credentials()
    
    # بناء الاتصال بخدمة Google Chat
    chat_service = build('chat', 'v1', credentials=creds)

    # إعداد تفاصيل الـ Space الجديد
    space_details = {
        "spaceType": "SPACE",           # لتحديد أنها غرفة دردشة (وليس محادثة فردية)
        "displayName": "إشعارات العملاء", # اسم الـ Space الذي سيظهر لك
        # يمكنك أيضاً تحديد مستوى الوصول (مثلاً مسموح للمدعوين فقط)
        "spaceDetails": {
            "description": "هذه المساحة مخصصة للإشعارات التلقائية من بايثون"
        }
    }

    try:
        print("جاري إنشاء الـ Space الجديد...")
        # إرسال طلب الإنشاء
        new_space = chat_service.spaces().create(body=space_details).execute()
        
        space_name = new_space.get('name') # هذا هو الـ ID الخاص بالـ Space
        print(f"✅ تم إنشاء الـ Space بنجاح!")
        print(f"اسم (ID) المساحة لاستخدامه لاحقاً: {space_name}")
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء إنشاء الـ Space: {e}")

if __name__ == '__main__':
    create_google_chat_space()