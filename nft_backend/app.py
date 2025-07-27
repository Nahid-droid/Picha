import eventlet # Import eventlet first
eventlet.monkey_patch() # Apply monkey patch at the very beginning

import os
import random
import asyncio
import logging
import time
from flask import Flask, request, jsonify, send_from_directory, session, g, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps
import json
from ic.principal import Principal
from config import Config
from services.nft_engine import NFTEngine
from models.data_models import GenerationMode, EventType, UniquenessFactors, ScarcityInfo, GeneticTraits, SocialMediaAuth
# Add for X (Twitter) integration
from services.social_media import SocialMediaService
# Add these imports at the top of app.py (after existing imports)
from canister_client import CanisterClient, NFTMetadata, CanisterError, NetworkType
from flask_socketio import SocketIO, emit # Import SocketIO and emit
from services.websocket_handlers import setup_websocket_handlers, broadcast_scarcity_update, broadcast_evolution_notification, broadcast_new_mint # Import WebSocket handlers and broadcasters
from models.database import DatabaseManager # Import DatabaseManager
from dataclasses import asdict
# Import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Validate configuration
Config.validate()

# --- CORS Configuration Setup ---
# Ensure CORS_ORIGINS from Config is a mutable list of allowed origins.
# Assuming Config.CORS_ORIGINS is a string or list loaded from environment variables.
# It's crucial that this list eventually includes your Vercel frontend URL.
allowed_origins = []
if isinstance(Config.CORS_ORIGINS, str):
    # Split comma-separated string from environment variables into a list
    allowed_origins = [o.strip() for o in Config.CORS_ORIGINS.split(',') if o.strip()]
elif isinstance(Config.CORS_ORIGINS, (list, tuple)):
    allowed_origins = list(Config.CORS_ORIGINS)

# Add the specific Vercel URL if it's not already in the allowed_origins list.
# THIS IS THE KEY CHANGE FOR YOUR CURRENT CORS ERROR.
vercel_frontend_url = "https://picha-wfxt-nahid-droids-projects.vercel.app"
if vercel_frontend_url not in allowed_origins:
    allowed_origins.append(vercel_frontend_url)

logger.info(f"Configured CORS allowed origins: {allowed_origins}")
# --- End CORS Configuration Setup ---

# Initialize canister client
canister_client = None
if Config.CANISTER_ENABLED:
    try:
        canister_client = CanisterClient(
            canister_id=Config.CANISTER_ID,
            network=Config.ICP_NETWORK,
            timeout=Config.CANISTER_TIMEOUT,
            max_retries=Config.CANISTER_MAX_RETRIES
        )
        logger.info(f"Canister client initialized successfully for network: {Config.ICP_NETWORK}")
    except Exception as e:
        logger.error(f"Failed to initialize canister client: {e}")
        canister_client = None

# Initialize Flask app
app = Flask(__name__)
# Set a secret key for session management
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_very_secret_key_for_flask_session_development_only')
if app.secret_key == 'a_very_secret_key_for_flask_session_development_only' and not Config.DEBUG:
    logger.warning("🚨 WARNING: FLASK_SECRET_KEY is not set in .env or is using a default value. This is insecure for production!")

# Apply CORS to the Flask app (HTTP endpoints). Only do this ONCE.
CORS(app, origins=allowed_origins, supports_credentials=True)

# Initialize Flask-SocketIO. Use the same allowed_origins for WebSocket connections.
if Config.DEBUG: # Development
    socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode='eventlet', logger=True, engineio_logger=True)
else: # Production
    socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode='eventlet') # Use eventlet for production for better performance

# Setup WebSocket event handlers
setup_websocket_handlers(socketio)


# Initialize NFT Engine
nft_engine = NFTEngine(
    stability_api_key=Config.STABILITY_API_KEY,
    db_path=Config.DATABASE_PATH,
    static_image_path=Config.STATIC_IMAGE_PATH,
    encryption_key=Config.ENCRYPTION_KEY,
    canister_client=canister_client # Pass canister client to NFT engine
)

# Initialize Social Media Service
social_media_service = SocialMediaService()
# Initialize Database Manager directly for OAuth routes if needed outside of nft_engine
db_manager = DatabaseManager(db_path=Config.DATABASE_PATH)


# Debugging Middleware
@app.before_request
def before_request_log():
    g.start_time = time.time()
    if request.path.startswith('/api/canister'):
        logger.info(f"CANISTER_CALL: Incoming request to {request.path}")

@app.after_request
def after_request_log(response):
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        if request.path.startswith('/api/canister'):
            status_code = response.status_code
            logger.info(f"CANISTER_CALL_RESPONSE: {request.path} - Status: {status_code} - Duration: {duration:.4f}s")
    return response

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key or api_key != Config.ADMIN_API_KEY:
            logger.warning(f"Unauthorized access attempt to {request.path} from {request.remote_addr}")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/artists', methods=['GET'])
