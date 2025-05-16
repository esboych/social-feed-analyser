#!/usr/bin/env python
"""
Test script for TwitterMonitor and WeaviateStorage components.

This script tests the tweet fetching and storage functionality without 
using sentiment analysis. It's useful for verifying Twitter API integration
and database storage functionality in isolation.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from twitter_sentiment.components.monitor import TwitterMonitor
from twitter_sentiment.components.storage import WeaviateStorage
from twitter_sentiment.utils.csv_loader import load_twitter_accounts


def setup_logging(log_level=logging.INFO):
    """Set up logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler()
        ]
    )


def main():
    """Test TwitterMonitor without sentiment analysis."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test TwitterMonitor and storage")
    parser.add_argument("--accounts", help="Path to accounts CSV file")
    parser.add_argument("--keywords", help="Comma-separated keywords")
    parser.add_argument("--limit", type=int, default=10, help="Maximum tweets to fetch")
    parser.add_argument("--store", action="store_true", help="Store fetched tweets in Weaviate")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--batch-size", type=int, default=3, help="Batch size for processing accounts")
    parser.add_argument("--use-sample", action="store_true", help="Use sample accounts instead of loading from file")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    accounts_file = args.accounts or os.getenv("ACCOUNTS_FILE") or "accounts.csv"
    keywords_str = args.keywords or os.getenv("TARGET_KEYWORDS") or "BTC,ETH,SOL"
    twitterapi_key = os.getenv("TWITTERAPI_KEY")
    weaviate_url = os.getenv("WEAVIATE_URL") or "http://localhost:8080"
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not twitterapi_key:
        logger.error("TwitterAPI.io API key not provided. Set TWITTERAPI_KEY environment variable.")
        return 1
    
    # Parse keywords
    if isinstance(keywords_str, str):
        keywords = [k.strip() for k in keywords_str.split(",")]
    else:
        keywords = keywords_str
    
    # Load Twitter accounts or use sample
    if args.use_sample:
        accounts = [
            "elonmusk",
            "VitalikButerin",
            "cz_binance",
            "michael_saylor",
            "SatoshiLite"
        ]
        logger.info(f"Using {len(accounts)} sample accounts")
    else:
        accounts = load_twitter_accounts(accounts_file)
        if not accounts:
            logger.error(f"No Twitter accounts found in {accounts_file}")
            return 1
        
        # Limit accounts for testing if needed
        max_accounts = min(10, len(accounts))
        if len(accounts) > max_accounts:
            logger.info(f"Limiting to first {max_accounts} accounts for testing")
            accounts = accounts[:max_accounts]
    
    logger.info(f"Using {len(accounts)} accounts")
    logger.info(f"Using keywords: {keywords}")
    
    # Initialize TwitterMonitor
    monitor = TwitterMonitor(
        api_key=twitterapi_key,
        accounts=accounts,
        crypto_keywords=keywords
    )
    
    # Initialize WeaviateStorage if needed
    storage = None
    if args.store:
        if not openai_api_key:
            logger.error("OpenAI API key required for storage. Set OPENAI_API_KEY environment variable.")
            return 1
        
        storage = WeaviateStorage(
            weaviate_url=weaviate_url,
            openai_api_key=openai_api_key
        )
        logger.info(f"Initialized WeaviateStorage at {weaviate_url}")
    
    # Fetch tweets
    logger.info("Fetching tweets...")
    all_tweets = []
    
    # Process accounts in smaller batches
    batch_size = args.batch_size
    for i in range(0, len(accounts), batch_size):
        batch = accounts[i:i+batch_size]
        
        # Temporarily override monitor's accounts with batch
        original_accounts = monitor.accounts
        monitor.accounts = batch
        
        # Fetch tweets for this batch
        try:
            batch_tweets = monitor.process_accounts()
            all_tweets.extend(batch_tweets)
            
            logger.info(f"Fetched {len(batch_tweets)} tweets from batch {i//batch_size + 1}")
        except Exception as e:
            logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
        
        # Restore original accounts
        monitor.accounts = original_accounts
        
        # Check if we've reached the limit
        if args.limit and len(all_tweets) >= args.limit:
            all_tweets = all_tweets[:args.limit]
            break
        
        # Avoid rate limits
        if i + batch_size < len(accounts):
            time.sleep(3)
    
    # If debug mode is enabled, show the structure of a tweet for diagnostics
    if all_tweets and args.debug:
        logger.debug(f"Sample tweet structure: {all_tweets[0]}")
        if "author" in all_tweets[0]:
            logger.debug(f"Author structure: {all_tweets[0]['author']}")
    
    # Display tweet information
    logger.info(f"Fetched a total of {len(all_tweets)} tweets")
    for i, tweet in enumerate(all_tweets):
        logger.info(f"Tweet {i+1}:")
        
        # Extract author information correctly - NOTE the correct field name is 'userName' (camelCase)
        author = tweet.get("author", {})
        username = "unknown"
        if isinstance(author, dict):
            # Try both "userName" (official format) and "username" (fallback)
            username = author.get("userName", author.get("username", "unknown"))
            
            # If debug is enabled, show what fields are available in the author object
            if args.debug and i == 0:
                logger.debug(f"Author field keys: {list(author.keys())}")
        
        logger.info(f"  Author: @{username}")
        logger.info(f"  Text: {tweet.get('text', '')[:100]}...")
        
        # Use createdAt for the creation date
        created_at = tweet.get("createdAt", "unknown")
        logger.info(f"  Created: {created_at}")
        logger.info(f"  ID: {tweet.get('id', 'unknown')}")
        logger.info("---")
    
    # Store tweets if requested
    if args.store and storage and all_tweets:
        logger.info("Storing tweets in Weaviate...")
        
        # Use placeholder sentiment
        placeholder_sentiment = "neutral"
        
        stored_count = 0
        for tweet in all_tweets:
            success = storage.store_tweet(tweet, placeholder_sentiment)
            if success:
                stored_count += 1
        
        logger.info(f"Stored {stored_count}/{len(all_tweets)} tweets with placeholder sentiment '{placeholder_sentiment}'")
        
        # Verify storage by querying some tweets
        if stored_count > 0:
            logger.info("Verifying storage by querying some tweets...")
            for keyword in keywords:
                results = storage.get_latest_sentiments(keyword, count=5)
                logger.info(f"Found {len(results)} tweets containing '{keyword}'")
    
    logger.info("Test completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())