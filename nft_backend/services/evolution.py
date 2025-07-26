import hashlib
import random
from typing import List, Dict, Any, Optional
from models.data_models import GeneticTraits, UniquenessFactors

class EvolutionaryAlgorithm:
    """Genetic trait system with micro-evolution parameters and social media impact."""
    
    def __init__(self):
        self.trait_bounds = {
            "luminosity": (0.0, 1.0),
            "architectural_complexity": (0.0, 1.0),
            "ethereal_quality": (0.0, 1.0),
            "evolution_speed": (0.1, 0.9),
            "style_intensity": (0.0, 1.0),
            "temporal_resonance": (0.0, 1.0)
        }
        # Define parameters for social media influence
        self.social_impact_factors = {
            "positive_sentiment_boost_ethereal": 0.05, # How much positive sentiment boosts ethereal_quality
            "negative_sentiment_reduce_luminosity": 0.03, # How much negative sentiment reduces luminosity
            "high_engagement_boost_complexity": 0.04, # How much high engagement boosts complexity
            "tweet_frequency_boost_speed": 0.02, # How much frequent tweets boost evolution_speed
            "keyword_match_boost_intensity": 0.03, # Impact of specific keywords on style_intensity
            "max_trait_change_per_evolution": 0.1 # Max change for any single trait per evolution cycle
        }
    
    def generate_initial_traits(self, uniqueness_factors: UniquenessFactors) -> GeneticTraits:
        """Generate initial genetic traits from personal data"""
        
        combined_data = (
            uniqueness_factors.location_hash + 
            uniqueness_factors.timestamp_seed + 
            uniqueness_factors.wallet_entropy +
            (uniqueness_factors.biometric_hash or "")
        )
        
        trait_hash = hashlib.sha256(combined_data.encode()).hexdigest()
        
        traits = {}
        trait_names = list(self.trait_bounds.keys())
        
        for i, trait_name in enumerate(trait_names):
            segment = trait_hash[i*8:(i+1)*8]
            # Ensure the segment has enough characters to convert to an int
            if not segment:
                normalized_value = 0.5 # Default to middle if hash segment is empty
            else:
                normalized_value = int(segment, 16) / (16**len(segment) - 1)
            
            bounds = self.trait_bounds[trait_name]
            trait_value = bounds[0] + normalized_value * (bounds[1] - bounds[0])
            
            traits[trait_name] = trait_value
        
        return GeneticTraits(**traits)

    def evolve_traits(self, current_traits: GeneticTraits, evolution_strength: float = 0.1) -> GeneticTraits:
        """
        Evolve an NFT's traits based on a general evolution strength.
        This is a simpler evolution, without social media influence.
        """
        new_traits = current_traits.to_dict()

        for trait_name, current_value in new_traits.items():
            if trait_name in self.trait_bounds:
                min_val, max_val = self.trait_bounds[trait_name]
                # Introduce a small random change based on evolution strength
                change = (random.random() - 0.5) * evolution_strength * 2 # Change can be positive or negative
                new_value = current_value + change
                new_traits[trait_name] = max(min_val, min(max_val, new_value))
        
        return GeneticTraits(**new_traits)

    def evolve_traits_with_social_data(self, 
                                        current_traits: GeneticTraits, 
                                        social_media_metrics: List[Dict[str, Any]],
                                        evolution_interval_days: int) -> GeneticTraits:
        """
        Evolves NFT traits based on social media activity over a given period.

        Args:
            current_traits (GeneticTraits): The current genetic traits of the NFT.
            social_media_metrics (List[Dict[str, Any]]): A list of recent social media
                                                          metrics (e.g., fetched tweets, sentiment scores).
            evolution_interval_days (int): The duration over which social media activity
                                           is considered for evolution (e.g., 30, 90, 180 days).

        Returns:
            GeneticTraits: The new, evolved genetic traits.
        """
        new_traits_data = current_traits.to_dict()
        
        # Initialize impact accumulators
        total_sentiment_score = 0.0
        sentiment_count = 0
        total_engagement = 0 # Sum of likes, retweets, replies, quotes, impressions
        tweet_frequency = 0
        keyword_matches = {} # e.g., {'AI': 5, 'NFT': 10}

        # Define a window for recent activity if needed (e.g., last 30 days)
        # For simplicity, we assume social_media_metrics are already filtered for the relevant period
        # If not, you'd filter them here based on `timestamp` and `evolution_interval_days`
        
        for metric in social_media_metrics:
            metric_type = metric.get('metric_type')
            metric_value = metric.get('metric_value')
            details = metric.get('details', {})

            if metric_type == 'tweet_sentiment' and isinstance(metric_value, float):
                total_sentiment_score += metric_value # Assuming -1.0 (negative) to 1.0 (positive)
                sentiment_count += 1
            elif metric_type == 'tweet_engagement' and isinstance(metric_value, float):
                total_engagement += metric_value
            elif metric_type == 'tweet_frequency' and isinstance(metric_value, float):
                tweet_frequency = metric_value # Assuming this is already aggregated frequency (e.g., tweets per day)
            elif metric_type == 'keyword_match' and isinstance(details, dict):
                for keyword, count in details.items():
                    keyword_matches[keyword] = keyword_matches.get(keyword, 0) + count

        # Calculate average sentiment (0.0 to 1.0 from -1.0 to 1.0)
        avg_sentiment = (total_sentiment_score / sentiment_count + 1.0) / 2.0 if sentiment_count > 0 else 0.5
        
        # Normalize engagement (this will depend on typical engagement numbers)
        # For simplicity, let's normalize by a hypothetical max engagement value
        # In a real system, you'd use statistical methods or dynamic normalization
        max_possible_engagement_in_interval = 10000 # Example: if 10 tweets, each with 1000 total engagement
        normalized_engagement = min(1.0, total_engagement / max_possible_engagement_in_interval)

        # Normalize tweet frequency (e.g., 0-100 tweets per day, normalize to 0-1)
        max_tweet_frequency = 50 # Example: 50 tweets per day is high frequency
        normalized_frequency = min(1.0, tweet_frequency / max_tweet_frequency)
        
        # Calculate keyword impact (example: sum of all keyword counts)
        total_keyword_matches = sum(keyword_matches.values())
        max_keyword_matches = 20 # Example: 20 matches is high
        normalized_keyword_impact = min(1.0, total_keyword_matches / max_keyword_matches)

        # --- Apply social media impact to traits ---
        
        # Ethereal Quality: Boosted by positive sentiment
        ethereal_boost = (avg_sentiment - 0.5) * self.social_impact_factors["positive_sentiment_boost_ethereal"] * 2 # Scale from -0.5 to 0.5 then apply boost
        new_traits_data['ethereal_quality'] += ethereal_boost
        
        # Luminosity: Reduced by negative sentiment (low average sentiment)
        luminosity_reduction = (0.5 - avg_sentiment) * self.social_impact_factors["negative_sentiment_reduce_luminosity"] * 2
        new_traits_data['luminosity'] -= luminosity_reduction

        # Architectural Complexity: Boosted by high engagement
        complexity_boost = normalized_engagement * self.social_impact_factors["high_engagement_boost_complexity"]
        new_traits_data['architectural_complexity'] += complexity_boost

        # Evolution Speed: Boosted by tweet frequency
        speed_boost = normalized_frequency * self.social_impact_factors["tweet_frequency_boost_speed"]
        new_traits_data['evolution_speed'] += speed_boost

        # Style Intensity: Influenced by keyword matches
        intensity_boost = normalized_keyword_impact * self.social_impact_factors["keyword_match_boost_intensity"]
        new_traits_data['style_intensity'] += intensity_boost

        # Ensure traits remain within their bounds and apply max change limit
        for trait_name, current_value in current_traits.to_dict().items():
            if trait_name in self.trait_bounds:
                min_val, max_val = self.trait_bounds[trait_name]
                
                # Apply max trait change limit per evolution cycle
                change = new_traits_data[trait_name] - current_value
                if abs(change) > self.social_impact_factors["max_trait_change_per_evolution"]:
                    change = (self.social_impact_factors["max_trait_change_per_evolution"] if change > 0 else -self.social_impact_factors["max_trait_change_per_evolution"])
                    new_traits_data[trait_name] = current_value + change

                # Clamp values to their bounds
                new_traits_data[trait_name] = max(min_val, min(max_val, new_traits_data[trait_name]))

        return GeneticTraits(**new_traits_data)

    def generate_next_generation(self, parent_traits: List[GeneticTraits]) -> List[GeneticTraits]:
        """
        Combines traits from multiple parent NFTs to generate offspring traits.
        (This is your existing genetic algorithm logic)
        """
        if len(parent_traits) < 2:
            raise ValueError("At least two parent NFTs are required for breeding.")

        # Simple average for demonstration; complex algorithms would involve crossover, mutation.
        avg_traits = {}
        for trait_name in self.trait_bounds.keys():
            total = sum(getattr(p, trait_name) for p in parent_traits)
            avg_traits[trait_name] = total / len(parent_traits)

        # Introduce some mutation for variety
        mutated_traits = {}
        mutation_strength = 0.05 # small mutation
        for trait_name, avg_value in avg_traits.items():
            min_val, max_val = self.trait_bounds[trait_name]
            mutation = (random.random() - 0.5) * mutation_strength
            mutated_value = avg_value + mutation
            mutated_traits[trait_name] = max(min_val, min(max_val, mutated_value))

        return [GeneticTraits(**mutated_traits)] # Returns a list of offspring, for simplicity just one here
