import argparse
import logging
import os
import sys
import time
from pathlib import Path

from twitter_sentiment.components.analyzer import SentimentAnalyzer
from twitter_sentiment.components.monitor import TwitterMonitor
from twitter_sentiment.components.notifier import NotificationService
from twitter_sentiment.components.scheduler import ScheduleManager
from twitter_sentiment.components.storage import WeaviateStorage
from twitter_sentiment.config import settings
from twitter_sentiment.utils.csv_loader import load_twitter_accounts


# Configure logging
def setup_logging(log_level=logging.INFO):
    """Set up logging configuration.
    
    Args:
        log_level: Logging level
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("twitter_sentiment.log")
        ]
    )


def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Twitter Sentiment Analysis")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("command", choices=["start", "test_twitter", "test_sentiment", "test_weaviate", "test_notify"], 
                        nargs="?", default="start", help="Command to run")
    parser.add_argument("--param", help="Optional parameter for test commands")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    
    # Load alternate config if specified
    if args.config:
        os.environ["DOTENV_FILE"] = args.config
        from importlib import reload
        from twitter_sentiment import config
        reload(config)
    
    # Process command
    if args.command == "test_twitter":
        # Test Twitter API
        monitor = TwitterMonitor(
            api_key=settings.twitterapi_key,
            accounts=["elonmusk", "VitalikButerin"],  # Test with known accounts
            crypto_keywords=settings.target_keywords
        )
        tweets = monitor.process_accounts()
        logger.info(f"Found {len(tweets)} tweets")
        for tweet in tweets[:5]:  # Show first 5
            logger.info(f"Tweet from {tweet.get('author', {}).get('username')}: {tweet.get('text')[:50]}...")
    
    elif args.command == "test_sentiment":
        # Test sentiment analysis
        analyzer = SentimentAnalyzer(
            openai_api_key=settings.openai_api_key,
            model=settings.openai_model
        )
        
        # Use provided parameter or default test tweets
        if args.param:
            test_tweets = [args.param]
        else:
            test_tweets = [
                "Bitcoin just hit $50,000! This is amazing news for crypto enthusiasts.",
                "Ethereum network congestion is causing high gas fees again. Not happy about this.",
                "Just another day in crypto. BTC moving sideways."
            ]
        
        for tweet in test_tweets:
            sentiment = analyzer.analyze_tweet(tweet)
            logger.info(f"Tweet: {tweet}")
            logger.info(f"Sentiment: {sentiment}")
            logger.info("---")
    
    elif args.command == "test_weaviate":
        # Test Weaviate storage
        storage = WeaviateStorage(
            weaviate_url=settings.weaviate_url,
            openai_api_key=settings.openai_api_key
        )
        
        # Check schema
        storage.ensure_schema_exists()
        
        # Test query
        for keyword in settings.target_keywords:
            trends = storage.query_sentiment_trends(keyword, timeframe_hours=24)
            logger.info(f"Sentiment trends for {keyword}: {trends}")
    
    elif args.command == "test_notify":
        # Test notification
        notifier = NotificationService(
            telegram_token=settings.telegram_token,
            telegram_chat_id=settings.telegram_chat_id,
            notification_method=settings.notification_method
        )
        
        message = args.param or "This is a test notification from the Twitter Sentiment Analysis system."
        success = notifier.send_notification(message, "TEST", channel="all")
        logger.info(f"Notification sent: {success}")
    
    elif args.command == "start":
        # Start the main application
        logger.info("Starting Twitter Sentiment Analysis system")
        
        # Load Twitter accounts
        accounts = load_twitter_accounts(settings.accounts_file)
        if not accounts:
            logger.error(f"No Twitter accounts found in {settings.accounts_file}")
            return 1
        
        # Initialize components
        monitor = TwitterMonitor(
            api_key=settings.twitterapi_key,
            accounts=accounts,
            crypto_keywords=settings.target_keywords
        )
        
        analyzer = SentimentAnalyzer(
            openai_api_key=settings.openai_api_key,
            model=settings.openai_model
        )
        
        storage = WeaviateStorage(
            weaviate_url=settings.weaviate_url,
            openai_api_key=settings.openai_api_key
        )
        
        notifier = NotificationService(
            telegram_token=settings.telegram_token,
            telegram_chat_id=settings.telegram_chat_id,
            notification_method=settings.notification_method
        )
        
        # Create and start scheduler
        scheduler = ScheduleManager(
            monitor=monitor,
            analyzer=analyzer,
            storage=storage,
            notifier=notifier,
            keywords=settings.target_keywords
        )
        
        try:
            scheduler.start(interval_seconds=settings.monitoring_interval)
            
            # Keep the application running
            logger.info("Application running. Press Ctrl+C to exit.")
            while True:
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Stopping application")
            scheduler.stop()
        
        except Exception as e:
            logger.error(f"Error in main application: {e}")
            scheduler.stop()
            return 1
    
    return 0


def cli():
    """Command-line interface entry point."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())