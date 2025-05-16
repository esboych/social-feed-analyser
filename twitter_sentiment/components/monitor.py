import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests


class TwitterMonitor:
    """Fixed-logic component for monitoring Twitter accounts.
    
    This component is responsible for fetching tweets from specified Twitter accounts
    using the TwitterAPI.io service. It implements batch processing and rate limiting
    to efficiently handle multiple accounts.
    """
    
    def __init__(self, api_key: str, accounts: List[str], crypto_keywords: List[str]):
        """Initialize the Twitter monitor.
        
        Args:
            api_key: TwitterAPI.io API key
            accounts: List of Twitter accounts to monitor
            crypto_keywords: List of cryptocurrency keywords to filter tweets by
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.accounts = accounts
        self.crypto_keywords = crypto_keywords
        self.last_tweet_ids = {}  # Track last tweet ID for each account
        
        # Set up API session with the correct header format
        self.session = requests.Session()
        self.headers = {
            "X-API-Key": self.api_key  # Capital X-API-Key as shown in the documentation
        }
        
        self.logger.info(f"Initialized TwitterMonitor with {len(accounts)} accounts")
    
    def fetch_tweets(self, username: str, keywords: Optional[List[str]] = None, 
                    since_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Fetch tweets from a specific user, optionally filtered by keywords.
        
        Args:
            username: Twitter username (without @)
            keywords: Optional list of keywords to filter tweets by
            since_id: Only fetch tweets newer than this ID
            limit: Maximum number of tweets to fetch
            
        Returns:
            List of tweet objects
        """
        # Use the correct endpoint for last tweets
        url = "https://api.twitterapi.io/twitter/user/last_tweets"
        
        # Set up parameters - using 'userName' with capital 'N' as required by the API
        params = {
            "userName": username,
            "limit": limit
        }
        
        if since_id:
            params["since_id"] = since_id
            
        # Make request
        try:
            self.logger.debug(f"Fetching tweets for {username} with params {params}")
            
            response = requests.request("GET", url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                # Extract tweets from response
                try:
                    data = response.json()
                    
                    # Check for successful response
                    if data.get("status") == "success" and "data" in data:
                        # Get the data object
                        data_obj = data["data"]
                        
                        # Get tweets from the correct nested location
                        if "tweets" in data_obj:
                            tweets = data_obj["tweets"]
                            self.logger.debug(f"Found {len(tweets)} tweets for {username}")
                            
                            # Filter by keywords if specified
                            if keywords and tweets:
                                filtered_tweets = []
                                for tweet in tweets:
                                    text = tweet.get("text", "").lower()
                                    if any(keyword.lower() in text for keyword in keywords):
                                        filtered_tweets.append(tweet)
                                
                                self.logger.debug(f"Filtered to {len(filtered_tweets)} tweets containing keywords")
                                return filtered_tweets
                            
                            return tweets
                        else:
                            self.logger.warning(f"No tweets field found in data object for {username}")
                            return []
                    else:
                        self.logger.warning(f"Unsuccessful response for {username}: {data.get('msg', 'No message')}")
                        return []
                    
                except Exception as e:
                    self.logger.error(f"Error parsing response for {username}: {e}")
                    self.logger.error(f"Response preview: {response.text[:200]}...")
                    return []
            else:
                self.logger.error(f"Error fetching tweets for {username}: Status {response.status_code}")
                self.logger.error(f"Response: {response.text[:150]}...")
                return []
                
        except requests.RequestException as e:
            self.logger.error(f"Request exception for {username}: {e}")
            return []
    
    def process_accounts(self, batch_size: int = 5) -> List[Dict]:
        """Process accounts in batches to avoid rate limits.
        
        Args:
            batch_size: Number of accounts to process in each batch
            
        Returns:
            List of new tweets
        """
        all_tweets = []
        
        # Process accounts in batches
        for i in range(0, len(self.accounts), batch_size):
            batch = self.accounts[i:i+batch_size]
            
            for account in batch:
                # Get last tweet ID for this account
                since_id = self.last_tweet_ids.get(account)
                
                # Fetch tweets
                tweets = self.fetch_tweets(
                    username=account,
                    keywords=self.crypto_keywords,
                    since_id=since_id
                )
                
                if tweets:
                    # Update last tweet ID if available
                    if tweets and isinstance(tweets[0], dict) and "id" in tweets[0]:
                        self.last_tweet_ids[account] = tweets[0]["id"]
                    all_tweets.extend(tweets)
                    
                    self.logger.info(f"Fetched {len(tweets)} tweets from @{account}")
                
            # Avoid rate limits
            if i + batch_size < len(self.accounts):
                time.sleep(2)
        
        self.logger.info(f"Processed {len(self.accounts)} accounts, found {len(all_tweets)} new tweets")
        return all_tweets