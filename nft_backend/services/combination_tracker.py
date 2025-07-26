import logging
from models.data_models import EventType, ScarcityInfo # Ensure ScarcityInfo and EventType are correctly imported
from models.database import DatabaseManager

logger = logging.getLogger(__name__)

class CombinationTracker:
    """Track artist-event combinations and manage scarcity"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.combination_limits = {
            "Da Vinci-architecture": 100,
            "Da Vinci-portrait": 150,
            "Van Gogh-nature": 200,
            "Van Gogh-abstract": 120,
            "Picasso-abstract": 80,
            "Picasso-portrait": 100,
            "Monet-nature": 250,
            "Dali-fantasy": 75,
            "Da Vinci-nature": 120,
            "Van Gogh-cosmic": 90,
            "Picasso-urban": 110,
            "Monet-historical": 180,
            "Dali-cosmic": 85
        }
    
    def get_scarcity_info(self, artist: str, event_type: EventType) -> ScarcityInfo:
        """Get scarcity information for artist-event combination"""
        
        combination = f"{artist}-{event_type.value}"
        total_limit = self.combination_limits.get(combination, 50)
        
        print(f"Tracker: get_scarcity_info for {combination} - total_limit: {total_limit}")
        minted_count, _ = self.db_manager.get_combination_count(combination) 
        print(f"Tracker: get_scarcity_info for {combination} - minted_count: {minted_count}")
        
        # Corrected ScarcityInfo instantiation to match the updated dataclass definition
        scarcity_info = ScarcityInfo(
            artist=artist,
            eventType=event_type,
            combination=combination, # Required by the updated ScarcityInfo dataclass
            total_limit=total_limit, # Renamed from total_supply to match dataclass field
            minted_count=minted_count, # Required by the updated ScarcityInfo dataclass
            rarity_score=0.0, # Placeholder, as CombinationTracker doesn't calculate this
            price_multiplier=1.0 # Placeholder, as CombinationTracker doesn't calculate this
        )
        return scarcity_info

    def record_mint(self, artist: str, event_type: EventType):
        """
        Increments the minted count for the given artist-event_type combination.
        This method is called after a successful NFT mint.
        """
        combination_key = f"{artist}-{event_type.value}"
        try:
            # 1. Get the current minted count and the total limit from the database
            current_minted_count, total_limit_from_db = self.db_manager.get_combination_count(combination_key)

            # 2. Increment the minted count
            new_minted_count = current_minted_count + 1

            # 3. Update the combination count in the database
            # Corrected: Removed total_limit_from_db as it was causing a TypeError.
            # update_combination_count likely only expects the combination_key and the new_minted_count.
            self.db_manager.update_combination_count(combination_key, new_minted_count)
            logger.info(f"Recorded mint for combination: {combination_key}. New count: {new_minted_count}")
        except Exception as e:
            logger.error(f"Failed to record mint for combination {combination_key}: {e}", exc_info=True)
            raise # Re-raise the exception to propagate the error

    # The existing increment_minted_count method from your context,
    # if it's separate from what record_mint is intended to do.
    # If record_mint replaces it, this can be removed.
    # def increment_minted_count(self, artist: str, event_type: EventType):
    #     combination = f"{artist}-{event_type.value}"
    #     total_limit = self.combination_limits.get(combination, 50)
    #     self.db_manager.update_combination_count(combination, total_limit)

    def is_combination_available(self, artist: str, event_type: EventType) -> bool:
        """Check if combination is available for minting"""
        combination = f"{artist}-{event_type.value}"
        
        # First ensure the combination exists in database
        total_limit = self.combination_limits.get(combination, 50)
        
        # Check current count
        minted_count, db_limit = self.db_manager.get_combination_count(combination)
        
        available = minted_count < total_limit
        print(f"Tracker: Combination '{combination}' availability check: {minted_count}/{total_limit} = {available}")
        return available

    def get_availability_status(self, artist: str, event_type: EventType) -> dict:
        """Get detailed availability status for frontend"""
        combination = f"{artist}-{event_type.value}"
        total_limit = self.combination_limits.get(combination, 50)
        minted_count, _ = self.db_manager.get_combination_count(combination)
        
        return {
            "combination": combination,
            "available": minted_count < total_limit,
            "minted_count": minted_count,
            "total_supply": total_limit
        }