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


def create_chat_service(creds):
    return build("chat", "v1", credentials=creds)


def list_spaces(service):
    results = service.spaces().list().execute()

    spaces = results.get("spaces", [])

    if not spaces:
        print("❌ No spaces found")
        return

    print("✅ Your Google Chat spaces:\n")

    for i, space in enumerate(spaces, start=1):
        print(f"{i}. Name:", space.get("displayName"))
        print("   ID:", space.get("name"))
        print("   Type:", space.get("spaceType"))
        print("-" * 30)


def add_space(service, space_name):
    space_body = {
        "displayName": space_name,
        "spaceType": "GROUP_CHAT"
    }

    try:
        created_space = service.spaces().create(body=space_body).execute()
        print(f"✅ Space '{space_name}' created successfully!")
        print("Space ID:", created_space.get("name"))
    except Exception as e:
        print("❌ Error creating space:", e)


def main():
    creds = authenticate()
    service = create_chat_service(creds)
    # list_spaces(service)
    add_space(service, "My New Chat Space")


if __name__ == "__main__":
    main()