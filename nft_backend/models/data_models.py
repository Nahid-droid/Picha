from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
from cryptography.fernet import Fernet
import json
from datetime import datetime

class GenerationMode(Enum):
    SELECTION = "selection"
    PROMPT = "prompt"
    EVOLUTION = "evolution"  # Added this for evolution mode

class EventType(str, Enum):
    ARCHITECTURE = "architecture"
    NATURE = "nature"
    PORTRAIT = "portrait"
    ABSTRACT = "abstract"
    COSMIC = "cosmic"
    URBAN = "urban"
    FANTASY = "fantasy"
    HISTORICAL = "historical"

@dataclass
class UniquenessFactors:
    """Encrypted personal data for NFT uniqueness"""
    location_hash: str
    timestamp_seed: str
    wallet_entropy: str
    wallet_principal: Optional[str] = None
    wallet_account_id: Optional[str] = None
    biometric_opt_in: bool = False
    biometric_hash: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UniquenessFactors':
        """Create UniquenessFactors from dictionary"""
        return cls(**data)
    
    def encrypt_personal_data(self, encryption_key: bytes) -> str:
        """Encrypt sensitive personal data and return as JSON string"""
        fernet = Fernet(encryption_key)
        sensitive_data = {
            'location_hash': self.location_hash,
            'timestamp_seed': self.timestamp_seed,
            'wallet_entropy': self.wallet_entropy,
            'wallet_principal': self.wallet_principal,
            'wallet_account_id': self.wallet_account_id,
            'biometric_opt_in': self.biometric_opt_in,
            'biometric_hash': self.biometric_hash
        }
        encrypted_data = fernet.encrypt(json.dumps(sensitive_data).encode())
        return encrypted_data.decode()
    
    @classmethod
    def decrypt_personal_data(cls, encrypted_data: str, encryption_key: bytes) -> 'UniquenessFactors':
        """Decrypt sensitive personal data and return UniquenessFactors object"""
        fernet = Fernet(encryption_key)
        decrypted_data = fernet.decrypt(encrypted_data.encode())
        data = json.loads(decrypted_data.decode())
        return cls(**data)

@dataclass
class GeneticTraits:
    """Genetic traits for NFT evolution"""
    luminosity: float
    architectural_complexity: float
    ethereal_quality: float
    evolution_speed: float
    style_intensity: float
    temporal_resonance: float
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GeneticTraits':
        """Create GeneticTraits from dictionary"""
        return cls(**data)
    
    def get_rarity_score(self) -> float:
        """Calculate rarity score based on trait distribution"""
        trait_rarity = 0.0
        for trait_value in [self.luminosity, self.architectural_complexity, 
                          self.ethereal_quality, self.style_intensity, self.temporal_resonance]:
            distance_from_center = abs(trait_value - 0.5)
            trait_rarity += distance_from_center * 2
        
        return min(1.0, trait_rarity / 5.0)

@dataclass
class ScarcityInfo:
    """Scarcity information for artist-event combinations"""
    artist: str
    eventType: EventType
    combination: str
    total_limit: int
    minted_count: int
    rarity_score: float
    price_multiplier: float
    
    # Add compatibility properties for the fields expected by app.py
    @property
    def total_supply(self) -> int:
        return self.total_limit
    
    @property
    def current_mint(self) -> int:
        return self.minted_count
    
    @property
    def remaining_slots(self) -> int:
        return self.total_limit - self.minted_count
    
    @property
    def rarity_tier(self) -> str:
        if self.rarity_score >= 0.8:
            return "Legendary"
        elif self.rarity_score >= 0.6:
            return "Epic"
        elif self.rarity_score >= 0.4:
            return "Rare"
        elif self.rarity_score >= 0.2:
            return "Uncommon"
        else:
            return "Common"
    
    @property
    def is_legendary(self) -> bool:
        return self.rarity_score >= 0.8
    
    @property
    def is_sold_out(self) -> bool: # <<< ADD THIS PROPERTY
        return self.minted_count >= self.total_limit
    
    def to_dict(self) -> dict:
        base_dict = asdict(self)
        # Add the computed properties to the dict
        base_dict.update({
            'total_supply': self.total_supply,
            'current_mint': self.current_mint,
            'remaining_slots': self.remaining_slots,
            'rarity_tier': self.rarity_tier,
            'is_legendary': self.is_legendary,
            'is_sold_out': self.is_sold_out # <<< ENSURE IT'S INCLUDED IN to_dict
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ScarcityInfo':
        """Create ScarcityInfo from dictionary"""
        # Extract only the fields that the dataclass expects
        dataclass_fields = {
            'combination': data.get('combination', ''),
            'total_limit': data.get('total_limit', data.get('total_supply', 0)),
            'minted_count': data.get('minted_count', data.get('current_mint', 0)),
            'rarity_score': data.get('rarity_score', 0.0),
            'price_multiplier': data.get('price_multiplier', 1.0)
        }
        return cls(**dataclass_fields)
    
    def is_available(self) -> bool:
        return self.minted_count < self.total_limit

@dataclass
class SocialMediaAuth:
    """
    Data model for storing a user's social media authentication tokens and handle.
    Sensitive tokens are encrypted.
    """
    wallet_principal: str  # The user's wallet principal, used as a primary key
    platform: str          # e.g., "x", "twitter", "facebook"
    social_user_id: str    # The user's ID on the social media platform
    username: str          # The user's handle/username on the social media platform
    encrypted_access_token: str
    encrypted_access_token_secret: str
    last_updated: str      # ISO format datetime string

    def to_dict(self) -> dict:
        """Convert SocialMediaAuth object to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SocialMediaAuth':
        """Create SocialMediaAuth object from a dictionary."""
        return cls(**data)

    def encrypt_tokens(self, access_token: str, access_token_secret: str, encryption_key: bytes) -> None:
        """
        Encrypts the access token and secret and stores them in the object.
        Call this after receiving plain tokens from OAuth.
        """
        fernet = Fernet(encryption_key)
        
        token_data = {
            'access_token': access_token,
            'access_token_secret': access_token_secret
        }
        
        self.encrypted_access_token = fernet.encrypt(json.dumps(token_data).encode()).decode()
        # For simplicity, we're combining both tokens into one encrypted string.
        # Alternatively, you could encrypt them separately. For this use case,
        # encrypting them together makes retrieval and decryption a single operation.
        self.encrypted_access_token_secret = "" # Clear this, as it's now part of the main encrypted string
        self.last_updated = datetime.now().isoformat()

    def decrypt_tokens(self, encryption_key: bytes) -> dict:
        """
        Decrypts the stored tokens and returns them as a dictionary.
        """
        fernet = Fernet(encryption_key)
        
        if not self.encrypted_access_token:
            raise ValueError("No encrypted access token found to decrypt.")
        
        decrypted_data = fernet.decrypt(self.encrypted_access_token.encode())
        token_data = json.loads(decrypted_data.decode())
        
        return {
            'access_token': token_data.get('access_token'),
            'access_token_secret': token_data.get('access_token_secret')
        }

