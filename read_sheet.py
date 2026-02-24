import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_credentials():
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

def read_google_sheet(sheets_service, spreadsheet_id, range_name):
    try:
        print(f"Fetching data from range: {range_name}...")
        sheet = sheets_service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        
        values = result.get('values', [])
        
        if not values:
            print("No data found in the specified range.")
            return []
            
        print(f"✅ Successfully fetched {len(values)} rows.")
        return values
        
    except Exception as e:
        print(f"❌ Error reading from Google Sheet: {e}")
        return []

def main():
    # 1. إعداد الاتصال
    creds = get_credentials()
    sheets_service = build('sheets', 'v4', credentials=creds)

    # 2. إعدادات الملف (استبدل هذه القيم ببيانات ملفك)
    SPREADSHEET_ID = '1izkRQU7FdhiE2s0gyCaz2_PUbZxjnD5LngChUmlmsjI' # الـ ID الخاص بملفك
    RANGE_NAME = 'Sheet1!A:G' # اسم الورقة والنطاق (تأكد من اسم الورقة)

    # 3. قراءة البيانات
    data = read_google_sheet(sheets_service, SPREADSHEET_ID, RANGE_NAME)

    # 4. طباعة البيانات للتأكد منها
    if data:
        print("\n--- Sheet Data ---")
        for index, row in enumerate(data):
            print(f"Row {index + 1}: {row}")
        print("------------------")

if __name__ == '__main__':
    main()