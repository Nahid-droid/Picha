// src/pages/Index.tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import WalletConnector from '@/components/WalletConnector'; // Ensure this import points to your WalletConnector
import ScarcityIndicator from '@/components/ScarcityIndicator'; // Import ScarcityIndicator
import { Wallet, Twitter, Star, Download, Zap, Palette, Building, User, Globe, CheckCircle, Wifi, WifiOff, XIcon, Loader2, AlertCircle, RefreshCw, Image, History, ChevronDown, ChevronUp, Coins, Sparkles, Calendar, Settings } from 'lucide-react';
import axios, { AxiosError } from 'axios';
import { toast } from 'sonner';
import io from 'socket.io-client';
import { Socket } from 'socket.io-client';
import { CSSProperties } from "react";

// Define the interfaces for GeneticTraits and ScarcityInfo (moved here for self-containment)
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

interface EvolutionEntry {
  version: string;
  timestamp: number;
  prompt_used: string;
  image_url: string;
  traits_changed: string[];
  event: string; // Added event to evolution history
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
  evolution_history: EvolutionEntry[];
  evolution_period_days: number;
}

// Wallet type definitions (copied from WalletConnector for self-containment)
interface WalletInfo {
  principal: string;
  accountId: string;
  isConnected: boolean;
  balance?: number;
}

// Interface for combination scarcity data received from /api/combinations
interface CombinationScarcityAPI {
  artist: string;
  event_type: string;
  is_available: boolean;
  scarcity_info: ScarcityInfo;
  waitlist_count: number;
  estimated_availability: string;
  price_multiplier: number;
}

interface APIError {
  message: string;
  status?: number;
  code?: string;
}

interface LoadingStates {
  initialData: boolean;
  nftGeneration: boolean;
  combinations: boolean;
  xAuth: boolean;
  wallet: boolean; // Added wallet loading state
}

// Type for API error responses
interface APIErrorResponse {
  error?: string;
  message?: string;
}

// WebSocket message interfaces
interface ScarcityUpdateMessage {
  artist: string;
  event_type: string;
  remaining_slots: number;
  total_supply: number;
  is_available: boolean;
  timestamp: number;
}

interface EvolutionUpdateMessage {
  nft_id: string;
  new_version: number;
  new_image_url: string;
  new_traits: GeneticTraits;
  message: string;
  timestamp: number;
}

interface NewMintMessage {
  nft_id: string;
  name: string;
  image_url: string;
  artist: string;
  event_type: string;
  owner_address: string;
  canister_id: string;
  timestamp: number;
}

// Custom Logo Component
const PichaLogo = () => {
  const logoStyles: { [key: string]: CSSProperties } = { // Explicitly type logoStyles as an object of CSSProperties
    logoContainer: {
      position: 'relative', // Now correctly typed
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '280px',
      height: '120px',
      transformStyle: 'preserve-3d',
      perspective: '1000px',
      margin: '0 auto 1rem',
    },
    logoText: {
      fontSize: '3.5rem',
      fontWeight: 900,
      color: '#fff',
      position: 'relative', // Now correctly typed
      zIndex: 10,
      letterSpacing: '2px',
      fontFamily: 'Orbitron, sans-serif',
      textShadow: `
        0 0 5px var(--cyber-cyan, #00f2ff),
        0 0 10px var(--cyber-cyan, #00f2ff),
        0 0 20px var(--cyber-pink, #ff00e0),
        0 0 35px var(--cyber-pink, #ff00e0)
      `,
      animation: 'textFlicker 3s infinite alternate',
    },
    pChar: {
      color: '#ffee00',
      textShadow: `
        0 0 5px #ffee00,
        0 0 10px #ffee00,
        0 0 20px var(--cyber-pink, #ff00e0),
        0 0 35px var(--cyber-pink, #ff00e0)
      `,
    },
    motifShape: {
      position: 'absolute', // Now correctly typed
      width: '100px',
      height: '100px',
      border: '2px solid #00f2ff',
      borderRadius: '30% 70% 70% 30% / 30% 30% 70% 70%',
      zIndex: 1,
      animation: 'morphAndRotate 12s infinite linear',
      boxShadow: `
        inset 0 0 15px #00f2ff,
        0 0 25px #00f2ff
      `,
    },
  };

  return (
    <>
      <style>{`
        @keyframes morphAndRotate {
          0% {
            transform: rotate(0deg);
            border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%;
          }
          50% {
            transform: rotate(180deg);
            border-radius: 60% 40% 30% 70% / 70% 50% 50% 30%;
          }
          100% {
            transform: rotate(360deg);
            border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%;
          }
        }
        
        @keyframes textFlicker {
          0%, 18%, 22%, 25%, 53%, 57%, 100% {
            text-shadow:
              0 0 5px #00f2ff,
              0 0 10px #00f2ff,
              0 0 20px #ff00e0,
              0 0 35px #ff00e0;
          }
          20%, 24%, 55% {
            text-shadow: none;
          }
        }
        
        .motif-shape::before {
          content: '';
          position: absolute;
          top: 8px;
          left: 8px;
          right: 8px;
          bottom: 8px;
          border: 1px solid #ff00e0;
          border-radius: inherit;
          animation: morphAndRotate 12s infinite linear reverse;
          box-shadow: 
            inset 0 0 10px #ff00e0,
            0 0 15px #ff00e0;
        }
      `}</style>
      <div style={logoStyles.logoContainer}>
        <div style={logoStyles.motifShape} className="motif-shape"></div>
        <div style={logoStyles.logoText}>
          <span style={logoStyles.pChar}>P</span>icha
        </div>
      </div>
    </>
  );
};

// Connection Card Component (Re-implemented from user's provided design)
interface ConnectionCardProps {
  title: string;
  subtitle: string;
  icon: React.ElementType;
  isConnected: boolean;
  connectionInfo: string[] | null;
  onConnect: () => void;
  isLoading?: boolean;
  children?: React.ReactNode; // To allow WalletConnector to be a child
}

