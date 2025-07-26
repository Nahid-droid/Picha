import os
import time
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import logging

# Ensure these imports are correct based on your project structure
from models.data_models import GenerationMode, EventType, UniquenessFactors, GeneticTraits, ScarcityInfo, SocialMediaAuth
from services.stability_ai import StabilityAI
from services.prompt_generator import EnhancedPromptGenerator
from services.evolution import EvolutionaryAlgorithm
from services.combination_tracker import CombinationTracker
from models.database import DatabaseManager
from canister_client import CanisterClient, NFTMetadata, Principal, CanisterError
from services.social_media import SocialMediaService 

# For NLTK sentiment analysis
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except nltk.downloader.DownloadError:
    nltk.download('vader_lexicon')

logger = logging.getLogger(__name__)

class NFTEngine:
    """Main NFT engine integrating all components, now including social media for evolution."""

    def __init__(self, stability_api_key: str, encryption_key: bytes,
                 db_path: str, static_image_path: str,
                 canister_client: Optional[CanisterClient] = None):
        self.prompt_generator = EnhancedPromptGenerator()
        self.evolution_algorithm = EvolutionaryAlgorithm()
        self.stability_ai = StabilityAI(stability_api_key)
        self.db_manager = DatabaseManager(db_path)
        self.combination_tracker = CombinationTracker(self.db_manager)
        self.encryption_key = encryption_key
        self.static_image_path = static_image_path
        self.canister_client = canister_client
        self.social_media_service = SocialMediaService()
        self.analyzer = SentimentIntensityAnalyzer() # Initialize VADER sentiment analyzer

    async def create_nft(self, mode: GenerationMode, artist: str, event_type: EventType,
                         uniqueness_factors: UniquenessFactors, owner_address: str,
                         genetic_traits: GeneticTraits, scarcity_info: ScarcityInfo,
                         evolution_period_days: int, # ADDED THIS PARAMETER
                         user_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new NFT, generates its image, and saves its metadata.
        Now also includes initial genetic traits and scarcity info.
        """
        nft_id = self.db_manager.generate_unique_id()
        name = f"{artist} {event_type.value.capitalize()} #{nft_id[:8]}"
        description = f"An evolving digital collectible by {artist}, capturing the essence of {event_type.value}."

        logger.debug(f"DEBUG: Before generate_prompt call in create_nft. uniqueness_factors type: {type(uniqueness_factors)}")
        logger.debug(f"DEBUG: uniqueness_factors content: {uniqueness_factors}")
        # Ensure uniqueness_factors is an instance of UniquenessFactors (it should be from app.py)
        # FIX: Handle the case where uniqueness_factors might be a dictionary instead of UniquenessFactors object
        # Replace the existing type checking section (around lines 50-60) with this:

# FIX: Handle the case where uniqueness_factors might be a dictionary, string, or UniquenessFactors object
        if isinstance(uniqueness_factors, str):
    # Convert JSON string to UniquenessFactors object
            try:
                uniqueness_factors_dict = json.loads(uniqueness_factors)
                uniqueness_factors = UniquenessFactors(**uniqueness_factors_dict)
                logger.info(f"Converted uniqueness_factors JSON string to UniquenessFactors object")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse uniqueness_factors JSON string: {e}")
                raise ValueError(f"Invalid uniqueness_factors JSON string: {e}")
        elif isinstance(uniqueness_factors, dict):
            try:
                logger.info(f"Converting uniqueness_factors dict to UniquenessFactors object: {uniqueness_factors}")
                logger.debug(f"DEBUG: Dict keys before Pydantic conversion: {uniqueness_factors.keys()}")
                uniqueness_factors = UniquenessFactors(**uniqueness_factors)
                logger.info(f"Converted uniqueness_factors dict to UniquenessFactors object")
            except Exception as e:
                logger.error(f"Failed to convert uniqueness_factors dict to UniquenessFactors object: {e}")
                logger.error(f"Dict content: {uniqueness_factors}")
                raise ValueError(f"Invalid uniqueness_factors dictionary: {e}")
        elif not isinstance(uniqueness_factors, UniquenessFactors):
            logger.error(f"Type error: uniqueness_factors is not UniquenessFactors in create_nft, found {type(uniqueness_factors)}")
            raise TypeError("uniqueness_factors must be an instance of UniquenessFactors, a dictionary, or a JSON string")
        # Generate initial image based on initial traits
        logger.debug(f"DEBUG: After conversion, uniqueness_factors type: {type(uniqueness_factors)}")
        logger.debug(f"DEBUG: After conversion, uniqueness_factors.location_hash: {uniqueness_factors.location_hash}")
        try:
            logger.debug(f"DEBUG: About to call generate_prompt with uniqueness_factors type: {type(uniqueness_factors)}")
            image_prompt = self.prompt_generator.generate_prompt(
                mode=mode, 
                artist=artist,
                event_type=event_type,
                user_prompt=user_prompt,
                uniqueness_factors=uniqueness_factors, 
                genetic_traits=genetic_traits 
            )
        except Exception as e:
            logger.error(f"Error in generate_prompt: {e}")
            logger.error(f"uniqueness_factors type: {type(uniqueness_factors)}")
            logger.error(f"uniqueness_factors value: {uniqueness_factors}")
            raise
        image_filename = f"{nft_id}.png"
        image_path = os.path.join(self.static_image_path, image_filename)

        try:
            image_generation_result = await self.stability_ai.generate_image(image_prompt, uniqueness_factors)
            image_url = image_generation_result["image_url"] 
            logger.info(f"Generated image for NFT {nft_id} at {image_url}")
        except Exception as e:
            logger.error(f"Failed to generate image for NFT {nft_id}: {e}")
            raise ValueError(f"Image generation failed: {e}")

        # Initial evolution history entry
        initial_evolution_entry = {
            "version": 0,
            "timestamp": datetime.now().isoformat(),
            "event": "mint",
            "image_url": image_url,
            "genetic_traits_at_evolution": genetic_traits.to_dict(),
            "prompt_used": image_prompt,
            "social_media_impact": None
        }

        # Store initial NFT data locally
        self.db_manager.save_nft(
            nft_id=nft_id,
            owner_address=owner_address,
            artist=artist,
            event_type=event_type.value,
            mode=mode.value,
            user_prompt=user_prompt,
            name=name,
            description=description,
            image_url=image_url,
            metadata=json.dumps({"attributes": []}), # Placeholder for additional attributes
            genetic_traits=json.dumps(genetic_traits.to_dict()),
            scarcity_info=json.dumps(scarcity_info.to_dict()),
            evolution_history=json.dumps([initial_evolution_entry]),
            canister_id=None, # Will be updated after successful mint on canister
            canister_status="pending_mint", # Initial status
            uniqueness_factors=json.dumps(uniqueness_factors.to_dict()), # Store as JSON string
            last_evolution_time=datetime.now().isoformat(), # Set initial evolution time to mint time
            evolution_period_days=evolution_period_days 
        )

        # Update scarcity metrics
        self.combination_tracker.record_mint(artist, event_type)

        return {
            "nft_id": nft_id,
            "name": name,
            "description": description,
            "image_url": image_url,
            "artist": artist,
            "event_type": event_type.value,
            "mode": mode.value,
            "user_prompt": user_prompt,
            "genetic_traits": genetic_traits.to_dict(),
            "scarcity_info": scarcity_info.to_dict(),
            "evolution_period_days": evolution_period_days 
        }

    def get_available_combinations(self) -> List[Dict[str, Any]]:
        """
        Retrieves all unique artist-event type combinations with their scarcity.
        The scarcity_info is returned as a nested object, including is_sold_out.
        """
        all_combinations_from_db = self.db_manager.get_all_combinations() 
        
        enhanced_combinations = []
        for combo_db_data in all_combinations_from_db: 
            artist = combo_db_data['artist']
            event_type_str = combo_db_data['event_type']
            
            try:
                event_type_enum = EventType(event_type_str)
                # Call get_scarcity_info to get the full ScarcityInfo object
                scarcity_obj = self.combination_tracker.get_scarcity_info(artist, event_type_enum)
                
                enhanced_combinations.append({
                    "artist": artist,
                    "event_type": event_type_str,
                    "is_available": scarcity_obj.is_available(), 
                    "scarcity_info": scarcity_obj.to_dict(), 
                    "waitlist_count": self.db_manager.get_waitlist_count(scarcity_obj.combination),
                    "estimated_availability": "immediate" if scarcity_obj.is_available() else "waitlist",
                    "price_multiplier": scarcity_obj.price_multiplier 
                })
            except ValueError:
                logger.warning(f"Skipping invalid event_type {event_type_str} for artist {artist} in get_available_combinations.")
                continue 
                
        return enhanced_combinations

    # NEW: Simple sentiment analysis placeholder
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyzes the sentiment of a given text using NLTK's VADER.
        Returns sentiment scores (neg, neu, pos, compound).
        """
        return self.analyzer.polarity_scores(text)

    # NEW: Process social media data into metrics
    def _process_social_media_data(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes raw tweet data into aggregated social media metrics
        relevant for NFT evolution.
        """
        total_tweets = len(tweets)
        total_likes = 0
        total_retweets = 0
        total_replies = 0
        total_quotes = 0
        total_impressions = 0 
        
        sentiment_compound_scores = []
        
        # Example keywords for content analysis
        relevant_keywords = ['nft', 'art', 'digital', 'collectible', 'crypto', 'evolution', 'ai', 'future', 'metaverse']
        keyword_matches = {keyword: 0 for keyword in relevant_keywords}

        for tweet in tweets:
            # Aggregate engagement
            public_metrics = tweet.get('public_metrics', {})
            total_likes += public_metrics.get('like_count', 0)
            total_retweets += public_metrics.get('retweet_count', 0)
            total_replies += public_metrics.get('reply_count', 0)
            total_quotes += public_metrics.get('quote_count', 0)
            total_impressions += public_metrics.get('impression_count', 0) 
            
            # Sentiment analysis
            sentiment_scores = self._analyze_sentiment(tweet.get('text', ''))
            sentiment_compound_scores.append(sentiment_scores['compound']) 
            
            # Keyword analysis
            text_lower = tweet.get('text', '').lower()
            for keyword in relevant_keywords:
                if keyword in text_lower:
                    keyword_matches[keyword] += 1
        
        # Calculate average sentiment (normalize to 0-1 from -1 to 1)
        avg_sentiment_compound = sum(sentiment_compound_scores) / total_tweets if total_tweets > 0 else 0.0
        normalized_avg_sentiment = (avg_sentiment_compound + 1.0) / 2.0 

        # Determine overall sentiment category based on average
        sentiment_category = "neutral"
        if avg_sentiment_compound >= 0.05: 
            sentiment_category = "positive"
        elif avg_sentiment_compound <= -0.05: 
            sentiment_category = "negative"

        processed_metrics = {
            "total_tweets": total_tweets,
            "total_engagement": total_likes + total_retweets + total_replies + total_quotes + total_impressions,
            "average_sentiment_compound": avg_sentiment_compound, 
            "normalized_average_sentiment": normalized_avg_sentiment, 
            "sentiment_category": sentiment_category,
            "keyword_matches": keyword_matches,
            "engagement_details": {
                "likes": total_likes,
                "retweets": total_retweets,
                "replies": total_replies,
                "quotes": total_quotes,
                "impressions": total_impressions 
            }
        }
        logger.info(f"Processed social media metrics: {processed_metrics}")
        return processed_metrics

    async def evolve_nft(self, nft_id: str, new_event_type: EventType, user_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Evolves an existing NFT based on its genetic traits and social media interaction.
        This new version integrates social media data into the evolution process.
        """
        nft_data = self.db_manager.get_nft(nft_id)
        if not nft_data:
            raise ValueError(f"NFT with ID {nft_id} not found.")

        # 1. Retrieve the NFT's owner's wallet principal.
        owner_wallet_principal = nft_data.get('owner_address')
        if not owner_wallet_principal:
            logger.error(f"NFT {nft_id} has no owner_address, cannot perform social evolution.")
            raise ValueError(f"NFT {nft_id} owner address missing. Cannot fetch social data.")

        # 2. Fetch the social media authentication (X tokens) for that principal.
        # 3. Decrypt the social media tokens.
        social_auth_data = self.db_manager.get_social_media_auth(owner_wallet_principal, "x")
        access_token = None
        access_token_secret = None
        if social_auth_data:
            try:
                # social_auth is already a SocialMediaAuth object due to get_social_media_auth return type hint
                decrypted_tokens = social_auth_data.decrypt_tokens(self.encryption_key) 
                access_token = decrypted_tokens.get('access_token')
                access_token_secret = decrypted_tokens.get('access_token_secret')
                logger.info(f"Successfully retrieved and decrypted X tokens for {owner_wallet_principal}")
            except Exception as e:
                logger.warning(f"Could not decrypt X tokens for {owner_wallet_principal}: {e}")
                # Continue without social data if decryption fails
        else:
            logger.info(f"No X authentication found for wallet principal: {owner_wallet_principal}. Evolving without social data.")

        # Determine the time period for fetching tweets
        last_evolution_time_str = nft_data.get('last_evolution_time')
        # Use evolution_period_days from the NFT data, default to 30 if not found
        evolution_period_days = nft_data.get('evolution_period_days', 30) 
        
        # Calculate `since_time` based on `last_evolution_time` and `evolution_period_days`
        if last_evolution_time_str:
            last_evolution_datetime = datetime.fromisoformat(last_evolution_time_str)
            since_time = last_evolution_datetime
            logger.info(f"Using last_evolution_time {since_time} for tweet fetching.")
        else:
            # Fallback to creation_time, or default to N days ago if no history
            creation_time_str = nft_data.get('created_at') 
            if creation_time_str:
                since_time = datetime.fromisoformat(creation_time_str)
                logger.info(f"Using creation_time {since_time} for tweet fetching (no last_evolution_time).")
            else:
                since_time = datetime.now() - timedelta(days=evolution_period_days) 
                logger.warning(f"No last_evolution_time or creation_time found for NFT {nft_id}, using {evolution_period_days} days ago for tweet fetching.")

        social_media_metrics = {}
        raw_tweets = []
        if access_token and access_token_secret:
            try:
                # 4. Use the SocialMediaService to fetch recent tweets from X.
                x_user_id = social_auth_data.social_user_id 
                if x_user_id:
                    # Pass since_time to get_user_tweets
                    tweets_response = self.social_media_service.get_user_tweets(
                        user_id=x_user_id, 
                        access_token=access_token, 
                        access_token_secret=access_token_secret,
                        since_time=since_time, 
                        tweet_count=100 
                    )
                    raw_tweets = tweets_response.get('tweets', [])
                    logger.info(f"Fetched {len(raw_tweets)} tweets for X user {x_user_id} since {since_time}.")
                else:
                    logger.warning(f"X User ID not found for wallet {owner_wallet_principal}. Cannot fetch tweets.")

                # 5. Process the raw tweet data to extract meaningful metrics.
                if raw_tweets:
                    social_media_metrics = self._process_social_media_data(raw_tweets)
                    
                    # 6. Pass these processed social media metrics to evolve_traits_with_social_data.
                    current_traits = GeneticTraits(**json.loads(nft_data['genetic_traits']))
                    evolved_traits = self.evolution_algorithm.evolve_traits_with_social_data(
                        current_traits=current_traits,
                        social_media_metrics=social_media_metrics,
                        evolution_interval_days=evolution_period_days 
                    )
                    logger.info(f"NFT {nft_id} traits evolved with social data.")
                else:
                    logger.info(f"No tweets fetched for NFT {nft_id}'s owner or no relevant tweets found. Evolving without social data influence.")
                    current_traits = GeneticTraits(**json.loads(nft_data['genetic_traits']))
                    # Fallback: Evolve traits based on existing algorithm (e.g., time-based or random drift)
                    evolved_traits = self.evolution_algorithm.evolve_traits(current_traits) 
                    logger.info(f"NFT {nft_id} traits evolved (fallback - no social data).")

            except Exception as e:
                logger.error(f"Error during social media data fetching or processing for NFT {nft_id}: {e}", exc_info=True)
                # Fallback: Evolve without social data if there's an error
                current_traits = GeneticTraits(**json.loads(nft_data['genetic_traits']))
                evolved_traits = self.evolution_algorithm.evolve_traits(current_traits) 
                logger.info(f"NFT {nft_id} traits evolved (fallback due to social data error).")
        else:
            logger.info(f"No valid X access tokens for NFT {nft_id} owner. Evolving without social data.")
            current_traits = GeneticTraits(**json.loads(nft_data['genetic_traits']))
            evolved_traits = self.evolution_algorithm.evolve_traits(current_traits) 


        # Increment NFT version
        new_version = nft_data.get('version', 0) + 1

        # 7. Generate a new image based on the evolved traits.
        # Safely reconstruct UniquenessFactors object from DB data
        uniqueness_factors_from_db = nft_data.get('uniqueness_factors')
        reconstructed_uniqueness_factors: UniquenessFactors

        if isinstance(uniqueness_factors_from_db, str):
            try:
                parsed_factors_dict = json.loads(uniqueness_factors_from_db)
                reconstructed_uniqueness_factors = UniquenessFactors(**parsed_factors_dict)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse or reconstruct UniquenessFactors from string: {e}. Data: {uniqueness_factors_from_db}")
                # Provide a fallback for robustness, though this indicates deeper data consistency issues
                reconstructed_uniqueness_factors = UniquenessFactors(
                    location_hash="", timestamp_seed="", wallet_entropy="", wallet_principal="" 
                )
        elif isinstance(uniqueness_factors_from_db, dict):
            # Already a dict, directly try to reconstruct
            reconstructed_uniqueness_factors = UniquenessFactors(**uniqueness_factors_from_db)
        elif isinstance(uniqueness_factors_from_db, UniquenessFactors):
            # Already the correct object type
            reconstructed_uniqueness_factors = uniqueness_factors_from_db
        else:
            logger.error(f"Unexpected type for uniqueness_factors from DB: {type(uniqueness_factors_from_db)}. Defaulting to empty.")
            reconstructed_uniqueness_factors = UniquenessFactors(
                location_hash="", timestamp_seed="", wallet_entropy="", wallet_principal="" 
            )

        logger.debug(f"DEBUG: Before generate_prompt call in evolve_nft. reconstructed_uniqueness_factors type: {type(reconstructed_uniqueness_factors)}")
        logger.debug(f"DEBUG: Before generate_prompt call in evolve_nft. reconstructed_uniqueness_factors: {reconstructed_uniqueness_factors}")


        new_image_prompt = self.prompt_generator.generate_prompt(
            mode=GenerationMode(nft_data['mode']), 
            artist=nft_data['artist'],
            event_type=EventType(nft_data['event_type']),
            user_prompt=user_prompt, 
            uniqueness_factors=reconstructed_uniqueness_factors, # Pass the reconstructed object
            genetic_traits=evolved_traits
        )
        
        new_image_filename = f"{nft_id}_v{new_version}.png"
        new_image_path = os.path.join(self.static_image_path, new_image_filename)

        try:
            new_image_url = await self.stability_ai.generate_image(new_image_prompt, new_image_path)
            logger.info(f"Generated new image for NFT {nft_id} version {new_version} at {new_image_url}")
        except Exception as e:
            logger.error(f"Failed to generate new image for NFT {nft_id} version {new_version}: {e}")
            raise ValueError(f"Image generation failed during evolution: {e}")

        # Update evolution history
        evolution_history = json.loads(nft_data.get('evolution_history', '[]'))
        
        # Determine traits that changed
        old_traits_dict = json.loads(nft_data['genetic_traits'])
        new_traits_dict = evolved_traits.to_dict()
        
        traits_changed = []
        for trait_name, new_value in new_traits_dict.items():
            old_value = old_traits_dict.get(trait_name)
            if old_value is not None and abs(new_value - old_value) > 0.001: 
                traits_changed.append(trait_name)

        new_evolution_entry = {
            "version": new_version,
            "timestamp": datetime.now().isoformat(),
            "event": new_event_type.value,
            "image_url": new_image_url,
            "genetic_traits_at_evolution": evolved_traits.to_dict(),
            "prompt_used": new_image_prompt,
            "social_media_impact": social_media_metrics, 
            "traits_changed": traits_changed
        }
        evolution_history.append(new_evolution_entry)

        # 8. Update the NFT's data locally.
        self.db_manager.update_nft_on_evolution(
            nft_id=nft_id,
            new_version=new_version,
            new_image_url=new_image_url,
            new_genetic_traits=json.dumps(evolved_traits.to_dict()),
            new_evolution_history=json.dumps(evolution_history),
            new_last_evolution_time=datetime.now().isoformat()
        )
        logger.info(f"NFT {nft_id} updated locally to version {new_version}.")

        # 9. Trigger an update on the ICP canister.
        updated_nft_data = self.db_manager.get_nft(nft_id) 
        if self.canister_client and updated_nft_data.get('canister_nft_id') and updated_nft_data.get('canister_status') == "minted":
            try:
                logger.info(f"Updating NFT {nft_id} on canister (canister ID: {updated_nft_data['canister_nft_id']})...")
                
                # Reconstruct the objects, then dump them to JSON strings for the canister client
                canister_genetic_traits_obj = GeneticTraits(**json.loads(updated_nft_data.get('genetic_traits', '{}')))
                canister_scarcity_info_obj = ScarcityInfo(**json.loads(updated_nft_data.get('scarcity_info', '{}')))
                # uniqueness_factors_for_canister is already an object from reconstruction earlier
                
                updated_nft_metadata = NFTMetadata(
                    name=updated_nft_data['name'],
                    description=updated_nft_data['description'],
                    image_url=updated_nft_data['image_url'],
                    genetic_traits=json.dumps(canister_genetic_traits_obj.to_dict()), # Convert to JSON string
                    scarcity_info=json.dumps(canister_scarcity_info_obj.to_dict()),   # Convert to JSON string
                    uniqueness_factors=json.dumps(reconstructed_uniqueness_factors.to_dict()), # Convert to JSON string
                    artist=updated_nft_data['artist'], 
                    eventType=updated_nft_data['event_type'], 
                    prompt=updated_nft_data['user_prompt'], 
                    mode=updated_nft_data['mode'], 
                    attributes=json.dumps(json.loads(updated_nft_data.get('metadata', '{}')).get('attributes', {})), # Convert to JSON string
                    created_timestamp=None 
                )

                canister_update_result = await self.canister_client.update_nft(
                    updated_nft_data['canister_nft_id'], 
                    updated_nft_metadata
                )

                if canister_update_result and canister_update_result.get('Ok'):
                    self.db_manager.update_nft_canister_status(nft_id, updated_nft_data['canister_nft_id'], "minted") 
                    logger.info(f"Evolved NFT {nft_id} successfully updated on canister.")
                elif canister_update_result and canister_update_result.get('Err'):
                    logger.error(f"Failed to update evolved NFT {nft_id} on canister: {canister_update_result['Err']}. Marking local status as failed_update.")
                    self.db_manager.update_nft_canister_status(nft_id, updated_nft_data['canister_nft_id'], "failed_update") 
                else:
                    logger.error(f"Unexpected response from canister during evolved NFT update for {nft_id}. Marking local status as failed_update.")
                    self.db_manager.update_nft_canister_status(nft_id, updated_nft_data['canister_nft_id'], "failed_update")

            except CanisterError as e:
                logger.error(f"Canister error during evolved NFT update for {nft_id}: {e.message}. Marking local status as failed_update.")
                self.db_manager.update_nft_canister_status(nft_id, updated_nft_data['canister_nft_id'], "failed_update")
            except Exception as e:
                logger.error(f"Unexpected error during evolved NFT update for {nft_id}: {e}. Marking local status as failed_update.")
                self.db_manager.update_nft_canister_status(nft_id, updated_nft_data['canister_nft_id'], "failed_update")
        else:
            logger.info(f"Canister update skipped for NFT {nft_id}. Canister client not enabled, NFT not minted on canister, or current canister status is not 'minted'.")


        return updated_nft_data 

    async def _process_evolution_queue(self):
        """
        Processes NFTs that are due for evolution.
        This method would typically be called by a background scheduler.
        """
        nfts_due_for_evolution = self.db_manager.get_nfts_due_for_evolution()
        if not nfts_due_for_evolution:
            logger.info("No NFTs are currently due for evolution.")
            return

        logger.info(f"Found {len(nfts_due_for_evolution)} NFTs due for evolution.")
        for nft_data in nfts_due_for_evolution:
            nft_id = nft_data['id']
            # Assuming a default evolution event type if not specified
            # In a real scenario, this might be dynamically determined or a fixed "auto-evolve" type
            default_event_type = EventType.URBAN # Or any other suitable default
            
            try:
                logger.info(f"Initiating auto-evolution for NFT: {nft_id}")
                # Call the main evolve_nft method without a user prompt
                # Here, we don't need a specific user_prompt, it's auto-evolution
                await self.evolve_nft(nft_id, default_event_type, user_prompt=f"Auto-evolution based on social data for {nft_id}")
                logger.info(f"Successfully auto-evolved NFT: {nft_id}")
            except Exception as e:
                logger.error(f"Failed to auto-evolve NFT {nft_id}: {e}", exc_info=True)
                # You might want to update the NFT's status to 'evolution_failed' in the DB here
                # Or log the error for manual intervention
