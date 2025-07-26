import tweepy
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta # Import datetime for timestamp comparison

# Assuming Config is available one level up from services directory
from config import Config

logger = logging.getLogger(__name__)

class SocialMediaService:
    """
    Service to handle X (formerly Twitter) API interactions, including OAuth
    authentication and fetching user tweets.
    """

    def __init__(self):
        """
        Initializes the SocialMediaService with API credentials from Config.
        Raises ValueError if required X API keys are not found.
        """
        self.consumer_key = Config.X_API_KEY
        self.consumer_secret = Config.X_API_SECRET
        self.callback_url = Config.X_CALLBACK_URL

        if not self.consumer_key or not self.consumer_secret or not self.callback_url:
            raise ValueError(
                "X_API_KEY, X_API_SECRET, and X_CALLBACK_URL must be set in config.py "
                "from your .env file for social media integration."
            )

        logger.info("SocialMediaService initialized.")

    def _get_oauth_handler(self, access_token: Optional[str] = None, access_token_secret: Optional[str] = None) -> tweepy.OAuth1UserHandler:
        """
        Helper to get an OAuthHandler instance.
        If access tokens are provided, it sets them.
        """
        handler = tweepy.OAuth1UserHandler(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            callback=self.callback_url
        )
        if access_token and access_token_secret:
            handler.set_access_token(
                access_token=access_token,
                access_token_secret=access_token_secret
            )
        return handler

    def start_oauth_flow(self) -> Dict[str, str]:
        """
        Initiates the X (Twitter) OAuth 1.0a authentication flow.
        Gets a request token and returns the authorization URL for the user to redirect to.

        Returns:
            Dict: Contains 'authorization_url' and 'request_token_secret'.
                  The 'request_token_secret' must be stored temporarily by the caller
                  to complete the OAuth flow in the callback.
        Raises:
            tweepy.TweepyException: If there's an issue obtaining the request token.
        """
        try:
            oauth = self._get_oauth_handler()
            # This requests a temporary "request token" from X
            # After this call, oauth.request_token will be populated as a dictionary
            authorization_url = oauth.get_authorization_url(signin_with_twitter=True)
            
            # The request token secret is needed in the callback to get the access token
            # FIX: Access using dictionary key instead of dot notation
            request_token_secret = oauth.request_token['oauth_token_secret']

            logger.info(f"Initiated X OAuth flow. Authorization URL: {authorization_url}")
            return {
                "authorization_url": authorization_url,
                "request_token_secret": request_token_secret
            }
        except tweepy.TweepyException as e:
            logger.error(f"Error starting X OAuth flow: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during X OAuth test: {e}")
            raise


    def complete_oauth_flow(self, oauth_token: str, oauth_verifier: str, request_token_secret: str) -> Dict[str, str]:
        """
        Completes the X (Twitter) OAuth 1.0a authentication flow.
        Exchanges the request token and verifier for a long-lived access token.

        Args:
            oauth_token (str): The oauth_token received from X in the callback URL.
            oauth_verifier (str): The oauth_verifier received from X in the callback URL.
            request_token_secret (str): The request token secret that was stored after `start_oauth_flow`.

        Returns:
            Dict: Contains 'access_token', 'access_token_secret', and 'user_id'.
                  These should be securely stored in your database linked to the user.
        Raises:
            tweepy.TweepyException: If there's an issue exchanging the tokens.
        """
        try:
            oauth = self._get_oauth_handler()
            # Set the temporary request token obtained in start_oauth_flow
            # This sets the internal request_token attribute on the handler as a dictionary
            oauth.request_token = {
                'oauth_token': oauth_token,
                'oauth_token_secret': request_token_secret # This is why we need to store it
            }

            # This exchanges the request token for a permanent access token
            access_token, access_token_secret = oauth.get_access_token(oauth_verifier)

            # Get user details using the new access tokens
            client = tweepy.Client(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            
            # Fetch user ID and username of the authenticated user
            user = client.get_me(user_auth=True, user_fields=['profile_image_url']) # Added profile_image_url to fields
            user_id = user.data.id if user.data else None
            username = user.data.username if user.data else None
            # profile_image_url = user.data.profile_image_url if user.data else None # Example of accessing more data

            if not user_id:
                raise tweepy.TweepyException("Could not retrieve user ID after OAuth completion.")

            logger.info(f"Completed X OAuth flow for user @{username} (ID: {user_id}).")
            return {
                "access_token": access_token,
                "access_token_secret": access_token_secret,
                "user_id": str(user_id), # Ensure it's a string
                "username": username
                # "profile_image_url": profile_image_url # Include if fetched
            }
        except tweepy.TweepyException as e:
            logger.error(f"Error completing X OAuth flow: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during X OAuth completion: {e}")
            raise

    def get_user_tweets(self, user_id: str, access_token: str, access_token_secret: str, 
                        tweet_count: int = 100, since_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Fetches recent tweets for a given user using their access tokens.
        Includes filtering by since_time (tweets created after this timestamp).

        Args:
            user_id (str): The ID of the user whose tweets to fetch.
            access_token (str): The user's X access token.
            access_token_secret (str): The user's X access token secret.
            tweet_count (int): The maximum number of tweets to retrieve (max 100 for API v2).
            since_time (Optional[datetime]): Fetch tweets created after this datetime.

        Returns:
            Dict: A dictionary containing the fetched tweets data and any metadata.
                  Format: {'tweets': [...], 'meta': {...}}
        Raises:
            tweepy.TweepyException: If there's an issue fetching the tweets.
            ValueError: If access tokens are missing.
        """
        if not (access_token and access_token_secret):
            raise ValueError("Access tokens are required to fetch user tweets.")

        try:
            client = tweepy.Client(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )

            # Prepare start_time for API if provided
            start_time_iso = None
            if since_time:
                # Ensure datetime is in UTC and ISO 8601 format with 'Z' for Twitter API
                # If naive datetime, assume UTC for simplicity
                if since_time.tzinfo is None:
                    start_time_iso = since_time.isoformat() + 'Z'
                else:
                    start_time_iso = since_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
                logger.info(f"Fetching tweets since: {start_time_iso}")


            # Using client.get_users_tweets for API v2
            # max_results can be between 5 and 100 for recent tweets
            response = client.get_users_tweets(
                id=user_id,
                max_results=min(tweet_count, 100), # Ensure max_results does not exceed 100
                tweet_fields=["created_at", "public_metrics", "text", "source"], # Request relevant fields
                start_time=start_time_iso # Pass the start_time parameter
            )
            
            tweets_data = []
            if response.data:
                for tweet in response.data:
                    tweets_data.append({
                        "id": tweet.id,
                        "text": tweet.text,
                        "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                        "public_metrics": { # Include all public metrics
                            "retweet_count": tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                            "reply_count": tweet.public_metrics.get('reply_count', 0) if tweet.public_metrics else 0,
                            "like_count": tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                            "quote_count": tweet.public_metrics.get('quote_count', 0) if tweet.public_metrics else 0,
                            "impression_count": tweet.public_metrics.get('impression_count', 0) if tweet.public_metrics else 0,
                        },
                        "source": tweet.source # E.g., "Twitter for iPhone", "Buffer", etc.
                    })

            logger.info(f"Fetched {len(tweets_data)} tweets for user ID: {user_id}")
            return {
                "tweets": tweets_data,
                "meta": response.meta # Includes pagination info
            }
        except tweepy.TweepyException as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching tweets for user {user_id}: {e}")
            raise

# Example Usage (for testing purposes, remove in production if not needed)
if __name__ == '__main__':
    # You would typically get these from your .env file
    # For testing, ensure your .env has valid X_API_KEY, X_API_SECRET, X_CALLBACK_URL
    # and temporarily set a dummy X_CALLBACK_URL if testing locally without a running Flask app
    # (e.g., X_CALLBACK_URL=http://localhost:5000/api/auth/x-callback)
    
    # NOTE: You MUST replace these with actual values from YOUR X Developer App
    # This block is just for demonstration and won't run correctly without actual keys and a callback endpoint.
    class MockConfig:
        X_API_KEY = os.getenv("X_API_KEY", "YOUR_X_API_KEY")
        X_API_SECRET = os.getenv("X_API_SECRET", "YOUR_X_API_SECRET")
        X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "YOUR_X_BEARER_TOKEN") # Not directly used in OAuth1.0a flow, but good to have
        X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", None) # For direct tweet fetching after OAuth
        X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", None) # For direct tweet fetching after OAuth
        X_CALLBACK_URL = os.getenv("X_CALLBACK_URL", "http://localhost:5000/api/auth/x-callback")

    # Temporarily override Config for this example if running standalone
    import sys
    sys.modules['config'] = MockConfig
    
    # Import pytz for timezone handling in example, usually handled by database/system
    try:
        import pytz
    except ImportError:
        print("Warning: pytz not installed. Install with: pip install pytz for full timezone support in example usage.")
        pytz = None


    try:
        service = SocialMediaService()

        # --- Test OAuth Flow (requires manual intervention) ---
        print("\n--- Starting OAuth Flow Test ---")
        try:
            # Removed client-side simulation, just show URL
            oauth_start_info = service.start_oauth_flow()
            auth_url = oauth_start_info["authorization_url"]
            req_token_secret = oauth_start_info["request_token_secret"]
            print(f"Please go to this URL to authorize: {auth_url}")
            print(f"Store this request token secret for callback: {req_token_secret}")
            print("After authorization, you will be redirected to your callback URL.")
            print("The URL will contain 'oauth_token' and 'oauth_verifier' as query parameters.")
            print("You would then use these in complete_oauth_flow.")
            
        except ValueError as ve:
            print(f"Configuration error for OAuth test: {ve}")
        except tweepy.TweepyException as te:
            print(f"Tweepy error during OAuth test: {te}")
        except Exception as e:
            print(f"An unexpected error occurred during OAuth test: {e}")

        # --- Test Fetching Tweets (requires existing access tokens) ---
        print("\n--- Fetching Tweets Test (requires saved tokens) ---")
        # For this part to work, you need to manually set X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET
        # in your .env file for a test user, or use the tokens obtained from the OAuth flow above.
        test_user_id = "YOUR_TEST_USER_ID" # Replace with a valid user ID (e.g., from your own X account)
        test_access_token = MockConfig.X_ACCESS_TOKEN
        test_access_token_secret = MockConfig.X_ACCESS_TOKEN_SECRET

        if test_user_id != "YOUR_TEST_USER_ID" and test_access_token and test_access_token_secret:
            try:
                # Test with a since_time (e.g., last 7 days)
                seven_days_ago = datetime.now() - timedelta(days=7)
                tweets = service.get_user_tweets(
                    user_id=test_user_id, 
                    access_token=test_access_token, 
                    access_token_secret=test_access_token_secret, 
                    tweet_count=5,
                    since_time=seven_days_ago
                )
                print(f"Successfully fetched {len(tweets['tweets'])} tweets for user {test_user_id} since {seven_days_ago}:")
                for tweet in tweets['tweets']:
                    print(f"- [{tweet['id']}] {tweet['text'][:70]}... (Likes: {tweet['public_metrics'].get('like_count', 0)})")
            except ValueError as ve:
                print(f"Configuration error for tweet fetching: {ve}")
            except tweepy.TweepyException as te:
                print(f"Tweepy error during tweet fetching: {te}")
            except Exception as e:
                print(f"An unexpected error occurred during tweet fetching: {e}")
        else:
            print("Skipping tweet fetching test: Please set YOUR_TEST_USER_ID, X_ACCESS_TOKEN, and X_ACCESS_TOKEN_SECRET in .env.")

    except ValueError as e:
        print(f"Service initialization error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during service initialization: {e}")