const ConnectionCard: React.FC<ConnectionCardProps> = ({ title, subtitle, icon: Icon, isConnected, connectionInfo, onConnect, isLoading = false, children }) => {
  return (
    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-cyan-500/30 backdrop-blur-lg rounded-xl p-6 hover:border-cyan-400 hover:shadow-lg hover:shadow-cyan-500/20 transition-all duration-300 hover:-translate-y-1">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-12 h-12 bg-gradient-to-br from-cyan-400 to-pink-500 rounded-xl flex items-center justify-center">
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">{title}</h3>
          <p className="text-sm text-gray-400">{subtitle}</p>
        </div>
      </div>
      <div>
        {isConnected ? (
          <div className="space-y-3">
            <div className="flex items-center space-x-2 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <span className="text-green-400 font-medium">Connected</span>
            </div>
            {connectionInfo && (
              <div className="space-y-2 p-3 bg-black/30 rounded-lg">
                {connectionInfo.map((info, index) => (
                  <div key={index} className="text-sm font-mono text-cyan-400">
                    {info}
                  </div>
                ))}
              </div>
            )}
            {children} {/* Render children (WalletConnector) here if connected */}
          </div>
        ) : (
          <>
            <button
              onClick={onConnect}
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-cyan-500 to-pink-500 hover:from-cyan-400 hover:to-pink-400 text-white font-semibold py-3 rounded-xl transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" /> Connecting...
                </span>
              ) : (
                `Connect ${title}`
              )}
            </button>
            {children} {/* Render children (WalletConnector) here if not connected, for its own button */}
          </>
        )}
      </div>
    </div>
  );
};

// Form Group Component (Re-implemented from user's provided design)
interface FormGroupProps {
  label: string;
  children: React.ReactNode;
  fullWidth?: boolean;
}

const FormGroup: React.FC<FormGroupProps> = ({ label, children, fullWidth = false }) => {
  return (
    <div className={`space-y-2 ${fullWidth ? 'col-span-2' : ''}`}>
      <label className="text-sm font-semibold text-white">{label}</label>
      {children}
    </div>
  );
};

// Custom Select Component (Re-implemented from user's provided design)
interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string; disabled?: boolean }[];
  placeholder?: string;
  disabled?: boolean;
}

const CustomSelect: React.FC<CustomSelectProps> = ({ value, onChange, options, placeholder, disabled = false }) => {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full p-3 bg-black/40 border border-cyan-500/30 rounded-lg text-white focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
      disabled={disabled}
    >
      {placeholder && <option value="" className="bg-[--background-secondary] text-gray-400">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled} className="bg-[--background-secondary] text-[--primary-text]">
          {option.label}
        </option>
      ))}
    </select>
  );
};

// NFT Preview Component (Redesigned based on user's NFTPreview and existing NFTPreviewCard)
interface NFTPreviewProps {
  imageURI?: string;
  artistStyle?: string;
  eventType?: string;
  version?: string;
  timestamp?: string;
  prompt?: string;
  geneticTraits?: GeneticTraits;
  scarcityInfo?: ScarcityInfo;
  evolutionHistory?: EvolutionEntry[];
  evolutionPeriodDays?: number;
  onUpdatePreview?: () => void; // Added for advanced mode update button
  isAdvancedMode?: boolean; // Added to control update button visibility
}

const NFTPreview: React.FC<NFTPreviewProps> = ({
  imageURI,
  artistStyle = 'Abstract Digital',
  eventType = 'Art Exhibition',
  version = 'v1.0',
  timestamp = new Date().toLocaleDateString(),
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
    setTimeout(() => setAnimateTraits(true), 500);
  }, [geneticTraits]); // Re-animate if traits change

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
                            <span key={trait} className="text-xs px-2 py-0.5 border border-[--neon-purple]/30 text-[--neon-purple] rounded-full">
                              {trait.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Show small thumbnail of image from that version */}
                      {entry.image_url && (
                          <img
                              src={`http://localhost:5000${entry.image_url}`}
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

// Feature Tag Component (Re-implemented from user's provided design)
interface FeatureTagProps {
  children: React.ReactNode;
  icon: React.ElementType;
}

const FeatureTag: React.FC<FeatureTagProps> = ({ children, icon: Icon }) => {
  return (
    <div className="flex items-center space-x-2 px-4 py-3 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-cyan-500/30 rounded-full hover:border-cyan-400 hover:bg-gradient-to-br hover:from-cyan-500/20 hover:to-pink-500/20 transition-all duration-300 cursor-pointer hover:-translate-y-1">
      {Icon && <Icon className="w-4 h-4 text-cyan-400" />}
      <span className="text-sm font-medium text-white">{children}</span>
    </div>
  );
};

// Error Alert Component (Re-implemented from user's provided design)
interface ErrorAlertProps {
  error: APIError;
  onRetry?: () => void;
}

const ErrorAlert: React.FC<ErrorAlertProps> = ({ error, onRetry }) => (
  <div className="mb-4 bg-[--error-background] border-[--error-border] text-[--error-text] p-4 rounded-lg">
    <div className="flex items-start space-x-3">
      <AlertCircle className="h-5 w-5 text-[--error-icon] flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">Error</p>
        <p className="text-sm mt-1">
          {error.message}
          {error.status && (
            <span className="ml-2 opacity-75">
              (Status: {error.status})
            </span>
          )}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 text-sm underline text-[--error-text] hover:opacity-80"
          >
            <RefreshCw className="w-4 h-4 mr-1 inline-block" />
            Retry
          </button>
        )}
      </div>
    </div>
  </div>
);


