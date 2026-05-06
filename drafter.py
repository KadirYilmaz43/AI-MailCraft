# Note: This logic was optimized by Claude Skills Agent.

import os
import json
from dataclasses import dataclass
from typing import Literal
import anthropic

from fetcher import Email

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

SENTIMENT_LABELS = Literal["positive", "neutral", "negative", "mixed"]
URGENCY_LABELS   = Literal["critical", "high", "medium", "low"]

# ---------------------------------------------------------------------------
# Veri Modeli
# ---------------------------------------------------------------------------

@dataclass
class DraftResult:
    """Tek bir mailin analiz + taslak yanıt sonucunu taşır."""
    email_id:       str
    subject:        str
    sender:         str
    sentiment:      SENTIMENT_LABELS
    urgency:        URGENCY_LABELS
    summary:        str          # 1-2 cümlelik özet
    key_points:     list[str]    # Maildeki kritik noktalar
    draft_reply:    str          # Profesyonel yanıt taslağı
    confidence:     float        # 0.0 – 1.0 arası model güveni

    def __repr__(self) -> str:
        return (
            f"DraftResult(id={self.email_id!r}, "
            f"sentiment={self.sentiment!r}, urgency={self.urgency!r})"
        )

    def pretty_print(self) -> None:
        """Sonucu terminalde okunabilir formatta gösterir."""
        sep = "=" * 65
        print(sep)
        print(f"📧  Konu   : {self.subject}")
        print(f"👤  Gönderen: {self.sender}")
        print(f"💬  Duygu  : {self.sentiment.upper()}")
        print(f"⚡  Aciliyet: {self.urgency.upper()}")
        print(f"🔍  Özet   : {self.summary}")
        print(f"📌  Kritik Noktalar:")
        for point in self.key_points:
            print(f"    • {point}")
        print(f"✉️  Taslak Yanıt:\n")
        print(self.draft_reply)
        print(sep)


# ---------------------------------------------------------------------------
# Prompt Fabrikası
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    return """Sen bir kurumsal iletişim asistanısın. Görevin:
1. Gelen e-postanın duygusunu (sentiment) ve aciliyetini (urgency) analiz etmek.
2. Maili kısaca özetlemek ve kritik noktaları çıkarmak.
3. Profesyonel, kibar ve net bir Türkçe yanıt taslağı oluşturmak.

Yanıtını SADECE aşağıdaki JSON şemasına uygun olarak ver. Başka hiçbir şey yazma:

{
  "sentiment":   "positive | neutral | negative | mixed",
  "urgency":     "critical | high | medium | low",
  "summary":     "string (max 2 cümle)",
  "key_points":  ["string", "string", ...],
  "draft_reply": "string (tam e-posta gövdesi, selamlama + içerik + kapanış)",
  "confidence":  float (0.0 ile 1.0 arası)
}

Urgency skalası:
- critical : Aynı gün yanıt, hukuki/finansal risk veya sistem kesintisi
- high     : 24 saat içinde yanıt, müşteri memnuniyetsizliği veya iş engeli
- medium   : 2-3 gün içinde yanıt, rutin iş talebi
- low      : Hafta içinde yanıt, bilgilendirme veya düşük öncelikli talep

Draft reply kuralları:
- Her zaman Türkçe yaz
- Resmi ama samimi bir ton kullan
- Konuya direkt gir, gereksiz dolgu cümle kullanma
- İmza satırını şöyle bitir: 'Saygılarımla,\\n[İsim]'
"""


def _build_user_prompt(email: Email) -> str:
    body = email.body_plain.strip() or email.snippet
    # Token limitini aşmamak için gövdeyi kırp
    if len(body) > 3000:
        body = body[:3000] + "\n\n[...geri kalanı kırpıldı...]"

    return f"""Aşağıdaki e-postayı analiz et ve yanıt taslağı oluştur:

GÖNDEREN: {email.sender}
ALICI: {email.recipient}
TARİH: {email.date}
KONU: {email.subject}
GÖVDE:
{body}
"""


# ---------------------------------------------------------------------------
# Ana Analiz Motoru
# ---------------------------------------------------------------------------

