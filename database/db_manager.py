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
            # 1. Create tables if they don't exist (for new setups)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    card_id INTEGER NOT NULL,
                    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (card_id) REFERENCES cards (id)
                );
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
                );
            ''')

            # 2. Perform migrations if needed
            cursor = await db.execute('PRAGMA table_info(cards)')
            columns = [row[1] for row in await cursor.fetchall()]
            if 'rarity' in columns:
                logger.info("Old 'cards' schema detected. Migrating...")
                await db.executescript('''
                    PRAGMA foreign_keys=off;
                    BEGIN TRANSACTION;
                    CREATE TABLE cards_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        image_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    INSERT INTO cards_new (id, name, image_path, created_at)
                    SELECT id, name, image_path, created_at FROM cards;
                    DROP TABLE cards;
                    ALTER TABLE cards_new RENAME TO cards;
                    COMMIT;
                    PRAGMA foreign_keys=on;
                ''')

            cursor = await db.execute('PRAGMA table_info(user_cards)')
            columns = [row[1] for row in await cursor.fetchall()]
            if 'rarity' not in columns:
                logger.info("Old 'user_cards' schema detected. Migrating...")
                # Dropping and recreating is simpler if data loss is acceptable for this table
                await db.execute('DROP TABLE IF EXISTS user_cards;')
                await db.execute('''
                    CREATE TABLE user_cards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        card_id INTEGER NOT NULL,
                        rarity TEXT NOT NULL,
                        claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (card_id) REFERENCES cards (id)
                    );
                ''')

            cursor = await db.execute('PRAGMA table_info(spawned_cards)')
            columns = [row[1] for row in await cursor.fetchall()]
            if 'rarity' not in columns:
                logger.info("Old 'spawned_cards' schema detected. Migrating...")
                await db.execute('DROP TABLE IF EXISTS spawned_cards;')
                await db.execute('''
                    CREATE TABLE spawned_cards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        card_id INTEGER NOT NULL,
                        rarity TEXT NOT NULL,
                        spawned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        claimed BOOLEAN DEFAULT FALSE,
                        claimed_by INTEGER,
                        claimed_at TIMESTAMP,
                        FOREIGN KEY (card_id) REFERENCES cards (id)
                    );
                ''')

            await db.commit()
            logger.info("Database initialized successfully.")
    

    
    async def create_spawn_session(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create a new spawn session with cards"""
        async with aiosqlite.connect(self.db_path) as db:
            updated_cards = []
            
            for card in cards:
                # Insert spawned card record
                cursor = await db.execute('''
                    INSERT INTO spawned_cards (card_id, rarity, spawned_at, claimed)
                    VALUES (?, ?, ?, FALSE)
                ''', (card['id'], card['rarity'], datetime.now()))
                
                spawn_id = cursor.lastrowid
                
                # Update card with spawn ID
                card['spawn_id'] = spawn_id
                updated_cards.append(card)
            
            await db.commit()
            return updated_cards
    
    async def claim_card(self, spawn_id: int, user_id: int, username: str) -> bool:
        """Claim a spawned card"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Check if the spawn exists and is not claimed
            spawn_cursor = await db.execute('SELECT * FROM spawned_cards WHERE id = ?', (spawn_id,))
            spawned_card = await spawn_cursor.fetchone()

            if not spawned_card or spawned_card['claimed']:
                return 'already_claimed'

            card_id = spawned_card['card_id']
            rarity = spawned_card['rarity']

            # Check if the user already owns this specific card-rarity combination
            owner_cursor = await db.execute('SELECT 1 FROM user_cards WHERE user_id = ? AND card_id = ? AND rarity = ?', (user_id, card_id, rarity))
            if await owner_cursor.fetchone():
                return 'user_owns'

            # All checks passed, claim the card
            await db.execute('''
                UPDATE spawned_cards 
                SET claimed = TRUE, claimed_by = ?, claimed_at = ?
                WHERE id = ?
            ''', (user_id, datetime.now(), spawn_id))
            
            await db.execute('''
                INSERT INTO user_cards (user_id, username, card_id, rarity, claimed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, card_id, rarity, datetime.now()))
            
            await db.commit()
            return 'success'
    
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
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT c.name, uc.rarity, uc.claimed_at
                FROM user_cards uc
                JOIN cards c ON uc.card_id = c.id
                WHERE uc.user_id = ?
                ORDER BY uc.claimed_at DESC
            ''', (user_id,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_card_info(self, card_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific card"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_cards(self) -> List[Dict[str, Any]]:
        """Get all cards from the database"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM cards")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_claimed_cards(self) -> List[Dict[str, Any]]:
        """Get all claimed card-rarity combinations"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT card_id, rarity FROM user_cards')
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # MySQL Migration Ready Methods
    async def migrate_to_mysql(self, mysql_config: Dict[str, str]):
        """Future method for migrating to MySQL"""
        # This would contain logic to migrate SQLite data to MySQL
        # For now, it's a placeholder
        pass
    
    def get_mysql_connection_string(self, config: Dict[str, str]) -> str:
        """Generate MySQL connection string"""
        return f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

    async def add_card(self, name: str, image_path: str) -> int:
        """Add a new card to the database"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO cards (name, image_path) VALUES (?, ?)",
                (name, image_path)
            )
            await db.commit()
            logger.info(f"Added card '{name}' to the database.")
            return cursor.lastrowid