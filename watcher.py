import time
import json
from pathlib import Path
from datetime import datetime
from fetcher import fetch_unread_emails
from drafter import analyze_and_draft_batch
from notifier import notify
from sender import send_reply

# ── Ayarlar ──────────────────────────────────────────────────────────────────
CHECK_INTERVAL_SECONDS = 60
SEEN_IDS_FILE          = Path("seen_ids.json")
CRITICAL_URGENCIES     = {"critical", "high"}
MAX_FETCH              = 20
# ─────────────────────────────────────────────────────────────────────────────

def load_seen_ids() -> set[str]:
    if SEEN_IDS_FILE.exists():
        return set(json.loads(SEEN_IDS_FILE.read_text(encoding="utf-8")))
    return set()

def save_seen_ids(ids: set[str]) -> None:
    SEEN_IDS_FILE.write_text(json.dumps(list(ids)), encoding="utf-8")

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def run() -> None:
    log("🚀 AI-MailCraft Otonom Servisi Başlatıldı")
    log(f"   Her {CHECK_INTERVAL_SECONDS} saniyede bir Gmail kontrol edilecek...")
    print()

    seen_ids = load_seen_ids()

    while True:
        try:
            log("📬 Gmail kontrol ediliyor...")
            emails = fetch_unread_emails(max_results=MAX_FETCH)

            new_emails = [e for e in emails if e.id not in seen_ids]

            if not new_emails:
                log("✅ Yeni mail yok.")
            else:
                log(f"✉️  {len(new_emails)} yeni mail bulundu! Analiz başlıyor...")
                results = analyze_and_draft_batch(new_emails)

                for result in results:
                    result.pretty_print()

                    if result.urgency in CRITICAL_URGENCIES:
                        # Kritik → bildirim gönder, otomatik yanıt verme
                        notify(
                            title=f"⚡ {result.urgency.upper()} — Yanıt Bekliyor",
                            message=f"Konu: {result.subject}\nGönderen: {result.sender}\nÖzet: {result.summary[:100]}",
                        )
                        log(f"🔔 Kritik mail — otomatik yanıt gönderilmedi, sen karar ver.")
                    else:
                        # Normal → otomatik yanıt gönder
                        email_obj = next(e for e in new_emails if e.id == result.email_id)
                        send_reply(email_obj, result.draft_reply)

                    seen_ids.add(result.email_id)

                save_seen_ids(seen_ids)

        except Exception as e:
            log(f"⚠️  Hata: {e}")

        log(f"⏳ {CHECK_INTERVAL_SECONDS} saniye bekleniyor...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    run()