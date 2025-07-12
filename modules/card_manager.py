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
        self.rarity_config = {
            'common': {'weight': 70, 'color': (0.5, 0.5, 0.5), 'emote': '⚪'},
            'uncommon': {'weight': 20, 'color': (0.2, 0.6, 0.8), 'emote': '🟢'},
            'rare': {'weight': 7, 'color': (0.8, 0.7, 0.2), 'emote': '🔵'},
            'epic': {'weight': 2.5, 'color': (0.6, 0.2, 0.8), 'emote': '🟣'},
            'legendary': {'weight': 0.5, 'color': (1, 0.5, 0), 'emote': '🟠'}
        }
    
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
        """Get random cards from the database that haven't been claimed yet"""
        all_cards = await self.db_manager.get_all_cards()
        if not all_cards:
            raise ValueError("No cards found in the database.")

        # Get all claimed card-rarity combinations
        claimed_cards = await self.db_manager.get_all_claimed_cards()
        claimed_set = set((c['card_id'], c['rarity']) for c in claimed_cards)

        # Generate potential spawnable cards with rarities
        potential_spawns = []
        for card in all_cards:
            for rarity in self.rarity_config.keys():
                if (card['id'], rarity) not in claimed_set:
                    potential_spawns.append({
                        'id': card['id'],
                        'name': card['name'],
                        'image_path': card['image_path'],
                        'rarity': rarity
                    })

        # If not enough potential spawns, return what we have (even if it's an empty list)
        if len(potential_spawns) < count:
            return potential_spawns

        # Randomly select cards
        return random.sample(potential_spawns, count)
    
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
        """Determine card rarity based on predefined weights"""
        rarities = list(self.rarity_config.keys())
        weights = [config['weight'] for config in self.rarity_config.values()]
        
        return random.choices(rarities, weights, k=1)[0]
    
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