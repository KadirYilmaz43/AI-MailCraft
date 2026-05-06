# Note: This logic was optimized by Claude Skills Agent.

import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Gmail read-only scope — genişletmek için GMAIL_MODIFY veya GMAIL_FULL kullanılabilir
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TOKEN_PATH = Path("token.json")
CREDENTIALS_PATH = Path("credentials.json")


def get_credentials() -> Credentials:
    """
    Google OAuth 2.0 akışını yönetir.
    - token.json varsa ve geçerliyse direkt kullanır.
    - Token süresi dolmuşsa otomatik yeniler.
    - Hiç token yoksa browser üzerinden OAuth akışı başlatır.
    """
    creds: Credentials | None = None

    # Daha önce kaydedilmiş token var mı?
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # Token yok ya da geçersiz
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Süresi dolmuş → sessizce yenile
            try:
                creds.refresh(Request())
                print("[Auth] Token yenilendi.")
            except Exception as e:
                print(f"[Auth] Token yenileme başarısız, yeniden giriş gerekiyor: {e}")
                creds = _run_oauth_flow()
        else:
            # İlk kez giriş
            creds = _run_oauth_flow()

        # Yeni token'ı kaydet
        _save_token(creds)

    return creds


def _run_oauth_flow() -> Credentials:
    """
    Browser tabanlı OAuth 2.0 akışını başlatır.
    Google Cloud Console'dan indirilen credentials.json gereklidir.
    """
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"'{CREDENTIALS_PATH}' bulunamadı.\n"
            "Google Cloud Console > APIs & Services > Credentials bölümünden\n"
            "OAuth 2.0 Client ID oluşturup JSON olarak indirin."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH), SCOPES
    )

    # port=0 → işletim sistemi boş bir port seçer
    creds = flow.run_local_server(port=0, prompt="consent")
    print("[Auth] Giriş başarılı.")
    return creds


def _save_token(creds: Credentials) -> None:
    """Token'ı diske yazar."""
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }
    TOKEN_PATH.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"[Auth] Token '{TOKEN_PATH}' dosyasına kaydedildi.")


def revoke_token() -> None:
    """
    Mevcut token'ı siler (çıkış / hesap değişikliği için).
    Sonraki çalışmada OAuth akışı yeniden başlar.
    """
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        print("[Auth] Token silindi. Sonraki çalışmada yeniden giriş gerekecek.")
    else:
        print("[Auth] Silinecek token bulunamadı.")