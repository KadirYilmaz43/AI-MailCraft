# Note: This logic was optimized by Claude Skills Agent.

def notify(title: str, message: str, timeout: int = 8) -> None:
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="AI-MailCraft",
            timeout=timeout,
        )
    except ImportError:
        print(f"\n{'='*50}")
        print(f"🔔 BİLDİRİM: {title}")
        print(f"   {message}")
        print(f"{'='*50}\n")
    except Exception as e:
        print(f"[Notifier] Bildirim gönderilemedi: {e}")
