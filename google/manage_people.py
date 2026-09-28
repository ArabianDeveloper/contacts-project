import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    "https://www.googleapis.com/auth/contacts",
]


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


def add_contact(service, first_name, last_name, phone=None, email=None):

    contact_body = {
        "names": [
            {
                "givenName": first_name,
                "familyName": last_name
            }
        ]
    }

    if phone:
        contact_body["phoneNumbers"] = [{"value": phone}]

    if email:
        contact_body["emailAddresses"] = [{"value": email}]

    result = service.people().createContact(body=contact_body).execute()

    # print(f"✅ Contact {first_name} {last_name} created successfully")
    return result.get("resourceName")


def get_or_create_label(service, label_name):
    groups = service.contactGroups().list(pageSize=200).execute()

    for group in groups.get("contactGroups", []):
        if group.get("name") == label_name:
            # print(f"✅ Label {label_name} found")
            return group.get("resourceName")

    # إذا غير موجود → إنشاء label
    body = {"contactGroup": {"name": label_name}}
    result = service.contactGroups().create(body=body).execute()

    # print(f"✅ Label {label_name} created")
    return result.get("resourceName")


def add_contact_to_label(service, contact_resource_name, group_resource_name):
    body = {
        "resourceNamesToAdd": [contact_resource_name]
    }

    service.contactGroups().members().modify(
        resourceName=group_resource_name,
        body=body
    ).execute()


def main():
    creds = get_credentials()
    service = build('people', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    data = read_google_sheet(sheets_service, '1gXMz0Kj_t1FaoMyt2ygGjl9VTVfHuOHDzycycECefhQ', 'Sheet1!A:G')
    if data:
        print("\n--- Sheet Data ---")
        for index, row in enumerate(data):
            print(f"Row {index + 1}: {row}")
            contact_id =add_contact(
                service,
                first_name=row[0] + " " + row[1] + " " + row[2],
                last_name=row[3],
                phone=row[4] if len(row) > 4 else None,
                email=row[5] if len(row) > 5 else None
            )
            contact_labels_list = row[6].split(",") if len(row) > 6 else []
            for label in contact_labels_list:
                label_id = get_or_create_label(service, label.strip())
                add_contact_to_label(service, contact_id, label_id)
                
            print(f"✅ Contact {row[0]} {row[1]} {row[2]} created successfuly and added to labels '{row[6]}'")

        print("------------------")

if __name__ == '__main__':
    main()