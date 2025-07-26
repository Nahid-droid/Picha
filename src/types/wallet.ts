/**
 * Wallet integration interfaces for React NFT application on Internet Computer Protocol (ICP)
 */

/**
 * Represents wallet information for ICP-based wallets
 * Contains essential wallet data including principal ID and account identifier
 */
export interface WalletInfo {
  /** ICP principal ID - unique identifier for the wallet on Internet Computer */
  principal: string;
  
  /** ICP account identifier - account-specific identifier derived from principal */
  accountId: string;
  
  /** Whether the wallet is currently connected to the application */
  isConnected: boolean;
  
  /** Optional ICP token balance in e8s (1 ICP = 100,000,000 e8s) */
  balance?: number;
}

/**
 * Represents wallet-related errors that can occur during wallet operations
 * Provides structured error information for proper error handling
 */
export interface WalletError {
  /** Error code for programmatic error identification */
  code: string;
  
  /** Human-readable error message for display or logging */
  message: string;
}

/**
 * Represents the complete state of wallet integration in the application
 * Used for managing wallet connection status, loading states, and errors
 */
export interface WalletState {
  /** Current wallet information, null if no wallet is connected */
  wallet: WalletInfo | null;
  
  /** Whether wallet operations (connect, disconnect, balance fetch) are in progress */
  loading: boolean;
  
  /** Current wallet error state, null if no error */
  error: WalletError | null;
}

/**
 * ICP-specific type definitions for Internet Computer Protocol integration
 */

/** ICP Principal ID type - string representation of a principal */
export type ICPPrincipal = string;

/** ICP Account Identifier type - hex string representation */
export type ICPAccountId = string;

/** ICP balance in e8s (smallest unit: 1 ICP = 100,000,000 e8s) */
export type ICPBalance = number;

/**
 * Common wallet operation result type for consistent return values
 */
export interface WalletOperationResult<T = unknown> {
  /** Whether the operation was successful */
  success: boolean;
  
  /** Result data if operation was successful */
  data?: T;
  
  /** Error information if operation failed */
  error?: WalletError;
}

/**
 * Wallet connection parameters for different wallet providers
 */
export interface WalletConnectionParams {
  /** Wallet provider name (e.g., 'plug', 'stoic', 'bitfinity') */
  provider: string;
  
  /** Optional host URL for wallet connection */
  host?: string;
  
  /** Optional timeout for connection attempts in milliseconds */
  timeout?: number;
}