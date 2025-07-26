import React, { useState, useEffect } from 'react';
import { Wallet, Loader, AlertCircle, LogOut, User } from 'lucide-react';

// Wallet type definitions
interface WalletInfo {
  principal: string;
  accountId: string;
  isConnected: boolean;
  balance?: number;
}

interface WalletError {
  code: string;
  message: string;
}

// Mock implementations for @dfinity libraries (kept for functionality)
class MockPrincipal {
  private principalString: string;

  constructor(principalString: string) {
    this.principalString = principalString;
  }

  toString(): string {
    return this.principalString;
  }

  static fromText(text: string): MockPrincipal {
    return new MockPrincipal(text);
  }
}

class MockIdentity {
  private principal: MockPrincipal;

  constructor(principalId: string) {
    this.principal = new MockPrincipal(principalId);
  }

  getPrincipal(): MockPrincipal {
    return this.principal;
  }
}

class MockAuthClient {
  private authenticated: boolean = false;
  private identity: MockIdentity | null = null;

  static async create(): Promise<MockAuthClient> {
    return new MockAuthClient();
  }

  async isAuthenticated(): Promise<boolean> {
    return this.authenticated;
  }

  getIdentity(): MockIdentity {
    if (!this.identity) {
      const mockPrincipalId = this.generateMockPrincipal();
      this.identity = new MockIdentity(mockPrincipalId);
    }
    return this.identity;
  }

  async login(options: {
    identityProvider?: string;
    maxTimeToLive?: bigint;
    onSuccess?: () => void;
    onError?: (error?: string) => void;
  }): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockPrincipalId = this.generateMockPrincipal();
        this.identity = new MockIdentity(mockPrincipalId);
        this.authenticated = true;
        options.onSuccess?.();
        resolve();
      }, 2000);
    });
  }

  async logout(): Promise<void> {
    this.authenticated = false;
    this.identity = null;
  }

  private generateMockPrincipal(): string {
    const chars = 'abcdefghijklmnopqrstuvwxyz234567';
    let result = '';
    for (let i = 0; i < 27; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
      if (i === 4 || i === 9 || i === 14 || i === 19 || i === 24) {
        result += '-';
      }
    }
    return result + '-cai';
  }
}

// Update the props interface to include the new callbacks
interface WalletConnectorProps {
  onWalletConnected: (walletInfo: WalletInfo) => void; // Callback for successful connection
  onWalletDisconnected: () => void; // Callback for successful disconnection
}

interface AuthState {
  isConnected: boolean;
  principal: string | null;
  loading: boolean;
  error: WalletError | null;
}

