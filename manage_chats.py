from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

SCOPES = [
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    'https://www.googleapis.com/auth/chat.spaces.create',
    'https://www.googleapis.com/auth/chat.memberships',
]


def authenticate():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def list_spaces(service):
    results = service.spaces().list().execute()

    spaces = results.get("spaces", [])

    if not spaces:
        print("❌ No spaces found")
        return

    # print("✅ Your Google Chat spaces:\n")

    # for i, space in enumerate(spaces, start=1):
        # print(f"{i}. Name:", space.get("displayName"))
        # print("   ID:", space.get("name"))
        # print("   Type:", space.get("spaceType"))
        # print("-" * 30)
    
    return spaces


def create_google_chat_space(service, space_title):

    # إعداد تفاصيل الـ Space الجديد
    space_details = {
        "spaceType": "SPACE",           # لتحديد أنها غرفة دردشة (وليس محادثة فردية)
        "displayName": space_title, # اسم الـ Space الذي سيظهر لك
        "spaceDetails": {
            "description": "هذه المساحة مخصصة للإشعارات التلقائية من بايثون"
        }
    }

    try:
        # print("Creating new Google Chat space...")
        # إرسال طلب الإنشاء
        new_space = service.spaces().create(body=space_details).execute()
        
        space_displayName = new_space.get('displayName') 
        space_name = new_space.get('name')
        # print(f'new space created: {space_displayName} (ID: {space_name})')
        return space_name
        
    except Exception as e:
        print(f"❌ Error creating space: {e}")


def list_space_members(service, space_name):

    try:
        print(f"Listing members in space: {space_name}\n")
        
        # 2. إرسال طلب جلب الأعضاء
        response = service.spaces().members().list(parent=space_name).execute()
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


def add_user_to_space(service, space_name, user_email):

    # 2. تجهيز بيانات العضو الجديد
    # نستخدم الإيميل مسبوقاً بكلمة "users/" للتعريف به
    membership_body = {
        "member": {
            "name": f"users/{user_email}",
            "type": "HUMAN"
        }
    }

    try:
        # print(f"Adding user {user_email} to space {space_name}...")
        
        # 3. إرسال طلب الإضافة
        result = service.spaces().members().create(
            parent=space_name,
            body=membership_body
        ).execute()

        member_name = result.get('name')
        
        # print(f"✅ User {user_email} added successfully.")
        return member_name
        
    except Exception as e:
        print(f"❌ Error while adding user: {e}")


def remove_all_members(service, space_name):

    try:
        print(f"Getting list of members in space {space_name}...\n")
        response = service.spaces().members().list(parent=space_name).execute()
        memberships = response.get('memberships', [])
        
        if not memberships:
            print("No members found in this space.")
            return

        for membership in memberships:
            if membership.get('role') == 'ROLE_MANAGER' or membership.get('role') == 'ROLE_ASSISTANT_MANAGER':
                continue # لا يحذف المشرفين
            membership_id = membership.get('name')
            service.spaces().members().delete(name=membership_id).execute()
            print(f"✅ Successfully removed member: {membership_id}")
            
    except Exception as e:
        print(f"❌ Error while removing members: {e}")


def remove_all_from_all(service):
    try:
        spaces = list_spaces(service)
        for space in spaces:
            space_name = space.get('name')
            remove_all_members(service, space_name)
    except Exception as e:
        print(f"❌ Error while removing members from all spaces: {e}")


def main():
    creds = authenticate()
    service = build("chat", "v1", credentials=creds)
    SPACE_NAME = "spaces/AAQARJ368ao"
    SPACE_TITLE = "team1"
    MEMBER_EMAIL = "s140004@student.squ.edu.om"

    # list_spaces(service)
    # create_google_chat_space(service, SPACE_TITLE)
    # list_space_members(service, SPACE_NAME)
    # add_user_to_space(service, SPACE_NAME, MEMBER_EMAIL)
    # remove_all_members(service, SPACE_NAME)
    # remove_all_from_all(service)


if __name__ == "__main__":
    main()