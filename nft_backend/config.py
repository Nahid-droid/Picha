import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load variables from .env file
load_dotenv()

class Config:
    # General configuration
    STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
    DATABASE_PATH = "nft_database.db"
    STATIC_IMAGE_PATH = "static/images"

    # Persistent encryption key from .env
    encryption_key_raw = os.getenv("ENCRYPTION_KEY")
    if encryption_key_raw:
        ENCRYPTION_KEY = encryption_key_raw.encode()
    else:
        raise ValueError("❌ ENCRYPTION_KEY is missing in .env file!")

    # Flask secret key for session management (REQUIRED for OAuth)
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'a_very_secret_key_for_flask_session_development_only')
    if FLASK_SECRET_KEY == 'a_very_secret_key_for_flask_session_development_only':
        print("🚨 WARNING: FLASK_SECRET_KEY is not set in .env or is using a default value. This is insecure for production!")

    # CORS origins - NOW READ DIRECTLY FROM ENVIRONMENT VARIABLE
    # This should be a comma-separated string of allowed origins (e.g., "http://localhost:3000,https://your-vercel-app.vercel.app")
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5000') # Default to backend's own origin for safety

    # Flask settings
    DEBUG = True # You might want to set this via env var too: os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = '0.0.0.0'
    PORT = 5000

    # Canister Configuration
    CANISTER_ENABLED = os.getenv('CANISTER_ENABLED', 'true').lower() == 'true'
    CANISTER_ID = os.getenv('CANISTER_ID', 'rrkah-fqaaa-aaaah-qcyqa-cai')
    ICP_NETWORK = os.getenv('ICP_NETWORK', 'local')  # 'local' or 'ic'
    CANISTER_TIMEOUT = int(os.getenv('CANISTER_TIMEOUT', '30'))
    CANISTER_MAX_RETRIES = int(os.getenv('CANISTER_MAX_RETRIES', '3'))

    # Admin Configuration
    ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', 'your-secure-admin-key-here')

    # X (Twitter) API Configuration - Added for social media integration
    X_API_KEY = os.getenv('X_API_KEY')
    X_API_SECRET = os.getenv('X_API_SECRET')
    X_BEARER_TOKEN = os.getenv('X_BEARER_TOKEN')
    X_ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
    X_ACCESS_TOKEN_SECRET = os.getenv('X_ACCESS_TOKEN_SECRET')
    
    # OAuth Callback URL for X (Twitter) - Crucial for redirect after authentication
    # This should be your backend's URL where X will redirect after user authorization.
    # Example: http://localhost:5000/api/auth/x-callback
    X_CALLBACK_URL = os.getenv('X_CALLBACK_URL', 'http://localhost:5000/api/auth/x-callback')


    @classmethod
    def validate(cls):
        """Validate configuration"""
        required_vars = ['STABILITY_API_KEY', 'ENCRYPTION_KEY', 'FLASK_SECRET_KEY'] # FLASK_SECRET_KEY is now required
        missing_vars = [var for var in required_vars if not getattr(cls, var)]

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

        # Validate canister configuration if enabled
        if cls.CANISTER_ENABLED:
            if not cls.CANISTER_ID:
                raise ValueError("CANISTER_ID is required when CANISTER_ENABLED is true")
            if cls.ICP_NETWORK not in ['local', 'ic']:
                raise ValueError("ICP_NETWORK must be 'local' or 'ic'")

        # Validate X (Twitter) API keys if integration is planned
        if not cls.X_API_KEY or not cls.X_API_SECRET or not cls.X_BEARER_TOKEN:
             print("⚠️ Warning: X (Twitter) API keys (X_API_KEY, X_API_SECRET, X_BEARER_TOKEN) are missing. Social media features may not work.")
        
        if not cls.X_ACCESS_TOKEN or not cls.X_ACCESS_TOKEN_SECRET:
             print("⚠️ Warning: X (Twitter) User Access Tokens (X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET) are missing. User-specific social media features may not work without user OAuth.")

        if not cls.X_CALLBACK_URL:
            print("⚠️ Warning: X_CALLBACK_URL is not set. X (Twitter) OAuth integration will not work without it.")

        print("✅ Configuration validated successfully")

