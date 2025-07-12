import sqlite3
import aiosqlite
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
import asyncio
from utils.logger import setup_logger

logger = setup_logger()

class DatabaseManager:
    def __init__(self, db_path: str = "database/cardcaptor.db"):
        self.db_path = db_path
        self.ensure_database_directory()
    
    def ensure_database_directory(self):
        """Ensure the database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    async def initialize_database(self):
        """Initialize the database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    rarity TEXT DEFAULT 'common',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    card_id INTEGER NOT NULL,
                    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (card_id) REFERENCES cards (id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS spawned_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL,
                    spawned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    claimed BOOLEAN DEFAULT FALSE,
                    claimed_by INTEGER,
                    claimed_at TIMESTAMP,
                    FOREIGN KEY (card_id) REFERENCES cards (id)
                )
            ''')
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def get_random_cards(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get random cards from the art folder"""
        art_folder = "art"
        if not os.path.exists(art_folder):
            logger.error(f"Art folder '{art_folder}' does not exist")
            return []
        
        # Get all image files from art folder
        image_files = [f for f in os.listdir(art_folder) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        
        if len(image_files) < count:
            logger.warning(f"Not enough images in art folder. Found {len(image_files)}, need {count}")
            count = len(image_files)
        
        # Randomly select images
        import random
        selected_files = random.sample(image_files, count)
        
        cards = []
        for file in selected_files:
            # Extract card name from filename (remove extension)
            card_name = os.path.splitext(file)[0].replace('_', ' ').title()
            
            cards.append({
                'id': len(cards) + 1,  # Temporary ID for this spawn
                'name': card_name,
                'image_path': os.path.join(art_folder, file),
                'rarity': self._determine_rarity()
            })
        
        return cards
    
    def _determine_rarity(self) -> str:
        """Determine card rarity randomly"""
        import random
        rarities = ['common', 'uncommon', 'rare', 'epic', 'legendary']
        weights = [50, 30, 15, 4, 1]  # Percentage weights
        return random.choices(rarities, weights=weights)[0]
    
    async def create_spawn_session(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create a new spawn session with cards"""
        async with aiosqlite.connect(self.db_path) as db:
            updated_cards = []
            
            for card in cards:
                # Insert spawned card record
                cursor = await db.execute('''
                    INSERT INTO spawned_cards (card_id, spawned_at, claimed)
                    VALUES (?, ?, FALSE)
                ''', (card['id'], datetime.now()))
                
                spawn_id = cursor.lastrowid
                
                # Update card with spawn ID
                card['spawn_id'] = spawn_id
                updated_cards.append(card)
            
            await db.commit()
            return updated_cards
    
    async def claim_card(self, spawn_id: int, user_id: int, username: str) -> bool:
        """Claim a spawned card"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if card is already claimed
            cursor = await db.execute('''
                SELECT claimed FROM spawned_cards WHERE id = ?
            ''', (spawn_id,))
            
            result = await cursor.fetchone()
            if not result or result[0]:  # Card doesn't exist or already claimed
                return False
            
            # Claim the card
            await db.execute('''
                UPDATE spawned_cards 
                SET claimed = TRUE, claimed_by = ?, claimed_at = ?
                WHERE id = ?
            ''', (user_id, datetime.now(), spawn_id))
            
            # Add to user's collection
            await db.execute('''
                INSERT INTO user_cards (user_id, username, card_id, claimed_at)
                SELECT ?, ?, card_id, ?
                FROM spawned_cards WHERE id = ?
            ''', (user_id, username, datetime.now(), spawn_id))
            
            await db.commit()
            return True
    
    async def is_card_claimed(self, spawn_id: int) -> bool:
        """Check if a spawned card is already claimed"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT claimed FROM spawned_cards WHERE id = ?
            ''', (spawn_id,))
            
            result = await cursor.fetchone()
            return result[0] if result else False
    
    async def get_user_cards(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all cards owned by a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT uc.card_id, uc.claimed_at, sc.card_id as original_card_id
                FROM user_cards uc
                JOIN spawned_cards sc ON uc.card_id = sc.card_id
                WHERE uc.user_id = ?
                ORDER BY uc.claimed_at DESC
            ''', (user_id,))
            
            rows = await cursor.fetchall()
            
            cards = []
            for row in rows:
                # Since we're using temporary IDs, we need to reconstruct card info
                # This is a simplified approach - in production, you'd want proper card storage
                cards.append({
                    'card_id': row[0],
                    'name': f"Card {row[0]}",  # Simplified name
                    'claimed_at': row[1]
                })
            
            return cards
    
    async def get_card_info(self, card_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific card"""
        # This is a placeholder since we're using dynamic card generation
        # In a full implementation, you'd store card details in the database
        return {
            'id': card_id,
            'name': f"Card {card_id}",
            'rarity': 'common'
        }
    
    # MySQL Migration Ready Methods
    async def migrate_to_mysql(self, mysql_config: Dict[str, str]):
        """Future method for migrating to MySQL"""
        # This would contain logic to migrate SQLite data to MySQL
        # For now, it's a placeholder
        pass
    
    def get_mysql_connection_string(self, config: Dict[str, str]) -> str:
        """Generate MySQL connection string"""
        return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"