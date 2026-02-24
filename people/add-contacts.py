from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os


SCOPES = ["https://www.googleapis.com/auth/contacts"]


def authenticate():
    """
    Authenticate user and return credentials
    """
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


def create_people_service(creds):
    service = build("people", "v1", credentials=creds)
    return service


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

    print("✅ Contact created successfully")
    return result.get("resourceName")


def get_or_create_label(service, label_name):
    groups = service.contactGroups().list(pageSize=200).execute()

    for group in groups.get("contactGroups", []):
        if group.get("name") == label_name:
            print("✅ Label found")
            return group.get("resourceName")

    # إذا غير موجود → إنشاء label
    body = {"contactGroup": {"name": label_name}}
    result = service.contactGroups().create(body=body).execute()

    print(f"✅ Label {label_name} created")
    return result.get("resourceName")


def add_contact_to_label(service, contact_resource_name, group_resource_name):
    body = {
        "resourceNamesToAdd": [contact_resource_name]
    }

    service.contactGroups().members().modify(
        resourceName=group_resource_name,
        body=body
    ).execute()

    print("✅ Contact added to label")


def main():
    creds = authenticate()
    service = create_people_service(creds)

    contact_id = add_contact(
            service,
            first_name="Ahmed",
            last_name="Ali",
            phone="+96890000000",
            email="ahmed@email.com"
        )
    
    label_id = get_or_create_label(service, "VIP Customers 2027")

    add_contact_to_label(service, contact_id, label_id)


if __name__ == "__main__":
    main()