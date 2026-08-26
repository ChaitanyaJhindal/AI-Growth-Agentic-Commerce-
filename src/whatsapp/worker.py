import asyncio
import logging
import time
from typing import Optional
from src import config
from src.whatsapp.queue import WhatsAppQueue, get_whatsapp_queue, mask_phone_number
from src.whatsapp.baileys_client import BaileysClient, get_baileys_client

logger = logging.getLogger("aura.whatsapp.worker")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [WhatsAppWorker] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class WhatsAppWorker:
    """
    Lightweight, sequential MongoDB queue worker for WhatsApp delivery.
    Operates with low concurrency (1 message at a time) and rate-limit spacing
    to ensure ultra-low CPU/RAM usage on Render Free and prevent WhatsApp spam triggers.
    """

    def __init__(
        self,
        queue: Optional[WhatsAppQueue] = None,
        client: Optional[BaileysClient] = None,
        poll_interval: Optional[float] = None,
        rate_limit_delay: Optional[float] = None
    ):
        self.queue = queue or get_whatsapp_queue()
        self.client = client or get_baileys_client()
        self.poll_interval = poll_interval or config.WHATSAPP_POLL_INTERVAL
        self.rate_limit_delay = rate_limit_delay or config.WHATSAPP_RATE_LIMIT_DELAY
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    def process_one_message(self) -> bool:
        """
        Claims and processes one pending message synchronously.
        Returns True if a message was claimed and processed, False if queue is empty.
        """
        claimed = self.queue.claim_next_pending(stale_timeout_seconds=300)
        if not claimed:
            return False

        message_id = claimed.get("message_id")
        recipient = claimed.get("recipient_phone")
        message_body = claimed.get("message", "")
        attempts = claimed.get("attempts", 0)

        masked_phone = mask_phone_number(recipient)
        logger.info(f"Processing message {message_id} for {masked_phone} (Attempt {attempts + 1})...")

        try:
            # Send message via Baileys Engine
            send_res = self.client.send_message(phone=recipient, message=message_body)
            self.queue.mark_sent(message_id, provider_meta=send_res)
            logger.info(f"✓ Message {message_id} sent successfully to {masked_phone}.")
            return True
        except Exception as e:
            err_msg = str(e)
            retry_res = self.queue.mark_failed_or_retry(message_id, error_msg=err_msg)
            new_status = retry_res.get("status")
            curr_attempts = retry_res.get("attempts")
            logger.warning(
                f"✗ Failed sending message {message_id} to {masked_phone}: {err_msg} "
                f"-> Status set to '{new_status}' (Attempt {curr_attempts}/{self.queue.max_attempts})."
            )
            return True

    async def run_loop(self):
        """
        Asynchronous polling loop for the worker.
        """
        self.is_running = True
        logger.info(
            f"WhatsApp Queue Worker started. Poll interval: {self.poll_interval}s, "
            f"Rate limit spacing: {self.rate_limit_delay}s, Max attempts: {self.queue.max_attempts}."
        )

        while self.is_running:
            try:
                # Process messages until queue is empty
                processed_any = False
                while self.is_running:
                    # Run atomic claim & send in threadpool to keep async loop non-blocking
                    had_message = await asyncio.to_thread(self.process_one_message)
                    if not had_message:
                        break
                    processed_any = True
                    # Rate limiting spacing between sequential message dispatches
                    await asyncio.sleep(self.rate_limit_delay)

                # Idle sleep when queue is empty
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("WhatsApp Worker loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in WhatsApp Worker loop: {e}")
                await asyncio.sleep(self.poll_interval)

        self.is_running = False

    def start_background(self) -> asyncio.Task:
        """Starts the worker as a background asyncio task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run_loop())
        return self._task

    def stop(self):
        """Stops the worker gracefully."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()


# Shared singleton worker instance
_whatsapp_worker = None

def get_whatsapp_worker() -> WhatsAppWorker:
    global _whatsapp_worker
    if _whatsapp_worker is None:
        _whatsapp_worker = WhatsAppWorker()
    return _whatsapp_worker
