import Time "mo:base/Time";
import Principal "mo:base/Principal";

module Types {
  public type GeneticTraits = {
    luminosity: Float;
    complexity: Float;
    ethereal_quality: Float;
    evolution_speed: Float;
    style_intensity: Float;
  };

  public type UniquenessFactors = {
    location_hash: Text;
    timestamp_seed: Text;
    wallet_entropy: Text;
    biometric_opt_in: Bool;
  };

  public type ScarcityInfo = {
    combination: Text; // "artist-eventType"
    total_limit: Nat;
    minted_count: Nat;
    rarity_score: Float;
    price_multiplier: Float;
  };

  public type VersionLog = {
    eventId: Text;
    timestamp: Time.Time;
    imageHash: Text;
    trigger: Text; // "initial_mint", "world_event", "micro_evolution"
    traits_changed: [Text];
  };

  public type NFT = {
    id: Nat;
    owner: Principal;
    artist: Text;
    eventType: Text;
    prompt: Text;
    mode: Text; // "selection" | "prompt"
    version: Nat;
    imageURI: Text;
    timestamp: Time.Time;
    history: [VersionLog];
    genetic_traits: GeneticTraits;
    uniqueness_factors: UniquenessFactors;
    scarcity_info: ScarcityInfo;
    last_evolution: Time.Time;
  };

  public type CombinationLimit = {
    combination: Text;
    limit: Nat;
    current_count: Nat;
    waitlist: [Principal]; // Changed from Text to Principal
  };

  public type MintResult = {
    #Ok: Nat;
    #Err: Text;
  };

  public type TransferResult = {
    #Ok: ();
    #Err: Text;
  };

  public type CombinationStats = {
    available: Nat;
    total: Nat;
    waitlist_size: Nat;
    price_multiplier: Float;
  };
}