def get_artists():
    """Get available artists"""
    return jsonify({"artists": list(nft_engine.prompt_generator.artists.keys())})

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get available event types"""
    return jsonify({"events": [event.value for event in EventType]})


@app.route('/static/images/<path:filename>')
def serve_nft_images(filename):
    """Serve NFT images from the configured static image path."""
    return send_from_directory(Config.STATIC_IMAGE_PATH, filename)

@app.route('/api/combinations', methods=['GET'])
def get_combinations():
    """Get all combinations with basic info"""
    try:
        combinations = nft_engine.get_available_combinations()
        return jsonify({"combinations": combinations})
    except Exception as e:
        logger.error(f"Error getting combinations: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# NEW CANISTER-RELATED ENDPOINTS AND HELPER FUNCTIONS
# ============================================================================

@app.route('/api/test-canister', methods=['GET'])
@admin_required # Restrict to admin users
async def test_canister_connection():
    """
    Test basic connection to the ICP canister.
    Attempts to call getCanisterStatus and get a dummy NFT.
    """
    if not canister_client:
        return jsonify({"status": "error", "message": "Canister client not initialized. CANISTER_ENABLED might be false or initialization failed."}), 503

    results = {}
    total_latency = 0.0

    # Test getCanisterStatus
    start_time = time.time()
    try:
        status_response = await canister_client.check_canister_status()
        latency = time.time() - start_time
        total_latency += latency
        results['canister_status_test'] = {
            "success": True,
            "message": "Canister status retrieved successfully.",
            "data": status_response,
            "latency_ms": f"{latency * 1000:.2f}ms"
        }
        logger.info(f"/api/test-canister: Canister status test successful. Latency: {latency * 1000:.2f}ms")
    except CanisterError as e:
        latency = time.time() - start_time
        results['canister_status_test'] = {
            "success": False,
            "message": f"Failed to get canister status: {e.message}",
            "error_code": e.code,
            "latency_ms": f"{latency * 1000:.2f}ms"
        }
        logger.error(f"/api/test-canister: Canister status test failed: {e.message}. Latency: {latency * 1000:.2f}ms")
    except Exception as e:
        latency = time.time() - start_time
        results['canister_status_test'] = {
            "success": False,
            "message": f"Unexpected error getting canister status: {str(e)}",
            "latency_ms": f"{latency * 1000:.2f}ms"
        }
        logger.error(f"/api/test-canister: Unexpected error in canister status test: {str(e)}. Latency: {latency * 1000:.2f}ms")

    # Test getNFT with a non-existent ID (to test query function without relying on existing data)
    dummy_nft_id = "non-existent-nft-id-12345"
    start_time = time.time()
    try:
        nft_data_response = await canister_client.get_nft(dummy_nft_id)
        latency = time.time() - start_time
        total_latency += latency
        if nft_data_response is None: # Motoko returns null for not found
            results['get_nft_test'] = {
                "success": True,
                "message": f"Query for dummy NFT ID '{dummy_nft_id}' returned null as expected (NFT not found).",
                "data": None,
                "latency_ms": f"{latency * 1000:.2f}ms"
            }
            logger.info(f"/api/test-canister: getNFT test successful (NFT not found). Latency: {latency * 1000:.2f}ms")
        else:
            results['get_nft_test'] = {
                "success": False, # Unexpectedly found an NFT
                "message": f"Query for dummy NFT ID '{dummy_nft_id}' unexpectedly returned data.",
                "data": nft_data_response,
                "latency_ms": f"{latency * 1000:.2f}ms"
            }
            logger.warning(f"/api/test-canister: getNFT test: Unexpected data found for dummy ID. Latency: {latency * 1000:.2f}ms")
    except CanisterError as e:
        latency = time.time() - start_time
        results['get_nft_test'] = {
            "success": False,
            "message": f"Failed to query dummy NFT: {e.message}",
            "error_code": e.code,
            "latency_ms": f"{latency * 1000:.2f}ms"
        }
        logger.error(f"/api/test-canister: getNFT test failed: {e.message}. Latency: {latency * 1000:.2f}ms")
    except Exception as e:
        latency = time.time() - start_time
        results['get_nft_test'] = {
            "success": False,
            "message": f"Unexpected error querying dummy NFT: {str(e)}",
            "latency_ms": f"{latency * 1000:.2f}ms"
        }
        logger.error(f"/api/test-canister: Unexpected error in getNFT test: {str(e)}. Latency: {latency * 1000:.2f}ms")

    # Overall status
    overall_status = "success" if all(res.get('success', False) for res in results.values()) else "failure"

    return jsonify({
        "overall_status": overall_status,
        "total_latency_ms": f"{total_latency * 1000:.2f}ms",
        "tests": results
    }), 200 if overall_status == "success" else 500

@app.route('/api/sync-check', methods=['GET'])
@admin_required # Restrict to admin users
async def sync_check():
    """
    Compares local SQLite data with canister data to find discrepancies.
    """
    if not canister_client:
        return jsonify({"status": "error", "message": "Canister client not initialized."}), 503

    sync_report = {
        "status": "partial_sync", # Default, will change to synced or discrepancies
        "discrepancies_found": False,
        "local_only_nfts": [],
        "canister_only_nfts": [],
        "mismatched_nfts": [],
        "total_local_nfts": 0,
        "total_canister_nfts": 0,
        "canister_sync_stats": None,
        "canister_latency_ms": "N/A"
    }

    try:
        start_time = time.time()
        all_canister_nfts_raw = await canister_client.list_all_nfts()
        canister_latency = time.time() - start_time
        sync_report["canister_latency_ms"] = f"{canister_latency * 1000:.2f}ms"
        logger.info(f"/api/sync-check: Fetched all canister NFTs. Count: {len(all_canister_nfts_raw)}")

        all_canister_nfts_map = {nft['id']: nft for nft in all_canister_nfts_raw}
        sync_report["total_canister_nfts"] = len(all_canister_nfts_raw)

        local_nfts = nft_engine.db_manager.get_all_nfts()
        sync_report["total_local_nfts"] = len(local_nfts)
        
        sync_report["canister_sync_stats"] = nft_engine.db_manager.get_canister_sync_stats()


        local_nft_ids = set()
        for local_nft in local_nfts:
            local_nft_ids.add(local_nft['id'])
            canister_nft_id = local_nft.get('canister_id')

            if not canister_nft_id:
                sync_report["local_only_nfts"].append({
                    "local_id": local_nft['id'],
                    "reason": "Not yet minted on canister or failed minting."
                })
                sync_report["discrepancies_found"] = True
                continue
            
            if canister_nft_id not in all_canister_nfts_map:
                sync_report["local_only_nfts"].append({
                    "local_id": local_nft['id'],
                    "canister_id": canister_nft_id,
                    "reason": "Found locally but not on canister (possibly burned on canister, or ID mismatch)."
                })
                sync_report["discrepancies_found"] = True
            else:
                canister_nft = all_canister_nfts_map[canister_nft_id]
                
                # Basic comparison (can be extended to compare more fields)
                # Ensure data types are consistent for comparison
                local_version = local_nft.get('version')
                canister_version = canister_nft.get('version')

                # Handle potential type differences (e.g., Motoko Nat to Python int)
                try:
                    local_image_url = local_nft.get('image_url')
                    canister_image_url = canister_nft.get('imageURI') # Motoko uses imageURI
                    
                    if str(local_version) != str(canister_version) or local_image_url != canister_image_url:
                        sync_report["mismatched_nfts"].append({
                            "local_id": local_nft['id'],
                            "canister_id": canister_nft_id,
                            "discrepancies": {
                                "version": {"local": local_version, "canister": canister_version} if str(local_version) != str(canister_version) else "match",
                                "image_url": {"local": local_image_url, "canister": canister_image_url} if local_image_url != canister_image_url else "match"
                            }
                        })
                        sync_report["discrepancies_found"] = True
                except Exception as e:
                    logger.error(f"Error comparing NFT {local_nft['id']} and {canister_nft_id}: {e}")
                    sync_report["mismatched_nfts"].append({
                        "local_id": local_nft['id'],
                        "canister_id": canister_nft_id,
                        "reason": f"Error during detailed comparison: {str(e)}"
                    })
                    sync_report["discrepancies_found"] = True

        # Find NFTs that are on the canister but not locally tracked (or not linked)
        for canister_id, canister_nft in all_canister_nfts_map.items():
            # Check if this canister_id exists as a 'canister_id' in any local NFT
            is_tracked_locally = nft_engine.db_manager.get_nft_by_canister_id(canister_id)
            if not is_tracked_locally:
                sync_report["canister_only_nfts"].append({
                    "canister_id": canister_id,
                    "owner": str(canister_nft.get('owner')),
                    "name": canister_nft.get('name', 'N/A'),
                    "reason": "Found on canister but not locally tracked."
                })
                sync_report["discrepancies_found"] = True

    except CanisterError as e:
        logger.error(f"Canister client error during sync check: {e.message}")
        sync_report["status"] = "canister_error"
        sync_report["message"] = f"Canister communication error: {e.message}"
        return jsonify(sync_report), 500
    except Exception as e:
        logger.error(f"Error during sync check: {e}")
        sync_report["status"] = "internal_error"
        sync_report["message"] = f"An internal error occurred: {str(e)}"
        return jsonify(sync_report), 500

    if not sync_report["discrepancies_found"]:
        sync_report["status"] = "synced"
        sync_report["message"] = "Local and canister data are in sync."
    else:
        sync_report["status"] = "discrepancies_found"
        sync_report["message"] = "Discrepancies found between local and canister data."

    return jsonify(sync_report), 200

@app.route('/api/retry-failed', methods=['POST'])
@admin_required # Restrict to admin users
async def retry_failed_canister_mints():
    """
    Finds NFTs that failed to mint on the canister and retries the minting process.
    """
    if not canister_client:
        return jsonify({"status": "error", "message": "Canister client not initialized."}), 503

    failed_nfts = nft_engine.db_manager.get_nfts_by_canister_status("failed_mint")
    retried_count = 0
    success_retries = []
    failed_retries = []

    logger.info(f"/api/retry-failed: Found {len(failed_nfts)} NFTs with failed_mint status.")

    for nft in failed_nfts:
        try:
            # Reconstruct NFTMetadata from local data
            # This requires careful mapping of local DB fields to NFTMetadata structure
            # Assuming 'metadata', 'genetic_traits', 'scarcity_info' are stored as JSON strings
            # and 'attributes' is also within 'metadata' or separately.

            # Deserialize JSON fields (these are already JSON strings from the DB)
            metadata_dict = json.loads(nft['metadata']) if nft['metadata'] else {}
            genetic_traits_json = nft['genetic_traits'] if nft['genetic_traits'] else '{}'
            scarcity_info_json = nft['scarcity_info'] if nft['scarcity_info'] else '{}'
            uniqueness_factors_json = nft['uniqueness_factors'] if nft['uniqueness_factors'] else '{}'

            # Construct NFTMetadata dataclass
            canister_metadata = NFTMetadata(
                name=nft['name'],
                description=nft['description'],
                image_url=nft['image_url'],
                artist=nft['artist'],
                eventType=nft['event_type'],
                prompt=nft['user_prompt'],
                mode=nft['mode'],
                uniqueness_factors=uniqueness_factors_json, # Pass as JSON string
                genetic_traits=genetic_traits_json,         # Pass as JSON string
                scarcity_info=scarcity_info_json,           # Pass as JSON string
                attributes=json.dumps(metadata_dict.get('attributes', {})) # Ensure attributes is a JSON string
            )

            owner_principal = Principal.from_text(nft['owner_address'])

            logger.info(f"Retrying mint for local NFT ID: {nft['id']}")
            mint_result = await canister_client.mint(owner_principal, canister_metadata)
            retried_count += 1

            if mint_result and mint_result.get('Ok'):
                canister_nft_id = mint_result['Ok']['id']
                nft_engine.db_manager.update_nft_canister_status(nft['id'], canister_nft_id, "minted")
                success_retries.append({
                    "local_id": nft['id'],
                    "canister_id": canister_nft_id,
                    "message": "Successfully re-minted on canister."
                })
                logger.info(f"Successfully re-minted NFT {nft['id']} on canister as {canister_nft_id}.")
            elif mint_result and mint_result.get('Err'):
                error_message = mint_result['Err']
                failed_retries.append({
                    "local_id": nft['id'],
                    "error": error_message,
                    "message": "Failed to re-mint on canister (canister error)."
                })
                logger.warning(f"Failed to re-mint NFT {nft['id']} on canister: {error_message}")
            else:
                failed_retries.append({
                    "local_id": nft['id'],
                    "error": "Unknown canister response",
                    "message": "Failed to re-mint on canister (unknown response)."
                })
                logger.warning(f"Unknown canister response for NFT {nft['id']} during retry.")

        except CanisterError as ce:
            failed_retries.append({
                "local_id": nft['id'],
                "error": str(ce),
                "message": "Canister client error during retry."
            })
            logger.error(f"Canister client error during retry for NFT {nft['id']}: {ce}")
        except Exception as e:
            failed_retries.append({
                "local_id": nft['id'],
                "error": str(e),
                "message": "Unexpected error during retry."
            })
            logger.error(f"Unexpected error during retry for NFT {nft['id']}: {e}")
            
    return jsonify({
        "status": "completed",
        "retried_count": retried_count,
        "success_retries": success_retries,
        "failed_retries": failed_retries
    }), 200

# Replace the existing /api/create-nft endpoint with this enhanced version
@app.route('/api/create-nft', methods=['POST'])
async def create_nft():
    """Create new NFT with dual storage (local + canister) and emit WebSocket events."""
    try:
        logger.info(f"Received create_nft request: {request.get_json()}")
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['mode', 'artist', 'event_type', 'uniqueness_factors', 'owner_address']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
        
        # Parse input data
        mode = GenerationMode(data['mode'])
        artist = data['artist']
        event_type = EventType(data['event_type'])
        user_prompt = data.get('user_prompt')
        owner_address = data['owner_address']
        
        # ADD THIS AVAILABILITY CHECK HERE:
        if not nft_engine.combination_tracker.is_combination_available(artist, event_type):
            status = nft_engine.combination_tracker.get_availability_status(artist, event_type)
            return jsonify({
                "error": "This combination is not available for minting",
                "status": status
            }), 400

        # NEW: Get evolution_period_days from request, default to 30
        evolution_period_days = data.get('evolution_period_days', 30)

        # Create uniqueness factors
        uniqueness_data = data['uniqueness_factors']
        uniqueness_factors = UniquenessFactors(
            location_hash=uniqueness_data['location_hash'],
            timestamp_seed=uniqueness_data['timestamp_seed'],
            wallet_entropy=uniqueness_data['wallet_entropy'],
            wallet_principal=uniqueness_data.get('wallet_principal', owner_address),  # Added
            wallet_account_id=uniqueness_data.get('wallet_account_id', ''),  # Added
            biometric_opt_in=uniqueness_data.get('biometric_opt_in', False),
            biometric_hash=uniqueness_data.get('biometric_hash')
        )

        # Generate genetic traits (example, adapt as needed)
        # Generate genetic traits based on uniqueness factors
        generated_genetic_traits = GeneticTraits(
                luminosity=hash(uniqueness_factors.location_hash) % 100 / 100.0,
                architectural_complexity=int(uniqueness_factors.timestamp_seed) % 100 / 100.0,
                ethereal_quality=hash(uniqueness_factors.wallet_entropy) % 100 / 100.0,
                evolution_speed=0.5,  # Default value
                style_intensity=0.7,  # Default value
                temporal_resonance=0.6  # Default value
        )
        
        # Scarcity info (example, adapt as needed)
        generated_scarcity_info = ScarcityInfo(
                combination=f"{artist}-{event_type.value}",
                total_limit=10000,
                minted_count=1,
                rarity_score=0.5,  # This will make it "Common" tier
                price_multiplier=1.0,
                artist=artist,
                eventType=event_type
        )
        
        try:
            # Step 1: Create NFT locally
            logger.info("Creating NFT locally...")
            local_nft_result = await nft_engine.create_nft(
                mode=mode, 
                artist=artist, 
                event_type=event_type, 
                user_prompt=user_prompt, 
                uniqueness_factors=uniqueness_factors, 
                owner_address=owner_address,
                genetic_traits=generated_genetic_traits, # Pass generated traits
                scarcity_info=generated_scarcity_info, # Pass generated scarcity
                evolution_period_days=evolution_period_days # Pass evolution period
            )
            
            local_nft_id = local_nft_result.get('nft_id')
            logger.info(f"NFT created locally with ID: {local_nft_id}")
            
            # Step 2: Prepare canister response fields
            canister_result = {
                "canister_mint_attempted": False,
                "canister_nft_id": None,
                "canister_status": "not_attempted",
                "canister_error": None
            }
            
            # Step 3: Attempt canister minting if client is available
            if canister_client and Config.CANISTER_ENABLED:
                # Initialize canister_mint_result to None here
                canister_mint_result = None
                try:
                    logger.info("Attempting to mint NFT on canister...")
                    
                    # Convert local NFT data to canister format
                    local_nft_data = nft_engine.db_manager.get_nft(local_nft_id)
                    
                    if local_nft_data:
                        # Create NFTMetadata object for canister
                        canister_metadata = NFTMetadata(
                            name=local_nft_data.get('name', f"NFT #{local_nft_id}"),
                            description=local_nft_data.get('description', ''),
                            image_url=local_nft_data.get('image_url', ''),
                            artist=local_nft_data.get('artist', 'unknown'),
                            eventType=local_nft_data.get('event_type', 'unknown'),
                            prompt=local_nft_data.get('user_prompt', ''),
                            mode=local_nft_data.get('mode', 'unknown'),
                            # These are already JSON strings from db_manager.save_nft
                            uniqueness_factors=local_nft_data.get('uniqueness_factors', '{}'),
                            genetic_traits=local_nft_data.get('genetic_traits', '{}'),
                            scarcity_info=local_nft_data.get('scarcity_info', '{}'),
                            # This needs to be explicitly dumped to JSON string
                            attributes=json.dumps(json.loads(local_nft_data.get('metadata', '{}')).get('attributes', {}))
                        )
                        
                        # Mint on canister
                        canister_mint_result = await canister_client.mint(Principal.from_text(owner_address), canister_metadata)
                        
                        if canister_mint_result and canister_mint_result.get('Ok'):
                            canister_result.update({
                                "canister_mint_attempted": True,
                                "canister_nft_id": canister_mint_result['Ok'].get('id'),
                                "canister_status": "success",
                                "canister_transaction_id": canister_mint_result['Ok'].get('transaction_id'),
                                "canister_block_height": canister_mint_result['Ok'].get('block_height')
                            })
                            
                            # Update local NFT with canister information
                            nft_engine.db_manager.update_nft_canister_info(
                                local_nft_id, 
                                canister_mint_result['Ok'].get('id'),
                                "minted"
                            )
                            
                            logger.info(f"Successfully minted on canister: {canister_mint_result['Ok'].get('id')}")
                        elif canister_mint_result and canister_mint_result.get('Err'):
                            error_message = canister_mint_result['Err']
                            logger.error(f"Canister minting failed: {error_message}")
                            canister_result.update({
                                "canister_mint_attempted": True,
                                "canister_status": "failed",
                                "canister_error": str(error_message),
                                "canister_error_code": getattr(error_message, 'code', None) # Assuming error_message might be a CanisterError object
                            })
                            
                            # Mark local NFT as pending canister mint
                            nft_engine.db_manager.update_nft_canister_info(
                                local_nft_id, 
                                None,
                                "failed_mint"
                            )
                        else:
                            logger.error("Unexpected response from canister minting.")
                            canister_result.update({
                                "canister_mint_attempted": True,
                                "canister_status": "error",
                                "canister_error": "Unexpected response from canister"
                            })
                            nft_engine.db_manager.update_nft_canister_info(
                                local_nft_id, 
                                None,
                                "failed_mint"
                            )
                        
                except CanisterError as e:
                    logger.error(f"Canister minting failed: {e.message}")
                    canister_result.update({
                        "canister_mint_attempted": True,
                        "canister_status": "failed",
                        "canister_error": e.message,
                        "canister_error_code": e.code
                    })
                    
                    # Mark local NFT as pending canister mint
                    nft_engine.db_manager.update_nft_canister_info(
                        local_nft_id, 
                        None,
                        "failed_mint"
                    )
                    
                except Exception as e:
                    logger.error(f"Unexpected canister error during minting: {e}")
                    canister_result.update({
                        "canister_mint_attempted": True,
                        "canister_status": "error",
                        "canister_error": f"Unexpected error: {str(e)}"
                    })
                    
                    # Mark local NFT as pending canister mint
                    nft_engine.db_manager.update_nft_canister_info(
                        local_nft_id, 
                        None,
                        "failed_mint"
                    )
            
            else:
                canister_result["canister_status"] = "disabled"
                logger.info("Canister minting skipped - client not available or disabled")
            
            # Step 4: Prepare final response
            final_response = {
                **local_nft_result,
                "storage": {
                    "local": {
                        "status": "success",
                        "nft_id": local_nft_id
                    },
                    "canister": canister_result
                },
                "dual_storage_status": "complete" if canister_result["canister_status"] == "success" else "partial"
            }
            
            # Determine HTTP status code
            if canister_result["canister_status"] in ["success", "disabled", "not_attempted"]:
                status_code = 201  # Created successfully
            else:
                status_code = 202  # Accepted but with warnings
            
            # --- WebSocket Integration: Broadcast new mint event ---
            # Fetch the complete NFT data from the DB to ensure all fields for broadcast are present
            newly_minted_nft_data = nft_engine.db_manager.get_nft(local_nft_id)
            if newly_minted_nft_data:
                broadcast_new_mint(socketio, newly_minted_nft_data)
                logger.info(f"Broadcasted new mint event for NFT ID: {local_nft_id}")

            # --- WebSocket Integration: Broadcast scarcity update ---
            # After a new NFT is created, the scarcity for its combination might change
            scarcity_info = nft_engine.combination_tracker.get_scarcity_info(artist, event_type)
            broadcast_scarcity_update(
                socketio, 
                artist, 
                event_type.value, 
                scarcity_info.remaining_slots, 
                scarcity_info.total_supply,
                scarcity_info.is_available()
            )
            logger.info(f"Broadcasted scarcity update for {artist}-{event_type.value}")
            
            return jsonify(final_response), status_code
            
        except Exception as e:
            logger.error(f"Error during NFT creation process: {e}")
            return jsonify({
                "error": str(e),
                "storage": {
                    "local": {"status": "failed"},
                    "canister": {"status": "not_attempted"}
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Error creating NFT (initial request handling): {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "storage": {
                "local": {"status": "failed"},
                "canister": {"status": "not_attempted"}
            }
        }), 500

@app.route('/api/canister-status', methods=['GET'])
@admin_required
async def canister_status():
    """Check canister health and status"""
    try:
        if not canister_client:
            return jsonify({
                "status": "disabled",
                "message": "Canister client not initialized",
                "canister_enabled": Config.CANISTER_ENABLED
            }), 503
        
        # Get canister status
        status_info = await canister_client.check_canister_status()
        canister_info = await canister_client.get_canister_info()
        
        response = {
            "status": "healthy",
            "canister_id": canister_info["canister_id"],
            "network": canister_info["network"],
            "endpoint": canister_info["endpoint"],
            "health_check": status_info.get("health_check", "unknown"),
            "last_check": status_info["timestamp"],
            "configuration": {
                "timeout": canister_info["timeout"],
                "max_retries": canister_info["max_retries"],
                "enabled": Config.CANISTER_ENABLED
            }
        }
        
        return jsonify(response)
        
    except CanisterError as e:
        logger.error(f"Canister status check failed: {e.message}")
        return jsonify({
            "status": "unhealthy",
            "error": e.message,
            "error_code": e.code,
            "canister_id": Config.CANISTER_ID,
            "network": Config.ICP_NETWORK
        }), 503
        
    except Exception as e:
        logger.error(f"Unexpected error checking canister status: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "canister_id": Config.CANISTER_ID
        }), 500

# Add this helper function after the existing routes (before if __name__ == '__main__':)
async def check_for_nft_evolution_jobs():
    """
    Background task to check for NFTs due for evolution and trigger their evolution.
    """
    logger.info("Scheduler: Checking for NFTs due for evolution...")
    try:
        nfts_due_for_evolution = nft_engine.db_manager.get_nfts_due_for_evolution()
        if not nfts_due_for_evolution:
            logger.info("Scheduler: No NFTs are currently due for evolution.")
            return

        logger.info(f"Scheduler: Found {len(nfts_due_for_evolution)} NFTs due for evolution.")
        for nft_data in nfts_due_for_evolution:
            nft_id = nft_data['id']
            owner_address = nft_data['owner_address']
            
            # Assuming a default evolution event type if not specified or needed for evolution context
            # In a real scenario, this might be dynamically determined or a fixed "auto-evolve" type
            # We use the current event_type of the NFT for consistency, or a sensible default.
            current_event_type = EventType(nft_data.get('event_type', EventType.URBAN.value)) # Default to Urban

            try:
                logger.info(f"Scheduler: Initiating auto-evolution for NFT: {nft_id} (Owner: {owner_address})")
                # Call the main evolve_nft method without a specific user prompt (auto-evolution)
                # This will assign evolved_nft
                evolved_nft = await nft_engine.evolve_nft(nft_id, current_event_type, user_prompt="auto-evolution based on social media activity")
                logger.info(f"Scheduler: Successfully auto-evolved NFT: {nft_id}")
                
                # Broadcast evolution notification after successful auto-evolution
                evolved_nft_data = nft_engine.db_manager.get_nft(nft_id)
                if evolved_nft_data:
                    broadcast_evolution_notification(
                        socketio, 
                        evolved_nft_data.get('id'), # Use evolved_nft_data
                        evolved_nft_data.get('version'), # Use evolved_nft_data
                        evolved_nft_data.get('image_url'), # Use evolved_nft_data
                        json.loads(evolved_nft_data.get('genetic_traits', '{}')) # Use evolved_nft_data
                    )
                    logger.info(f"Scheduler: Broadcasted evolution update for NFT ID: {nft_id}")

            except Exception as e:
                logger.error(f"Scheduler: Failed to auto-evolve NFT {nft_id}: {e}", exc_info=True)
                # You might want to update the NFT's status to 'evolution_failed' in the DB here
                # Or log the error for manual intervention for failed auto-evolutions
    except Exception as e:
        logger.error(f"Scheduler: Error in check_for_nft_evolution_jobs loop: {e}", exc_info=True)

async def retry_canister_minting_background():
    """Background function to retry failed canister mints (can be called by scheduler)"""
    if not canister_client:
        logger.info("Canister client not available for retry operations")
        return
    
    try:
        # Get NFTs pending canister minting (using 'failed_mint' status for retries)
        pending_nfts = nft_engine.db_manager.get_nfts_by_canister_status("failed_mint")
        
        for nft_data in pending_nfts:
            try:
                logger.info(f"Retrying canister mint for NFT {nft_data['id']}")
                
                # These are already JSON strings from db_manager.save_nft
                genetic_traits_json = nft_data.get('genetic_traits', '{}')
                scarcity_info_json = nft_data.get('scarcity_info', '{}')
                uniqueness_factors_json = nft_data.get('uniqueness_factors', '{}')
                attributes_dict = json.loads(nft_data.get('metadata', '{}')).get('attributes', {})

                canister_metadata = NFTMetadata(
                    name=nft_data.get('name', f"NFT #{nft_data['id']}"),
                    description=nft_data.get('description', ''),
                    image_url=nft_data.get('image_url', ''),
                    artist=nft_data.get('artist', 'unknown'),
                    eventType=nft_data.get('event_type', 'unknown'),
                    prompt=nft_data.get('user_prompt', ''),
                    mode=nft_data.get('mode', 'unknown'),
                    uniqueness_factors=uniqueness_factors_json,
                    genetic_traits=genetic_traits_json,
                    scarcity_info=scarcity_info_json,
                    attributes=json.dumps(attributes_dict) # Ensure attributes is a JSON string
                )
                
                # Attempt to mint again
                canister_mint_result = await canister_client.mint(Principal.from_text(nft_data['owner_address']), canister_metadata)
                
                if canister_mint_result and canister_mint_result.get('Ok'):
                    # Update local NFT with new canister info
                    nft_engine.db_manager.update_nft_canister_status(
                        nft_data['id'], 
                        canister_mint_result['Ok'].get('id'),
                        "minted"
                    )
                    logger.info(f"Successfully retried canister mint for NFT {nft_data['id']}: {canister_mint_result['Ok'].get('id')}")
                elif canister_mint_result and canister_mint_result.get('Err'):
                    error_message = canister_mint_result['Err']
                    logger.error(f"Failed to retry canister mint for NFT {nft_data['id']} due to CanisterError: {error_message}")
                    # Keep status as failed_mint for future retries if it's not a permanent error
                    # Consider adding a retry counter to avoid infinite retries
                    nft_engine.db_manager.update_nft_canister_status(
                        nft_data['id'], 
                        None,
                        "failed_mint" 
                    )
                else:
                    logger.error(f"Unexpected response retrying canister mint for NFT {nft_data['id']}.")
                    nft_engine.db_manager.update_nft_canister_status(
                        nft_data['id'], 
                        None,
                        "failed_mint" 
                    )
            except CanisterError as e:
                logger.error(f"Failed to retry canister mint for NFT {nft_data['id']} due to CanisterClient error: {e.message}")
                nft_engine.db_manager.update_nft_canister_status(
                    nft_data['id'], 
                    None,
                    "failed_mint" 
                )
            except Exception as e:
                logger.error(f"Failed to retry canister mint for NFT {nft_data['id']} due to unexpected error: {e}")
                nft_engine.db_manager.update_nft_canister_status(
                    nft_data['id'], 
                    None,
                    "failed_mint" 
                )
    
    except Exception as e:
        logger.error(f"Error in retry_canister_minting_background: {e}")

# Add endpoint for manual retry (optional)
@app.route('/api/retry-canister-mints', methods=['POST'])
@admin_required
async def manual_retry_canister_mints():
    """Manually trigger retry of failed canister mints"""
    try:
        if not canister_client:
            return jsonify({"error": "Canister client not available"}), 503
        
        # Run retry function in the background (or directly if blocking is acceptable)
        await retry_canister_minting_background()
        
        return jsonify({
            "message": "Canister mint retry initiated",
            "status": "processing"
        })
        
    except Exception as e:
        logger.error(f"Error in manual retry: {e}")
        return jsonify({"error": str(e)}), 500

# Add admin-only endpoint
@app.route('/api/admin/canister-stats', methods=['GET'])
@admin_required
async def admin_canister_stats():
    """Get detailed canister statistics (admin only)"""
    try:
        if not canister_client:
            return jsonify({"error": "Canister client not available"}), 503
        
        # Get comprehensive canister statistics
        stats = {
            "canister_info": await canister_client.get_canister_info(),
            "local_nfts": len(nft_engine.db_manager.get_all_nfts()),
            "sync_status": {},
            "performance_metrics": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Add sync status
        local_nfts = nft_engine.db_manager.get_all_nfts()
        minted_count = sum(1 for nft in local_nfts if nft.get('canister_status') == 'minted')
        pending_count = sum(1 for nft in local_nfts if nft.get('canister_status') == 'pending_retry')
        failed_count = sum(1 for nft in local_nfts if nft.get('canister_status') in ['failed_mint', 'error'])
        
        stats["sync_status"] = {
            "total_local": len(local_nfts),
            "minted_on_canister": minted_count,
            "pending_retry": pending_count,
            "failed": failed_count,
            "sync_percentage": (minted_count / len(local_nfts) * 100) if local_nfts else 100
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Admin canister stats error: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# NEW X (Twitter) OAuth ROUTES
# ============================================================================

@app.route('/api/auth/x-initiate', methods=['GET'])
async def x_initiate_auth():
    """
    Initiates the X (Twitter) OAuth 1.0a flow.
    Requires a 'wallet_principal' query parameter to associate the OAuth session.
    """
    wallet_principal = request.args.get('wallet_principal')
    if not wallet_principal:
        logger.error("x_initiate_auth: Missing wallet_principal query parameter.")
        return jsonify({"error": "Missing wallet_principal parameter"}), 400

    try:
        oauth_start_info = social_media_service.start_oauth_flow()
        
        # Store the request token secret in the session, associated with the wallet principal
        session['x_request_token_secret'] = oauth_start_info['request_token_secret']
        session['x_oauth_wallet_principal'] = wallet_principal # Store principal for callback
        
        logger.info(f"Initiated X OAuth for wallet: {wallet_principal}. Redirecting to: {oauth_start_info['authorization_url']}")
        return redirect(oauth_start_info['authorization_url'])
    except Exception as e:
        logger.error(f"Error initiating X OAuth flow for wallet {wallet_principal}: {e}", exc_info=True)
        # Redirect back to frontend with an error status
        frontend_callback_url = f"{Config.CORS_ORIGINS[0]}?auth_status=error&message=FailedToInitiateOAuth"
        return redirect(frontend_callback_url)


@app.route('/api/auth/x-callback', methods=['GET'])
async def x_callback_auth():
    """
    Handles the callback from X (Twitter) after user authorization.
    Exchanges request token for access token and saves it.
    """
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    
    request_token_secret = session.pop('x_request_token_secret', None)
    wallet_principal = session.pop('x_oauth_wallet_principal', None) # Retrieve and clear

    if not all([oauth_token, oauth_verifier, request_token_secret, wallet_principal]):
        logger.error(f"x_callback_auth: Missing required parameters in callback or session. "
                     f"oauth_token: {bool(oauth_token)}, oauth_verifier: {bool(oauth_verifier)}, "
                     f"request_token_secret: {bool(request_token_secret)}, wallet_principal: {bool(wallet_principal)}")
        frontend_callback_url = f"{Config.CORS_ORIGINS[0]}?auth_status=error&message=InvalidCallbackParameters"
        return redirect(frontend_callback_url)

    try:
        # Complete the OAuth flow to get final access tokens
        final_tokens = social_media_service.complete_oauth_flow(
            oauth_token=oauth_token,
            oauth_verifier=oauth_verifier,
            request_token_secret=request_token_secret
        )

        # Create SocialMediaAuth object
        social_auth = SocialMediaAuth(
            wallet_principal=wallet_principal,
            platform="x", # Assuming "x" for Twitter
            social_user_id=final_tokens['user_id'],
            username=final_tokens['username'],
            encrypted_access_token="", # Will be set by encrypt_tokens
            encrypted_access_token_secret="", # Will be cleared by encrypt_tokens
            last_updated="" # Will be set by encrypt_tokens
        )
        
        # Encrypt and store tokens
        social_auth.encrypt_tokens(
            access_token=final_tokens['access_token'],
            access_token_secret=final_tokens['access_token_secret'],
            encryption_key=Config.ENCRYPTION_KEY
        )

        # Save to database
        db_manager.save_social_media_auth(social_auth)

        logger.info(f"X OAuth completed and tokens saved for wallet: {wallet_principal}, X user: @{social_auth.username}")
        # Redirect back to frontend with success status and user info
        frontend_callback_url = (
            f"{Config.CORS_ORIGINS[0]}?auth_status=success"
            f"&platform=x"
            f"&username={social_auth.username}"
            f"&user_id={social_auth.social_user_id}"
            f"&wallet_principal={wallet_principal}"
        )
        return redirect(frontend_callback_url)

    except Exception as e:
        logger.error(f"Error completing X OAuth flow for wallet {wallet_principal}: {e}", exc_info=True)
        frontend_callback_url = f"{Config.CORS_ORIGINS[0]}?auth_status=error&message=FailedToCompleteOAuth&details={str(e)}"
        return redirect(frontend_callback_url)


# ============================================================================
# EXISTING ROUTES CONTINUATION
# ============================================================================

@app.route('/api/check-scarcity', methods=['POST'])
def check_scarcity():
    """
    Check if artist-event combination is available and broadcast scarcity updates.
    """
    try:
        data = request.get_json()
        
        if not data or 'artist' not in data or 'event_type' not in data:
            return jsonify({"error": "Artist and event_type are required"}), 400
        
        artist = data['artist']
        event_type_str = data['event_type']
        
        # Validate artist
        if artist not in nft_engine.prompt_generator.artists:
            return jsonify({"error": f"Invalid artist: {artist}"}), 400
        
        # Validate and convert event type
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            return jsonify({"error": f"Invalid event type: {event_type_str}. Must be one of {[e.value for e in EventType]}"}), 400
        
        # Get scarcity information
        scarcity_info = nft_engine.combination_tracker.get_scarcity_info(artist, event_type)
        
        # Get waitlist count for this combination
        waitlist = nft_engine.db_manager.get_waitlist(scarcity_info.combination)
        waitlist_count = len(waitlist)
        
        response = {
            "artist": artist,
            "event_type": event_type_str,
            "is_available": scarcity_info.is_available(),
            "scarcity_info": scarcity_info.to_dict(),
            "waitlist_count": waitlist_count,
            "estimated_availability": "immediate" if scarcity_info.is_available() else "waitlist",
            "price_multiplier": scarcity_info.price_multiplier
        }

        # --- WebSocket Integration: Broadcast scarcity update ---
        # This endpoint is primarily for checking, but if the scarcity changes as a result
        # of some internal logic (e.g., a background process minting), this broadcast
        # ensures clients are updated. For explicit scarcity changes (like a mint),
        # the broadcast is handled in create_nft.
        broadcast_scarcity_update(
            socketio, 
            artist, 
            event_type_str, 
            scarcity_info.remaining_slots, 
            scarcity_info.total_supply,
            scarcity_info.is_available()
        )
        logger.info(f"Broadcasted scarcity update (from check-scarcity) for {artist}-{event_type_str}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error checking scarcity: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/nft/<nft_id>/evolution', methods=['GET'])
def get_nft_evolution(nft_id):
    """Get evolution history for specific NFT"""
    try:
        # Get NFT from database
        nft_data = nft_engine.db_manager.get_nft(nft_id)
        
        if not nft_data:
            return jsonify({"error": "NFT not found"}), 404
        
        # Extract evolution history and genetic traits
        evolution_history = nft_data.get('evolution_history', [])
        current_traits = nft_data.get('genetic_traits', {})
        
        # Calculate evolution statistics
        total_evolutions = len(evolution_history) - 1  # Subtract initial mint
        
        # Get trait change patterns
        trait_changes = {}
        for entry in evolution_history[1:]:  # Skip initial mint
            for trait in entry.get('traits_changed', []):
                if trait not in trait_changes:
                    trait_changes[trait] = 0
                trait_changes[trait] += 1
        
        response = {
            "nft_id": nft_id,
            "name": nft_data.get('name'),
            "total_evolutions": total_evolutions,
            "evolution_history": evolution_history,
            "current_genetic_traits": current_traits,
            "trait_change_summary": trait_changes,
            "evolution_period_days": nft_data.get('evolution_period_days') # Include evolution period
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting NFT evolution: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/nft/<nft_id>', methods=['GET'])
def get_nft_details(nft_id):
    """Get details of a specific NFT"""
    try:
        nft = nft_engine.db_manager.get_nft(nft_id)
        if nft:
            return jsonify(nft)
        return jsonify({"error": "NFT not found"}), 404
    except Exception as e:
        logger.error(f"Error getting NFT details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/nfts', methods=['GET'])
def get_all_nfts():
    """Get all NFTs"""
    try:
        nfts = nft_engine.db_manager.get_all_nfts()
        return jsonify({"nfts": nfts})
    except Exception as e:
        logger.error(f"Error getting all NFTs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/evolve-nft', methods=['POST'])
async def evolve_nft():
    """Evolve an existing NFT and broadcast evolution updates."""
    # Initialize evolved_nft to None
    evolved_nft = None
    try:
        data = request.get_json()
        required_fields = ['nft_id', 'new_event_type'] # user_prompt is now optional
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
        
        nft_id = data['nft_id']
        new_event_type = EventType(data['new_event_type'])
        user_prompt = data.get('user_prompt') # Get user_prompt if provided
        
        evolved_nft = await nft_engine.evolve_nft(nft_id, new_event_type, user_prompt)

        # --- WebSocket Integration: Broadcast evolution notification ---
        if evolved_nft:
            broadcast_evolution_notification(
                socketio, 
                evolved_nft.get('id'), 
                evolved_nft.get('version'), 
                evolved_nft.get('image_url'), 
                json.loads(evolved_nft.get('genetic_traits', '{}'))
            )
            logger.info(f"Broadcasted evolution update for NFT ID: {evolved_nft.get('id')}")

        return jsonify(evolved_nft), 200
            
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error evolving NFT: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt():
    """Generate a prompt based on artist, event type, and optional user input"""
    try:
        data = request.get_json()
        artist = data.get('artist')
        event_type = data.get('event_type')
        user_prompt = data.get('user_prompt')
        
        if not artist or not event_type:
            return jsonify({"error": "Artist and event_type are required"}), 400
        
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            return jsonify({"error": f"Invalid event type: {event_type}. Must be one of {[e.value for e in EventType]}"}), 400
            
        generated_prompt = nft_engine.prompt_generator.generate_prompt(
            artist=artist,
            event_type=event_type_enum,
            user_prompt=user_prompt
        )
        return jsonify({"prompt": generated_prompt})
    except Exception as e:
        logger.error(f"Error generating prompt: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/random-traits', methods=['GET'])
def generate_random_traits():
    """Generate a set of random genetic traits"""
    try:
        # Assuming generate_initial_traits is the right method for random-like generation
        # and it needs UniquenessFactors. For a truly "random" endpoint, it might be simplified.
        # For now, let's create dummy uniqueness factors.
        dummy_uniqueness = UniquenessFactors(
            location_hash=str(time.time()),
            timestamp_seed=str(int(time.time() * 1000)),
            wallet_entropy=str(random.randint(100000000, 999999999)),
            wallet_principal="dummy_principal"
        )
        traits = nft_engine.evolution_algorithm.generate_initial_traits(dummy_uniqueness)
        return jsonify(traits.to_dict())
    except Exception as e:
        logger.error(f"Error generating random traits: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/genetic-algorithm/next-generation', methods=['POST'])
def next_generation():
    """Simulate the next generation based on selected NFTs"""
    try:
        data = request.get_json()
        selected_nfts_ids = data.get('selected_nfts_ids')
        
        if not selected_nfts_ids or not isinstance(selected_nfts_ids, list) or len(selected_nfts_ids) < 2:
            return jsonify({"error": "Please select at least two NFTs for breeding."}), 400
            
        # Retrieve full NFT data for the selected IDs
        selected_nfts = [nft_engine.db_manager.get_nft(nft_id) for nft_id in selected_nfts_ids]
        selected_nfts = [nft for nft in selected_nfts if nft is not None] # Filter out any not found NFTs
        
        if len(selected_nfts) < 2:
            return jsonify({"error": "Could not find at least two selected NFTs in the database."}), 400
        
        # Extract genetic traits from selected NFTs
        parent_traits = [GeneticTraits(**json.loads(nft['genetic_traits'])) for nft in selected_nfts]
        
        # Generate offspring traits
        offspring_traits = nft_engine.evolution_algorithm.generate_next_generation(parent_traits) # Corrected to evolution_algorithm
        
        # For simplicity, let's create a placeholder for a new NFT with these traits
        # In a real application, you might then use these traits to mint a new NFT
        # For now, we'll just return the new traits.
        return jsonify({"offspring_traits": [trait.to_dict() for trait in offspring_traits]})
        
    except Exception as e:
        logger.error(f"Error generating next generation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/waitlist', methods=['POST'])
def join_waitlist():
    """Add a user to the waitlist for a specific combination"""
    try:
        data = request.get_json()
        artist = data.get('artist')
        event_type_str = data.get('event_type')
        user_address = data.get('user_address')
        
        if not artist or not event_type_str or not user_address:
            return jsonify({"error": "Artist, event_type, and user_address are required"}), 400
        
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            return jsonify({"error": f"Invalid event type: {event_type_str}. Must be one of {[e.value for e in EventType]}"}), 400
            
        success = nft_engine.db_manager.add_to_waitlist(f"{artist}-{event_type.value}", user_address) # Pass combination string
        
        if success:
            return jsonify({"message": "Successfully joined waitlist", "artist": artist, "event_type": event_type_str, "user_address": user_address}), 201
        else:
            return jsonify({"message": "You are already on the waitlist for this combination."}), 200 # Or 409 Conflict
            
    except Exception as e:
        logger.error(f"Error joining waitlist: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/waitlist/<artist>/<event_type>', methods=['GET'])
def get_waitlist(artist, event_type):
    """Get the waitlist for a specific artist-event combination"""
    try:
        waitlist_entries = nft_engine.db_manager.get_waitlist(f"{artist}-{event_type}")
        return jsonify({"waitlist": waitlist_entries})
    except Exception as e:
        logger.error(f"Error retrieving waitlist for {artist}-{event_type}: {e}")
        return jsonify({"error": str(e)}), 500

# --- WebSocket Test Endpoint ---
@app.route('/api/test-websocket', methods=['GET'])
def test_websocket_endpoint():
    """
    Sends a test message to all connected WebSocket clients and returns
    the number of active connections.
    """
    try:
        # Emit a test message to all connected clients
        socketio.emit('test_server_message', {'message': 'This is a test message from the server!', 'timestamp': time.time()})
        
        # Get the number of connected clients (this is an approximation, SocketIO manages SIDs)
        # There isn't a direct way to get a count of all connected SIDs from the SocketIO object
        # without iterating or using internal structures, which is not recommended.
        # For a basic test, we can just confirm the emit happened.
        logger.info("Sent test_server_message to all connected WebSocket clients.")
        
        return jsonify({
            "status": "success",
            "message": "Test WebSocket message emitted to all clients.",
            "note": "Number of active connections cannot be directly retrieved via HTTP endpoint in this setup, but message was sent."
        }), 200
    except Exception as e:
        logger.error(f"Error sending test WebSocket message: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/dist/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join('dist', 'js'), filename)

@app.route('/api/dist/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join('dist', 'css'), filename)

@app.route('/api/dist/<path:filename>')
def serve_dist_files(filename):
    return send_from_directory('dist', filename)

@app.route('/')
def serve_index():
    return send_from_directory('dist', 'index.html')

# Initialize APScheduler
scheduler = BackgroundScheduler()

# Add the evolution job
# Runs every hour, for demonstration. Adjust interval as needed.
# In a production scenario, you might adjust the interval based on expected
# frequency of evolution, e.g., daily ('interval', days=1).
# For testing, you might use a shorter interval like minutes=1.
scheduler.add_job(
    func=check_for_nft_evolution_jobs,
    trigger=IntervalTrigger(minutes=5), # Check every 5 minutes
    id='nft_evolution_job',
    name='Check and evolve NFTs',
    replace_existing=True,
    max_instances=1 # Ensure only one instance runs at a time
)

# Add a job to retry failed canister mints (e.g., every 30 minutes)
scheduler.add_job(
    func=retry_canister_minting_background,
    trigger=IntervalTrigger(minutes=30),
    id='canister_mint_retry_job',
    name='Retry failed canister mints',
    replace_existing=True,
    max_instances=1
)


if __name__ == '__main__':
    logger.info("Starting APScheduler...")
    scheduler.start()
    logger.info("APScheduler started.")
    
    # Ensure Flask and SocketIO run on the main thread
    port = int(os.environ.get("PORT", 5000))
    logger.info("🔄 About to start socketio server...")
    socketio.run(app, debug=False, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
    logger.info("✅ Server started successfully!")
