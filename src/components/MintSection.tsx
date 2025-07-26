import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast'; // Assuming this hook is available
import MintButton from './MintButton';
import { Zap, Clock } from 'lucide-react';
import axios from 'axios';

// Define the interfaces for GeneticTraits and ScarcityInfo
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
  is_sold_out: boolean; // Added for explicit sold out status
  remaining_slots?: number; // Added for convenience
}

interface NFTData {
  id: string;
  image_uri: string;
  artist: string;
  event_type: string;
  version: number;
  timestamp: number;
  genetic_traits: GeneticTraits; // Use the defined interface
  scarcity_info: ScarcityInfo;   // Use the defined interface
  prompt: string;
  evolution_history: any[]; // Simplified for this component, full type in Index.tsx
  evolution_period_days: number; // Added evolution period
}

interface MintSectionProps {
  mode: 'basic' | 'advanced';
  artists: string[];
  events: string[];
  onNFTCreated: (nft: NFTData | null) => void;
  selectedArtist: string;
  setSelectedArtist: (artist: string) => void;
  selectedEvent: string;
  setSelectedEvent: (event: string) => void;
  customPrompt: string;
  setCustomPrompt: (prompt: string) => void;
  evolutionPeriod: number;
  setEvolutionPeriod: (period: number) => void;
  isLoading: boolean;
  onGenerateNFT: () => void; // Callback for generating NFT
  walletConnected: boolean; // Prop to indicate wallet connection status
  getScarcityForCombination: (artist: string, eventType: string) => ScarcityInfo | undefined;
}

