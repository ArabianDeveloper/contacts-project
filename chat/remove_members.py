from googleapiclient.discovery import build
from manage_chats import authenticate as get_credentials


# def remove_user_from_space(space_name, target_user):
#     # 1. تسجيل الدخول وبناء الاتصال
#     creds = get_credentials()
#     chat_service = build('chat', 'v1', credentials=creds)

#     try:
#         print(f"البحث عن '{target_user}' في المساحة...")
        
#         # 2. جلب قائمة جميع الأعضاء في هذه المساحة
#         response = chat_service.spaces().members().list(parent=space_name).execute()
#         memberships = response.get('memberships', [])
        
#         membership_id_to_delete = None

#         # 3. المرور على الأعضاء للبحث عن الشخص المطلوب
#         for membership in memberships:
#             member_data = membership.get('member', {})
            
#             # نبحث إذا كان الاسم أو الإيميل المستهدف موجوداً ضمن بيانات هذا العضو
#             # (نستخدم str للبحث في كل بيانات العضو للضمان)
#             if target_user.lower() in str(member_data).lower():
#                 # وجدناه! نأخذ "رقم العضوية" الخاص به للحذف
#                 membership_id_to_delete = membership.get('name') 
#                 break

#         # 4. تنفيذ أمر الحذف إذا وجدناه
#         if membership_id_to_delete:
#             print(f"تم العثور عليه! جاري الإزالة: {membership_id_to_delete}...")
#             chat_service.spaces().members().delete(name=membership_id_to_delete).execute()
#             print("✅ تم إزالة العضو بنجاح!")
#         else:
#             print(f"❌ لم يتم العثور على العضو '{target_user}' في هذه المساحة.")
            
#     except Exception as e:
#         print(f"❌ حدث خطأ أثناء إزالة المستخدم: {e}")


def remove_all_members(space_name):
    creds = get_credentials()
    chat_service = build('chat', 'v1', credentials=creds)

    try:
        print(f"جاري جلب قائمة الأعضاء للمساحة...\n")
        response = chat_service.spaces().members().list(parent=space_name).execute()
        memberships = response.get('memberships', [])
        
        if not memberships:
            print("لا يوجد أعضاء في هذه المساحة.")
            return

        for membership in memberships:
            if membership.get('role') == 'ROLE_MANAGER' or membership.get('role') == 'ROLE_ASSISTANT_MANAGER':
                continue # لا يحذف المشرفين
            membership_id = membership.get('name')
            chat_service.spaces().members().delete(name=membership_id).execute()
            print(f"✅ تم إزالة العضو: {membership_id}")
            
    except Exception as e:
        print(f"❌ حدث خطأ أثناء إزالة الأعضاء: {e}")


# --- طريقة التشغيل ---
if __name__ == '__main__':

    # يمكنك كتابة إيميل الشخص أو اسمه (كما يظهر في Google Chat) للبحث عنه وحذفه
    # USER_TO_REMOVE = "s144209@student.squ.edu.om" 
    
    # remove_user_from_space(MY_SPACE_NAME, USER_TO_REMOVE)

    
    # اسم (ID) المساحة الخاصة بك
    MY_SPACE_NAME = "spaces/AAQARJ368ao"
    
    remove_all_members(MY_SPACE_NAME)