const WalletConnector: React.FC<WalletConnectorProps> = ({
  onWalletConnected,
  onWalletDisconnected
}) => {
  const [authClient, setAuthClient] = useState<MockAuthClient | null>(null);
  const [authState, setAuthState] = useState<AuthState>({
    isConnected: false,
    principal: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async (): Promise<void> => {
    try {
      const client = await MockAuthClient.create();
      setAuthClient(client);
      await checkAuthStatus(client);
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        loading: false,
        error: {
          code: 'INIT_ERROR',
          message: 'Failed to initialize authentication client'
        }
      }));
    }
  };

  const checkAuthStatus = async (client: MockAuthClient): Promise<void> => {
    try {
      const isAuthenticated = await client.isAuthenticated();

      if (isAuthenticated) {
        const identity = client.getIdentity();
        const principal = identity.getPrincipal().toString();

        const walletInfo: WalletInfo = {
          principal,
          accountId: generateAccountId(principal),
          isConnected: true
        };

        setAuthState({
          isConnected: true,
          principal,
          loading: false,
          error: null
        });

        // Call the onWalletConnected prop here
        onWalletConnected(walletInfo);
      } else {
        setAuthState(prev => ({
          ...prev,
          loading: false
        }));
      }
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        loading: false,
        error: {
          code: 'AUTH_CHECK_ERROR',
          message: 'Failed to check authentication status'
        }
      }));
    }
  };

  const handleConnect = async (): Promise<void> => {
    if (!authClient) {
      setAuthState(prev => ({
        ...prev,
        error: {
          code: 'CLIENT_NOT_READY',
          message: 'Authentication client is not ready'
        }
      }));
      return;
    }

    setAuthState(prev => ({ ...prev, loading: true, error: null }));

    try {
      await new Promise<void>((resolve, reject) => {
        authClient.login({
          identityProvider: process.env.NODE_ENV === 'development'
            ? 'http://localhost:4943/?canisterId=rdmx6-jaaaa-aaaaa-aaadq-cai'
            : 'https://identity.ic0.app',
          maxTimeToLive: BigInt(7 * 24 * 60 * 60 * 1000 * 1000 * 1000),
          onSuccess: () => resolve(),
          onError: (error) => reject(new Error(error || 'Authentication failed'))
        });
      });

      const identity = authClient.getIdentity();
      const principal = identity.getPrincipal().toString();

      const walletInfo: WalletInfo = {
        principal,
        accountId: generateAccountId(principal),
        isConnected: true
      };

      setAuthState({
        isConnected: true,
        principal,
        loading: false,
        error: null
      });

      // Call the onWalletConnected prop here after successful login
      onWalletConnected(walletInfo);
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        loading: false,
        error: {
          code: 'CONNECTION_FAILED',
          message: error instanceof Error ? error.message : 'Failed to connect wallet'
        }
      }));
    }
  };

  const handleDisconnect = async (): Promise<void> => {
    if (!authClient) return;

    setAuthState(prev => ({ ...prev, loading: true, error: null }));

    try {
      await authClient.logout();

      setAuthState({
        isConnected: false,
        principal: null,
        loading: false,
        error: null
      });

      // Call the onWalletDisconnected prop here after successful logout
      onWalletDisconnected();
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        loading: false,
        error: {
          code: 'DISCONNECT_FAILED',
          message: 'Failed to disconnect wallet'
        }
      }));
    }
  };

  const generateAccountId = (principalId: string): string => {
    try {
      const principal = MockPrincipal.fromText(principalId);
      // This is a mock account ID generation. In a real ICP app,
      // account ID is derived from principal and a subaccount (often 0).
      // For simplicity, we'll just use a portion of the principal.
      return principal.toString().substring(0, 32);
    } catch {
      return principalId.substring(0, 32);
    }
  };

  const formatPrincipal = (principal: string): string => {
    if (principal.length <= 12) return principal;
    return `${principal.substring(0, 8)}...${principal.substring(principal.length - 4)}`;
  };

  const clearError = (): void => {
    setAuthState(prev => ({ ...prev, error: null }));
  };

  // This component now only renders the internal connection/disconnection buttons and status
  // It is expected to be wrapped by the ConnectionCard in Index.tsx
  return (
    <div className="w-full">
      {authState.error && (
        <div className="mb-4 p-3 bg-[--error-background] border border-[--error-border] rounded-lg text-[--error-text]">
          <div className="flex items-start space-x-2">
            <AlertCircle className="h-5 w-5 text-[--error-icon] flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">Connection Error</p>
              <p className="text-sm mt-1">{authState.error.message}</p>
              <button
                onClick={clearError}
                className="text-sm underline mt-2 text-[--error-text] hover:opacity-80"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {authState.isConnected && authState.principal ? (
        <div className="space-y-5">
          {/* This section is now handled by the parent ConnectionCard, so we can simplify or remove it here if the parent passes connectionInfo */}
          {/* For now, keeping a simplified version if WalletConnector is used standalone */}
          <div className="p-4 bg-[--cyber-green]/10 border border-[--cyber-green]/30 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <User className="h-5 w-5 text-[--cyber-green]" />
              <span className="text-base font-medium text-[--cyber-green]">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[--secondary-text]">Principal ID:</p>
                <p className="font-mono text-sm text-[--electric-blue] break-all">
                  {formatPrincipal(authState.principal)}
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={handleDisconnect}
            disabled={authState.loading}
            className="w-full flex items-center justify-center space-x-2 px-6 py-3 rounded-lg transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed
                       bg-[--background-secondary] border border-[--border] text-[--secondary-text] font-medium text-base hover:bg-[--background-secondary]/80 hover:border-[--neon-purple]"
          >
            {authState.loading ? (
              <>
                <Loader className="h-5 w-5 animate-spin text-[--muted-text]" />
                <span>Disconnecting...</span>
              </>
            ) : (
              <>
                <LogOut className="h-5 w-5 text-[--muted-text]" />
                <span>Disconnect</span>
              </>
            )}
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          <button
            onClick={handleConnect}
            disabled={authState.loading}
            className="w-full flex items-center justify-center space-x-2 px-6 py-3 rounded-lg transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed
                       bg-gradient-to-r from-[--electric-blue] to-[--neon-purple] text-[--primary-text] font-medium text-base shadow-lg hover:shadow-xl animate-pulse-glow"
          >
            {authState.loading ? (
              <>
                <Loader className="h-5 w-5 animate-spin" />
                <span>Connecting...</span>
              </>
            ) : (
              <>
                <Wallet className="h-5 w-5" />
                <span>Connect Wallet</span>
              </>
            )}
          </button>

          <p className="text-xs text-[--muted-text] text-center leading-relaxed">
            Connect securely with Internet Identity to access your ICP wallet and manage NFTs.
            Your data stays private and secure.
          </p>
        </div>
      )}
    </div>
  );
};

export default WalletConnector;
