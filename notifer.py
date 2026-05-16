# Note: This logic was optimized by Claude Skills Agent.

"""
Windows masaüstü bildirimi gönderir.
'plyer' kütüphanesi kullanılır — pip install plyer
"""

def notify(title: str, message: str, timeout: int = 8) -> None:
    """
    Sağ alt köşede Windows toast bildirimi gösterir.

    Args:
        title:   Bildirim başlığı
        message: Bildirim içeriği
        timeout: Kaç saniye görünsün (varsayılan: 8)
    """
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="AI-MailCraft",
            timeout=timeout,
        )
    except ImportError:
        # plyer kurulu değilse terminale yaz
        print(f"\n{'='*50}")
        print(f"🔔 BİLDİRİM: {title}")
        print(f"   {message}")
        print(f"{'='*50}\n")
    except Exception as e:
        print(f"[Notifier] Bildirim gönderilemedi: {e}")
