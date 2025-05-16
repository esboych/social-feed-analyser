import logging
import pandas as pd
from typing import List


def load_twitter_accounts(file_path: str) -> List[str]:
    """Load Twitter accounts from CSV file.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of Twitter usernames
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin1', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.error(f"Could not read CSV file {file_path} with any encoding")
            return []
        
        # Extract usernames from DataFrame
        if 'username' in df.columns:
            username_col = 'username'
        elif 'Username' in df.columns:
            username_col = 'Username'
        elif 'account' in df.columns:
            username_col = 'account'
        else:
            # Try to use the first column
            username_col = df.columns[0]
        
        # Extract usernames and remove @ symbol if present
        usernames = [
            username.lstrip('@') if isinstance(username, str) else username
            for username in df[username_col].tolist()
        ]
        
        # Filter out any invalid usernames
        valid_usernames = [
            username for username in usernames 
            if isinstance(username, str) and username.strip()
        ]
        
        logger.info(f"Loaded {len(valid_usernames)} Twitter accounts from {file_path}")
        return valid_usernames
    
    except Exception as e:
        logger.error(f"Error loading Twitter accounts: {e}")
        return []