import logging
import threading
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler


class ScheduleManager:
    """Fixed-logic component for managing scheduled jobs.
    
    This component orchestrates the monitoring, analysis, and notification
    processes, running them on defined schedules.
    """
    
    def __init__(self, monitor, analyzer, storage, notifier, keywords=None):
        """Initialize the scheduler.
        
        Args:
            monitor: TwitterMonitor instance
            analyzer: SentimentAnalyzer instance
            storage: WeaviateStorage instance
            notifier: NotificationService instance
            keywords: List of keywords to monitor for notifications
        """
        self.logger = logging.getLogger(__name__)
        self.monitor = monitor
        self.analyzer = analyzer
        self.storage = storage
        self.notifier = notifier
        self.keywords = keywords or ["BTC", "ETH", "SOL"]
        
        self.running = False
        self.scheduler = None
        
        # Thread lock for monitoring job
        self.monitor_lock = threading.Lock()
        
        self.logger.info("Initialized ScheduleManager")
    
    def _monitoring_job(self):
        """Job to monitor Twitter and process tweets."""
        # Use lock to prevent concurrent runs
        if not self.monitor_lock.acquire(blocking=False):
            self.logger.info("Previous monitoring job still running, skipping")
            return
        
        try:
            self.logger.info("Running monitoring job")
            
            # Fetch tweets
            tweets = self.monitor.process_accounts()
            
            if not tweets:
                self.logger.info("No new tweets found")
                return
            
            # Analyze sentiments
            analyzed_tweets = self.analyzer.analyze_batch(tweets)
            
            # Store results
            stored_count = 0
            for tweet, sentiment in analyzed_tweets:
                success = self.storage.store_tweet(tweet, sentiment)
                if success:
                    stored_count += 1
            
            self.logger.info(f"Stored {stored_count} tweets with sentiment analysis")
            
        except Exception as e:
            self.logger.error(f"Error in monitoring job: {e}")
        finally:
            self.monitor_lock.release()
    
    def _notification_check_job(self):
        """Job to check sentiment thresholds and send notifications."""
        try:
            self.logger.info("Checking sentiment thresholds")
            
            for keyword in self.keywords:
                # Get latest sentiments
                latest_sentiments = self.storage.get_latest_sentiments(keyword, count=10)
                
                if not latest_sentiments:
                    continue
                
                # Check threshold
                result = self.notifier.check_sentiment_threshold(latest_sentiments)
                
                if result["triggered"]:
                    message = (
                        f"🔥 Positive sentiment alert for {keyword}! "
                        f"{result['positive_count']}/{result['total_count']} "
                        f"recent tweets ({result['percentage']}%) are positive. "
                        f"Consider potential investment opportunities."
                    )
                    
                    self.notifier.send_notification(message, keyword)
        
        except Exception as e:
            self.logger.error(f"Error in notification check job: {e}")
    
    def start(self, interval_seconds=300):
        """Start the scheduled jobs.
        
        Args:
            interval_seconds: Interval in seconds for the monitoring job
        """
        if self.running:
            self.logger.warning("Scheduler already running")
            return
            
        self.scheduler = BackgroundScheduler()
        
        # Add monitoring job
        self.scheduler.add_job(
            self._monitoring_job,
            'interval',
            seconds=interval_seconds,
            id='monitoring_job'
        )
        
        # Add notification check job (every minute)
        self.scheduler.add_job(
            self._notification_check_job,
            'interval',
            seconds=60,
            id='notification_job'
        )
        
        self.scheduler.start()
        self.running = True
        self.logger.info(f"Scheduler started with {interval_seconds}s monitoring interval")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self.running:
            self.scheduler.shutdown()
            self.running = False
            self.logger.info("Scheduler stopped")