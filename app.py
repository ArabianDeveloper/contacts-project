'''
- get contats from google sheet
- add them to google contacts
- create a labels for each team and add the contacts to their respective labels
- create a google chat space for each team and add the contacts to their respective spaces
'''
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from manage_people import add_contact, get_or_create_label, add_contact_to_label, read_google_sheet
from manage_chats import add_user_to_space, create_google_chat_space, list_spaces


SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    'https://www.googleapis.com/auth/chat.spaces.create',
    'https://www.googleapis.com/auth/chat.memberships',
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

def main():
    creds = get_credentials()
    sheets_service = build('sheets', 'v4', credentials=creds)
    people_service = build('people', 'v1', credentials=creds)
    chat_service = build("chat", "v1", credentials=creds)

    data = read_google_sheet(sheets_service, '1gXMz0Kj_t1FaoMyt2ygGjl9VTVfHuOHDzycycECefhQ', 'Sheet1')
    if data:
        print("\n--- Sheet Data ---")
        for index, row in enumerate(data):
            print(f"Row {index + 1}: {row}")
            contact_id =add_contact(
                people_service,
                first_name=row[0] + " " + row[1] + " " + row[2],
                last_name=row[3],
                phone=row[4] if len(row) > 4 else None,
                email=row[5] if len(row) > 5 else None
            )
            contact_labels_list = row[6].split(",") if len(row) > 6 else []
            for label in contact_labels_list:
                label_id = get_or_create_label(people_service, label.strip())
                add_contact_to_label(people_service, contact_id, label_id)
                
            print(f"✅ Contact {row[0]} {row[1]} {row[2]} created successfuly and added to labels '{row[6]}'")

            spaces = {}
            for space in list_spaces(chat_service):
                spaces[space.get("displayName")] = space.get("name")
            
            for label in contact_labels_list:
                if label.strip() not in spaces:
                    Nspace_id = create_google_chat_space(chat_service, label.strip())
                    add_user_to_space(chat_service, Nspace_id, row[5])
                else:
                    add_user_to_space(chat_service, spaces[label.strip()], row[5])
            
            print(f"✅ Contact {row[0]} {row[1]} {row[2]} added to Google Chat spaces for labels '{row[6]}'")

        print("Done processing all rows.")


if __name__ == '__main__':
    main()