import sqlite3
import json
import time
import logging
from threading import Lock
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid # Import the uuid module

# Import the new SocialMediaAuth data model
from models.data_models import SocialMediaAuth, UniquenessFactors, GeneticTraits, ScarcityInfo # Ensure all are imported for data parsing

logger = logging.getLogger(__name__)
db_lock = Lock()

class DatabaseManager:
    """Database management for NFT storage and social media tokens"""
    
    def __init__(self, db_path: str = "nft_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            self.conn = conn # Store connection for other methods
            self.create_tables() # Call the updated create_tables method
            
    def create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nfts (
                id TEXT PRIMARY KEY,
                owner_address TEXT NOT NULL,
                artist TEXT NOT NULL,
                event_type TEXT NOT NULL,
                mode TEXT NOT NULL,
                user_prompt TEXT,
                name TEXT NOT NULL,
                description TEXT,
                image_url TEXT,
                metadata TEXT,
                genetic_traits TEXT,
                scarcity_info TEXT,
                evolution_history TEXT,
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                canister_nft_id TEXT,
                canister_status TEXT,
                uniqueness_factors TEXT,
                last_evolution_time TEXT,
                evolution_period_days INTEGER DEFAULT 30
            )
        """)
        
        # Add evolution_period_days column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE nfts ADD COLUMN evolution_period_days INTEGER DEFAULT 30")
            logger.info("Added 'evolution_period_days' column to 'nfts' table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("Column 'evolution_period_days' already exists in 'nfts' table.")
            else:
                logger.error(f"Error adding 'evolution_period_days' column: {e}")

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS combination_counts (
                combination TEXT PRIMARY KEY,
                minted_count INTEGER DEFAULT 0,
                total_limit INTEGER
            )
        ''')
        # Initialize default combinations on startup if they don't exist
        for combo, limit in self.get_default_combination_limits().items():
            # Check if combination exists, if not, insert with minted_count 0
            cursor.execute("INSERT OR IGNORE INTO combination_counts (combination, minted_count, total_limit) VALUES (?, ?, ?)", (combo, 0, limit))
        self.conn.commit()
        print("DB: combination_counts table created/ensured with default 0 count.") # ADD THIS PRINT

        # Check for existing combinations and maybe log them
        cursor.execute("SELECT * FROM combination_counts")
        existing_combos = cursor.fetchall()
        print(f"DB: Initial state of combination_counts after creation/check: {existing_combos}") # ADD THIS PRINT
        print("DB: All combinations initialized/updated")
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS waitlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                combination TEXT,
                user_address TEXT,
                timestamp INTEGER,
                email TEXT,
                notification_sent INTEGER DEFAULT 0,
                UNIQUE(combination, user_address)
            )
        ''')

        # NEW TABLE: Social Media Authentication Tokens
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS social_media_auth (
                wallet_principal TEXT NOT NULL,
                platform TEXT NOT NULL,
                social_user_id TEXT NOT NULL,
                username TEXT,
                encrypted_access_token TEXT NOT NULL, -- Stores the encrypted combined tokens
                last_updated TEXT NOT NULL,
                PRIMARY KEY (wallet_principal, platform) -- Composite primary key
            )
        ''')

        # NEW TABLE: Social Media Metrics (for NFT evolution influence)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS social_media_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_principal TEXT NOT NULL, -- Link to the user who owns the social account
                platform TEXT NOT NULL,
                timestamp TEXT NOT NULL, -- When these metrics were logged
                metric_type TEXT NOT NULL, -- e.g., 'tweet_sentiment', 'engagement_score', 'tweet_frequency'
                metric_value REAL,         -- Numeric value of the metric
                details TEXT,              -- JSON string for more details (e.g., raw tweet text, sentiment breakdown)
                FOREIGN KEY (wallet_principal, platform) REFERENCES social_media_auth(wallet_principal, platform)
            )
        ''')


        self.conn.commit() # Commit changes after creating tables

    # Helper for default combination limits
    def get_default_combination_limits(self) -> Dict[str, int]:
        return {
            "Da Vinci-architecture": 100,
            "Da Vinci-portrait": 150,
            "Van Gogh-nature": 200,
            "Van Gogh-abstract": 120,
            "Picasso-abstract": 80,
            "Picasso-portrait": 100,
            "Monet-nature": 250,
            "Dali-fantasy": 75,
            "Da Vinci-nature": 120,
            "Van Gogh-cosmic": 90,
            "Picasso-urban": 110,
            "Monet-historical": 180,
            "Dali-cosmic": 85
        }

    # NEW METHOD: Generate a unique ID for NFTs
    def generate_unique_id(self) -> str:
        """
        Generates a unique ID for an NFT using UUID4.
        """
        return str(uuid.uuid4())

    def save_nft(self, nft_id: str, owner_address: str, artist: str, event_type: str,
                 mode: str, name: str, image_url: str,
                 genetic_traits: str, scarcity_info: str, evolution_history: str,
                 uniqueness_factors: str, last_evolution_time: str,
                 evolution_period_days: int,
                 user_prompt: Optional[str] = None, description: Optional[str] = None,
                 metadata: Optional[str] = None, version: int = 1,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None,
                 canister_id: Optional[str] = None, canister_status: Optional[str] = None):
        """Save NFT to database, including evolution period."""
        if created_at is None:
            created_at = datetime.now().isoformat()
        if updated_at is None:
            updated_at = datetime.now().isoformat()

        with db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO nfts 
                    (id, owner_address, artist, event_type, mode, user_prompt, name, description, 
                     image_url, metadata, genetic_traits, scarcity_info, evolution_history, 
                     version, created_at, updated_at, canister_nft_id, canister_status, 
                     uniqueness_factors, last_evolution_time, evolution_period_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    nft_id,
                    owner_address,
                    artist,
                    event_type,
                    mode,
                    user_prompt,
                    name,
                    description,
                    image_url,
                    metadata,
                    genetic_traits,
                    scarcity_info,
                    evolution_history,
                    version,
                    created_at,
                    updated_at,
                    canister_id,
                    canister_status,
                    uniqueness_factors,
                    last_evolution_time,
                    evolution_period_days
                ))
                conn.commit()
                logger.info(f"NFT {nft_id} saved/updated in DB with evolution_period_days: {evolution_period_days}")
    
    def get_nft(self, nft_id: str) -> Optional[dict]:
        """Get NFT by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM nfts WHERE id = ?', (nft_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                nft_dict = dict(zip(columns, row))
                # Parse JSON fields
                if nft_dict.get('metadata'):
                    nft_dict['metadata'] = json.loads(nft_dict['metadata'])
                if nft_dict.get('genetic_traits'):
                    nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
                if nft_dict.get('scarcity_info'):
                    nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
                if nft_dict.get('evolution_history'):
                    nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
                if nft_dict.get('uniqueness_factors'):
                    nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
                return nft_dict
        return None
    
    def get_user_nfts(self, owner_address: str) -> List[dict]:
        """Get all NFTs for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM nfts WHERE owner_address = ?', (owner_address,))
            rows = cursor.fetchall()
            
            nfts = []
            columns = [description[0] for description in cursor.description]
            for row in rows:
                nft_dict = dict(zip(columns, row))
                # Parse JSON fields
                if nft_dict.get('metadata'):
                    nft_dict['metadata'] = json.loads(nft_dict['metadata'])
                if nft_dict.get('genetic_traits'):
                    nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
                if nft_dict.get('scarcity_info'):
                    nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
                if nft_dict.get('evolution_history'):
                    nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
                if nft_dict.get('uniqueness_factors'):
                    nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
                nfts.append(nft_dict)
            
            return nfts
    
    def update_combination_count(self, combination: str, total_limit: int = 100):
        """Update combination count"""
        with db_lock:
            with sqlite3.connect(self.db_path) as conn:
                # Check if it exists first
                cursor = conn.execute('SELECT minted_count, total_limit FROM combination_counts WHERE combination = ?', (combination,))
                row = cursor.fetchone()

                if not row: # If combination doesn't exist, insert it with count 0
                    conn.execute('''
                        INSERT INTO combination_counts (combination, minted_count, total_limit)
                        VALUES (?, 0, ?)
                    ''', (combination, total_limit))
                    print(f"DB: Initialized new combination '{combination}' with count 0 and limit {total_limit}.")

                # Now, update the count
                conn.execute('''
                    UPDATE combination_counts
                    SET minted_count = minted_count + 1
                    WHERE combination = ?
                ''', (combination,))
                conn.commit()
                print(f"DB: Incremented count for '{combination}'.")
    
    def get_combination_count(self, combination: str) -> tuple:
        """Get combination count and limit"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT minted_count, total_limit 
                FROM combination_counts 
                WHERE combination = ?
            ''', (combination,))
            row = cursor.fetchone()
            
            if row:
                print(f"DB: get_combination_count for '{combination}' returned: {row[0]}, {row[1]}")
                return row[0], row[1]
            print(f"DB: get_combination_count for '{combination}' not found, returning 0, 100.")
            return 0, 100  # Default values

    def add_to_waitlist(self, combination: str, user_address: str, email: str = None) -> bool:
        """Add user to waitlist for a combination"""
        try:
            with db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR IGNORE INTO waitlists 
                        (combination, user_address, timestamp, email)
                        VALUES (?, ?, ?, ?)
                    ''', (combination, user_address, int(time.time()), email))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error adding to waitlist: {e}")
            return False

    def get_waitlist(self, combination: str) -> List[dict]:
        """Get waitlist for a combination"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT user_address, timestamp, email 
                FROM waitlists 
                WHERE combination = ?
                ORDER BY timestamp ASC
            ''', (combination,))
            
            waitlist = []
            for row in cursor.fetchall():
                waitlist.append({
                    'user_address': row[0],
                    'timestamp': row[1],
                    'email': row[2]
                })
            
            return waitlist

    def get_all_nfts(self):
        """Get all NFTs from database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM nfts ORDER BY created_at DESC
        """)
        
        columns = [description[0] for description in cursor.description]
        nfts = []
        
        for row in cursor.fetchall():
            nft_dict = dict(zip(columns, row))
            # Parse JSON fields
            if nft_dict.get('metadata'):
                nft_dict['metadata'] = json.loads(nft_dict['metadata'])
            if nft_dict.get('genetic_traits'):
                nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
            if nft_dict.get('scarcity_info'):
                nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
            if nft_dict.get('evolution_history'):
                nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
            if nft_dict.get('uniqueness_factors'):
                nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
            
            nfts.append(nft_dict)
        
        return nfts
    
    def update_nft_canister_info(self, local_nft_id, canister_nft_id, status):
        """Method to update NFT with canister information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE nfts 
                SET canister_nft_id = ?, canister_status = ?, updated_at = ?
                WHERE id = ?
            """, (canister_nft_id, status, datetime.now().isoformat(), local_nft_id))
            
            conn.commit()
            return cursor.rowcount > 0

    def get_nfts_by_canister_status(self, status: str) -> List[dict]:
        """Get NFTs by their canister sync status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM nfts WHERE canister_status = ? ORDER BY created_at ASC', (status,))
            rows = cursor.fetchall()
            
            nfts = []
            columns = [description[0] for description in cursor.description]
            for row in rows:
                nft_dict = dict(zip(columns, row))
                # Parse JSON fields
                if nft_dict.get('metadata'):
                    nft_dict['metadata'] = json.loads(nft_dict['metadata'])
                if nft_dict.get('genetic_traits'):
                    nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
                if nft_dict.get('scarcity_info'):
                    nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
                if nft_dict.get('evolution_history'):
                    nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
                if nft_dict.get('uniqueness_factors'):
                    nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
                nfts.append(nft_dict)
            return nfts

    def update_nft_canister_status(self, nft_id: str, canister_id: Optional[str], status: str):
        """Update NFT's canister ID and status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE nfts 
                SET canister_nft_id = ?, canister_status = ?, updated_at = ?
                WHERE id = ?
            """, (canister_id, status, datetime.now().isoformat(), nft_id))
            conn.commit()

    def get_nft_by_canister_id(self, canister_id: str) -> Optional[dict]:
        """Get NFT by canister_nft_id"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM nfts WHERE canister_nft_id = ?', (canister_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                nft_dict = dict(zip(columns, row))
                # Parse JSON fields
                if nft_dict.get('metadata'):
                    nft_dict['metadata'] = json.loads(nft_dict['metadata'])
                if nft_dict.get('genetic_traits'):
                    nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
                if nft_dict.get('scarcity_info'):
                    nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
                if nft_dict.get('evolution_history'):
                    nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
                if nft_dict.get('uniqueness_factors'):
                    nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
                return nft_dict
        return None
    
    def get_pending_canister_mints(self):
        """Get NFTs that are pending canister minting"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM nfts 
            WHERE canister_status = 'pending_retry'
            ORDER BY created_at ASC
        """)
        
        columns = [description[0] for description in cursor.description]
        nfts = []
        
        for row in cursor.fetchall():
            nft_dict = dict(zip(columns, row))
            # Parse JSON fields
            if nft_dict.get('metadata'):
                nft_dict['metadata'] = json.loads(nft_dict['metadata'])
            if nft_dict.get('genetic_traits'):
                nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
            if nft_dict.get('scarcity_info'):
                nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
            if nft_dict.get('evolution_history'):
                nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
            if nft_dict.get('uniqueness_factors'):
                nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
            
            nfts.append(nft_dict)
        
        return nfts
    
    def get_failed_canister_mints(self):
        """Get NFTs that failed canister minting"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM nfts 
            WHERE canister_status IN ('failed', 'error', 'pending_retry')
            ORDER BY created_at ASC
        """)
        
        columns = [description[0] for description in cursor.description]
        nfts = []
        
        for row in cursor.fetchall():
            nft_dict = dict(zip(columns, row))
            # Parse JSON fields
            if nft_dict.get('metadata'):
                nft_dict['metadata'] = json.loads(nft_dict['metadata'])
            if nft_dict.get('genetic_traits'):
                nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
            if nft_dict.get('scarcity_info'):
                nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
            if nft_dict.get('evolution_history'):
                nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
            if nft_dict.get('uniqueness_factors'):
                nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
            
            nfts.append(nft_dict)
        
        return nfts
    
    def get_canister_sync_stats(self):
        """Get statistics about canister sync status"""
        cursor = self.conn.cursor()
        
        # Get counts by canister status
        cursor.execute("""
            SELECT 
                canister_status,
                COUNT(*) as count
            FROM nfts 
            GROUP BY canister_status
        """)
        
        stats = {}
        total_nfts = 0
        
        for row in cursor.fetchall():
            status, count = row
            stats[status or 'unknown'] = count
            total_nfts += count
        
        # Calculate percentages
        if total_nfts > 0:
            for status in stats:
                stats[status] = {
                    'count': stats[status],
                    'percentage': (stats[status] / total_nfts) * 100
                }
        
        return {
            'total_nfts': total_nfts,
            'status_breakdown': stats,
            'minted_percentage': stats.get('minted', {}).get('percentage', 0)
        }

    # ====================================================================
    # NEW METHODS FOR SOCIAL MEDIA AUTH AND METRICS
    # ====================================================================

    def save_social_media_auth(self, auth_data: SocialMediaAuth):
        """
        Saves or updates a user's social media authentication data.
        """
        with db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO social_media_auth 
                    (wallet_principal, platform, social_user_id, username, encrypted_access_token, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    auth_data.wallet_principal,
                    auth_data.platform,
                    auth_data.social_user_id,
                    auth_data.username,
                    auth_data.encrypted_access_token,
                    auth_data.last_updated
                ))
                conn.commit()
                logger.info(f"Social media auth saved/updated for {auth_data.platform} user: {auth_data.username}")

    def get_social_media_auth(self, wallet_principal: str, platform: str) -> Optional[SocialMediaAuth]:
        """
        Retrieves a user's social media authentication data for a specific platform.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT wallet_principal, platform, social_user_id, username, encrypted_access_token, last_updated
                FROM social_media_auth
                WHERE wallet_principal = ? AND platform = ?
            ''', (wallet_principal, platform))
            
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                auth_dict = dict(zip(columns, row))
                return SocialMediaAuth(**auth_dict)
            return None

    def delete_social_media_auth(self, wallet_principal: str, platform: str) -> bool:
        """
        Deletes a user's social media authentication data for a specific platform.
        """
        with db_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM social_media_auth
                    WHERE wallet_principal = ? AND platform = ?
                ''', (wallet_principal, platform))
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"Social media auth deleted for {platform} and wallet {wallet_principal}")
                    return True
                logger.info(f"No social media auth found to delete for {platform} and wallet {wallet_principal}")
                return False

    def save_social_media_metric(self, wallet_principal: str, platform: str, 
                                 metric_type: str, metric_value: float, details: Optional[Dict] = None):
        """
        Saves a specific social media metric for a user.
        """
        with db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO social_media_metrics 
                    (wallet_principal, platform, timestamp, metric_type, metric_value, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    wallet_principal,
                    platform,
                    datetime.now().isoformat(),
                    metric_type,
                    metric_value,
                    json.dumps(details) if details else None
                ))
                conn.commit()
                logger.debug(f"Saved metric {metric_type} for {platform} user {wallet_principal}")

    def get_social_media_metrics(self, wallet_principal: str, platform: str, 
                                 metric_type: Optional[str] = None, 
                                 since_timestamp: Optional[str] = None,
                                 limit: int = 100) -> List[Dict]:
        """
        Retrieves social media metrics for a user, optionally filtered by type and time.
        """
        with sqlite3.connect(self.db_path) as conn:
            query = '''
                SELECT timestamp, metric_type, metric_value, details
                FROM social_media_metrics
                WHERE wallet_principal = ? AND platform = ?
            '''
            params = [wallet_principal, platform]

            if metric_type:
                query += ' AND metric_type = ?'
                params.append(metric_type)
            if since_timestamp:
                query += ' AND timestamp >= ?'
                params.append(since_timestamp)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)

            cursor = conn.execute(query, tuple(params))
            
            metrics = []
            for row in cursor.fetchall():
                metric = {
                    'timestamp': row[0],
                    'metric_type': row[1],
                    'metric_value': row[2],
                    'details': json.loads(row[3]) if row[3] else None
                }
                metrics.append(metric)
            return metrics

    # NEW METHOD: get_all_combinations (already added in previous turn)
    def get_all_combinations(self) -> List[Dict[str, Any]]:
        """
        Retrieves all unique artist-event type combinations from the combination_counts table.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT combination, total_limit, minted_count FROM combination_counts')
            rows = cursor.fetchall()
            print(f"DB: get_all_combinations raw rows: {rows}")
            combinations = []
            for row in rows:
                combo_str = row[0]
                parts = combo_str.split('-')
                if len(parts) == 2:
                    artist = parts[0]
                    event_type_value = parts[1]
                    combinations.append({
                        "artist": artist,
                        "event_type": event_type_value,
                        "total_limit": row[1],
                        "minted_count": row[2]
                    })
            print(f"DB: get_all_combinations processed: {combinations}")
            return combinations
            
    # NEW METHOD: get_waitlist_count
    def get_waitlist_count(self, combination: str) -> int:
        """
        Retrieves the number of users in the waitlist for a specific combination.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM waitlists WHERE combination = ?
            ''', (combination,))
            count = cursor.fetchone()[0]
            return count

    def get_nfts_due_for_evolution(self) -> List[Dict[str, Any]]:
        """
        Retrieves NFTs that are due for evolution based on their last_evolution_time
        and evolution_period_days.
        """
        nfts_due = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, owner_address, artist, event_type, mode, user_prompt, name, description, 
                       image_url, metadata, genetic_traits, scarcity_info, evolution_history, 
                       version, created_at, updated_at, canister_nft_id, canister_status, 
                       uniqueness_factors, last_evolution_time, evolution_period_days
                FROM nfts
                WHERE last_evolution_time IS NOT NULL AND evolution_period_days IS NOT NULL
            """)
            
            columns = [description[0] for description in cursor.description]
            for row in cursor.fetchall():
                nft_dict = dict(zip(columns, row))
                
                last_evolution_time = datetime.fromisoformat(nft_dict['last_evolution_time'])
                evolution_period_days = nft_dict['evolution_period_days']
                
                # Calculate next evolution time
                next_evolution_time = last_evolution_time + timedelta(days=evolution_period_days)
                
                if datetime.now() >= next_evolution_time:
                    # Parse JSON fields before adding to list
                    if nft_dict.get('metadata'):
                        nft_dict['metadata'] = json.loads(nft_dict['metadata'])
                    if nft_dict.get('genetic_traits'):
                        nft_dict['genetic_traits'] = json.loads(nft_dict['genetic_traits'])
                    if nft_dict.get('scarcity_info'):
                        nft_dict['scarcity_info'] = json.loads(nft_dict['scarcity_info'])
                    if nft_dict.get('evolution_history'):
                        nft_dict['evolution_history'] = json.loads(nft_dict['evolution_history'])
                    if nft_dict.get('uniqueness_factors'):
                        nft_dict['uniqueness_factors'] = json.loads(nft_dict['uniqueness_factors'])
                        
                    nfts_due.append(nft_dict)
        return nfts_due

    def update_nft_on_evolution(self, nft_id: str, new_version: int, new_image_url: str,
                                new_genetic_traits: str, new_evolution_history: str,
                                new_last_evolution_time: str):
        """
        Updates NFT fields after an evolution event.
        """
        with db_lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE nfts
                    SET version = ?,
                        image_url = ?,
                        genetic_traits = ?,
                        evolution_history = ?,
                        last_evolution_time = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (new_version, new_image_url, new_genetic_traits,
                      new_evolution_history, new_last_evolution_time,
                      datetime.now().isoformat(), nft_id))
                conn.commit()
                logger.info(f"NFT {nft_id} updated locally after evolution to version {new_version}")