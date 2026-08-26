import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from src import config
from src.whatsapp.queue import mask_phone_number

class BaileysClient:
    """
    Python client for the internal Node.js Baileys WhatsApp Engine (127.0.0.1:5001).
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.WHATSAPP_BAILEYS_URL).rstrip('/')

    def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Sends a WhatsApp message through the local Baileys engine.
        """
        is_dry_run = os.getenv("WHATSAPP_DRY_RUN", "").lower() in ("true", "1", "yes") or config.WHATSAPP_DRY_RUN
        if is_dry_run:
            return {
                "success": True,
                "simulated": True,
                "provider": "baileys_mock",
                "recipient": mask_phone_number(phone)
            }

        url = f"{self.base_url}/send"
        payload = json.dumps({
            "phone": phone,
            "message": message
        }).encode('utf-8')

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=12) as res:
                data = json.loads(res.read().decode('utf-8'))
                if data.get("success"):
                    return {
                        "success": True,
                        "provider_message_id": data.get("messageId"),
                        "timestamp": data.get("timestamp"),
                        "provider": "baileys"
                    }
                raise RuntimeError(data.get("error", "Baileys failed to send message."))
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode('utf-8'))
                msg = err_data.get("error", e.reason)
            except Exception:
                msg = f"HTTP {e.code}: {e.reason}"
            raise RuntimeError(f"Baileys Engine Error: {msg}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Baileys Service Unavailable at {self.base_url}: {e.reason}")

    def get_status(self) -> Dict[str, Any]:
        """Checks the connection status of the Baileys engine."""
        url = f"{self.base_url}/status"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3) as res:
                return json.loads(res.read().decode('utf-8'))
        except Exception:
            return {
                "running": False,
                "connected": False,
                "authenticated": False,
                "engine": "baileys",
                "dry_run": os.getenv("WHATSAPP_DRY_RUN", "").lower() in ("true", "1", "yes") or config.WHATSAPP_DRY_RUN
            }

    def get_qr(self) -> Dict[str, Any]:
        """Fetches the latest connection QR code if waiting for authentication."""
        url = f"{self.base_url}/qr"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3) as res:
                return json.loads(res.read().decode('utf-8'))
        except Exception:
            return {"authenticated": False, "qr": None}


# Shared singleton client
_baileys_client = None

def get_baileys_client() -> BaileysClient:
    global _baileys_client
    if _baileys_client is None:
        _baileys_client = BaileysClient()
    return _baileys_client
