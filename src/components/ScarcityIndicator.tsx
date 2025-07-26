// src/components/ScarcityIndicator.tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import io from 'socket.io-client';

// Define the socket type
type SocketType = ReturnType<typeof io>;
import { cn } from '@/lib/utils'; // Assuming you have a utility for class concatenation
import { AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert'; // Assuming you have Shadcn Alert components
import { Progress } from '@/components/ui/progress'; // Assuming you have a Shadcn Progress component

// Define the props interface for ScarcityIndicator
interface ScarcityIndicatorProps {
  artist: string;
  eventType: string;
  initialTotalSupply: number; // Initial total supply
  initialRemainingSlots: number; // Initial remaining slots
  onScarcityChange?: (remaining: number) => void;
}

// Define the WebSocket message interface for scarcity updates
interface ScarcityUpdateMessage {
  artist: string;
  event_type: string;
  remaining_slots: number;
  total_supply: number;
  is_available: boolean;
  timestamp: number;
}

// Custom hook for WebSocket connection management
const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<SocketType | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reconnectAttempts = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_INTERVAL_MS = 3000; // 3 seconds

  useEffect(() => {
    if (socket && socket.connected) {
      return;
    }
    const newSocket = io(url, {
      transports: ['websocket'],
      reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
      reconnectionDelay: RECONNECT_INTERVAL_MS,
    });

    newSocket.on('connect', () => {
      setIsConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
      console.log('WebSocket connected:', newSocket.id);
    });

    newSocket.on('disconnect', (reason) => {
      setIsConnected(false);
      console.warn('WebSocket disconnected:', reason);
      if (reason === 'io server disconnect') {
        // The server initiated the disconnect, so don't try to reconnect
        setError('Disconnected by server. Please refresh the page.');
      } else {
        // Otherwise, reconnect attempts will be made by the client automatically
        setError('WebSocket disconnected. Attempting to reconnect...');
      }
    });

    newSocket.on('connect_error', (err) => {
      console.error('WebSocket connection error:', err);
      setError(`Connection failed: ${err.message}. Retrying...`);
      // The socket.io client handles reconnection attempts automatically
    });

    setSocket(newSocket);

    // Cleanup on unmount
    return () => {
      newSocket.disconnect();
    };
  }, [url]);

  return { socket, isConnected, error };
};

