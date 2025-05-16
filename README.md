# Social Sentiment Analysis System

A hybrid system for monitoring Twitter sentiment about cryptocurrencies, combining fixed logic components with AI-powered sentiment analysis.

## Overview

This application monitors specified Twitter accounts for cryptocurrency-related content, analyzes the sentiment of tweets using OpenAI's language models, stores results in a Weaviate vector database, and sends notifications when positive sentiment exceeds defined thresholds.

## Architecture

The system uses a hybrid architecture:
- **Fixed Logic Components**: Twitter monitoring, data storage, scheduling, notifications
- **AI Components**: Sentiment analysis using OpenAI models

### Component Diagram

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│                │     │                │     │                │
│  Monitoring    │────►│  Sentiment     │────►│  Storage       │
│  Service       │     │  Analyzer      │     │  Service       │
│  (Fixed Logic) │     │  (OpenAI LLM)  │     │  (Fixed Logic) │
│                │     │                │     │                │
└────────────────┘     └────────────────┘     └────────────────┘
        │                                              │
        │                                              │
        ▼                                              ▼
┌────────────────┐                           ┌────────────────┐
│                │                           │                │
│  Scheduled     │                           │  Notification  │
│  Jobs          │                           │  Service       │
│  (Fixed Logic) │                           │  (Fixed Logic) │
│                │                           │                │
└────────────────┘                           └────────────────┘
```

## Setup

### Prerequisites

- Python 3.10+
- Poetry
- Docker and Docker Compose (for Weaviate)
- TwitterAPI.io API key
- OpenAI API key
- Telegram Bot Token (optional)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/twitter-sentiment-analysis.git
   cd twitter-sentiment-analysis
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Create `.env` file with your configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

4. Start Weaviate:
   ```bash
   docker-compose up -d
   ```

5. Initialize Weaviate schema:
   ```bash
   poetry run python scripts/init_weaviate.py
   ```

6. Prepare Twitter accounts list:
   - Create a CSV file named `accounts.csv` with a column named `username` containing Twitter usernames
   - Alternatively, specify a different file in your `.env` configuration

## Usage

### Starting the Application

```bash
# Using the CLI command defined in pyproject.toml
poetry run twitter-sentiment start

# Or using the module directly
poetry run python -m twitter_sentiment.main start
```

### Testing Components

Test Twitter API integration:
```bash
poetry run twitter-sentiment test_twitter
```

Test sentiment analysis:
```bash
poetry run twitter-sentiment test_sentiment
# Or with a specific tweet
poetry run twitter-sentiment test_sentiment --param "Bitcoin price is soaring today!"
```

Test Weaviate storage:
```bash
poetry run twitter-sentiment test_weaviate
```

Test notification system:
```bash
poetry run twitter-sentiment test_notify
# Or with a specific message
poetry run twitter-sentiment test_notify --param "This is a custom test message"
```

### Command Line Options

```
usage: twitter-sentiment [-h] [--debug] [--config CONFIG] [--param PARAM]
                         {start,test_twitter,test_sentiment,test_weaviate,test_notify}

Twitter Sentiment Analysis

positional arguments:
  {start,test_twitter,test_sentiment,test_weaviate,test_notify}
                        Command to run

options:
  -h, --help            show this help message and exit
  --debug               Enable debug logging
  --config CONFIG       Path to config file
  --param PARAM         Optional parameter for test commands
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| TWITTERAPI_KEY | TwitterAPI.io API key | Required |
| OPENAI_API_KEY | OpenAI API key | Required |
| OPENAI_MODEL | OpenAI model for sentiment analysis | gpt-3.5-turbo-instruct |
| WEAVIATE_URL | Weaviate instance URL | http://localhost:8080 |
| TELEGRAM_TOKEN | Telegram bot token | Optional |
| TELEGRAM_CHAT_ID | Telegram chat ID | Optional |
| NOTIFICATION_METHOD | Notification method (telegram, console, both) | console |
| MONITORING_INTERVAL | Interval in seconds for checking tweets | 300 |
| SENTIMENT_THRESHOLD | Threshold for positive sentiment notifications | 7 |
| TARGET_KEYWORDS | Comma-separated list of keywords to monitor | BTC,ETH,SOL |
| ACCOUNTS_FILE | Path to CSV file with Twitter accounts | accounts.csv |

## How It Works

1. **Monitoring**: The system periodically checks specified Twitter accounts for new tweets containing cryptocurrency keywords.
2. **Analysis**: Each tweet is analyzed using OpenAI's language models to determine sentiment (positive, neutral, negative).
3. **Storage**: Results are stored in a Weaviate vector database for efficient retrieval and querying.
4. **Notification**: When 7 out of 10 recent tweets about a specific cryptocurrency show positive sentiment, a notification is sent.

### Example Notification

```
🔥 Positive sentiment alert for BTC! 7/10 recent tweets (70.0%) are positive. Consider potential investment opportunities.
```

## Extending the System

### Adding New Components

The modular architecture makes it easy to add new components:

1. Create a new component in the `twitter_sentiment/components/` directory
2. Add integration in `main.py`
3. Update configuration as needed

### Future Enhancements

Potential agentic enhancements:
- Content classification for more intelligent filtering
- Adaptive threshold adjustment based on market conditions
- Insightful reporting and correlation with external events

## Troubleshooting

Common issues:

- **Weaviate connection errors**: Ensure Docker is running and Weaviate container is healthy
- **Twitter API rate limits**: Adjust monitoring interval and batch size
- **Missing tweets**: Check account list and keywords configuration
- **Sentiment analysis errors**: Verify OpenAI API key and model availability

## License

This project is licensed under the MIT License - see the LICENSE file for details.