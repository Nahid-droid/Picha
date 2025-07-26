import hashlib
import random
from typing import Optional
from models.data_models import GenerationMode, EventType, UniquenessFactors, GeneticTraits # Import GeneticTraits

class EnhancedPromptGenerator:
    """Enhanced prompt generation with personal context integration"""
    
    def __init__(self):
        self.artists = {
            "Da Vinci": {
                "style_modifiers": ["Renaissance precision", "anatomical detail", "sfumato technique"],
                "signature_elements": ["flying machines", "architectural sketches", "human studies"]
            },
            "Van Gogh": {
                "style_modifiers": ["swirling brushstrokes", "vibrant colors", "emotional intensity"],
                "signature_elements": ["starry skies", "cypress trees", "wheat fields"]
            },
            "Picasso": {
                "style_modifiers": ["cubist fragmentation", "geometric forms", "multiple perspectives"],
                "signature_elements": ["abstract faces", "bull imagery", "guitar motifs"]
            },
            "Monet": {
                "style_modifiers": ["impressionist light", "color harmony", "atmospheric effects"],
                "signature_elements": ["water lilies", "cathedral series", "garden scenes"]
            },
            "Dali": {
                "style_modifiers": ["surrealist imagery", "melting forms", "dream-like quality"],
                "signature_elements": ["melting clocks", "elephants on stilts", "desert landscapes"]
            }
        }
        
        self.event_contexts = {
            EventType.ARCHITECTURE: {
                "base_prompts": ["floating city", "crystal palace", "organic building", "sky fortress"],
                "modifiers": ["with impossible geometry", "defying gravity", "made of light"]
            },
            EventType.NATURE: {
                "base_prompts": ["enchanted forest", "mountain peak", "ocean depths", "desert oasis"],
                "modifiers": ["with bioluminescent elements", "in perpetual twilight", "with crystalline formations"]
            },
            EventType.PORTRAIT: {
                "base_prompts": ["ethereal figure", "cosmic being", "time traveler", "dimensional guardian"],
                "modifiers": ["with glowing eyes", "surrounded by energy", "partially transparent"]
            },
            EventType.ABSTRACT: {
                "base_prompts": ["geometric harmony", "color symphony", "form in motion", "dimensional rift"],
                "modifiers": ["with flowing particles", "in quantum flux", "with temporal distortions"]
            },
            EventType.COSMIC: {
                "base_prompts": ["nebula formation", "galactic center", "black hole", "stellar nursery"],
                "modifiers": ["with impossible colors", "bending spacetime", "with cosmic consciousness"]
            },
            EventType.URBAN: {
                "base_prompts": ["neon cityscape", "industrial complex", "street art", "urban jungle"],
                "modifiers": ["with cyberpunk elements", "in rain-soaked streets", "with holographic displays"]
            },
            EventType.FANTASY: {
                "base_prompts": ["magical realm", "dragon's lair", "enchanted castle", "fairy kingdom"],
                "modifiers": ["with mystical creatures", "glowing with magic", "in eternal twilight"]
            },
            EventType.HISTORICAL: {
                "base_prompts": ["ancient temple", "medieval castle", "renaissance palace", "baroque cathedral"],
                "modifiers": ["with historical accuracy", "in golden lighting", "with period details"]
            }
        }
    
    def generate_prompt(self, mode: GenerationMode, artist: str, event_type: EventType, 
                       user_prompt: Optional[str], uniqueness_factors: UniquenessFactors, 
                       genetic_traits: GeneticTraits) -> str: # Added genetic_traits
        """Generate AI prompt with personal context integration"""
        
        if mode == GenerationMode.SELECTION:
            return self._generate_selection_prompt(artist, event_type, uniqueness_factors, genetic_traits) # Pass genetic_traits
        elif mode == GenerationMode.PROMPT:
            return self._generate_custom_prompt(user_prompt, artist, uniqueness_factors, genetic_traits) # Pass genetic_traits
        else:
            raise ValueError(f"Invalid generation mode: {mode}")
    
    def _generate_selection_prompt(self, artist: str, event_type: EventType, 
                                 uniqueness_factors: UniquenessFactors, 
                                 genetic_traits: GeneticTraits) -> str: # Added genetic_traits
        """Generate selection mode prompt"""
        if isinstance(uniqueness_factors, dict):
        # Convert dictionary to UniquenessFactors object
            uniqueness_factors = UniquenessFactors(**uniqueness_factors)
        elif isinstance(uniqueness_factors, str):
        # If it's a string, try to parse it as JSON
            import json
            try:
                factors_dict = json.loads(uniqueness_factors)
                uniqueness_factors = UniquenessFactors(**factors_dict)
            except (json.JSONDecodeError, TypeError) as e:
            # Fallback to default values if parsing fails
                uniqueness_factors = UniquenessFactors(
                location_hash="default_hash",
                timestamp_seed="0",
                wallet_entropy="default_entropy",
                wallet_principal="default_principal"
            )
        elif not isinstance(uniqueness_factors, UniquenessFactors):
        # Fallback for any other unexpected type
            uniqueness_factors = UniquenessFactors(
            location_hash="default_hash",
            timestamp_seed="0", 
            wallet_entropy="default_entropy",
            wallet_principal="default_principal"
        )
        event_config = self.event_contexts[event_type]
        event_hash = int(hashlib.sha256(uniqueness_factors.location_hash.encode()).hexdigest()[:8], 16)
        base_event = event_config["base_prompts"][event_hash % len(event_config["base_prompts"])]
        
        artist_config = self.artists.get(artist, {"style_modifiers": ["artistic style"]})
        style_hash = int(hashlib.sha256(uniqueness_factors.wallet_entropy.encode()).hexdigest()[:8], 16)
        style_modifier = artist_config["style_modifiers"][style_hash % len(artist_config["style_modifiers"])]
        
        unique_context = self._generate_unique_context(uniqueness_factors, event_type)
        genetic_context = self._generate_genetic_traits_context(genetic_traits) # Generate genetic traits context
        
        prompt = f"{base_event} in {artist} style with {style_modifier}, {unique_context}, {genetic_context}" # Added genetic_context
        
        return prompt
    
    def _generate_custom_prompt(self, user_prompt: str, artist: str, 
                              uniqueness_factors: UniquenessFactors, 
                              genetic_traits: GeneticTraits) -> str: # Added genetic_traits
        """Generate prompt mode: User prompt + personal data injection"""
        
        if not user_prompt:
            raise ValueError("User prompt required for prompt mode")
        
        if isinstance(uniqueness_factors, dict):
        # Convert dictionary to UniquenessFactors object
            uniqueness_factors = UniquenessFactors(**uniqueness_factors)
        elif isinstance(uniqueness_factors, str):
        # If it's a string, try to parse it as JSON
            import json
            try:
                factors_dict = json.loads(uniqueness_factors)
                uniqueness_factors = UniquenessFactors(**factors_dict)
            except (json.JSONDecodeError, TypeError) as e:
            # Fallback to default values if parsing fails
                uniqueness_factors = UniquenessFactors(
                location_hash="default_hash",
                timestamp_seed="0",
                wallet_entropy="default_entropy", 
                wallet_principal="default_principal"
            )
        elif not isinstance(uniqueness_factors, UniquenessFactors):
        # Fallback for any other unexpected type
            uniqueness_factors = UniquenessFactors(
            location_hash="default_hash",
            timestamp_seed="0",
            wallet_entropy="default_entropy",
            wallet_principal="default_principal"
        )
        personal_context = self._inject_personal_context(uniqueness_factors, artist)
        genetic_context = self._generate_genetic_traits_context(genetic_traits) # Generate genetic traits context
        
        enhanced_prompt = f"{user_prompt}, {personal_context}, {genetic_context}" # Added genetic_context
        
        return enhanced_prompt
    
    def _generate_unique_context(self, factors: UniquenessFactors, event_type: EventType) -> str:
        """Generate unique context from location, timestamp, wallet signature"""
        
        location_hash = int(factors.location_hash[:8], 16)
        location_contexts = [
            "at the intersection of dimensions",
            "where time flows differently",
            "in a pocket of altered reality",
            "at the convergence of energies",
            "in a place of ancient power"
        ]
        location_context = location_contexts[location_hash % len(location_contexts)]
        
        timestamp = int(factors.timestamp_seed)
        hour = (timestamp % 86400) // 3600
        
        if 5 <= hour < 12:
            time_context = "bathed in dawn light"
        elif 12 <= hour < 17:
            time_context = "under the midday sun"
        elif 17 <= hour < 20:
            time_context = "in golden hour glow"
        elif 20 <= hour < 24:
            time_context = "under twilight skies"
        else:
            time_context = "in the depth of night"
        
        wallet_hash = hashlib.sha256(factors.wallet_entropy.encode()).hexdigest()
        signature_contexts = [
            "marked by cosmic signature",
            "sealed with dimensional energy",
            "infused with personal essence",
            "bonded to creator's spirit",
            "attuned to owner's frequency"
        ]
        wallet_context = signature_contexts[int(wallet_hash[:8], 16) % len(signature_contexts)]
        
        return f"{location_context}, {time_context}, {wallet_context}"
    
    def _inject_personal_context(self, factors: UniquenessFactors, artist: str) -> str:
        """Inject personal data into prompt"""
        
        location_context = "infused with geographical essence"
        temporal_context = "anchored in this moment of creation"
        
        artist_config = self.artists.get(artist, {"signature_elements": ["artistic elements"]})
        # Corrected: Hash wallet_entropy before converting to int to ensure valid hexadecimal
        wallet_entropy_hash = hashlib.sha256(factors.wallet_entropy.encode()).hexdigest()
        element_hash = int(wallet_entropy_hash[:8], 16) # Use a portion of the hex hash
        
        signature_element = artist_config["signature_elements"][element_hash % len(artist_config["signature_elements"])]
        artist_context = f"featuring {signature_element}"
        
        contexts = [location_context, temporal_context, artist_context]
        
        return ", ".join(contexts)

    def _generate_genetic_traits_context(self, genetic_traits: GeneticTraits) -> str:
        """Generate descriptive phrases from genetic traits for the prompt."""
        trait_phrases = []

        # Assuming GeneticTraits has attributes like luminosity, architectural_complexity, etc.
        # Adjust these conditions and phrases based on the actual meaning and desired impact of your traits.
        if genetic_traits.luminosity > 0.75:
            trait_phrases.append("vibrantly luminous")
        elif genetic_traits.luminosity < 0.25:
            trait_phrases.append("subtly shadowed")

        if genetic_traits.architectural_complexity > 0.75:
            trait_phrases.append("with intricate architectural forms")
        elif genetic_traits.architectural_complexity < 0.25:
            trait_phrases.append("with minimalist structures")

        if genetic_traits.ethereal_quality > 0.75:
            trait_phrases.append("possessing an otherworldly aura")
        elif genetic_traits.ethereal_quality < 0.25:
            trait_phrases.append("grounded and tangible")

        if genetic_traits.evolution_speed > 0.75:
            trait_phrases.append("dynamic and evolving rapidly")
        elif genetic_traits.evolution_speed < 0.25:
            trait_phrases.append("stable and unchanging")

        if genetic_traits.style_intensity > 0.75:
            trait_phrases.append("with intense artistic expression")
        elif genetic_traits.style_intensity < 0.25:
            trait_phrases.append("with gentle and soft styling")

        if genetic_traits.temporal_resonance > 0.75:
            trait_phrases.append("echoing through time")
        elif genetic_traits.temporal_resonance < 0.25:
            trait_phrases.append("rooted in the present moment")
        
        if trait_phrases:
            return " and ".join(trait_phrases)
        return ""