def analyze_and_draft(
    email: Email,
    api_key: str | None = None,
) -> DraftResult:
    """
    Tek bir Email nesnesini alır, Claude API'ye gönderir,
    sentiment + urgency analizi ve taslak yanıt döndürür.

    Args:
        email:   fetcher.py'den gelen Email nesnesi.
        api_key: Anthropic API anahtarı. None ise ANTHROPIC_API_KEY env var kullanılır.

    Returns:
        Doldurulmuş DraftResult nesnesi.
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    print(f"[Drafter] Analiz ediliyor → '{email.subject}' ({email.id})")

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_build_system_prompt(),
        messages=[
            {"role": "user", "content": _build_user_prompt(email)}
        ],
    )

    raw_text = message.content[0].text.strip()
    parsed   = _safe_parse_json(raw_text, email)

    return DraftResult(
        email_id    = email.id,
        subject     = email.subject,
        sender      = email.sender,
        sentiment   = parsed["sentiment"],
        urgency     = parsed["urgency"],
        summary     = parsed["summary"],
        key_points  = parsed["key_points"],
        draft_reply = parsed["draft_reply"],
        confidence  = float(parsed.get("confidence", 0.8)),
    )


def analyze_and_draft_batch(
    emails: list[Email],
    api_key: str | None = None,
    urgency_filter: URGENCY_LABELS | None = None,
) -> list[DraftResult]:
    """
    Birden fazla maili sırayla analiz eder.

    Args:
        emails:         fetcher.py'den gelen Email listesi.
        api_key:        Anthropic API anahtarı.
        urgency_filter: Yalnızca belirli aciliyet seviyesini döndür ('critical', 'high' vb.)

    Returns:
        DraftResult listesi (urgency_filter varsa filtrelenmiş).
    """
    results: list[DraftResult] = []

    for i, email in enumerate(emails, 1):
        print(f"[Drafter] {i}/{len(emails)} işleniyor...")
        try:
            result = analyze_and_draft(email, api_key=api_key)
            results.append(result)
        except Exception as e:
            print(f"[Drafter] ⚠️  Mail {email.id} işlenemedi: {e}")
            continue

    if urgency_filter:
        results = [r for r in results if r.urgency == urgency_filter]
        print(f"[Drafter] Filtre uygulandı → urgency='{urgency_filter}', {len(results)} sonuç.")

    # Aciliyete göre sırala: critical → high → medium → low
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(key=lambda r: urgency_order.get(r.urgency, 99))

    return results


# ---------------------------------------------------------------------------
# JSON Güvenli Ayrıştırıcı
# ---------------------------------------------------------------------------

def _safe_parse_json(raw: str, fallback_email: Email) -> dict:
    """
    Model çıktısını JSON olarak ayrıştırır.
    Ayrıştırma başarısız olursa güvenli bir varsayılan döndürür.
    """
    # Markdown kod bloğunu temizle (```json ... ```)
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"[Drafter] ⚠️  JSON ayrıştırma hatası: {e}. Varsayılan değerler kullanılıyor.")
        return {
            "sentiment":   "neutral",
            "urgency":     "medium",
            "summary":     fallback_email.snippet or "Özet çıkarılamadı.",
            "key_points":  ["Model çıktısı ayrıştırılamadı."],
            "draft_reply": (
                f"Sayın yetkili,\n\n"
                f"'{fallback_email.subject}' konulu mailinizi aldık. "
                f"En kısa sürede size geri döneceğiz.\n\n"
                f"Saygılarımla,\n[İsim]"
            ),
            "confidence":  0.0,
        }


# ---------------------------------------------------------------------------
# Dışa Aktarma
# ---------------------------------------------------------------------------

def export_results_to_json(results: list[DraftResult], path: str = "drafts.json") -> None:
    """Tüm sonuçları JSON dosyasına kaydeder (pipeline entegrasyonu için)."""
    data = [
        {
            "email_id":    r.email_id,
            "subject":     r.subject,
            "sender":      r.sender,
            "sentiment":   r.sentiment,
            "urgency":     r.urgency,
            "summary":     r.summary,
            "key_points":  r.key_points,
            "draft_reply": r.draft_reply,
            "confidence":  r.confidence,
        }
        for r in results
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[Drafter] {len(results)} sonuç '{path}' dosyasına kaydedildi.")


# ---------------------------------------------------------------------------
# Kullanım Örneği
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from fetcher import fetch_unread_emails

    # 1. Okunmamış mailleri çek
    emails = fetch_unread_emails(max_results=5)

    if not emails:
        print("İşlenecek mail bulunamadı.")
    else:
        # 2. Toplu analiz yap
        results = analyze_and_draft_batch(emails)

        # 3. Terminalde göster
        for result in results:
            result.pretty_print()

        # 4. JSON olarak kaydet (opsiyonel)
        export_results_to_json(results, path="drafts.json")
