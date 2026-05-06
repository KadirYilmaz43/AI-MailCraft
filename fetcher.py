# Note: This logic was optimized by Claude Skills Agent.

import base64
import re
from dataclasses import dataclass, field
from typing import Optional
from email import message_from_bytes
from email.header import decode_header as _decode_header

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth import get_credentials


# ---------------------------------------------------------------------------
# Veri Modeli
# ---------------------------------------------------------------------------

@dataclass
class Email:
    """Tek bir e-postayı temsil eden sade veri modeli."""
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date: str
    snippet: str                    # Gmail'in kısa önizleme metni
    body_plain: str                 # Düz metin gövde
    body_html: str                  # HTML gövde (opsiyonel)
    labels: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"Email(id={self.id!r}, from={self.sender!r}, "
            f"subject={self.subject!r})"
        )


# ---------------------------------------------------------------------------
# Gmail Servisi
# ---------------------------------------------------------------------------

def build_gmail_service():
    """Kimlik doğrulanmış Gmail API servisini döndürür."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service


# ---------------------------------------------------------------------------
# Okunmamış Mailleri Çekme
# ---------------------------------------------------------------------------

def fetch_unread_emails(
    max_results: int = 20,
    label_ids: list[str] | None = None,
    query: str = "is:unread",
) -> list[Email]:
    """
    Gmail INBOX'taki okunmamış mailleri çeker ve ayrıştırır.

    Args:
        max_results:  Çekilecek maksimum mail sayısı (varsayılan: 20).
        label_ids:    Filtre için etiketler (varsayılan: ["INBOX"]).
        query:        Gmail arama sorgusu (varsayılan: "is:unread").

    Returns:
        Email nesnelerinin listesi.
    """
    if label_ids is None:
        label_ids = ["INBOX"]

    service = build_gmail_service()
    emails: list[Email] = []

    try:
        # 1) Okunmamış mesajların ID listesini al
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=label_ids,
                q=query,
                maxResults=max_results,
            )
            .execute()
        )

        messages = response.get("messages", [])
        if not messages:
            print("[Fetcher] Okunmamış mail bulunamadı.")
            return []

        print(f"[Fetcher] {len(messages)} okunmamış mail bulundu. Ayrıştırılıyor...")

        # 2) Her mail için tam içeriği çek ve ayrıştır
        for msg_ref in messages:
            msg_id = msg_ref["id"]
            try:
                raw_msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                email_obj = _parse_message(raw_msg)
                emails.append(email_obj)
            except HttpError as e:
                print(f"[Fetcher] Mail {msg_id} alınamadı: {e}")
                continue

    except HttpError as e:
        print(f"[Fetcher] Gmail API hatası: {e}")
        raise

    print(f"[Fetcher] {len(emails)} mail başarıyla ayrıştırıldı.")
    return emails


# ---------------------------------------------------------------------------
# Yardımcı: Mesaj Ayrıştırma
# ---------------------------------------------------------------------------

def _parse_message(raw_msg: dict) -> Email:
    """Ham Gmail API mesajını Email nesnesine dönüştürür."""
    headers = {
        h["name"].lower(): h["value"]
        for h in raw_msg.get("payload", {}).get("headers", [])
    }

    subject = _decode_mime_str(headers.get("subject", "(Konu Yok)"))
    sender = headers.get("from", "")
    recipient = headers.get("to", "")
    date = headers.get("date", "")

    body_plain, body_html = _extract_body(raw_msg.get("payload", {}))

    return Email(
        id=raw_msg["id"],
        thread_id=raw_msg.get("threadId", ""),
        subject=subject,
        sender=sender,
        recipient=recipient,
        date=date,
        snippet=raw_msg.get("snippet", ""),
        body_plain=body_plain,
        body_html=body_html,
        labels=raw_msg.get("labelIds", []),
    )


def _extract_body(payload: dict) -> tuple[str, str]:
    """
    Multipart veya tekil payload'dan düz metin ve HTML gövdeyi çıkarır.
    Yinelemeli olarak iç içe part'ları tarar.
    """
    plain = ""
    html = ""

    mime_type = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if parts:
        # Multipart mesaj → her parçayı incele
        for part in parts:
            p, h = _extract_body(part)
            plain = plain or p
            html = html or h
    else:
        # Yaprak düğüm → veriyi decode et
        data = payload.get("body", {}).get("data", "")
        decoded = _base64_decode(data)

        if "text/plain" in mime_type:
            plain = decoded
        elif "text/html" in mime_type:
            html = decoded

    return plain, html


def _base64_decode(data: str) -> str:
    """Gmail'in URL-safe base64 verisini unicode string'e çevirir."""
    if not data:
        return ""
    try:
        padded = data + "=" * (4 - len(data) % 4)
        raw_bytes = base64.urlsafe_b64decode(padded)
        return raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _decode_mime_str(value: str) -> str:
    """
    RFC 2047 ile kodlanmış başlık değerlerini (örn. =?UTF-8?B?...?=) çözer.
    """
    parts = _decode_header(value)
    decoded_parts = []
    for text, encoding in parts:
        if isinstance(text, bytes):
            decoded_parts.append(text.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded_parts.append(text)
    return "".join(decoded_parts)


# ---------------------------------------------------------------------------
# Kullanım Örneği
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    emails = fetch_unread_emails(max_results=10)
    for email in emails:
        print("-" * 60)
        print(f"Kimden : {email.sender}")
        print(f"Konu   : {email.subject}")
        print(f"Tarih  : {email.date}")
        print(f"Özet   : {email.snippet[:120]}...")
