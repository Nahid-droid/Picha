// src/components/NFTPreviewCard.tsx
import React, { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge'; // Assuming this component is available
import { Button } from '@/components/ui/button'; // Assuming this component is available
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'; // Assuming these components are available
import { Image, Calendar, User, Globe, Zap, Star, Download, History, ChevronDown, ChevronUp } from 'lucide-react';

// Re-defining interfaces here for self-containment as per instructions
interface GeneticTraits {
  luminosity: number;
  architectural_complexity: number;
  ethereal_quality: number;
  evolution_speed: number;
  style_intensity: number;
  temporal_resonance: number;
}

interface ScarcityInfo {
  combination: string;
  total_limit: number;
  minted_count: number;
  rarity_score: number;
  price_multiplier: number;
  is_sold_out: boolean;
  remaining_slots?: number;
}

interface EvolutionEntry {
  version: string;
  timestamp: number; // Unix timestamp in seconds
  prompt_used: string;
  image_url: string;
  traits_changed: string[];
  event: string; // Added event to evolution history
}

interface NFTPreviewCardProps {
  imageURI?: string;
  artistStyle?: string;
  eventType?: string;
  version?: string;
  timestamp?: string; // This should be a string (locale date string)
  prompt?: string;
  geneticTraits?: GeneticTraits;
  scarcityInfo?: ScarcityInfo;
  evolutionHistory?: EvolutionEntry[];
  evolutionPeriodDays?: number;
  onUpdatePreview?: () => void;
  isAdvancedMode?: boolean;
}

const NFTPreviewCard: React.FC<NFTPreviewCardProps> = ({
  imageURI,
  artistStyle = 'Abstract Digital',
  eventType = 'Art Exhibition',
  version = 'v1.0',
  timestamp = new Date().toLocaleDateString(), // Default to current date string
  prompt,
  geneticTraits,
  scarcityInfo,
  evolutionHistory = [],
  evolutionPeriodDays,
  onUpdatePreview,
  isAdvancedMode = false,
}) => {
  const [animateTraits, setAnimateTraits] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    // Trigger animation when component mounts or geneticTraits change
    setTimeout(() => setAnimateTraits(true), 500);
  }, [geneticTraits]);

  const traitEntries = geneticTraits ? Object.entries(geneticTraits) : [];

  const handleDownload = () => {
    if (imageURI) {
      const link = document.createElement('a');
      link.href = imageURI;
      link.download = `nft-${artistStyle.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const getRarityColor = (score: number): string => {
    if (score >= 0.8) return 'text-[--hot-pink]'; // Legendary
    if (score >= 0.6) return 'text-[--neon-purple]'; // Epic
    if (score >= 0.4) return 'text-[--electric-blue]'; // Rare
    if (score >= 0.2) return 'text-[--warning]'; // Uncommon
    return 'text-[--muted-text]'; // Common
  };

  const getRarityLabel = (score: number): string => {
    if (score >= 0.8) return 'Legendary';
    if (score >= 0.6) return 'Epic';
    if (score >= 0.4) return 'Rare';
    if (score >= 0.2) return 'Uncommon';
    return 'Common';
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
      {/* NFT Preview */}
      <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-cyan-500/30 backdrop-blur-lg rounded-xl p-6">
        <h3 className="text-xl text-center text-cyan-400 mb-4 font-bold">Your Generated NFT</h3>
        <div className="relative aspect-square mb-4 bg-gradient-to-br from-cyan-400 to-pink-500 rounded-lg overflow-hidden">
          {scarcityInfo && (
            <div className="absolute top-3 left-3 z-10">
              <div className="flex items-center space-x-1 px-3 py-1 bg-black/80 text-cyan-400 border border-cyan-400/50 rounded-full text-sm">
                <Star className="w-4 h-4" />
                <span>{getRarityLabel(scarcityInfo.rarity_score)}</span>
              </div>
            </div>
          )}
          {imageURI ? (
            <img
              src={imageURI}
              alt="NFT Preview"
              className="w-full h-full object-cover rounded-lg shadow-md transition-transform duration-300 group-hover:scale-[1.02]"
              onError={(e) => {
                console.error('Image failed to load:', imageURI);
                e.currentTarget.style.display = 'none';
                const placeholderText = document.createElement('div');
                placeholderText.className = 'absolute inset-0 flex items-center justify-center text-[--muted-text] text-sm font-medium bg-[--background-secondary] rounded-lg';
                placeholderText.innerText = 'Image not available';
                e.currentTarget.parentElement?.appendChild(placeholderText);
              }}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <Image className="w-24 h-24 text-white/50" />
            </div>
          )}
        </div>
        {imageURI && (
          <button
            onClick={handleDownload}
            className="w-full bg-black/60 border border-cyan-500 text-cyan-400 hover:bg-cyan-500 hover:text-black transition-all duration-300 py-3 rounded-xl flex items-center justify-center"
          >
            <Download className="w-4 h-4 mr-2" />
            Download NFT
          </button>
        )}
      </div>

      {/* NFT Stats */}
      <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-cyan-500/30 backdrop-blur-lg rounded-xl p-6">
        <h3 className="text-lg text-center text-white mb-4 font-bold">"{prompt || `${artistStyle} style ${eventType}`}"</h3>
        <div className="space-y-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <User className="w-3 h-3 text-cyan-400" />
                <span>Artist</span>
              </div>
              <p className="font-medium text-white truncate">{artistStyle}</p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Globe className="w-3 h-3 text-cyan-400" />
                <span>Event</span>
              </div>
              <p className="font-medium text-white truncate">{eventType}</p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Calendar className="w-3 h-3 text-cyan-400" />
                <span>Created</span>
              </div>
              <p className="font-medium text-white">{timestamp}</p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Zap className="w-3 h-3 text-cyan-400" />
                <span>Version</span>
              </div>
              <p className="font-medium text-white">{version}</p>
            </div>
          </div>

          {/* Genetic Traits */}
          {traitEntries.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">Genetic Traits:</h4>
              <div className="grid grid-cols-2 gap-4">
                {traitEntries.map(([key, value]) => (
                  <div key={key} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400 capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs font-medium text-cyan-400">
                        {Math.round(value * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-black/50 rounded-full h-2 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-400 to-pink-500 rounded-full transition-all duration-1000 ease-out"
                        style={{
                          width: animateTraits ? `${value * 100}%` : '0%'
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evolution Info */}
          {evolutionPeriodDays !== undefined && (
            <div className="p-4 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-300">Evolution Interval:</span>
                <span className="text-sm font-medium text-cyan-400">Every {evolutionPeriodDays} days</span>
              </div>
              <p className="text-xs text-gray-400">
                This NFT will automatically evolve based on its owner's X activity.
              </p>
            </div>
          )}

          {/* Scarcity Info */}
          {scarcityInfo && (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-300">Availability:</span>
                <span className="text-sm font-medium text-cyan-400">
                  {scarcityInfo.remaining_slots || (scarcityInfo.total_limit - scarcityInfo.minted_count)} remaining
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-300">Price Multiplier:</span>
                <span className="text-sm font-medium text-yellow-400">{scarcityInfo.price_multiplier}x</span>
              </div>
            </div>
          )}

          {/* Evolution History Section */}
          {evolutionHistory && evolutionHistory.length > 1 && (
            <div className="border-t border-[--border] pt-6 space-y-4">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="w-full flex items-center justify-between text-base font-medium text-[--neon-purple] hover:text-[--electric-blue] transition-colors duration-200"
              >
                <span className="flex items-center gap-2">
                  <History className="w-5 h-5" />
                  View Evolution History ({evolutionHistory.length} versions)
                </span>
                {showHistory ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
              </button>

              {showHistory && (
                <div className="space-y-4 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                  {evolutionHistory.slice().reverse().map((entry, index) => (
                    <div key={index} className="glassmorphism rounded-lg p-4 bg-[--background-secondary]/50 border border-[--border]">
                      <div className="flex items-center justify-between text-xs text-[--muted-text] mb-2">
                        <span>Version: <span className="font-medium text-[--electric-blue]">{entry.version}</span></span>
                        <span>{new Date(entry.timestamp * 1000).toLocaleDateString()}</span>
                      </div>
                      <p className="text-sm font-medium mb-1 text-[--secondary-text]">Event: {entry.event.replace(/_/g, ' ').toUpperCase()}</p>
                      <p className="text-xs text-[--muted-text] italic mb-2">"{entry.prompt_used}"</p>

                      {entry.traits_changed && entry.traits_changed.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {entry.traits_changed.map(trait => (
                            <Badge key={trait} variant="outline" className="glassmorphism text-xs px-2 py-0.5 border-[--neon-purple]/30 text-[--neon-purple]">
                              {trait.replace(/_/g, ' ')}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* Show small thumbnail of image from that version */}
                      {entry.image_url && (
                          <img
                              src={`${import.meta.env.VITE_API_BASE_URL}${entry.image_url}`}
                              alt={`Version ${entry.version}`}
                              className="w-20 h-20 object-cover rounded-md mt-2 border border-[--border]"
                          />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {isAdvancedMode && onUpdatePreview && (
            <button
              onClick={onUpdatePreview}
              className="w-full px-6 py-3 rounded-lg text-base font-medium transition-all duration-300 transform hover:scale-[1.02]
                         bg-gradient-to-r from-[--electric-blue] to-[--neon-purple] text-[--primary-text] shadow-lg hover:shadow-xl"
            >
              Update Preview
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default NFTPreviewCard;
