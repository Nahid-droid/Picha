import React from 'react';
import { Loader2, Coins, Sparkles } from 'lucide-react';

interface MintButtonProps {
  isLoading?: boolean;
  disabled?: boolean;
  onMint: () => void;
  // artistStyle?: string; // Removed as per new design, parent handles this
  // eventType?: string;   // Removed as per new design, parent handles this
}

const MintButton: React.FC<MintButtonProps> = ({
  isLoading = false,
  disabled = false,
  onMint,
}) => {
  const internalDisabled = disabled || isLoading;

  return (
    <button
      onClick={onMint}
      disabled={internalDisabled}
      className="w-full py-4 text-lg font-bold bg-gradient-to-r from-cyan-500 via-yellow-400 to-pink-500 hover:from-cyan-400 hover:via-yellow-300 hover:to-pink-400 text-black rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
    >
      {isLoading ? (
        <>
          <Loader2 className="w-5 h-5 mr-2 animate-spin" />
          Minting NFT...
        </>
      ) : (
        <>
          <Coins className="w-5 h-5 mr-2 group-hover:rotate-12 transition-transform duration-300" />
          Mint NFT
          <Sparkles className="w-5 h-5 ml-2 group-hover:scale-110 transition-transform duration-300" />
        </>
      )}
    </button>
  );
};

export default MintButton;
