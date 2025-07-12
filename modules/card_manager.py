from typing import List, Dict, Any, Optional
import random
import os
from database.db_manager import DatabaseManager
from utils.logger import setup_logger

logger = setup_logger()

class CardManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.art_folder = "art"
    
    async def spawn_cards(self, count: int = 3) -> List[Dict[str, Any]]:
        """Spawn random cards for claiming"""
        try:
            # Get random cards from art folder
            cards = await self._get_random_art_cards(count)
            
            # Create spawn session in database
            spawned_cards = await self.db_manager.create_spawn_session(cards)
            
            logger.info(f"Spawned {len(spawned_cards)} cards")
            return spawned_cards
            
        except Exception as e:
            logger.error(f"Error spawning cards: {e}")
            raise
    
    async def _get_random_art_cards(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get random cards from the art folder"""
        if not os.path.exists(self.art_folder):
            raise FileNotFoundError(f"Art folder '{self.art_folder}' does not exist")
        
        # Get all image files
        image_files = [f for f in os.listdir(self.art_folder) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'))]
        
        if len(image_files) < count:
            logger.warning(f"Not enough images in art folder. Found {len(image_files)}, requested {count}")
            count = len(image_files)
        
        if not image_files:
            raise ValueError("No image files found in art folder")
        
        # Randomly select images
        selected_files = random.sample(image_files, count)
        
        cards = []
        for i, file in enumerate(selected_files):
            # Extract card name from filename
            card_name = self._extract_card_name(file)
            
            cards.append({
                'id': i + 1,  # Temporary ID for this spawn session
                'name': card_name,
                'image_path': os.path.join(self.art_folder, file),
                'rarity': self._determine_rarity(),
                'filename': file
            })
        
        return cards
    
    def _extract_card_name(self, filename: str) -> str:
        """Extract a readable card name from filename"""
        # Remove file extension
        name = os.path.splitext(filename)[0]
        
        # Replace underscores and hyphens with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Capitalize each word
        name = ' '.join(word.capitalize() for word in name.split())
        
        return name
    
    def _determine_rarity(self) -> str:
        """Determine card rarity with weighted randomness"""
        rarities = ['common', 'uncommon', 'rare', 'epic', 'legendary']
        weights = [50, 30, 15, 4, 1]  # Percentage weights
        return random.choices(rarities, weights=weights)[0]
    
    def get_rarity_color(self, rarity: str) -> int:
        """Get color code for rarity"""
        rarity_colors = {
            'common': 0x808080,     # Gray
            'uncommon': 0x00ff00,   # Green
            'rare': 0x0080ff,       # Blue
            'epic': 0x8000ff,       # Purple
            'legendary': 0xffd700    # Gold
        }
        return rarity_colors.get(rarity, 0x808080)
    
    async def claim_card(self, spawn_id: int, user_id: int, username: str) -> bool:
        """Claim a spawned card"""
        try:
            success = await self.db_manager.claim_card(spawn_id, user_id, username)
            
            if success:
                logger.info(f"Card {spawn_id} claimed by {username} ({user_id})")
            else:
                logger.warning(f"Failed to claim card {spawn_id} by {username} ({user_id})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error claiming card {spawn_id}: {e}")
            return False
    
    async def is_card_claimed(self, spawn_id: int) -> bool:
        """Check if a card is already claimed"""
        try:
            return await self.db_manager.is_card_claimed(spawn_id)
        except Exception as e:
            logger.error(f"Error checking if card {spawn_id} is claimed: {e}")
            return True  # Assume claimed on error to be safe
    
    async def get_user_cards(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all cards owned by a user"""
        try:
            return await self.db_manager.get_user_cards(user_id)
        except Exception as e:
            logger.error(f"Error getting cards for user {user_id}: {e}")
            return []
    
    def get_card_stats(self, cards: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get statistics about a collection of cards"""
        stats = {
            'total': len(cards),
            'common': 0,
            'uncommon': 0,
            'rare': 0,
            'epic': 0,
            'legendary': 0
        }
        
        for card in cards:
            rarity = card.get('rarity', 'common')
            if rarity in stats:
                stats[rarity] += 1
        
        return stats
    
    def format_card_info(self, card: Dict[str, Any]) -> str:
        """Format card information for display"""
        rarity = card.get('rarity', 'common').title()
        name = card.get('name', 'Unknown Card')
        
        rarity_emojis = {
            'Common': '⚪',
            'Uncommon': '🟢',
            'Rare': '🔵',
            'Epic': '🟣',
            'Legendary': '🟡'
        }
        
        emoji = rarity_emojis.get(rarity, '⚪')
        
        return f"{emoji} **{name}** ({rarity})"
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top card collectors"""
        # This would be implemented with a proper database query
        # For now, it's a placeholder
        return []
    
    def validate_art_folder(self) -> Dict[str, Any]:
        """Validate the art folder and return info"""
        info = {
            'exists': os.path.exists(self.art_folder),
            'file_count': 0,
            'valid_files': [],
            'invalid_files': []
        }
        
        if info['exists']:
            all_files = os.listdir(self.art_folder)
            valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
            
            for file in all_files:
                if file.lower().endswith(valid_extensions):
                    info['valid_files'].append(file)
                else:
                    info['invalid_files'].append(file)
            
            info['file_count'] = len(info['valid_files'])
        
        return info