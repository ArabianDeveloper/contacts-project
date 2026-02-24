import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/contacts']

def get_credentials():
    """دالة للتعامل مع تسجيل الدخول وجلب الصلاحيات"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return creds

def list_all_labels(people_service):
    """دالة لجلب وطباعة جميع التصنيفات، وتعيد قاموساً يحتوي على الأسماء والـ IDs"""
    try:
        print("\n--- Fetching All Labels ---")
        results = people_service.contactGroups().list().execute()
        groups = results.get('contactGroups', [])
        
        labels_dict = {} # لتخزين البيانات وإرجاعها لاستخدامها لاحقاً
        
        if not groups:
            print("No labels found in your account.")
        else:
            for group in groups:
                name = group.get('name', 'System Group / Unnamed')
                group_id = group.get('resourceName')
                labels_dict[name] = group_id
                print(f"Name: {name} | ID: {group_id}")
                
        print("---------------------------\n")
        return labels_dict
        
    except Exception as e:
        print(f"Error fetching labels: {e}")
        return None

def add_new_label(people_service, label_name):
    """دالة لإنشاء تصنيف جديد باستخدام الاسم الذي تمرره لها"""
    try:
        print(f"Attempting to create new label: '{label_name}'...")
        new_group = people_service.contactGroups().create(
            body={"contactGroup": {"name": label_name}}
        ).execute()
        
        group_id = new_group.get('resourceName')
        print(f"✅ Label '{label_name}' created successfully with ID: {group_id}")
        
        return group_id
        
    except Exception as e:
        print(f"❌ Error creating label: {e}")
        return None

def main():
    # 1. تسجيل الدخول
    creds = get_credentials()
    people_service = build('people', 'v1', credentials=creds)

    # 2. عرض جميع التصنيفات الحالية
    existing_labels = list_all_labels(people_service)

    # 3. تجربة إضافة تصنيف جديد (كمثال)
    new_label_name = "VIP Customers 2026"
    
    # نتحقق أولاً إذا كان التصنيف موجوداً حتى لا نكرره
    if existing_labels and new_label_name in existing_labels:
        print(f"Label '{new_label_name}' already exists!")
    else:
        # إذا لم يكن موجوداً، نقوم بإنشائه
        add_new_label(people_service, new_label_name)
        
        # يمكنك استدعاء دالة العرض مرة أخرى للتأكد من إضافته
        # list_all_labels(people_service)

if __name__ == '__main__':
    main()