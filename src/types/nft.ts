// src/types/nft.ts

export interface GeneticTraits {
  luminosity: number;
  architectural_complexity: number;
  ethereal_quality: number;
  evolution_speed: number;
  style_intensity: number;
  temporal_resonance: number;
}

export interface ScarcityInfo {
  combination: string;
  total_limit: number;
  minted_count: number;
  rarity_score: number;
  price_multiplier: number;
  // Ensure these computed properties from the backend are also explicitly defined here
  total_supply?: number;
  current_mint?: number;
  remaining_slots?: number;
  rarity_tier?: string;
  is_legendary?: boolean;
  is_sold_out?: boolean; // <<< ADDED THIS LINE
}

// New interface for individual evolution entries
export interface EvolutionEntry {
  version: number;
  timestamp: string; // ISO format string
  event: string;
  image_url: string;
  genetic_traits_at_evolution: GeneticTraits;
  prompt_used: string;
  social_media_impact?: any; // Optional: Store processed social media metrics
  traits_changed?: string[]; // Optional: List of trait names that changed
}

export interface NFTData {
  id: string;
  image_uri: string;
  artist: string;
  event_type: string;
  version: number;
  timestamp: number; // Unix timestamp
  genetic_traits: GeneticTraits;
  scarcity_info: ScarcityInfo;
  prompt: string;
  evolution_history: EvolutionEntry[]; // Array of evolution entries
  evolution_period_days: number; // The interval for automatic evolution
}
