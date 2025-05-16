import logging
import time
from typing import Dict, List, Optional

import requests


class NotificationService:
    """Fixed-logic component for sending notifications.
    
    This component handles notification triggers and delivery via different channels
    (console, Telegram).
    """
    
    def __init__(self, telegram_token: Optional[str] = None, 
                telegram_chat_id: Optional[str] = None,
                notification_method: str = "console"):
        """Initialize the notification service.
        
        Args:
            telegram_token: Telegram bot token
            telegram_chat_id: Telegram chat ID
            notification_method: Notification method (console, telegram, both)
        """
        self.logger = logging.getLogger(__name__)
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.notification_method = notification_method
        
        # Track last notification time to prevent spam
        self.last_notification_time = {}
        
        # Set minimum interval between notifications (1 hour)
        self.min_interval = 3600
        
        self.logger.info(f"Initialized NotificationService with method: {notification_method}")
    
    def check_sentiment_threshold(self, sentiments: List[Dict], threshold: int = 7) -> Dict:
        """Check if sentiment crosses threshold (e.g., 7/10 positive tweets).
        
        Args:
            sentiments: List of sentiment objects
            threshold: Minimum number of positive sentiments to trigger
            
        Returns:
            Dictionary with trigger status and statistics
        """
        if len(sentiments) < 10:
            return {"triggered": False, "reason": "Not enough data"}
        
        # Count positive sentiments
        positive_count = sum(1 for s in sentiments if s.get("sentiment") == "positive")
        
        # Check if threshold is met
        triggered = positive_count >= threshold
        
        return {
            "triggered": triggered,
            "positive_count": positive_count,
            "total_count": len(sentiments),
            "percentage": round((positive_count / len(sentiments)) * 100, 1)
        }
    
    def _can_send_notification(self, keyword: str) -> bool:
        """Check if we can send notification based on rate limiting.
        
        Args:
            keyword: Keyword for the notification
            
        Returns:
            True if notification can be sent, False otherwise
        """
        current_time = time.time()
        last_time = self.last_notification_time.get(keyword, 0)
        
        if current_time - last_time >= self.min_interval:
            self.last_notification_time[keyword] = current_time
            return True
        return False
    
    def _send_telegram(self, message: str) -> bool:
        """Send notification via Telegram.
        
        Args:
            message: Message to send
            
        Returns:
            True if successful, False otherwise
        """
        if not (self.telegram_token and self.telegram_chat_id):
            self.logger.warning("Cannot send Telegram notification: missing token or chat_id")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    def send_notification(self, message: str, keyword: str, channel: str = "all") -> bool:
        """Send notification via specified channel.
        
        Args:
            message: Message to send
            keyword: Keyword for rate limiting
            channel: Notification channel (all, console, telegram)
            
        Returns:
            True if at least one notification was sent, False otherwise
        """
        # Check rate limiting
        if not self._can_send_notification(keyword):
            self.logger.info(f"Skipping notification for {keyword} due to rate limiting")
            return False
        
        success = False
        
        # Send via console
        if channel in ["all", "console"] or self.notification_method in ["all", "console"]:
            self.logger.info(f"NOTIFICATION: {message}")
            success = True
        
        # Send via Telegram
        if channel in ["all", "telegram"] or self.notification_method in ["all", "telegram"]:
            telegram_success = self._send_telegram(message)
            success = success or telegram_success
        
        return success