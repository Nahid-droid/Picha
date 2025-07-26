"""
Internet Computer Protocol (ICP) Motoko Canister Client

A Python client module for interacting with ICP canisters using the ic-py library.
Provides NFT minting, retrieval, updating capabilities with comprehensive error handling.
"""

import logging
import time
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from enum import Enum

try:
    from ic.client import Client
    from ic.identity import Identity
    from ic.agent import Agent
    from ic.principal import Principal
    from ic.candid import encode, decode
except ImportError as e:
    raise ImportError(
        "ic-py library is required. Install with: pip install ic-py"
    ) from e


class NetworkType(Enum):
    """Supported ICP network types"""
    LOCAL = "local"
    MAINNET = "mainnet"
    TESTNET = "testnet"


@dataclass
class GeneticTraits:
    """NFT genetic traits data structure"""
    luminosity: float
    architectural_complexity: float
    ethereal_quality: float
    evolution_speed: float
    style_intensity: float
    temporal_resonance: float # Ensure this matches your Python GeneticTraits

@dataclass
class UniquenessFactors:
    """Encrypted personal data for NFT uniqueness (Matches Motoko type)"""
    location_hash: str
    timestamp_seed: str
    wallet_entropy: str
    biometric_opt_in: bool
    # wallet_principal: Optional[str] = None # Not present in Motoko type provided
    # wallet_account_id: Optional[str] = None # Not present in Motoko type provided
    # biometric_hash: Optional[str] = None # Not present in Motoko type provided


@dataclass
class ScarcityInfo:
    """NFT scarcity information"""
    combination: str
    total_limit: int
    minted_count: int
    rarity_score: float
    price_multiplier: float
    # Note: rarity_tier and is_legendary are computed properties in Python,
    # not directly stored in Motoko's ScarcityInfo.

@dataclass
class NFTMetadata:
    """Complete NFT metadata structure for minting/updating on Motoko"""
    name: str
    description: str
    image_url: str # Corresponds to imageURI on Motoko
    artist: str
    eventType: str # Corresponds to eventType on Motoko
    prompt: str
    mode: str
    uniqueness_factors: UniquenessFactors # Pass the dataclass directly
    genetic_traits: GeneticTraits # Pass the dataclass directly
    scarcity_info: ScarcityInfo # Pass the dataclass directly
    attributes: Dict[str, str] # Note: Motoko uses [(Text, Text)], map accordingly if needed.

@dataclass
class NFTData: # For deserializing from Motoko's NFTData response
    id: str
    owner: Principal
    artist: str
    eventType: str
    prompt: str
    mode: str
    version: int
    imageURI: str
    timestamp: int # Time.Time in Motoko, likely Nat for nanoseconds
    history: List[Dict[str, Any]] # Or a specific VersionLog dataclass if defined
    genetic_traits: GeneticTraits
    uniqueness_factors: UniquenessFactors
    scarcity_info: ScarcityInfo
    last_evolution: int # Time.Time in Motoko
    name: str
    description: str
    attributes: Dict[str, str]


