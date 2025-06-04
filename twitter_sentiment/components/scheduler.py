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
                self.logger.info("No tweets found from monitored accounts")
                return
            
            self.logger.info(f"Found {len(tweets)} tweets to analyze")
            
            # Analyze sentiments
            analyzed_tweets = self.analyzer.analyze_batch(tweets)
            
            # Store results with improved reporting
            stats = self.storage.store_tweets_batch(analyzed_tweets)
            
            # Report results based on what actually happened
            if stats["new_tweets"] == 0 and stats["existing_tweets"] > 0:
                self.logger.info(
                    f"No new tweets to process - all {stats['existing_tweets']} tweets already analyzed"
                )
            elif stats["new_tweets"] > 0:
                self.logger.info(
                    f"Successfully processed {stats['new_tweets']} new tweets for sentiment analysis"
                )
                
                # If we have errors, log them separately
                if stats["errors"] > 0:
                    self.logger.warning(f"{stats['errors']} tweets failed to store due to errors")
            
            elif stats["errors"] > 0:
                self.logger.error(f"All {stats['errors']} tweets failed to store")
            
        except Exception as e:
            self.logger.error(f"Error in monitoring job: {e}")
        finally:
            self.monitor_lock.release()
    
    def _notification_check_job(self):
        """Job to check sentiment thresholds and send notifications."""
        try:
            self.logger.debug("Checking sentiment thresholds")
            
            for keyword in self.keywords:
                # Get latest sentiments
                latest_sentiments = self.storage.get_latest_sentiments(keyword, count=10)
                
                if not latest_sentiments:
                    self.logger.debug(f"No recent tweets found containing '{keyword}'")
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
                    
                    success = self.notifier.send_notification(message, keyword)
                    if success:
                        self.logger.info(f"Sent positive sentiment notification for {keyword}")
                    else:
                        self.logger.warning(f"Failed to send notification for {keyword}")
                else:
                    self.logger.debug(
                        f"Sentiment threshold not met for {keyword}: "
                        f"{result.get('positive_count', 0)}/{result.get('total_count', 0)} positive"
                    )
        
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