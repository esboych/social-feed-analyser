import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import re

import weaviate


class WeaviateStorage:
    """Fixed-logic component for storing tweet data in Weaviate.
    
    This component handles the storage and retrieval of tweet sentiment data
    in the Weaviate vector database.
    """
    
    def __init__(self, weaviate_url: str, openai_api_key: str):
        """Initialize the Weaviate storage.
        
        Args:
            weaviate_url: URL of the Weaviate instance
            openai_api_key: OpenAI API key for vectorization
        """
        self.logger = logging.getLogger(__name__)
        self.weaviate_url = weaviate_url
        self.openai_api_key = openai_api_key
        
        # Initialize Weaviate client
        self.client = weaviate.Client(
            url=weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        
        # Ensure schema exists
        self.ensure_schema_exists()
        
        self.logger.info(f"Initialized WeaviateStorage with endpoint {weaviate_url}")
    
    def ensure_schema_exists(self) -> None:
        """Create schema if it doesn't exist."""
        # Check if schema exists
        try:
            self.client.schema.get("TweetSentiment")
            self.logger.info("TweetSentiment schema already exists")
            return
        except Exception:
            pass
            
        # Create schema
        schema = {
            "class": "TweetSentiment",
            "vectorizer": "text2vec-openai",
            "properties": [
                {
                    "name": "tweet_text",
                    "dataType": ["text"]
                },
                {
                    "name": "sentiment",
                    "dataType": ["string"]
                },
                {
                    "name": "timestamp",
                    "dataType": ["date"]
                },
                {
                    "name": "source",
                    "dataType": ["text"]
                },
                {
                    "name": "tweet_id",
                    "dataType": ["string"]
                },
                {
                    "name": "author_username",
                    "dataType": ["string"]
                },
                {
                    "name": "author_name",
                    "dataType": ["string"]
                },
                {
                    "name": "retweet_count",
                    "dataType": ["int"]
                },
                {
                    "name": "like_count",
                    "dataType": ["int"]
                }
            ]
        }
        
        self.client.schema.create_class(schema)
        self.logger.info("Created TweetSentiment schema in Weaviate")
    
    def _convert_timestamp_to_rfc3339(self, timestamp: str) -> str:
        """Convert Twitter timestamp to RFC3339 format.
        
        Args:
            timestamp: Timestamp from Twitter API (e.g., "Thu May 15 22:00:22 +0000 2025")
            
        Returns:
            Timestamp in RFC3339 format (e.g., "2025-05-15T22:00:22Z")
        """
        try:
            # First try parsing as RFC3339 - if it's already in the right format
            try:
                # Check if it's already in ISO format
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return timestamp
            except (ValueError, AttributeError):
                pass
                
            # Try to handle the Twitter format: "Thu May 15 22:00:22 +0000 2025"
            # First, check if it matches the expected pattern
            pattern = r"\w{3} (\w{3}) (\d{1,2}) (\d{2}):(\d{2}):(\d{2}) \+0000 (\d{4})"
            match = re.match(pattern, timestamp)
            
            if match:
                month_map = {
                    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
                }
                
                month, day, hour, minute, second, year = match.groups()
                month_num = month_map.get(month, "01")
                day_padded = day.zfill(2)
                
                return f"{year}-{month_num}-{day_padded}T{hour}:{minute}:{second}Z"
            
            # If the pattern doesn't match, try parsing with datetime
            dt = datetime.strptime(timestamp, "%a %b %d %H:%M:%S %z %Y")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        except Exception as e:
            self.logger.warning(f"Error converting timestamp '{timestamp}': {e}")
            # Return current time as fallback
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def store_tweet(self, tweet_data: Dict, sentiment: str) -> bool:
        """Store a tweet with its sentiment analysis in Weaviate.
        
        Args:
            tweet_data: Tweet data object
            sentiment: Sentiment classification
            
        Returns:
            True if storage was successful, False otherwise
        """
        try:
            tweet_id = tweet_data.get("id")
            tweet_text = tweet_data.get("text", "")
            
            # Extract author information (may be nested)
            author = tweet_data.get("author", {})
            username = "unknown"
            author_name = "Unknown"
            
            if isinstance(author, dict):
                # Use the correct camelCase field name - 'userName' not 'username'
                username = author.get("userName", author.get("username", "unknown"))
                # Name field is likely 'name' or could be a different field
                author_name = author.get("name", author.get("displayname", "Unknown"))
            
            # Extract creation date and convert to RFC3339 format
            created_at = tweet_data.get("createdAt", datetime.now().isoformat())
            timestamp = self._convert_timestamp_to_rfc3339(created_at)
            
            # Extract engagement metrics
            retweet_count = int(tweet_data.get("retweetCount", 0))
            like_count = int(tweet_data.get("likeCount", 0))
            
            # Create UUID based on tweet ID for deduplication
            tweet_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"twitter:{tweet_id}")
            
            properties = {
                "tweet_text": tweet_text,
                "sentiment": sentiment,
                "timestamp": timestamp,
                "source": f"@{username}",
                "tweet_id": str(tweet_id),
                "author_username": username,
                "author_name": author_name,
                "retweet_count": retweet_count,
                "like_count": like_count
            }
            
            self.client.data_object.create(
                class_name="TweetSentiment",
                data_object=properties,
                uuid=str(tweet_uuid)
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing tweet {tweet_data.get('id', 'unknown')}: {e}")
            return False
    
    def query_sentiment_trends(self, keyword: str, timeframe_hours: int = 24) -> Dict:
        """Query sentiment trends for a specific keyword.
        
        Args:
            keyword: Keyword to search for
            timeframe_hours: Timeframe in hours to search
            
        Returns:
            Dictionary with sentiment statistics
        """
        try:
            # Get timestamp for timeframe hours ago
            time_ago = (
                datetime.now()
                .timestamp() - (timeframe_hours * 3600)
            )
            time_str = datetime.fromtimestamp(time_ago).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Build GraphQL query
            query = """
            {
              Get {
                TweetSentiment(
                  where: {
                    operator: And,
                    operands: [
                      { path: ["tweet_text"], operator: Like, valueText: $keyword },
                      { path: ["timestamp"], operator: GreaterThanEqual, valueDate: $timestamp }
                    ]
                  }
                ) {
                  sentiment
                  tweet_text
                  timestamp
                  source
                  author_username
                  retweet_count
                  like_count
                }
              }
            }
            """
            
            # Execute query
            result = self.client.query.raw(
                query,
                {"keyword": f"*{keyword}*", "timestamp": time_str}
            )
            
            tweets = result["data"]["Get"]["TweetSentiment"]
            
            # Count sentiments
            sentiments = {"positive": 0, "neutral": 0, "negative": 0}
            for tweet in tweets:
                sentiment = tweet.get("sentiment", "neutral")
                sentiments[sentiment] += 1
            
            return {
                "total": len(tweets),
                "sentiments": sentiments,
                "timeframe_hours": timeframe_hours
            }
        except Exception as e:
            self.logger.error(f"Error querying sentiment trends: {e}")
            return {"total": 0, "sentiments": {"positive": 0, "neutral": 0, "negative": 0}}
    
    def get_latest_sentiments(self, keyword: str, count: int = 10) -> List[Dict]:
        """Get the latest sentiments for a specific keyword.
        
        Args:
            keyword: Keyword to search for
            count: Number of results to return
            
        Returns:
            List of tweet sentiment objects
        """
        try:
            query = """
            {
              Get {
                TweetSentiment(
                  where: {
                    path: ["tweet_text"],
                    operator: Like,
                    valueText: $keyword
                  }
                  limit: $count
                  sort: [{ path: ["timestamp"], order: desc }]
                ) {
                  sentiment
                  tweet_text
                  timestamp
                  source
                  author_username
                  retweet_count
                  like_count
                }
              }
            }
            """
            
            result = self.client.query.raw(
                query,
                {"keyword": f"*{keyword}*", "count": count}
            )
            
            return result["data"]["Get"]["TweetSentiment"]
        except Exception as e:
            self.logger.error(f"Error getting latest sentiments: {e}")
            return []