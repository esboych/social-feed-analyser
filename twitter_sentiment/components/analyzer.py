import logging
from typing import Dict, List, Tuple

import openai


class SentimentAnalyzer:
    """LLM-based component for sentiment analysis.
    
    This component uses OpenAI's language models to analyze the sentiment of tweets.
    It implements a fixed prompt structure to ensure consistent classification.
    """
    
    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo-instruct"):
        """Initialize the sentiment analyzer.
        
        Args:
            openai_api_key: OpenAI API key
            model: OpenAI model to use (default: gpt-3.5-turbo-instruct)
        """
        self.logger = logging.getLogger(__name__)
        self.model = model
        
        # Configure OpenAI
        openai.api_key = openai_api_key
        
        self.logger.info(f"Initialized SentimentAnalyzer with model {model}")
    
    def _create_prompt(self, tweet_text: str) -> str:
        """Create a prompt for sentiment analysis.
        
        Args:
            tweet_text: Text of the tweet to analyze
            
        Returns:
            Formatted prompt for the OpenAI model
        """
        return (
            "Analyze the sentiment of this tweet as either 'positive', 'neutral', or 'negative'.\n\n"
            f"Tweet: \"{tweet_text}\"\n\n"
            "Sentiment: "
        )
    
    def analyze_tweet(self, tweet_text: str) -> str:
        """Analyze the sentiment of a single tweet.
        
        Args:
            tweet_text: Text of the tweet to analyze
            
        Returns:
            Sentiment classification: "positive", "neutral", or "negative"
        """
        prompt = self._create_prompt(tweet_text)
        
        try:
            response = openai.Completion.create(
                model=self.model,
                prompt=prompt,
                max_tokens=1,
                temperature=0,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            sentiment = response.choices[0].text.strip().lower()
            
            # Validate and normalize sentiment
            if sentiment not in ["positive", "neutral", "negative"]:
                self.logger.warning(f"Invalid sentiment result: {sentiment}. Defaulting to neutral.")
                sentiment = "neutral"
                
            return sentiment
        except Exception as e:
            self.logger.error(f"Error in sentiment analysis: {e}")
            return "neutral"  # Default to neutral on error
    
    def analyze_batch(self, tweets: List[Dict]) -> List[Tuple[Dict, str]]:
        """Analyze sentiment for a batch of tweets.
        
        Args:
            tweets: List of tweet objects
            
        Returns:
            List of (tweet, sentiment) tuples
        """
        results = []
        
        for tweet in tweets:
            tweet_text = tweet.get("text", "")
            sentiment = self.analyze_tweet(tweet_text)
            results.append((tweet, sentiment))
            
        self.logger.info(f"Analyzed {len(tweets)} tweets")
        return results