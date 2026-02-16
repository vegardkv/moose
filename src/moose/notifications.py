"""Discord webhook notifications."""
import aiohttp
from datetime import datetime
from moose.config import DISCORD_WEBHOOK_URL


async def send_discord(message: str, level: str = "info") -> None:
    """
    Send a message to Discord via webhook.
    
    Args:
        message: The message content
        level: Message level (info, warning, error)
    """
    # Map level to color
    color_map = {
        "info": 3447003,      # Blue
        "warning": 16776960,  # Yellow
        "error": 15158332,    # Red
    }
    
    color = color_map.get(level.lower(), 3447003)
    timestamp = datetime.utcnow().isoformat()
    
    # Discord embed payload
    payload = {
        "embeds": [{
            "title": f"🦌 Moose - {level.upper()}",
            "description": message,
            "color": color,
            "timestamp": timestamp,
        }]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status not in (200, 204):
                    # Don't raise - we don't want notification failures to crash the app
                    print(f"Discord webhook failed with status {resp.status}")
    except Exception as e:
        # Don't raise - notification failures should not crash the app
        print(f"Discord webhook error: {e}")