class CanisterError(Exception):
    """Custom exception for canister-related errors"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.error_code = error_code
        super().__init__(message)


class NetworkError(CanisterError):
    """Network-related canister errors"""
    pass


class SerializationError(CanisterError):
    """Data serialization/deserialization errors"""
    pass


class CanisterClient:
    """
    Client for interacting with ICP Motoko canisters
    
    Provides methods for NFT operations with comprehensive error handling,
    retry logic, and support for multiple network environments.
    """
    
    # Network endpoints
    NETWORK_ENDPOINTS = {
        NetworkType.LOCAL: "http://localhost:8080",
        NetworkType.MAINNET: "https://ic0.app",
        NetworkType.TESTNET: "https://testnet.dfinity.network"
    }
    
    def __init__(
        self,
        canister_id: str,
        network: str = "local",
        identity: Optional[Identity] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize the canister client
        
        Args:
            canister_id: The canister ID to interact with
            network: Network type ("local", "mainnet", "testnet")
            identity: ICP identity for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed calls
        """
        self.canister_id = canister_id
        self.network = NetworkType(network.lower())
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Setup logging
        self.logger = logging.getLogger(f"CanisterClient-{canister_id[:8]}")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        try:
            # Initialize ICP client and agent
            self.client = Client(url=self.NETWORK_ENDPOINTS[self.network])
            self.agent = Agent(
                identity=identity or Identity(),
                client=self.client
            )
            self.principal = Principal.from_str(canister_id)
            
            self.logger.info(
                f"Initialized canister client for {canister_id} on {network} network"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize canister client: {e}")
            raise NetworkError(f"Client initialization failed: {e}")
    
    async def _retry_call_async(self, func, *args, **kwargs):
        """
        Execute async function with retry logic
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CanisterError: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Attempt {attempt + 1}/{self.max_retries}")
                return await func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}"
                )
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time) # Use asyncio.sleep for async functions
        
        raise CanisterError(
            f"All {self.max_retries} attempts failed. Last error: {last_exception}"
        )
    
    def _serialize_nft_metadata(self, metadata: NFTMetadata) -> Dict[str, Any]:
        """
        Serialize NFT metadata for canister call.
        Ensures attribute tuples are correctly formatted.
        """
        try:
            # Convert attributes dictionary to list of (Text, Text) tuples
            attributes_list = [(k, str(v)) for k, v in metadata.attributes.items()]

            return {
                "name": metadata.name,
                "description": metadata.description,
                "image_url": metadata.image_url,
                "artist": metadata.artist,
                "eventType": metadata.eventType,
                "prompt": metadata.prompt,
                "mode": metadata.mode,
                "uniqueness_factors": {
                    "location_hash": metadata.uniqueness_factors.location_hash,
                    "timestamp_seed": metadata.uniqueness_factors.timestamp_seed,
                    "wallet_entropy": metadata.uniqueness_factors.wallet_entropy,
                    "biometric_opt_in": metadata.uniqueness_factors.biometric_opt_in
                },
                "genetic_traits": {
                    "luminosity": metadata.genetic_traits.luminosity,
                    "complexity": metadata.genetic_traits.architectural_complexity, # Map to Motoko 'complexity'
                    "ethereal_quality": metadata.genetic_traits.ethereal_quality,
                    "evolution_speed": metadata.genetic_traits.evolution_speed,
                    "style_intensity": metadata.genetic_traits.style_intensity,
                    # Motoko's GeneticTraits in main.mo seems to have only these 5.
                    # Ensure consistency or add handling for 'temporal_resonance' if present.
                    # For now, assuming only these 5 are expected by Motoko.
                },
                "scarcity_info": {
                    "combination": metadata.scarcity_info.combination,
                    "total_limit": metadata.scarcity_info.total_limit,
                    "minted_count": metadata.scarcity_info.minted_count,
                    "rarity_score": metadata.scarcity_info.rarity_score,
                    "price_multiplier": metadata.scarcity_info.price_multiplier
                },
                "attributes": attributes_list, # Pass as list of tuples
            }
        except Exception as e:
            raise SerializationError(f"Failed to serialize NFT metadata: {e}")
    
    def _deserialize_nft_data(self, data: Dict[str, Any]) -> NFTData:
        """
        Deserialize NFTData from canister response.
        Handles mapping Motoko fields to Python dataclass.
        """
        try:
            genetic_traits = GeneticTraits(
                luminosity=float(data["genetic_traits"]["luminosity"]),
                architectural_complexity=float(data["genetic_traits"]["complexity"]), # Map from Motoko 'complexity'
                ethereal_quality=float(data["genetic_traits"]["ethereal_quality"]),
                evolution_speed=float(data["genetic_traits"]["evolution_speed"]),
                style_intensity=float(data["genetic_traits"]["style_intensity"]),
                temporal_resonance=0.0 # Default if not present in Motoko, or handle if it exists
            )
            
            uniqueness_factors = UniquenessFactors(
                location_hash=data["uniqueness_factors"]["location_hash"],
                timestamp_seed=data["uniqueness_factors"]["timestamp_seed"],
                wallet_entropy=data["uniqueness_factors"]["wallet_entropy"],
                biometric_opt_in=data["uniqueness_factors"]["biometric_opt_in"]
            )

            scarcity_info = ScarcityInfo(
                combination=data["scarcity_info"]["combination"],
                total_limit=int(data["scarcity_info"]["total_limit"]),
                minted_count=int(data["scarcity_info"]["minted_count"]),
                rarity_score=float(data["scarcity_info"]["rarity_score"]),
                price_multiplier=float(data["scarcity_info"]["price_multiplier"])
            )
            
            return NFTData(
                id=str(data["id"]),
                owner=Principal.from_str(data["owner"]),
                artist=data["artist"],
                eventType=data["eventType"],
                prompt=data["prompt"],
                mode=data["mode"],
                version=int(data["version"]),
                imageURI=data["imageURI"],
                timestamp=int(data["timestamp"]),
                history=data.get("history", []), # Assuming history is already in a Python-compatible format
                genetic_traits=genetic_traits,
                uniqueness_factors=uniqueness_factors,
                scarcity_info=scarcity_info,
                last_evolution=int(data["last_evolution"]),
                name=data["name"],
                description=data["description"],
                attributes={k: v for k, v in data.get("attributes", [])} # Convert list of tuples to dict
            )
        except (KeyError, TypeError) as e:
            self.logger.error(f"Failed to deserialize NFT data: {data}. Error: {e}")
            raise SerializationError(f"Failed to deserialize NFT data: {e}")
    
    async def mint(self, owner: Principal, nft_metadata: NFTMetadata) -> Dict[str, Any]:
        """
        Mint a new NFT on the canister.
        
        Args:
            owner: The principal of the owner.
            nft_metadata: NFTMetadata object to mint.
            
        Returns:
            Mint result with NFT ID and transaction details (or error).
            
        Raises:
            CanisterError: If minting fails.
        """
        self.logger.info(f"Minting NFT: {nft_metadata.name} for owner: {owner.to_text()}")
        
        async def _mint_call():
            try:
                serialized_data = self._serialize_nft_metadata(nft_metadata)
                
                # Motoko's mint function takes (Principal, NFTMetadata)
                result = await self.agent.update_call(
                    canister_id=self.principal,
                    method_name="mint",
                    # The encode_args should match the candid signature of your Motoko function
                    # It's (owner: Principal, metadata: NFTMetadata)
                    encode_args=[owner, serialized_data],
                    timeout=self.timeout
                )
                
                # The result from Motoko's MintResult is { #Ok: NFTData; #Err: Text; }
                if "Err" in result:
                    self.logger.error(f"Canister mint failed: {result['Err']}")
                    raise CanisterError(f"Mint failed: {result['Err']}")
                
                # If it's Ok, it contains the full NFTData
                minted_nft_data_raw = result["Ok"]
                # Optionally deserialize the NFTData if you need the dataclass here
                # minted_nft_data = self._deserialize_nft_data(minted_nft_data_raw) 

                self.logger.info(f"Successfully minted NFT with ID: {minted_nft_data_raw.get('id')}")
                return {"Ok": minted_nft_data_raw} # Return the raw result structure
                
            except Exception as e:
                self.logger.error(f"Mint operation failed: {e}")
                raise CanisterError(f"Failed to mint NFT: {e}")
        
        return await self._retry_call_async(_mint_call)
    
    async def get_nft(self, nft_id: str) -> Optional[NFTData]:
        """
        Retrieve NFT metadata from canister.
        
        Args:
            nft_id: NFT identifier (string).
            
        Returns:
            NFTData object or None if not found.
            
        Raises:
            CanisterError: If retrieval fails.
        """
        self.logger.info(f"Retrieving NFT: {nft_id}")
        
        async def _get_call():
            try:
                # Motoko's getNFT function takes (id: Text) and returns (?NFTData)
                result = await self.agent.query_call(
                    canister_id=self.principal,
                    method_name="getNFT", # Changed to getNFT for Motoko
                    encode_args=[nft_id],
                    timeout=self.timeout
                )
                
                # The result from Motoko's query function for Option type is [data] or []
                if not result: # If result is empty list (null in Motoko Option)
                    self.logger.info(f"NFT {nft_id} not found")
                    return None
                
                nft_data_raw = result[0] # When #Ok, it's a list with one element
                metadata = self._deserialize_nft_data(nft_data_raw)
                
                self.logger.info(f"Successfully retrieved NFT: {nft_id}")
                return metadata
                
            except Exception as e:
                self.logger.error(f"Get NFT operation failed: {e}")
                raise CanisterError(f"Failed to get NFT {nft_id}: {e}")
        
        return await self._retry_call_async(_get_call)
    
    async def update_nft(self, nft_id: str, new_metadata: NFTMetadata) -> Dict[str, Any]:
        """
        Update NFT metadata on canister.
        
        Args:
            nft_id: NFT identifier (Text).
            new_metadata: NFTMetadata object containing all fields to update.
            
        Returns:
            UpdateResult (Dict with 'Ok': True/False or 'Err': message).
            
        Raises:
            CanisterError: If update fails.
        """
        self.logger.info(f"Updating NFT {nft_id} with new metadata.")
        
        async def _update_call():
            try:
                # Serialize the entire new_metadata object
                serialized_update_data = self._serialize_nft_metadata(new_metadata)
                
                # Motoko's updateNFT function takes (id: Text, updates: NFTMetadata)
                result = await self.agent.update_call(
                    canister_id=self.principal,
                    method_name="updateNFT",
                    encode_args=[nft_id, serialized_update_data],
                    timeout=self.timeout
                )
                
                # The result from Motoko's UpdateResult is { #Ok: Bool; #Err: Text; }
                if "Err" in result:
                    self.logger.error(f"Canister update failed for {nft_id}: {result['Err']}")
                    raise CanisterError(f"Update failed: {result['Err']}")
                
                self.logger.info(f"Successfully updated NFT: {nft_id}")
                return {"Ok": result["Ok"]} # Returns {"Ok": True} on success
                
            except Exception as e:
                self.logger.error(f"Update operation failed for {nft_id}: {e}")
                raise CanisterError(f"Failed to update NFT {nft_id}: {e}")
        
        return await self._retry_call_async(_update_call)
    
    async def list_all_nfts(self) -> List[NFTData]:
        """
        Lists all NFTs currently minted on the canister.
        
        Returns:
            A list of NFTData objects.
        """
        self.logger.info("Listing all NFTs from canister.")
        
        async def _list_all_call():
            try:
                # Motoko's listAllNFTs function takes no args and returns [NFTData]
                result = await self.agent.query_call(
                    canister_id=self.principal,
                    method_name="listAllNFTs",
                    encode_args=[],
                    timeout=self.timeout
                )
                
                if not isinstance(result, list):
                    raise CanisterError(f"Unexpected response type for listAllNFTs: {type(result)}")

                # Deserialize each NFTData
                all_nfts = [self._deserialize_nft_data(nft_raw) for nft_raw in result]
                
                self.logger.info(f"Successfully listed {len(all_nfts)} NFTs.")
                return all_nfts
                
            except Exception as e:
                self.logger.error(f"List all NFTs operation failed: {e}")
                raise CanisterError(f"Failed to list all NFTs: {e}")
        
        return await self._retry_call_async(_list_all_call)

    async def check_canister_status(self) -> Dict[str, Any]:
        """
        Check canister status and health
        
        Returns:
            Canister status information
            
        Raises:
            CanisterError: If status check fails
        """
        self.logger.info("Checking canister status")
        
        async def _check_status():
            try:
                # Call the Motoko canister's getCanisterStatus method
                result = await self.agent.query_call(
                    canister_id=self.principal,
                    method_name="getCanisterStatus",
                    encode_args=[],
                    timeout=self.timeout
                )
                
                if isinstance(result, list) and len(result) > 0:
                    status_info_raw = result[0] # Motoko query_call returns a list [status_record]
                    
                    status_info = {
                        "canister_id": self.canister_id,
                        "network": self.network.value,
                        "status": status_info_raw.get("status", "unknown"),
                        "memory_size": int(status_info_raw.get("memory_size", 0)), # Convert Nat to int
                        "cycles": int(status_info_raw.get("cycles", 0)),         # Convert Nat to int
                        "module_hash": status_info_raw.get("module_hash"),
                        "controllers": [str(p) for p in status_info_raw.get("controllers", [])], # Convert Principals to strings
                        "timestamp": int(time.time()) # Add a client-side timestamp for the check
                    }
                    self.logger.info("Canister status check completed successfully")
                    return status_info
                else:
                    raise CanisterError("Unexpected response format for getCanisterStatus")
                
            except Exception as e:
                self.logger.error(f"Status check failed: {e}")
                raise CanisterError(f"Failed to check canister status: {e}")
        
        return await self._retry_call_async(_check_status)
    
    def get_canister_info(self) -> Dict[str, Any]:
        """
        Get comprehensive canister information
        
        Returns:
            Dictionary with canister details
        """
        return {
            "canister_id": self.canister_id,
            "network": self.network.value,
            "endpoint": self.NETWORK_ENDPOINTS[self.network],
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "principal": str(self.principal)
        }


# Example usage and testing functions
def create_sample_nft_metadata() -> NFTMetadata:
    """Create sample NFT metadata for testing"""
    return NFTMetadata(
        name="Test NFT",
        description="A test NFT for canister client.",
        image_url="ipfs://testcid123",
        artist="AI_Artist",
        eventType="architecture",
        prompt="A futuristic building",
        mode="prompt",
        uniqueness_factors=UniquenessFactors(
            location_hash="loc123",
            timestamp_seed="time456",
            wallet_entropy="wallet789",
            biometric_opt_in=False
        ),
        genetic_traits=GeneticTraits(
            luminosity=0.5,
            architectural_complexity=0.6,
            ethereal_quality=0.7,
            evolution_speed=0.5,
            style_intensity=0.8,
            temporal_resonance=0.3 # Include all traits from Python dataclass
        ),
        scarcity_info=ScarcityInfo(
            combination="AI_Artist-architecture",
            total_limit=100,
            minted_count=0,
            rarity_score=0.1,
            price_multiplier=1.0
        ),
        attributes={
            "color_palette": "blue-green",
            "style": "minimalist"
        }
    )


if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Example usage
        try:
            # Initialize client for local development
            client = CanisterClient(
                canister_id="rdmx6-jaaaa-aaaaa-aaadq-cai", # Replace with your canister ID from .env
                network="local"
            )
            
            # Check canister status
            status = await client.check_canister_status()
            print(f"Canister Status: {status}")
            
            # Create sample NFT metadata
            sample_nft = create_sample_nft_metadata()
            
            # Mint NFT (example - requires an actual principal for the owner)
            # You'd typically get the owner principal from your frontend/authentication
            # For testing, you might use a dummy principal or your own test principal
            # from dfx identity get-principal
            dummy_owner_principal = Principal.from_text("2vxsx-fae") # Replace with a real Principal for testing mint
            
            # Mint NFT
            print("\n--- Testing Minting NFT ---")
            try:
                mint_result = await client.mint(dummy_owner_principal, sample_nft)
                print(f"Mint Result: {mint_result}")
                minted_nft_id = mint_result['Ok']['id'] if 'Ok' in mint_result else None
                if minted_nft_id:
                    print(f"Minted NFT ID: {minted_nft_id}")
            except CanisterError as e:
                print(f"Minting failed: {e.message}")
            except Exception as e:
                print(f"An unexpected error occurred during minting: {e}")

            # Get NFT
            if minted_nft_id:
                print(f"\n--- Testing Get NFT ({minted_nft_id}) ---")
                fetched_nft = await client.get_nft(minted_nft_id)
                if fetched_nft:
                    print(f"Fetched NFT: {fetched_nft.name}, Version: {fetched_nft.version}, Image: {fetched_nft.imageURI}")
                    # Update the fetched NFT's metadata for the update test
                    fetched_nft.version += 1
                    fetched_nft.image_url = "ipfs://newimagehash" + str(int(time.time()))
                    fetched_nft.genetic_traits.luminosity = 0.9 # Example trait change
                    fetched_nft.description = "Updated description after evolution."
                else:
                    print("Minted NFT not found for get test.")
                    
            # Update NFT (if a minted_nft_id was obtained)
            if minted_nft_id and fetched_nft:
                print(f"\n--- Testing Update NFT ({minted_nft_id}) ---")
                try:
                    update_result = await client.update_nft(minted_nft_id, fetched_nft) # Pass the dataclass
                    print(f"Update Result: {update_result}")
                    if update_result.get('Ok'):
                        print(f"Successfully updated NFT {minted_nft_id} on canister.")
                        # Verify update
                        re_fetched_nft = await client.get_nft(minted_nft_id)
                        if re_fetched_nft:
                            print(f"Re-fetched updated NFT: Version {re_fetched_nft.version}, Image: {re_fetched_nft.imageURI}")
                except CanisterError as e:
                    print(f"Updating failed: {e.message}")
                except Exception as e:
                    print(f"An unexpected error occurred during updating: {e}")
            else:
                print("Skipping NFT update test as no NFT was minted/found.")

            # List All NFTs
            print("\n--- Testing List All NFTs ---")
            all_nfts = await client.list_all_nfts()
            print(f"Total NFTs on canister: {len(all_nfts)}")
            if all_nfts:
                print("First NFT listed:", all_nfts[0].name, all_nfts[0].id)
            
            print("\nCanister client tests completed successfully!")
            
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())