const Index = () => {
  // State management with better organization
  const [mode, setMode] = useState<'basic' | 'advanced'>('basic');
  const [customPrompt, setCustomPrompt] = useState('');
  const [selectedArtist, setSelectedArtist] = useState('');
  const [selectedEvent, setSelectedEvent] = useState('');
  const [nftResult, setNftResult] = useState<NFTData | null>(null);
  const [evolutionPeriod, setEvolutionPeriod] = useState<number>(30); // Default to 30 days

  // Wallet state management
  const [wallet, setWallet] = useState<WalletInfo | null>(null);

  // X (Twitter) social media connection state
  const [isXConnected, setIsXConnected] = useState<boolean>(false);
  const [xUsername, setXUsername] = useState<string | null>(null);
  const [xUserId, setXUserId] = useState<string | null>(null);

  // Enhanced loading states
  const [loadingStates, setLoadingStates] = useState<LoadingStates>({
    initialData: false,
    nftGeneration: false,
    combinations: false,
    xAuth: false,
    wallet: false, // Initialize wallet loading state
  });

  // Enhanced error handling
  const [errors, setErrors] = useState<{
    initialization?: APIError;
    nftGeneration?: APIError;
    validation?: string;
    wallet?: APIError;
    websocket?: string;
    xAuth?: string;
  }>({});

  const [artists, setArtists] = useState<string[]>([]);
  const [events, setEvents] = useState<string[]>([]);
  const [retryCount, setRetryCount] = useState(0);
  const [allCombinationsScarcity, setAllCombinationsScarcity] = useState<CombinationScarcityAPI[]>([]);

  // WebSocket state
  const socketRef = useRef<typeof Socket | null>(null);
  const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);

  // Utility function to create standardized error objects
  const createAPIError = (error: unknown, context: string): APIError => {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<APIErrorResponse>;
      return {
        message: axiosError.response?.data?.error ||
                axiosError.response?.data?.message ||
                axiosError.message ||
                `Network error occurred while ${context}`,
        status: axiosError.response?.status,
        code: axiosError.code
      };
    } else if (error instanceof Error) {
      return {
        message: `${error.message} while ${context}`,
      };
    } else {
      return {
        message: `Unknown error occurred while ${context}`,
      };
    }
  };

  // Enhanced error clearing function
  const clearErrors = (errorType?: keyof typeof errors) => {
    setErrors(prev => {
      if (errorType) {
        const newErrors = { ...prev };
        delete newErrors[errorType];
        return newErrors;
      }
      return {};
    });
  };

  // Utility function to generate a random hex string with validation
  const generateRandomHex = (length: number): string => {
    try {
      if (length <= 0 || length % 2 !== 0) {
        throw new Error('Length must be a positive even number');
      }

      const bytes = new Uint8Array(length / 2);
      crypto.getRandomValues(bytes);
      return Array.from(bytes)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
    } catch (error) {
      console.warn('Failed to generate secure random hex, falling back to Math.random');
      // Fallback for environments without crypto API
      return Math.random().toString(16).substring(2, length + 2).padEnd(length, '0');
    }
  };

  // Enhanced uniqueness factors generation with wallet integration
  const generateUniquenessFactors = (walletInfo?: WalletInfo | null) => {
    try {
      const locationHash = generateRandomHex(16);
      const timestampSeed = Math.floor(Date.now() / 1000).toString();

      // Use wallet-based entropy when available
      let walletEntropy: string;
      if (walletInfo?.principal) {
        // Create deterministic entropy from wallet principal
        walletEntropy = walletInfo.principal.slice(-16).padStart(16, '0');
      } else {
        // Fallback to random entropy for demo mode
        walletEntropy = generateRandomHex(16);
      }

      return {
        location_hash: locationHash,
        timestamp_seed: timestampSeed,
        wallet_entropy: walletEntropy,
        wallet_principal: walletInfo?.principal || null,
        wallet_account_id: walletInfo?.accountId || null,
        biometric_opt_in: false,
        biometric_hash: null
      };
    } catch (error) {
      console.error('Error generating uniqueness factors:', error);
      // Fallback with basic randomization
      return {
        location_hash: Math.random().toString(36).substring(2, 18),
        timestamp_seed: Math.floor(Date.now() / 1000).toString(),
        wallet_entropy: Math.random().toString(36).substring(2, 18),
        wallet_principal: walletInfo?.principal || null,
        wallet_account_id: walletInfo?.accountId || null,
        biometric_opt_in: false,
        biometric_hash: null
      };
    }
  };

  // Fetch all combinations scarcity data
  const fetchAllCombinationsScarcity = useCallback(async () => {
    setLoadingStates(prev => ({ ...prev, combinations: true }));
    try {
      const response = await axios.get('http://localhost:5000/api/combinations');
      if (response.data?.combinations && Array.isArray(response.data.combinations)) {
        setAllCombinationsScarcity(response.data.combinations as CombinationScarcityAPI[]);
        console.log("Fetched and processed all combinations scarcity:", response.data.combinations);
      } else {
        console.warn('Unexpected response format for combinations:', response.data);
      }
    } catch (error) {
      console.error('Error fetching all combinations scarcity:', error);
      toast.error('Failed to load combination scarcity data.');
    } finally {
      setLoadingStates(prev => ({ ...prev, combinations: false }));
    }
  }, []);

  // Enhanced data fetching with retry logic using useCallback to fix the dependency issue
  const fetchInitialData = useCallback(async (isRetry = false) => {
    if (!isRetry) {
      setLoadingStates(prev => ({ ...prev, initialData: true }));
    }

    clearErrors('initialization');

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

      const [artistsResponse, eventsResponse] = await Promise.all([
        axios.get('http://localhost:5000/api/artists', {
          signal: controller.signal,
          timeout: 8000
        }),
        axios.get('http://localhost:5000/api/events', {
          signal: controller.signal,
          timeout: 8000
        })
      ]);

      clearTimeout(timeoutId);

      // Validate response data
      if (!artistsResponse.data?.artists || !Array.isArray(artistsResponse.data.artists)) {
        throw new Error('Invalid artists data received from server');
      }

      if (!eventsResponse.data?.events || !Array.isArray(eventsResponse.data.events)) {
        throw new Error('Invalid events data received from server');
      }

      setArtists(artistsResponse.data.artists);
      setEvents(eventsResponse.data.events);

      // Set default selections with validation
      if (artistsResponse.data.artists.length > 0) {
        setSelectedArtist(artistsResponse.data.artists[0]);
      }
      if (eventsResponse.data.events.length > 0) {
        setSelectedEvent(eventsResponse.data.events[0]);
      }

      setRetryCount(0); // Reset retry count on success

    } catch (error) {
      console.error('Error fetching initial data:', error);

      if (axios.isAxiosError(error) && error.code === 'ECONNABORTED') {
        setErrors(prev => ({
          ...prev,
          initialization: {
            message: 'Request timed out. Please check your connection and try again.',
            code: 'TIMEOUT'
          }
        }));
      } else {
        setErrors(prev => ({
          ...prev,
          initialization: createAPIError(error, 'loading initial data')
        }));
      }
    } finally {
      setLoadingStates(prev => ({ ...prev, initialData: false }));
    }
  }, []); // Empty dependency array since function doesn't depend on any state

  // Enhanced retry logic
  const retryFetchInitialData = () => {
    const newRetryCount = retryCount + 1;
    setRetryCount(newRetryCount);

    // Exponential backoff with max delay
    const delay = Math.min(1000 * Math.pow(2, newRetryCount - 1), 5000);

    setTimeout(() => {
      fetchInitialData(true);
    }, delay);
  };

  // Initial data loading and combinations loading
  useEffect(() => {
    fetchInitialData();
    fetchAllCombinationsScarcity(); // Fetch initial scarcity data for all combinations
  }, [fetchInitialData, fetchAllCombinationsScarcity]);

  // Wallet state management - this would be integrated based on the actual WalletConnector implementation
  useEffect(() => {
    const checkWalletState = () => {
      try {
        const savedWallet = localStorage.getItem('connected-wallet');
        if (savedWallet) {
          const walletData = JSON.parse(savedWallet);
          if (walletData.principal || walletData.accountId) {
            setWallet(walletData);
          }
        }
      } catch (error) {
        console.warn('Could not restore wallet state:', error);
      }
    };

    checkWalletState();
  }, []);

  // X (Twitter) OAuth Callback Handling
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const authStatus = params.get('auth_status');
    const platform = params.get('platform');
    const username = params.get('username');
    const userId = params.get('user_id');
    const walletPrincipal = params.get('wallet_principal');
    const errorMessage = params.get('message');
    const errorDetails = params.get('details');

    if (authStatus === 'success' && platform === 'x' && username && userId && walletPrincipal) {
      setIsXConnected(true);
      setXUsername(username);
      setXUserId(userId);
      // You might want to store this in local storage or state related to the wallet
      // For now, let's just log it and display the status.
      localStorage.setItem('x-auth-status', JSON.stringify({
        isConnected: true,
        username,
        userId,
        walletPrincipal,
        timestamp: Date.now()
      }));
      toast.success(`Connected to X as @${username}!`);
      // Clear URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (authStatus === 'error' && platform === 'x') {
      setIsXConnected(false);
      setXUsername(null);
      setXUserId(null);
      localStorage.removeItem('x-auth-status');
      const errorMsg = errorMessage || 'Unknown error during X authentication.';
      const detailedError = errorDetails ? `${errorMsg} Details: ${errorDetails}` : errorMsg;
      setErrors(prev => ({ ...prev, xAuth: detailedError }));
      toast.error('Failed to connect to X.');
      // Clear URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
        // Attempt to restore X auth status from local storage if not just redirected
        try {
            const savedXAuth = localStorage.getItem('x-auth-status');
            if (savedXAuth) {
                const authData = JSON.parse(savedXAuth);
                if (authData.isConnected && authData.username && authData.userId) {
                    setIsXConnected(true);
                    setXUsername(authData.username);
                    setXUserId(authData.userId);
                }
            }
        } catch (e) {
            console.warn("Failed to restore X auth from local storage", e);
            localStorage.removeItem('x-auth-status');
        }
    }
  }, []); // Run only once on component mount

  // Function to initiate X OAuth flow
  const handleConnectXAccount = async () => {
    if (!wallet || !wallet.principal) {
      toast.error("Please connect your wallet first to link your X account.");
      return;
    }

    setLoadingStates(prev => ({ ...prev, xAuth: true }));
    clearErrors('xAuth');
    try {
      // Redirect to your backend's OAuth initiation endpoint
      // The backend will then redirect to X
      window.location.href = `http://localhost:5000/api/auth/x-initiate?wallet_principal=${wallet.principal}`;
    } catch (error) {
      console.error("Error initiating X OAuth:", error);
      setErrors(prev => ({ ...prev, xAuth: "Failed to initiate X account connection." }));
      toast.error("Failed to connect X account.");
    } finally {
      setLoadingStates(prev => ({ ...prev, xAuth: false }));
    }
  };

  // WebSocket connection and event handling
  useEffect(() => {
    // Ensure 'io' is correctly imported and available
    if (socketRef.current && socketRef.current.connected) {
      return;
    }
    const socket = io('http://localhost:5000', {
      transports: ['websocket'],
      reconnectionAttempts: 5,
      reconnectionDelay: 3000,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      setIsWebSocketConnected(true);
      clearErrors('websocket');
      console.log('Index page WebSocket connected:', socket.id);
      // Subscribe to general new mint events
      // No specific room for general mints, they are broadcast to all by default
    });

    socket.on('disconnect', (reason) => {
      setIsWebSocketConnected(false);
      setErrors(prev => ({ ...prev, websocket: `WebSocket disconnected: ${reason}. Attempting to reconnect...` }));
      console.warn('Index page WebSocket disconnected:', reason);
    });

    socket.on('connect_error', (err) => {
      setIsWebSocketConnected(false);
      setErrors(prev => ({ ...prev, websocket: `WebSocket connection error: ${err.message}. Retrying...` }));
      console.error('Index page WebSocket connection error:', err);
    });

    // Listen for new mint events
    const handleNewMint = (data: NewMintMessage) => {
      console.log('Received new_mint event:', data);
      toast.success(`New NFT Minted: ${data.name || data.nft_id.slice(0, 8)}... by ${data.artist}!`, {
        description: `Owner: ${data.owner_address.slice(0, 10)}...`,
        action: {
          label: 'View',
          onClick: () => window.open(`/api/nft/${data.nft_id}`, '_blank'), // Or navigate to a view page
        },
      });

      // Update scarcity for the relevant combination
      setAllCombinationsScarcity(prev =>
        prev.map(combo => {
          // Use the updated ScarcityInfo structure from backend response
          if (combo.artist === data.artist && combo.event_type === data.event_type) { // Changed to use event_type directly
            // Safely get current values, default to 0 if undefined
            const currentMinted = combo.scarcity_info?.minted_count || 0;
            const currentTotal = combo.scarcity_info?.total_limit || 0;

            const newMintedCount = currentMinted + 1;
            const newRemainingSlots = currentTotal - newMintedCount;

            return {
              ...combo,
              scarcity_info: {
                ...combo.scarcity_info,
                minted_count: newMintedCount,
                remaining_slots: newRemainingSlots,
                is_sold_out: newRemainingSlots <= 0, // Recalculate is_sold_out
              } as ScarcityInfo, // Cast to ScarcityInfo to ensure type correctness
              is_available: newRemainingSlots > 0, // Recalculate is_available
            };
          }
          return combo;
        })
      );
    };
    socket.on('new_mint', handleNewMint);

    // Listen for scarcity updates (general, from other mints)
    const handleScarcityUpdate = (data: ScarcityUpdateMessage) => {
      console.log('Received general scarcity_update event:', data);
      setAllCombinationsScarcity(prev =>
        prev.map(combo => {
          // Use the updated ScarcityInfo structure from backend response
          if (combo.artist === data.artist && combo.event_type === data.event_type) { // Changed to use event_type directly
            const newMintedCount = data.total_supply - data.remaining_slots;
            return {
              ...combo,
              scarcity_info: {
                ...combo.scarcity_info,
                remaining_slots: data.remaining_slots,
                total_supply: data.total_supply,
                minted_count: newMintedCount,
                is_sold_out: data.remaining_slots <= 0, // Recalculate is_sold_out
              } as ScarcityInfo, // Cast to ScarcityInfo
              is_available: data.is_available,
            };
          }
          return combo;
        })
      );

      // Show toast notification for critical scarcity changes
      if (data.remaining_slots <= 0) {
        toast.warning(`SOLD OUT: ${data.artist} - ${data.event_type}!`, {
          description: 'This combination is no longer available for minting.',
          duration: 5000,
        });
      } else if (data.remaining_slots < 50 && data.remaining_slots > 0) {
        toast.info(`Limited Slots: ${data.artist} - ${data.event_type} has ${data.remaining_slots} left!`, {
          duration: 3000,
        });
      }
    };
    socket.on('scarcity_update', handleScarcityUpdate);

    // Listen for evolution updates for *this* user's NFT
    const handleEvolutionUpdate = (data: EvolutionUpdateMessage) => {
      // Fetch the full NFT data again to get the latest evolution history and other fields
      // This is more robust than trying to merge partial updates locally
      axios.get(`http://localhost:5000/api/nft/${data.nft_id}`)
        .then(response => {
          const updatedNftData = response.data;
          if (updatedNftData) {
            console.log('Received evolution_update event for current NFT and refetched:', updatedNftData);
            // Convert timestamp from seconds to milliseconds for Date object
            updatedNftData.timestamp = updatedNftData.timestamp * 1000;
            setNftResult(updatedNftData); // Update the whole NFT object
            toast.success(`Your NFT (${updatedNftData.id.slice(0, 8)}...) has evolved!`, {
              description: `Now version ${updatedNftData.version}.`,
              duration: 5000,
            });
          }
        })
        .catch(error => {
          console.error(`Failed to refetch NFT ${data.nft_id} after evolution update:`, error);
          toast.error(`NFT ${data.nft_id.slice(0,8)}... evolved, but failed to fetch latest details.`);
        });
    };
    socket.on('evolution_update', handleEvolutionUpdate);


    // Cleanup on unmount
    return () => {
      console.log('Index page: Disconnecting WebSocket...');
      socket.off('new_mint', handleNewMint);
      socket.off('scarcity_update', handleScarcityUpdate);
      socket.off('evolution_update', handleEvolutionUpdate);
      socket.disconnect();
    };
  }, []);

  // Join evolution room if an NFT is generated and has an ID
  useEffect(() => {
    if (nftResult?.id && isWebSocketConnected && socketRef.current) {
      console.log(`Attempting to join evolution room for NFT: ${nftResult.id}`);
      socketRef.current.emit('join_evolution_room', { nft_id: nftResult.id });
    }
    // Cleanup previous evolution room if nftResult changes
    return () => {
      if (socketRef.current && nftResult?.id) { // Only attempt to leave if there was an NFT previously
        console.log(`Leaving evolution room for NFT: ${nftResult.id}`);
        socketRef.current.emit('leave_evolution_room', { nft_id: nftResult.id });
      }
    };
    // The dependency should be `nftResult?.id` to ensure re-subscription if NFT changes
  }, [nftResult?.id, isWebSocketConnected]);


  // New callback function for WalletConnector
  const handleWalletConnected = useCallback((walletInfo: WalletInfo) => {
    setWallet(walletInfo);
    setLoadingStates(prev => ({ ...prev, wallet: false }));
    try {
      localStorage.setItem('connected-wallet', JSON.stringify(walletInfo));
      toast.success('Wallet connected successfully!');
    } catch (error) {
      console.error('Failed to save wallet to local storage:', error);
      toast.error('Failed to save wallet connection. Please try again.');
    }
  }, []);

  // New callback function for WalletConnector disconnection
  const handleWalletDisconnected = useCallback(() => {
    setWallet(null);
    setLoadingStates(prev => ({ ...prev, wallet: false }));
    // Also disconnect X account if wallet is disconnected
    setIsXConnected(false);
    setXUsername(null);
    setXUserId(null);
    localStorage.removeItem('connected-wallet');
    localStorage.removeItem('x-auth-status');
    try {
      localStorage.removeItem('connected-wallet');
      toast.info('Wallet disconnected.');
    } catch (error) {
      console.error('Failed to remove wallet from local storage:', error);
      toast.error('Failed to clear wallet connection. Please try again.');
    }
  }, []);


  // Enhanced form validation with wallet check
  const validateForm = (): string | null => {
    // Check wallet connection first
    if (!wallet) {
      return 'Please connect your wallet to generate NFTs';
    }

    if (mode === 'basic') {
      if (!selectedArtist) {
        return 'Please select an artist';
      }
      if (!selectedEvent) {
        return 'Please select an event';
      }
      // Get the current scarcity info for the selected combination
      const selectedComboScarcity = getScarcityForCombination(selectedArtist, selectedEvent);

      // Check if the selected combination is sold out
      if (selectedComboScarcity?.is_sold_out) {
        return `The ${selectedArtist} - ${selectedEvent} combination is currently sold out.`;
      }
    } else {
      if (!customPrompt.trim()) {
        return 'Please enter a custom prompt';
      }
      if (customPrompt.trim().length < 10) {
        return 'Custom prompt must be at least 10 characters long';
      }
      if (customPrompt.trim().length > 500) {
        return 'Custom prompt must be less than 500 characters';
      }
    }
    return null;
  };

  // Enhanced NFT generation with wallet integration and better error handling
  const handleUpdatePreview = async () => {
    // Clear previous errors
    clearErrors('nftGeneration');
    clearErrors('validation');

    // Validate wallet connection first
    if (!wallet) {
      setErrors(prev => ({
        ...prev,
        validation: 'Please connect your wallet to generate NFTs'
      }));
      return;
    }

    // Validate form
    const validationError = validateForm();
    if (validationError) {
      setErrors(prev => ({ ...prev, validation: validationError }));
      return;
    }

    setLoadingStates(prev => ({ ...prev, nftGeneration: true }));

    try {
      // Use wallet principal or accountId as owner address
      const ownerAddress = wallet.principal || wallet.accountId;
      if (!ownerAddress) {
        throw new Error('Invalid wallet information - no principal or account ID available');
      }

      const requestData = {
        mode: mode === 'basic' ? 'selection' : 'prompt',
        artist: selectedArtist || 'Da Vinci',
        event_type: selectedEvent || 'architecture',
        owner_address: ownerAddress,
        user_prompt: mode === 'advanced' ? customPrompt.trim() : null,
        uniqueness_factors: generateUniquenessFactors(wallet),
        evolution_period_days: evolutionPeriod, // Use selected evolution period
      };

      // Validate request data
      if (!requestData.artist || !requestData.event_type) {
        throw new Error('Missing required fields for NFT generation');
      }

      console.log('Sending NFT generation request:', requestData);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout for generation

      const response = await axios.post(
        'http://localhost:5000/api/create-nft',
        requestData,
        {
          signal: controller.signal,
          timeout: 25000 // 25 second axios timeout
        }
      );

      clearTimeout(timeoutId);

      console.log('Server response:', response.data);

      // More flexible response parsing - check multiple possible structures
      let nft = null;

      // The backend now sends the NFT data directly at the top level, with 'nft_id'
      if (response.data && typeof response.data === 'object' && 'nft_id' in response.data) {
        nft = response.data;
      } else if (response.data?.nft) {
        nft = response.data.nft;
      } else if (response.data?.data) {
        nft = response.data.data;
      } else if (response.data?.result) {
        nft = response.data.result;
      } else {
        console.error('Unexpected response structure:', response.data);
        throw new Error(`Server returned unexpected response format. Response keys: ${Object.keys(response.data || {}).join(', ')}`);
      }

      if (!nft) {
        throw new Error('No NFT data found in server response');
      }

      // Validate required NFT fields with more flexible checking
      const requiredFields = ['nft_id']; // Changed to nft_id as per backend
      const missingFields = requiredFields.filter(field => !nft[field]);

      if (missingFields.length > 0) {
        console.warn(`Missing some expected NFT fields: ${missingFields.join(', ')}`);
        console.log('Available NFT fields:', Object.keys(nft));
      }

      // Build NFT data with fallbacks for missing fields
      const nftData: NFTData = {
          id: nft.nft_id || `nft-${Date.now()}`, // Use nft.nft_id
          image_uri: `http://localhost:5000${nft.image_url}` || nft.image_uri || '', // Prepend base URL
          artist: nft.artist || selectedArtist || 'Unknown Artist',
          event_type: nft.event_type || selectedEvent || 'Unknown Event',
          version: nft.version || 1,
          timestamp: nft.timestamp || Math.floor(Date.now() / 1000),
          genetic_traits: nft.genetic_traits || { // Ensure default for genetic_traits
            luminosity: 0, architectural_complexity: 0, ethereal_quality: 0,
            evolution_speed: 0, style_intensity: 0, temporal_resonance: 0
          },
          scarcity_info: nft.scarcity_info || { // Ensure default for scarcity_info
            combination: '', total_limit: 0, minted_count: 0, rarity_score: 0,
            price_multiplier: 0, is_sold_out: false, remaining_slots: 0
          },
          prompt: nft.prompt || (mode === 'advanced' ? customPrompt : `${selectedArtist} style ${selectedEvent}`),
          evolution_history: nft.evolution_history || [], // Ensure evolution_history is present
          evolution_period_days: nft.evolution_period_days || evolutionPeriod, // Ensure evolution_period_days is present
      };

      console.log('Parsed NFT data:', nftData);
      setNftResult(nftData);
      toast.success('NFT generated successfully!');

    } catch (error) {
      console.error('NFT generation failed:', error);

      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          setErrors(prev => ({
            ...prev,
            nftGeneration: {
              message: 'NFT generation timed out. The server may be busy, please try again.',
              code: 'TIMEOUT'
            }
          }));
        } else if (error.response?.status === 429) {
          setErrors(prev => ({
            ...prev,
            nftGeneration: {
              message: 'Too many requests. Please wait a moment before trying again.',
              status: 429,
              code: 'RATE_LIMIT'
            }
          }));
        } else if (error.response?.status === 500) {
          setErrors(prev => ({
            ...prev,
            nftGeneration: {
              message: 'Server error occurred during NFT generation. Please try again.',
              status: 500,
              code: 'SERVER_ERROR'
            }
          }));
        } else {
          setErrors(prev => ({
            ...prev,
            nftGeneration: createAPIError(error, 'generating NFT')
          }));
        }
      } else {
        setErrors(prev => ({
          ...prev,
          nftGeneration: createAPIError(error, 'generating NFT')
        }));
      }
      toast.error('Failed to generate NFT.');
    } finally {
      setLoadingStates(prev => ({ ...prev, nftGeneration: false }));
    }
  };

  const getScarcityForCombination = (artist: string, eventType: string): ScarcityInfo | undefined => {
    // Add a check to ensure allCombinationsScarcity is populated and valid
    if (!allCombinationsScarcity || allCombinationsScarcity.length === 0) {
      console.log("getScarcityForCombination: allCombinationsScarcity is empty or not loaded.");
      return undefined; // Or return a default/fallback scarcity info
    }

    // Find the combination in the fetched list
    const foundCombo = allCombinationsScarcity.find(
      combo => combo.artist === artist && combo.event_type === eventType
    );

    // Return the nested scarcity_info object directly, which should now contain is_sold_out
    return foundCombo?.scarcity_info;
  };

  return (
    // Global CSS variables and base styles for the new theme
    <>
      <style >{`
        :root {
          --background-dark: #0A0A0F;
          --background-secondary: #1A1A2E;
          --surface: #16213E;
          --electric-blue: #00D4FF;
          --neon-purple: #8B5CF6;
          --cyber-green: #00FF88;
          --hot-pink: #FF0080;
          --warning: #FFB800;
          --error: #FF4444;
          --success: #4ADE80;
          --info: #60A5FA;
          --primary-text: #FFFFFF;
          --secondary-text: #B8BCC8;
          --muted-text: #6B7280;
          --disabled-text: #4B5563;

          /* Gradients as CSS variables for easier use */
          --primary-gradient: linear-gradient(135deg, var(--electric-blue) 0%, var(--neon-purple) 100%);
          --success-gradient: linear-gradient(135deg, var(--cyber-green) 0%, var(--success) 100%);
          --warning-gradient: linear-gradient(135deg, var(--warning) 0%, var(--hot-pink) 100%);
          --background-radial-gradient: radial-gradient(circle at 20% 80%, var(--background-secondary) 0%, var(--background-dark) 100%);

          /* Shadcn overrides to use custom colors */
          --background: var(--background-dark);
          --foreground: var(--primary-text);
          --card: var(--surface);
          --card-foreground: var(--primary-text);
          --popover: var(--background-secondary);
          --popover-foreground: var(--primary-text);
          --primary: var(--electric-blue);
          --primary-foreground: var(--primary-text);
          --secondary: var(--background-secondary);
          --secondary-foreground: var(--secondary-text);
          --muted: var(--muted-text);
          --muted-foreground: var(--muted-text);
          --accent: var(--neon-purple); /* Using neon-purple for accent */
          --accent-foreground: var(--primary-text);
          --destructive: var(--error);
          --destructive-foreground: var(--primary-text);
          --border: rgba(255, 255, 255, 0.1); /* Light border for glassmorphism */
          --input: rgba(255, 255, 255, 0.2); /* Input border */
          --ring: var(--electric-blue);
          --radius: 0.75rem; /* Default border radius for components */

          /* Custom NFT specific colors */
          --nft-primary: var(--electric-blue);
          --nft-accent: rgba(139, 92, 246, 0.2); /* Neon Purple with transparency */
          --nft-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);

          /* Error Alert specific colors */
          --error-background: rgba(255, 68, 68, 0.1);
          --error-border: rgba(255, 68, 68, 0.4);
          --error-text: var(--error);
          --error-icon: var(--error);
        }

        /* Glassmorphism effect */
        .glassmorphism {
          background-color: var(--surface);
          border: 1px solid var(--border);
          box-shadow: var(--nft-shadow);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
        }

        /* Custom scrollbar for a futuristic look */
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: var(--background-secondary);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--neon-purple);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: var(--electric-blue);
        }

        /* Animations */
        @keyframes pulse-glow {
          0%, 100% {
            box-shadow: 0 0 0px var(--electric-blue), 0 0 0px var(--neon-purple);
          }
          50% {
            box-shadow: 0 0 15px var(--electric-blue), 0 0 30px var(--neon-purple);
          }
        }

        .animate-pulse-glow {
          animation: pulse-glow 2s infinite cubic-bezier(0.4, 0, 0.2, 1);
        }

        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }

        .shimmer-effect::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,.2), transparent);
          transform: translateX(-100%);
          animation: shimmer 1.5s infinite;
        }
      `}</style>
      <div className="min-h-screen py-12 px-4 bg-[--background-dark] text-[--primary-text] font-inter" style={{ backgroundImage: 'var(--background-radial-gradient)' }}>
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-16">
            <PichaLogo />
            <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-cyan-400 to-pink-500 bg-clip-text text-transparent">
              NFT Studio
            </h1>
            <p className="text-lg text-gray-300 max-w-2xl mx-auto mb-2">
              Create unique AI-generated NFTs with personal uniqueness factors and evolving traits.
            </p>
            <p className="text-cyan-400 font-medium">Experience the future of digital art.</p>
          </div>

          {/* Connection Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
            <ConnectionCard
              title="Internet Identity"
              subtitle="Connect your ICP wallet securely"
              icon={Wallet}
              isConnected={!!wallet}
              connectionInfo={wallet ? [
                `Principal ID: ${wallet.principal}`,
                `Account ID: ${wallet.accountId}`
              ] : null}
              onConnect={() => setLoadingStates(prev => ({ ...prev, wallet: true }))} // Set loading state for WalletConnector
              isLoading={loadingStates.wallet}
            >
              {/* WalletConnector renders its own content, we just pass callbacks */}
              <WalletConnector
                onWalletConnected={handleWalletConnected}
                onWalletDisconnected={handleWalletDisconnected}
              />
            </ConnectionCard>
            
            <ConnectionCard
              title="Social Connect"
              subtitle={isXConnected ? `Connected to X as @${xUsername}` : 'Connect your X account'}
              icon={Twitter}
              isConnected={isXConnected}
              connectionInfo={isXConnected ? [
                `ID: ${xUserId}`,
                'Your NFT\'s evolution can now be influenced by your X activity.'
              ] : null}
              onConnect={handleConnectXAccount}
              isLoading={loadingStates.xAuth}
            />
          </div>

          {/* Error Alerts */}
          {errors.wallet && (
            <ErrorAlert
              error={errors.wallet}
              onRetry={() => clearErrors('wallet')}
            />
          )}

          {errors.initialization && (
            <ErrorAlert
              error={errors.initialization}
              onRetry={retryFetchInitialData}
            />
          )}

          {errors.nftGeneration && (
            <ErrorAlert
              error={errors.nftGeneration}
              onRetry={() => clearErrors('nftGeneration')}
            />
          )}

          {errors.validation && (
            <div className="mb-6 max-w-2xl mx-auto bg-[--error-background] border-[--error-border] text-[--error-text] p-4 rounded-lg">
              <div className="flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-[--error-icon] flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-base font-medium">
                    {errors.validation}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* WebSocket Connection Status */}
          {errors.websocket && (
            <div className="mb-6 max-w-2xl mx-auto bg-[--error-background] border-[--error-border] text-[--error-text] p-4 rounded-lg">
              <div className="flex items-start space-x-3">
                <WifiOff className="h-5 w-5 text-[--error-icon] flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-base font-medium">
                    {errors.websocket}
                  </p>
                </div>
              </div>
            </div>
          )}
          {!isWebSocketConnected && !errors.websocket && (
            <div className="mb-6 max-w-2xl mx-auto bg-[--background-secondary] border border-[--warning]/50 text-[--primary-text] p-4 rounded-lg flex items-center space-x-3">
              <WifiOff className="h-5 w-5 text-[--warning]" />
              <p className="text-[--secondary-text]">Connecting to real-time updates...</p>
            </div>
          )}
          {isWebSocketConnected && !errors.websocket && (
            <div className="mb-6 max-w-2xl mx-auto bg-[--background-secondary] border border-[--cyber-green]/50 text-[--primary-text] p-4 rounded-lg flex items-center space-x-3">
              <Wifi className="h-5 w-5 text-[--cyber-green]" />
              <p className="text-[--secondary-text]">Real-time updates active.</p>
            </div>
          )}

          {/* Loading State for Initial Data */}
          {loadingStates.initialData && (
            <div className="mb-6 max-w-2xl mx-auto bg-[--background-secondary] text-[--primary-text] p-4 rounded-lg flex items-center space-x-3">
              <Loader2 className="h-5 w-5 animate-spin text-[--electric-blue]" />
              <p className="text-[--secondary-text]">
                Loading artists and events...
              </p>
            </div>
          )}
          {loadingStates.combinations && (
            <div className="mb-6 max-w-2xl mx-auto bg-[--background-secondary] text-[--primary-text] p-4 rounded-lg flex items-center space-x-3">
              <Loader2 className="h-5 w-5 animate-spin text-[--electric-blue]" />
              <p className="text-[--secondary-text]">
                Loading scarcity data...
              </p>
            </div>
          )}

          {/* Creation Section */}
          <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-cyan-500/30 backdrop-blur-lg rounded-xl p-6 mb-12">
            <div className="text-center space-y-4 mb-6">
              <div className="inline-flex items-center space-x-2 px-4 py-2 bg-cyan-500/20 border border-cyan-500/50 rounded-full">
                <Wifi className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-cyan-400">Real-time updates active.</span>
              </div>
              
              <div className="flex justify-center">
                <div className="flex bg-black/30 rounded-xl overflow-hidden">
                  <button
                    onClick={() => setMode('basic')}
                    className={`px-6 py-3 text-sm font-semibold transition-all duration-200 ${
                      mode === 'basic'
                        ? 'bg-gradient-to-r from-cyan-500 to-pink-500 text-white'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    Basic Mode
                  </button>
                  <button
                    onClick={() => setMode('advanced')}
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
                {mode === 'basic' ? (
                  <>
                    <FormGroup label="Artist Style">
                      <CustomSelect
                        value={selectedArtist}
                        onChange={(value) => {
                          setSelectedArtist(value);
                          clearErrors('validation');
                        }}
                        options={artists.map(artist => ({ value: artist, label: artist }))}
                        placeholder={loadingStates.initialData ? 'Loading...' : 'Choose an artist style...'}
                        disabled={loadingStates.initialData || loadingStates.nftGeneration}
                      />
                    </FormGroup>
                    
                    <FormGroup label="Event Type">
                      <CustomSelect
                        value={selectedEvent}
                        onChange={(value) => {
                          setSelectedEvent(value);
                          clearErrors('validation');
                        }}
                        options={events.map(event => {
                          const comboScarcityInfo = getScarcityForCombination(selectedArtist, event);
                          const isSoldOut = comboScarcityInfo?.is_sold_out || false;
                          return {
                            value: event,
                            label: `${event.charAt(0).toUpperCase() + event.slice(1)} ${isSoldOut ? '(Sold Out)' : ''}`,
                            disabled: isSoldOut,
                          };
                        })}
                        placeholder={loadingStates.initialData ? 'Loading...' : 'Select an event type...'}
                        disabled={loadingStates.initialData || loadingStates.nftGeneration}
                      />
                    </FormGroup>
                  </>
                ) : (
                  <FormGroup label="Custom Prompt" fullWidth>
                    <textarea
                      value={customPrompt}
                      onChange={(e) => {
                        setCustomPrompt(e.target.value);
                        clearErrors('validation');
                      }}
                      placeholder="Describe your NFT... (e.g., 'A cyberpunk cityscape with neon lights and flying cars')"
                      className="min-h-[120px] w-full p-3 bg-black/40 border border-cyan-500/30 rounded-lg text-white focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={loadingStates.nftGeneration}
                      maxLength={500}
                    />
                    <div className="text-sm text-gray-400 text-right mt-1">
                      {customPrompt.length}/500 characters
                    </div>
                  </FormGroup>
                )}
              </div>
              
              <FormGroup label="NFT Evolution Interval" fullWidth>
                <CustomSelect
                  value={String(evolutionPeriod)}
                  onChange={(value) => setEvolutionPeriod(parseInt(value))}
                  options={[
                    { value: '7', label: 'Weekly (7 days)' },
                    { value: '15', label: 'Bi-Weekly (15 days)' },
                    { value: '30', label: 'Monthly (30 days)' },
                    { value: '90', label: 'Quarterly (90 days)' },
                    { value: '180', label: 'Semi-Annually (180 days)' },
                    { value: '365', label: 'Annually (365 days)' },
                  ]}
                  disabled={loadingStates.nftGeneration}
                />
                <p className="text-xs text-gray-400 mt-2">
                  Your NFT will automatically evolve based on your social media activity every {evolutionPeriod} days.
                </p>
              </FormGroup>
              
              <button
                onClick={handleUpdatePreview}
                disabled={
                  !wallet ||
                  loadingStates.initialData ||
                  loadingStates.nftGeneration ||
                  (mode === 'basic' && (!selectedArtist || !selectedEvent || (getScarcityForCombination(selectedArtist, selectedEvent)?.is_sold_out ?? true))) ||
                  (mode === 'advanced' && !customPrompt.trim())
                }
                className="w-full py-4 text-lg font-bold bg-gradient-to-r from-cyan-500 via-yellow-400 to-pink-500 hover:from-cyan-400 hover:via-yellow-300 hover:to-pink-400 text-black rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {loadingStates.nftGeneration ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    GENERATING NFT...
                  </>
                ) : !wallet ? (
                  <>
                    <Wallet className="w-5 h-5 mr-2" />
                    CONNECT WALLET TO GENERATE
                  </>
                ) : (
                  <>
                    <Zap className="w-5 h-5 mr-2" />
                    GENERATE NFT
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Scarcity Indicator */}
          {selectedArtist && selectedEvent && (
            <div className="max-w-xl mx-auto mb-16">
              <ScarcityIndicator
                artist={selectedArtist}
                eventType={selectedEvent}
                initialTotalSupply={getScarcityForCombination(selectedArtist, selectedEvent)?.total_limit || 0}
                initialRemainingSlots={getScarcityForCombination(selectedArtist, selectedEvent)?.remaining_slots || 0}
                onScarcityChange={(remaining) => {
                  setAllCombinationsScarcity(prev =>
                    prev.map(combo => {
                      if (combo.artist === selectedArtist && combo.event_type === selectedEvent) {
                        const newMintedCount = (combo.scarcity_info?.total_limit || 0) - remaining;
                        const newRemainingSlots = remaining;
                        return {
                          ...combo,
                          scarcity_info: {
                            ...combo.scarcity_info,
                            minted_count: newMintedCount,
                            remaining_slots: newRemainingSlots,
                            is_sold_out: newRemainingSlots <= 0,
                          } as ScarcityInfo,
                          is_available: newRemainingSlots > 0,
                        };
                      }
                      return combo;
                    })
                  );
                }}
              />
            </div>
          )}

          {/* Result Card */}
          {nftResult && (
            <div className="mb-16">
              <h2 className="text-4xl font-bold text-center mb-10 bg-gradient-to-r from-[--electric-blue] to-[--cyber-green] bg-clip-text text-transparent">
                Your Generated NFT
              </h2>
              <div className="flex justify-center">
                <NFTPreview
                  artistStyle={nftResult.artist}
                  eventType={nftResult.event_type}
                  version={`v${nftResult.version}`}
                  timestamp={new Date(nftResult.timestamp * 1000).toLocaleDateString()}
                  imageURI={nftResult.image_uri}
                  prompt={nftResult.prompt}
                  geneticTraits={nftResult.genetic_traits}
                  scarcityInfo={nftResult.scarcity_info}
                  evolutionHistory={nftResult.evolution_history}
                  evolutionPeriodDays={nftResult.evolution_period_days}
                  isAdvancedMode={mode === 'advanced'}
                  onUpdatePreview={handleUpdatePreview}
                />
              </div>
            </div>
          )}

          {/* Features */}
          <div className="text-center space-y-6">
            <h2 className="text-3xl font-bold mb-8 text-[--electric-blue]">Core Features</h2>
            <div className="flex flex-wrap gap-4 justify-center">
              <FeatureTag icon={Palette}>AI-Generated Art</FeatureTag>
              <FeatureTag icon={Wallet}>Wallet Integration</FeatureTag>
              <FeatureTag icon={Star}>Unique Genetic Traits</FeatureTag>
              <FeatureTag icon={Building}>Scarcity Tracking</FeatureTag>
              <FeatureTag icon={User}>Personal Uniqueness</FeatureTag>
              <FeatureTag icon={Zap}>Real-time Generation</FeatureTag>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Index;
