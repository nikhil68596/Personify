from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle
import os
import base64
import json
import subprocess
import time

# OAuth 2.0 Scopes for Gmail API
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
]

# Pub/Sub Topic Details
PROJECT_ID = "personified-449620"
TOPIC_NAME = f"projects/{PROJECT_ID}/topics/gmail-notifications"

# Store Seen Email IDs to Prevent Duplicates
seen_emails = set()

# OAuth Authentication
def get_credentials():
    """Authenticate the user via OAuth 2.0 and store credentials in a token file."""
    creds = None

    if os.path.exists("token.pickle"):
        print("🔄 Loading existing OAuth token...")
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        print("🔑 No valid token found. Authenticating via OAuth...")
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
        print("✅ New OAuth token saved.")

    return creds

# Start Gmail Watch Request
def watch_gmail():
    """Registers a Gmail watch request to receive email notifications via Pub/Sub."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    request_body = {
        "labelIds": ["INBOX"],
        "topicName": TOPIC_NAME,
    }

    try:
        print("📡 Sending watch request to Gmail...")
        response = service.users().watch(userId="me", body=request_body).execute()
        print(f"✅ Gmail Watch Response: {response}")
    except Exception as e:
        print(f"❌ Error in watch request: {e}")

# Fetch Emails Using historyId
def get_new_emails(service, history_id):
    """Fetches all new emails received since the last historyId and avoids duplicates."""
    try:
        print(f"🔍 Checking Gmail API for historyId {history_id}...")
        history = service.users().history().list(userId="me", startHistoryId=history_id).execute()
        messages = history.get("history", [])

        if not messages:
            print("⚠️ No new emails found using historyId. Fetching the latest email manually...")
            fetch_latest_email(service)
            return

        for record in messages:
            if "messages" in record:
                for msg in record["messages"]:
                    msg_id = msg["id"]
                    if msg_id not in seen_emails:
                        seen_emails.add(msg_id)
                        print(f"📩 Fetching email with ID: {msg_id}")
                        fetch_email_by_id(service, msg_id)
                    else:
                        print(f"⚠️ Skipping duplicate email ID: {msg_id}")
    except Exception as e:
        print(f"❌ Error fetching emails with historyId {history_id}: {e}")
        print("⚠️ Falling back to manual fetch...")
        fetch_latest_email(service)

def fetch_email_by_id(service, msg_id):
    """Fetches and prints email details by message ID."""
    print(f"📨 Retrieving email content for message ID: {msg_id}...")
    message = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    headers = message["payload"].get("headers", [])
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

    # Decode the email body
    body = "No Body Available"
    if "parts" in message["payload"]:
        for part in message["payload"]["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part["body"]:
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break

    print(f"\n📩 New Email Received!")
    print(f"📌 From: {sender}")
    print(f"📌 Subject: {subject}")
    print(f"📌 Body Preview: {body[:500]}")  # Show first 500 characters

def fetch_latest_email(service):
    """Manually fetches the latest email from the inbox."""
    print("📬 Fetching latest email manually...")
    results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=1).execute()
    messages = results.get("messages", [])

    if messages:
        msg_id = messages[0]["id"]
        if msg_id not in seen_emails:
            seen_emails.add(msg_id)
            print(f"📨 Found latest email with ID: {msg_id}")
            fetch_email_by_id(service, msg_id)
        else:
            print(f"⚠️ Skipping duplicate latest email ID: {msg_id}")
    else:
        print("⚠️ No emails found in the inbox.")

# Listen for Emails via Pub/Sub
def listen_for_emails():
    """Continuously listens for new Gmail notifications via Pub/Sub and fetches emails."""
    service = build("gmail", "v1", credentials=get_credentials())

    while True:
        result = subprocess.run(
            ["gcloud", "pubsub", "subscriptions", "pull", "--auto-ack", "gmail-notifications-sub", "--format=json"],
            capture_output=True, text=True
        )

        if result.stdout.strip():
            try:
                messages = json.loads(result.stdout)
                data_found = False
                for msg in messages:
                    print("📡 Pub/Sub Notification Received.")
                    if "data" in msg:
                        print("🔍 Extracting email details from Pub/Sub...")
                        data = json.loads(msg["data"])
                        history_id = data.get("historyId")
                        if history_id:
                            print(f"🕵️ Processing historyId: {history_id}")
                            get_new_emails(service, history_id)
                            data_found = True
                if not data_found:
                    print("⚠️ No valid email data found in Pub/Sub. Checking manually...")
                    fetch_latest_email(service)
            except json.JSONDecodeError:
                print("⚠️ Error decoding Pub/Sub response. Skipping...")
        else:
            print("⚠️ No messages received from Pub/Sub. Checking manually...")
            fetch_latest_email(service)

        time.sleep(5)  # Wait 5 seconds before checking again

# Run the Script
if __name__ == "__main__":
    watch_gmail()  # Start watching Gmail for new messages
    listen_for_emails()  # Start listening for new emails
