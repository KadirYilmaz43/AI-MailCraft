# AI-MailCraft Ana Kontrol Merkezi
from fetcher import fetch_unread_emails
from drafter import analyze_and_draft_batch

def start_ai_mailcraft():
    print("🚀 AI-MailCraft Otonom Servisi Başlatılıyor...")
    
    # 1. Okunmamış mailleri çek (Halim'in Modülü)
    unread_emails = fetch_unread_emails(max_results=5)
    
    if not unread_emails:
        print("😴 Yeni mesaj yok. Sistem tetikte bekliyor.")
        return

    print(f"✅ {len(unread_emails)} yeni mail yakalandı. AI analizi başlıyor...")
    
    # 2. Mailleri analiz et ve taslak hazırla (Tuna'nın Modülü)
    # Not: Çevresel değişkenlerde ANTHROPIC_API_KEY tanımlı olmalıdır.
    results = analyze_and_draft_batch(unread_emails)
    
    # 3. Sonuçları ekrana bas
    print("\n--- ANALİZ VE TASLAK SONUÇLARI ---")
    for res in results:
        res.pretty_print()

if __name__ == "__main__":
    start_ai_mailcraft()
