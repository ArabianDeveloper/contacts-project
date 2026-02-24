from googleapiclient.discovery import build
from manage_chats import authenticate as get_credentials # تأكد من استدعاء دالة تسجيل الدخول الخاصة بك

def add_user_to_space(space_name, user_email):
    # 1. تسجيل الدخول وبناء الاتصال
    creds = get_credentials()
    chat_service = build('chat', 'v1', credentials=creds)

    # 2. تجهيز بيانات العضو الجديد
    # نستخدم الإيميل مسبوقاً بكلمة "users/" للتعريف به
    membership_body = {
        "member": {
            "name": f"users/{user_email}",
            "type": "HUMAN"
        }
    }

    try:
        print(f"جاري إضافة {user_email} إلى المساحة...")
        
        # 3. إرسال طلب الإضافة
        result = chat_service.spaces().members().create(
            parent=space_name,
            body=membership_body
        ).execute()
        
        print(f"✅ تم إضافة المستخدم بنجاح!")
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء إضافة المستخدم: {e}")

# --- طريقة التشغيل ---
if __name__ == '__main__':
    # استبدل هذا بالـ ID الذي ظهر لك عندما أنشأت الـ Space
    MY_SPACE_NAME = "spaces/AAQA4Evj6ao" 
    
    # الإيميل الذي تريد إضافته
    USER_TO_ADD = "s144209@student.squ.edu.om"
    
    add_user_to_space(MY_SPACE_NAME, USER_TO_ADD)