const MintSection: React.FC<MintSectionProps> = ({
  mode,
  artists,
  events,
  onNFTCreated,
  selectedArtist,
  setSelectedArtist,
  selectedEvent,
  setSelectedEvent,
  customPrompt,
  setCustomPrompt,
  evolutionPeriod,
  setEvolutionPeriod,
  isLoading,
  onGenerateNFT,
  walletConnected,
  getScarcityForCombination,
}) => {
  const { toast } = useToast(); // Assuming useToast is available

  const isAdvancedMode = mode === 'advanced';

  const formatDisplayValue = (value: string) => {
    return value
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const intervalOptions = [
    { value: '7', label: 'Weekly (7 days)' },
    { value: '15', label: 'Bi-Weekly (15 days)' },
    { value: '30', label: 'Monthly (30 days)' },
    { value: '90', label: 'Quarterly (90 days)' },
    { value: '180', label: 'Semi-Annually (180 days)' },
    { value: '365', label: 'Annually (365 days)' },
  ];

  // This component no longer handles the direct minting logic,
  // but rather triggers the `onGenerateNFT` callback passed from `Index.tsx`.
  // The internal `handleMint` logic is now `onGenerateNFT`.

  return (
    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-cyan-500/30 backdrop-blur-lg rounded-xl p-6 mb-12">
      <div className="text-center space-y-4 mb-6">
        <div className="inline-flex items-center space-x-2 px-4 py-2 bg-cyan-500/20 border border-cyan-500/50 rounded-full">
          <Clock className="w-4 h-4 text-cyan-400" /> {/* Changed to Clock for 'Real-time' */}
          <span className="text-sm text-cyan-400">Real-time updates active.</span>
        </div>
        
        <div className="flex justify-center">
          <div className="flex bg-black/30 rounded-xl overflow-hidden">
            <button
              onClick={() => { /* Logic to set mode in parent */ }} // Parent handles mode change
              className={`px-6 py-3 text-sm font-semibold transition-all duration-200 ${
                mode === 'basic'
                  ? 'bg-gradient-to-r from-cyan-500 to-pink-500 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Basic Mode
            </button>
            <button
              onClick={() => { /* Logic to set mode in parent */ }} // Parent handles mode change
              className={`px-6 py-3 text-sm font-semibold transition-all duration-200 ${
                mode === 'advanced'
                  ? 'bg-gradient-to-r from-cyan-500 to-pink-500 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Advanced Mode
            </button>
          </div>
        </div>
      </div>
      
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {isAdvancedMode ? (
            <>
              {/* No longer using separate advancedArtist/Event states in MintSection,
                  Index.tsx will handle the prompt directly. */}
              {/* This part of the UI is now handled by the custom prompt textarea in Index.tsx */}
            </>
          ) : (
            <>
              {/* Artist Dropdown */}
              <div className="space-y-2">
                <Label htmlFor="basic-artist" className="text-sm font-semibold text-[--secondary-text]">Artist</Label>
                <select
                  id="basic-artist"
                  value={selectedArtist}
                  onChange={(e) => setSelectedArtist(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg bg-black/40 border border-cyan-500/30 text-white
                             focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={isLoading}
                >
                  <option value="" className="bg-[--background-secondary] text-gray-400">Select Artist</option>
                  {artists.map(artist => (
                    <option key={artist} value={artist} className="bg-[--background-secondary] text-[--primary-text]">{artist}</option>
                  ))}
                </select>
              </div>

              {/* Event Dropdown */}
              <div className="space-y-2">
                <Label htmlFor="basic-event" className="text-sm font-semibold text-[--secondary-text]">Event Type</Label>
                <select
                  id="basic-event"
                  value={selectedEvent}
                  onChange={(e) => setSelectedEvent(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg bg-black/40 border border-cyan-500/30 text-white
                             focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={isLoading}
                >
                  <option value="" className="bg-[--background-secondary] text-gray-400">Select Event</option>
                  {events.map(event => {
                    const comboScarcityInfo = getScarcityForCombination(selectedArtist, event);
                    const isSoldOut = comboScarcityInfo?.is_sold_out || false;
                    return (
                      <option key={event} value={event} disabled={isSoldOut} className="bg-[--background-secondary] text-[--primary-text]">
                        {formatDisplayValue(event)} {isSoldOut && '(Sold Out)'}
                      </option>
                    );
                  })}
                </select>
              </div>
            </>
          )}
          {isAdvancedMode && (
            <div className="col-span-full space-y-2">
              <Label htmlFor="custom-prompt" className="text-sm font-semibold text-[--secondary-text]">
                Custom Prompt
              </Label>
              <Textarea
                id="custom-prompt"
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Describe your NFT... (e.g., 'A cyberpunk cityscape with neon lights and flying cars')"
                className="min-h-[120px] px-4 py-3 rounded-lg bg-black/40 border border-cyan-500/30 text-white
                           focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isLoading}
                maxLength={500}
              />
              <div className="text-sm text-gray-400 text-right mt-1">
                {customPrompt.length}/500 characters
              </div>
            </div>
          )}
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="evolution-interval" className="text-sm font-semibold text-[--secondary-text]">NFT Evolution Interval</Label>
          <select
            id="evolution-interval"
            value={String(evolutionPeriod)}
            onChange={(e) => setEvolutionPeriod(parseInt(e.target.value))}
            className="w-full px-4 py-3 rounded-lg bg-black/40 border border-cyan-500/30 text-white
                       focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading}
          >
            {intervalOptions.map(option => (
              <option key={option.value} value={option.value} className="bg-[--background-secondary] text-[--primary-text]">
                {option.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-2">
            Your NFT will automatically evolve based on your social media activity every {evolutionPeriod} days.
          </p>
        </div>

        <MintButton
          isLoading={isLoading}
          onMint={onGenerateNFT} // Call the passed-in generate function
          disabled={
            !walletConnected ||
            isLoading ||
            (mode === 'basic' && (!selectedArtist || !selectedEvent || (getScarcityForCombination(selectedArtist, selectedEvent)?.is_sold_out ?? true))) ||
            (mode === 'advanced' && !customPrompt.trim())
          }
        />

        {/* Selection/Prompt Preview */}
        {(isAdvancedMode ? (customPrompt.trim()) : (selectedArtist || selectedEvent)) && (
          <div className="glassmorphism p-5 rounded-lg border border-[--nft-primary]/20 shadow-inner">
            <p className="text-sm text-[--muted-text] mb-3">
              {isAdvancedMode ? 'Current Prompt:' : 'Current Selection:'}
            </p>
            {isAdvancedMode ? (
              <div className="space-y-3">
                {customPrompt.trim() && (
                  <p className="text-sm text-[--secondary-text] italic border-l-2 border-[--neon-purple] pl-3">"{customPrompt}"</p>
                )}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {selectedArtist && (
                  <Badge variant="outline" className="glassmorphism border-[--nft-primary]/30 text-[--electric-blue] px-3 py-1 text-sm">
                    {formatDisplayValue(selectedArtist)}
                  </Badge>
                )}
                {selectedEvent && (
                  <Badge variant="outline" className="glassmorphism border-[--nft-primary]/30 text-[--electric-blue] px-3 py-1 text-sm">
                    {formatDisplayValue(selectedEvent)}
                  </Badge>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MintSection;
