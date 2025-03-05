from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import base64
import os

# Define SCOPES
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Authenticate and get service
def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

# Function to extract email body
def extract_body(payload):
    """Recursively extracts the email body from nested parts."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] in ["text/plain", "text/html"]:
                body_data = part["body"].get("data", "")
                if body_data:
                    return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
            if "parts" in part:  # Check nested parts
                return extract_body(part)
    
    # Single-part email
    body_data = payload["body"].get("data", "")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
    
    return "(No Content)"

# Function to extract attachment names
def extract_attachments(payload):
    """Extracts attachment filenames if present."""
    attachments = []
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("filename") and part["body"].get("attachmentId"):
                attachments.append(part["filename"])
            if "parts" in part:  # Check nested parts for attachments
                attachments.extend(extract_attachments(part))
    return attachments

# Function to search and retrieve emails
def search_emails(service, sender_email, subject_text):
    query = f"from:{sender_email} subject:{subject_text}"
    results = service.users().messages().list(userId="me", q=query).execute()

    messages = results.get("messages", [])
    if not messages:
        print("No emails found.")
        return
    
    for msg in messages:
        msg_id = msg["id"]
        msg_data = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        
        payload = msg_data["payload"]
        headers = payload.get("headers", [])
        
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "No Date")
        body = extract_body(payload)
        attachments = extract_attachments(payload)

        print(f"\nEmail ID: {msg_id}")
        print(f"Date: {date}")
        print(f"Subject: {subject}")
        print(f"Body Preview: {body[:500]}")
        print(f"Attachments: {', '.join(attachments) if attachments else 'None'}")

# Run search
if __name__ == "__main__":
    sender_email = "example@gmail.com"  # Replace with the sender's email
    subject_text = "specific subject"   # Replace with the subject to search
    service = get_gmail_service()
    search_emails(service, sender_email, subject_text)
