# Note: This logic was optimized by Claude Skills Agent.

import os
import json
from dataclasses import dataclass
import anthropic
from fetcher import Email

# ---------------------------------------------------------------------------
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
# ---------------------------------------------------------------------------

@dataclass
class DraftResult:
    email_id:    str
    subject:     str
    sender:      str
    sentiment:   str
    urgency:     str
    summary:     str
    key_points:  list[str]
    draft_reply: str
    confidence:  float

    def pretty_print(self) -> None:
        sep = "=" * 65
        print(sep)
        print(f"📧  Konu    : {self.subject}")
        print(f"👤  Gönderen: {self.sender}")
        print(f"💬  Duygu   : {self.sentiment.upper()}")
        print(f"⚡  Aciliyet: {self.urgency.upper()}")
        print(f"🔍  Özet    : {self.summary}")
        print(f"📌  Kritik Noktalar:")
        for point in self.key_points:
            print(f"    • {point}")
        print(f"\n✉️  Taslak Yanıt:\n\n{self.draft_reply}\n{sep}")


def analyze_and_draft(email: Email) -> DraftResult:
    print(f"[Drafter] Analiz ediliyor → '{email.subject}'")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY ortam değişkeni tanımlı değil!")

    client = anthropic.Anthropic(api_key=api_key)

    body = email.body_plain.strip() or email.snippet
    if len(body) > 3000:
        body = body[:3000] + "\n\n[...kırpıldı...]"

    system_prompt = """Sen bir kurumsal iletişim asistanısın.
Sana bir e-posta verilecek. Sen bu e-postayı analiz edecek ve SADECE aşağıdaki JSON formatında yanıt vereceksin. Başka hiçbir şey yazma.

{
  "sentiment": "positive | neutral | negative | mixed",
  "urgency": "critical | high | medium | low",
  "summary": "1-2 cümle özet",
  "key_points": ["nokta 1", "nokta 2"],
  "draft_reply": "Tam e-posta yanıtı buraya. Türkçe yaz. Saygılarımla,\\n[İsim] ile bitir.",
  "confidence": 0.9
}"""

    user_prompt = f"""Aşağıdaki e-postayı analiz et:

GÖNDEREN: {email.sender}
KONU: {email.subject}
İÇERİK:
{body}"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    parsed = _safe_parse_json(raw, email)

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


def analyze_and_draft_batch(emails: list[Email]) -> list[DraftResult]:
    results = []
    for i, email in enumerate(emails, 1):
        print(f"[Drafter] {i}/{len(emails)} işleniyor...")
        try:
            result = analyze_and_draft(email)
            results.append(result)
        except Exception as e:
            print(f"[Drafter] ⚠️ Mail atlandı: {e}")
    return results


def _safe_parse_json(raw: str, email: Email) -> dict:
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return {
            "sentiment":   "neutral",
            "urgency":     "medium",
            "summary":     email.snippet or "Özet çıkarılamadı.",
            "key_points":  ["Ayrıştırma hatası oluştu."],
            "draft_reply": "Otomatik taslak oluşturulamadı.",
            "confidence":  0.0,
        } 