const ScarcityIndicator: React.FC<ScarcityIndicatorProps> = ({
  artist,
  eventType,
  initialTotalSupply,
  initialRemainingSlots,
  onScarcityChange,
}) => {
  const [remainingSlots, setRemainingSlots] = useState(initialRemainingSlots);
  const [totalSupply, setTotalSupply] = useState(initialTotalSupply);

  // Use the custom WebSocket hook
  const { socket, isConnected, error: wsError } = useWebSocket('http://localhost:5000'); // Your backend WebSocket URL

  // Calculate percentage for progress bar
  const percentage = totalSupply > 0 ? (remainingSlots / totalSupply) * 100 : 0;

  // Determine color based on scarcity level
  const indicatorColorClass = useCallback(() => {
    if (remainingSlots <= 0) return 'bg-[--error]';
    if (percentage < 20) return 'bg-gradient-to-r from-[--warning] to-[--hot-pink]'; // Warning Gradient
    if (percentage < 50) return 'bg-[--warning]'; // Yellowish for medium scarcity
    return 'bg-gradient-to-r from-[--cyber-green] to-[--success]'; // Success Gradient
  }, [remainingSlots, percentage]);

  useEffect(() => {
    // Update local state when initial props change (e.g., when user selects a new combination)
    setRemainingSlots(initialRemainingSlots);
    setTotalSupply(initialTotalSupply);
  }, [initialRemainingSlots, initialTotalSupply]);


  useEffect(() => {
    if (socket && isConnected) {
      // Join the specific scarcity room for this artist-event combination
      const roomData = { artist, event_type: eventType };
      socket.emit('join_scarcity_room', roomData);
      console.log(`Attempting to join scarcity room: scarcity-${artist}-${eventType}`);

      // Listen for scarcity updates
      const handleScarcityUpdate = (data: ScarcityUpdateMessage) => {
        // Ensure the update is for the current combination
        if (data.artist === artist && data.event_type === eventType) {
          console.log('Received scarcity update:', data);
          setRemainingSlots(data.remaining_slots);
          setTotalSupply(data.total_supply); // Update total supply if it can change
          if (onScarcityChange) {
            onScarcityChange(data.remaining_slots);
          }
        }
      };

      socket.on('scarcity_update', handleScarcityUpdate);

      // Cleanup on unmount or when artist/eventType changes
      return () => {
        if (socket && socket.connected) {
        socket.off('scarcity_update', handleScarcityUpdate);
        socket.emit('leave_scarcity_room', roomData);
        console.log(`Leaving scarcity room: scarcity-${artist}-${eventType}`);
        }
      };
    }
  }, [socket, artist, eventType, onScarcityChange, isConnected]);

  return (
    <div className="glassmorphism p-6 rounded-xl shadow-[--nft-shadow] border border-[--border] animate-fade-in">
      <h3 className="text-xl font-semibold mb-3 text-[--primary-text]">
        Scarcity for <span className="text-[--electric-blue]">{artist}</span> - <span className="text-[--neon-purple]">{eventType.charAt(0).toUpperCase() + eventType.slice(1)}</span>
      </h3>

      {/* WebSocket Connection Status */}
      {wsError && (
        <Alert variant="destructive" className="mb-4 glassmorphism bg-[--error-background] border-[--error-border] text-[--error-text] text-sm">
          <AlertCircle className="h-4 w-4 text-[--error-icon]" />
          <AlertDescription>{wsError}</AlertDescription>
        </Alert>
      )}
      {!isConnected && !wsError && (
        <Alert className="mb-4 glassmorphism border-[--warning]/50 text-[--primary-text] text-sm">
          <WifiOff className="h-4 w-4 text-[--warning]" />
          <AlertDescription className="text-[--secondary-text]">Connecting to real-time updates...</AlertDescription>
        </Alert>
      )}
      {isConnected && !wsError && (
        <Alert className="mb-4 glassmorphism border-[--cyber-green]/50 text-[--primary-text] text-sm">
          <Wifi className="h-4 w-4 text-[--cyber-green]" />
          <AlertDescription className="text-[--secondary-text]">Live updates active.</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center justify-between mb-3">
        <span className="text-base text-[--secondary-text]">Slots Remaining:</span>
        <span className={cn(
            "font-bold text-3xl transition-colors duration-300",
            remainingSlots <= 0 ? "text-[--error]" : percentage < 20 ? "text-[--hot-pink]" : percentage < 50 ? "text-[--warning]" : "text-[--cyber-green]"
          )}>
          {remainingSlots} / {totalSupply}
        </span>
      </div>

      <div className="relative h-8 bg-[--background-secondary] rounded-full overflow-hidden border border-[--border]" aria-label={`Scarcity level: ${percentage.toFixed(0)}%`}>
        <Progress
          value={percentage}
          className={cn("h-full transition-all duration-500 ease-out", indicatorColorClass())}
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
        />
        <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-[--primary-text] mix-blend-difference">
          {percentage.toFixed(0)}%
        </div>
      </div>

      {remainingSlots <= 0 && (
        <p className="text-base text-[--error] mt-4 font-semibold text-center animate-pulse">
          SOLD OUT!
        </p>
      )}
      {remainingSlots > 0 && percentage < 10 && (
        <p className="text-base text-[--warning] mt-4 font-semibold text-center">
          Very Limited! Act Fast!
        </p>
      )}
    </div>
  );
};

export default ScarcityIndicator;
