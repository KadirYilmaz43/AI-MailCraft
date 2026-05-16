import base64
import re
from email.mime.text import MIMEText
from fetcher import Email
from googleapiclient.discovery import build
from auth import get_credentials

def build_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def extract_email_address(sender: str) -> str:
    """'Ad Soyad <email@gmail.com>' formatından sadece email adresini çıkarır."""
    match = re.search(r'<(.+?)>', sender)
    if match:
        return match.group(1).strip()
    return sender.strip()

def send_reply(original_email: Email, reply_body: str) -> bool:
    try:
        service = build_gmail_service()

        to_address = extract_email_address(original_email.sender)

        message = MIMEText(reply_body, "plain", "utf-8")
        message["To"] = to_address
        message["Subject"] = f"Re: {original_email.subject}"
        message["In-Reply-To"] = original_email.id
        message["References"] = original_email.id

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        service.users().messages().send(
            userId="me",
            body={
                "raw": raw,
                "threadId": original_email.thread_id,
            }
        ).execute()

        print(f"[Sender] ✅ Yanıt gönderildi → {to_address}")
        return True

    except Exception as e:
        print(f"[Sender] ❌ Yanıt gönderilemedi: {e}")
        return False