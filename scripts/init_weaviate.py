#!/usr/bin/env python
import argparse
import logging
import os
import sys
from pathlib import Path

import weaviate
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


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
    """Initialize Weaviate schema."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Initialize Weaviate schema")
    parser.add_argument("--url", help="Weaviate URL")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--force", action="store_true", help="Force recreate schema")
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    weaviate_url = args.url or os.getenv("WEAVIATE_URL") or "http://localhost:8080"
    openai_api_key = args.openai_key or os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        logger.error("OpenAI API key not provided. Use --openai-key or set OPENAI_API_KEY environment variable.")
        return 1
    
    logger.info(f"Initializing Weaviate schema at {weaviate_url}")
    
    try:
        # Initialize Weaviate client
        client = weaviate.Client(
            url=weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        
        # Check if schema exists
        schema_exists = False
        try:
            existing_schema = client.schema.get("TweetSentiment")
            schema_exists = True
            
            if args.force:
                logger.info("Schema already exists. Deleting existing schema...")
                client.schema.delete_class("TweetSentiment")
                schema_exists = False
            else:
                logger.info("Schema already exists. Use --force to recreate.")
        except Exception:
            logger.info("No existing schema found.")
        
        # Create schema if it doesn't exist or was deleted
        if not schema_exists:
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
                    }
                ]
            }
            
            client.schema.create_class(schema)
            logger.info("Schema created successfully.")
        
        # Verify schema works
        logger.info("Testing connection to Weaviate...")
        meta = client.get_meta()
        logger.info(f"Connected to Weaviate version {meta['version']}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error initializing Weaviate schema: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())