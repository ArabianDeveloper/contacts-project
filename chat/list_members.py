from googleapiclient.discovery import build
from manage_chats import authenticate as get_credentials # استدعاء دالة تسجيل الدخول الخاصة بك

def list_space_members(space_name):
    
    # 1. تسجيل الدخول وبناء الاتصال
    creds = get_credentials()
    chat_service = build('chat', 'v1', credentials=creds)

    try:
        print(f"Listing members in space: {space_name}\n")
        
        # 2. إرسال طلب جلب الأعضاء
        response = chat_service.spaces().members().list(parent=space_name).execute()
        memberships = response.get('memberships', [])
        
        if not memberships:
            print("لا يوجد أعضاء في هذه المساحة.")
            return

        # 3. طباعة البيانات بشكل مرتب
        print("-" * 45)
        for index, membership in enumerate(memberships, start=1):
            member_info = membership.get('member', {})
            
            # استخراج البيانات الأساسية للعضو
            member_role = membership.get('role', 'UNKNOWN') # دور العضو (OWNER, MANAGER, MEMBER)
            display_name = member_info.get('displayName', 'N/A') # الاسم المعروض للعضو
            member_type = member_info.get('type', 'UNKNOWN') # هل هو إنسان (HUMAN) أم بوت (BOT)
            member_id = member_info.get('name', 'N/A')     # الـ ID المستخدم في الحذف

            print(f"👤 Member {index}:")
            print(f"Role         : {member_role}")
            print(f"Display Name : {display_name}")
            print(f"Type         : {member_type}")
            print(f"ID           : {member_id}")
            print("-" * 45)
            
    except Exception as e:
        print(f"Error while listing members: {e}")

# --- طريقة التشغيل ---
if __name__ == '__main__':
    # استبدل هذا بالـ ID الخاص بالمساحة (Space)
    MY_SPACE_NAME = "spaces/AAQARJ368ao"
    
    list_space_members(MY_SPACE_NAME)