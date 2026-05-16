@echo off
title AI-MailCraft — Otonom Mail Servisi
color 0A

echo.
echo  ============================================
echo   AI-MailCraft Baslatiliyor...
echo  ============================================
echo.

:: Anthropic API anahtarini buraya yapistir
set ANTHROPIC_API_KEY=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

:: Gerekli paketleri kur (ilk acilista)
pip install anthropic plyer google-auth google-auth-oauthlib google-api-python-client --quiet

echo  [OK] Paketler hazir.
echo  [OK] API anahtari yuklendi.
echo  [OK] Servis basliyor... Kapat pencereyi durdurmak icin.
echo.

python watcher.py

pause