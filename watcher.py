# Note: This logic was optimized by Claude Skills Agent.

import time
import json
from pathlib import Path
from datetime import datetime

from fetcher import fetch_unread_emails
from drafter import analyze_and_draft_batch
from notifier import notify

# ── Ayarlar ──────────────────────────────────────────────────────────────────
CHECK_INTERVAL_SECONDS = 60          # Her kaç saniyede bir Gmail kontrol edilsin
SEEN_IDS_FILE          = Path("seen_ids.json")   # Daha önce görülen mail ID'leri
CRITICAL_URGENCIES     = {"critical", "high"}    # Bildirim gönderilecek seviyeler
MAX_FETCH              = 20          # Bir seferde en fazla kaç mail çekilsin
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

            # Daha önce görülmemiş mailleri filtrele
            new_emails = [e for e in emails if e.id not in seen_ids]

            if not new_emails:
                log("✅ Yeni mail yok.")
            else:
                log(f"✉️  {len(new_emails)} yeni mail bulundu! Analiz başlıyor...")
                results = analyze_and_draft_batch(new_emails)

                for result in results:
                    # Terminale yazdır
                    result.pretty_print()

                    # Önemli ise Windows bildirimi gönder
                    if result.urgency in CRITICAL_URGENCIES:
                        notify(
                            title=f"⚡ {result.urgency.upper()} — Yeni Mail",
                            message=f"Konu: {result.subject}\n"
                                    f"Gönderen: {result.sender}\n"
                                    f"Özet: {result.summary[:100]}",
                        )

                    # ID'yi kaydet
                    seen_ids.add(result.email_id)

                save_seen_ids(seen_ids)

        except Exception as e:
            log(f"⚠️  Hata: {e}")

        log(f"⏳ {CHECK_INTERVAL_SECONDS} saniye bekleniyor...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
