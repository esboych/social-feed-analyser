#!/usr/bin/env python
"""
Test script for TwitterAPI.io connection using the last_tweets endpoint.

This script tests the connection to TwitterAPI.io using the correct endpoint
and parameter name for retrieving a user's last tweets.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_twitter_api():
    """Test connection to TwitterAPI.io using the last_tweets endpoint."""
    api_key = os.getenv("TWITTERAPI_KEY")
    
    if not api_key:
        print("ERROR: TWITTERAPI_KEY not found in environment variables")
        print("Make sure to create a .env file with your API key")
        return False
    
    # Display a masked version of the key for debugging
    masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
    print(f"Found API key: {masked_key}")
    
    # Use the correct endpoint for last tweets
    url = "https://api.twitterapi.io/twitter/user/last_tweets"
    headers = {"X-API-Key": api_key}
    
    # Try a simple request to the API
    try:
        # Use a popular account for testing
        test_username = "elonmusk"
        print(f"Testing API with query for user: @{test_username}")
        
        # Add username parameter with capital 'N' as required
        params = {"userName": test_username, "limit": 5}
        
        # Make the request
        response = requests.request("GET", url, headers=headers, params=params)
        
        # Check response
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Success! Response received with {len(response.text)} bytes")
                
                # Print the top-level keys to understand the structure
                print(f"Response structure - top level keys: {list(data.keys())}")
                
                # Check the structure in more detail
                if "status" in data and data["status"] == "success":
                    print("Status: success")
                    
                    # Check if data field exists
                    if "data" in data:
                        data_obj = data["data"]
                        print(f"Data field keys: {list(data_obj.keys())}")
                        
                        # Check if tweets field exists in data
                        if "tweets" in data_obj:
                            tweets = data_obj["tweets"]
                            print(f"Found {len(tweets)} tweets")
                            
                            # Display tweet information
                            if tweets:
                                first_tweet = tweets[0]
                                print("\nSample tweet data:")
                                print(f"Tweet ID: {first_tweet.get('id', 'unknown')}")
                                print(f"Text: {first_tweet.get('text', 'No text')[:100]}...")
                                print(f"Available fields: {list(first_tweet.keys())}")
                            
                            return True
                        else:
                            print("No 'tweets' field found in the data object")
                    else:
                        print("No 'data' field found in the response")
                else:
                    print(f"Unexpected response status: {data.get('status', 'unknown')}")
                    print(f"Message: {data.get('msg', 'No message')}")
                
                # If we reached here, something went wrong with the parsing
                print(f"Raw response preview: {response.text[:200]}...")
                return False
                
            except Exception as e:
                print(f"Error parsing response: {e}")
                print(f"Raw response preview: {response.text[:200]}...")
                return False
        else:
            print(f"ERROR: API returned status code {response.status_code}")
            print(f"Response body: {response.text}")
            
            # Provide troubleshooting advice
            if response.status_code == 400:
                print("\nTROUBLESHOOTING FOR 400 BAD REQUEST:")
                print("1. Check if the required parameters are provided correctly")
                print("2. Verify parameter names (e.g., 'username' vs 'userName')")
                print("3. Try different parameter combinations")
            elif response.status_code == 401:
                print("\nTROUBLESHOOTING FOR 401 UNAUTHORIZED:")
                print("1. Verify your API key is correct")
                print("2. Check if your TwitterAPI.io subscription is active")
            elif response.status_code == 404:
                print("\nTROUBLESHOOTING FOR 404 NOT FOUND:")
                print("1. Check if the API endpoint URL is correct")
                print("2. Verify the user exists and is public")
            
            return False
            
    except Exception as e:
        print(f"ERROR: Exception occurred during API request: {e}")
        return False


if __name__ == "__main__":
    print("Twitter API Connection Test")
    print("--------------------------")
    result = test_twitter_api()
    
    print("\nTest result:", "PASSED" if result else "FAILED")
    
    if not result:
        print("\nIMPORTANT:")
        print("If the test failed, check your API key and subscription status.")
        print("You may need to contact TwitterAPI.io support for assistance.")
    
    sys.exit(0 if result else 1)