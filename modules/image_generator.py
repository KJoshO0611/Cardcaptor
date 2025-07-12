import cairo
import os
import tempfile
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
from utils.logger import setup_logger

logger = setup_logger()

class ImageGenerator:
    def __init__(self):
        self.card_width = 200
        self.card_height = 280
        self.spacing = 20
        self.border_width = 3
        self.corner_radius = 10
        
        # Colors for rarities
        self.rarity_colors = {
            'common': (128, 128, 128),     # Gray
            'uncommon': (0, 255, 0),       # Green
            'rare': (0, 128, 255),         # Blue
            'epic': (128, 0, 255),         # Purple
            'legendary': (255, 215, 0)     # Gold
        }
    
    async def create_card_image(self, cards: List[Dict[str, Any]]) -> str:
        """Create a combined image of multiple cards using Cairo"""
        if not cards:
            raise ValueError("No cards provided for image generation")
        
        # Calculate total image dimensions
        total_width = (self.card_width * len(cards)) + (self.spacing * (len(cards) + 1))
        total_height = self.card_height + (self.spacing * 2)
        
        # Create Cairo surface
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, total_width, total_height)
        ctx = cairo.Context(surface)
        
        # Fill background
        ctx.set_source_rgb(0.1, 0.1, 0.1)  # Dark gray background
        ctx.paint()
        
        # Draw each card
        for i, card in enumerate(cards):
            x = self.spacing + (i * (self.card_width + self.spacing))
            y = self.spacing
            
            await self._draw_card(ctx, card, x, y)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        surface.write_to_png(temp_file.name)
        temp_file.close()
        
        logger.info(f"Generated card image: {temp_file.name}")
        return temp_file.name
    
    async def _draw_card(self, ctx: cairo.Context, card: Dict[str, Any], x: int, y: int):
        """Draw a single card using Cairo"""
        # Get rarity color
        rarity = card.get('rarity', 'common')
        border_color = self.rarity_colors.get(rarity, (128, 128, 128))
        
        # Draw card background with rounded corners
        self._draw_rounded_rectangle(ctx, x, y, self.card_width, self.card_height, 
                                   self.corner_radius, (0.2, 0.2, 0.2))
        
        # Draw border
        self._draw_rounded_rectangle_border(ctx, x, y, self.card_width, self.card_height, 
                                          self.corner_radius, border_color, self.border_width)
        
        # Load and draw the card image
        image_path = card.get('image_path', '')
        if os.path.exists(image_path):
            await self._draw_card_image(ctx, image_path, x + self.border_width, 
                                      y + self.border_width, 
                                      self.card_width - (self.border_width * 2),
                                      self.card_height - 60 - (self.border_width * 2))
        
        # Draw card name
        self._draw_card_text(ctx, card.get('name', 'Unknown'), 
                           x + self.card_width // 2, 
                           y + self.card_height - 30,
                           border_color)
        
        # Draw rarity indicator
        self._draw_rarity_indicator(ctx, rarity, x + self.card_width - 30, y + 15)
    
    def _draw_rounded_rectangle(self, ctx: cairo.Context, x: int, y: int, 
                              width: int, height: int, radius: int, color: Tuple[float, float, float]):
        """Draw a rounded rectangle"""
        ctx.set_source_rgb(*color)
        ctx.new_sub_path()
        ctx.arc(x + radius, y + radius, radius, 3.14159, 3 * 3.14159 / 2)
        ctx.arc(x + width - radius, y + radius, radius, 3 * 3.14159 / 2, 0)
        ctx.arc(x + width - radius, y + height - radius, radius, 0, 3.14159 / 2)
        ctx.arc(x + radius, y + height - radius, radius, 3.14159 / 2, 3.14159)
        ctx.close_path()
        ctx.fill()
    
    def _draw_rounded_rectangle_border(self, ctx: cairo.Context, x: int, y: int, 
                                     width: int, height: int, radius: int, 
                                     color: Tuple[int, int, int], border_width: int):
        """Draw a rounded rectangle border"""
        ctx.set_source_rgb(color[0]/255, color[1]/255, color[2]/255)
        ctx.set_line_width(border_width)
        ctx.new_sub_path()
        ctx.arc(x + radius, y + radius, radius, 3.14159, 3 * 3.14159 / 2)
        ctx.arc(x + width - radius, y + radius, radius, 3 * 3.14159 / 2, 0)
        ctx.arc(x + width - radius, y + height - radius, radius, 0, 3.14159 / 2)
        ctx.arc(x + radius, y + height - radius, radius, 3.14159 / 2, 3.14159)
        ctx.close_path()
        ctx.stroke()
    
    async def _draw_card_image(self, ctx: cairo.Context, image_path: str, 
                             x: int, y: int, width: int, height: int):
        """Draw the card image using Cairo - FIXED VERSION"""
        try:
            # Load image with PIL first to handle various formats
            pil_image = Image.open(image_path)
            
            # Convert to RGBA if needed (Cairo works better with RGBA)
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
            
            # Resize to fit the card
            pil_image = pil_image.resize((width, height), Image.LANCZOS)
            
            # Convert PIL image to numpy array for proper buffer handling
            img_array = np.array(pil_image)
            
            # Create a writable buffer
            height_img, width_img = img_array.shape[:2]
            
            # Create Cairo surface with proper format
            img_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width_img, height_img)
            
            # Get the buffer from Cairo surface
            buf = img_surface.get_data()
            
            # Convert RGBA to BGRA (Cairo's internal format)
            img_bgra = np.zeros((height_img, width_img, 4), dtype=np.uint8)
            img_bgra[:, :, 0] = img_array[:, :, 2]  # B
            img_bgra[:, :, 1] = img_array[:, :, 1]  # G
            img_bgra[:, :, 2] = img_array[:, :, 0]  # R
            img_bgra[:, :, 3] = img_array[:, :, 3]  # A
            
            # Copy data to Cairo buffer
            buf[:] = img_bgra.flatten().tobytes()
            
            # Mark surface as dirty after manual modification
            img_surface.mark_dirty()
            
            # Draw the image
            ctx.set_source_surface(img_surface, x, y)
            ctx.paint()
            
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            # Draw placeholder rectangle
            ctx.set_source_rgb(0.3, 0.3, 0.3)
            ctx.rectangle(x, y, width, height)
            ctx.fill()
            
            # Draw "No Image" text
            ctx.set_source_rgb(0.7, 0.7, 0.7)
            ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(14)
            text = "No Image"
            text_extents = ctx.text_extents(text)
            text_x = x + (width - text_extents.width) / 2
            text_y = y + (height + text_extents.height) / 2
            ctx.move_to(text_x, text_y)
            ctx.show_text(text)
    
    def _draw_card_text(self, ctx: cairo.Context, text: str, x: int, y: int, color: Tuple[int, int, int]):
        """Draw card text centered"""
        ctx.set_source_rgb(color[0]/255, color[1]/255, color[2]/255)
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(12)
        
        # Truncate text if too long
        if len(text) > 20:
            text = text[:17] + "..."
        
        text_extents = ctx.text_extents(text)
        text_x = x - text_extents.width / 2
        ctx.move_to(text_x, y)
        ctx.show_text(text)
    
    def _draw_rarity_indicator(self, ctx: cairo.Context, rarity: str, x: int, y: int):
        """Draw rarity indicator circle"""
        color = self.rarity_colors.get(rarity, (128, 128, 128))
        
        # Draw circle
        ctx.set_source_rgb(color[0]/255, color[1]/255, color[2]/255)
        ctx.arc(x, y, 8, 0, 2 * 3.14159)
        ctx.fill()
        
        # Draw border
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(1)
        ctx.arc(x, y, 8, 0, 2 * 3.14159)
        ctx.stroke()
    
    async def create_user_collection_image(self, cards: List[Dict[str, Any]], username: str) -> str:
        """Create an image showing user's card collection"""
        if not cards:
            # Create empty collection image
            return await self._create_empty_collection_image(username)
        
        # Calculate grid dimensions
        cards_per_row = 4
        rows = (len(cards) + cards_per_row - 1) // cards_per_row
        
        # Calculate image dimensions
        total_width = (self.card_width * cards_per_row) + (self.spacing * (cards_per_row + 1))
        total_height = (self.card_height * rows) + (self.spacing * (rows + 1)) + 50  # Extra space for title
        
        # Create Cairo surface
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, total_width, total_height)
        ctx = cairo.Context(surface)
        
        # Fill background
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.paint()
        
        # Draw title
        ctx.set_source_rgb(1, 1, 1)
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(20)
        title = f"{username}'s Collection ({len(cards)} cards)"
        text_extents = ctx.text_extents(title)
        title_x = (total_width - text_extents.width) / 2
        ctx.move_to(title_x, 30)
        ctx.show_text(title)
        
        # Draw cards in grid
        for i, card in enumerate(cards):
            row = i // cards_per_row
            col = i % cards_per_row
            
            x = self.spacing + (col * (self.card_width + self.spacing))
            y = 50 + self.spacing + (row * (self.card_height + self.spacing))
            
            await self._draw_card(ctx, card, x, y)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        surface.write_to_png(temp_file.name)
        temp_file.close()
        
        return temp_file.name
    
    async def _create_empty_collection_image(self, username: str) -> str:
        """Create an image for empty collection"""
        width, height = 400, 300
        
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        
        # Fill background
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.paint()
        
        # Draw title
        ctx.set_source_rgb(1, 1, 1)
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(20)
        title = f"{username}'s Collection"
        text_extents = ctx.text_extents(title)
        title_x = (width - text_extents.width) / 2
        ctx.move_to(title_x, 50)
        ctx.show_text(title)
        
        # Draw empty message
        ctx.set_font_size(16)
        ctx.set_source_rgb(0.7, 0.7, 0.7)
        message = "No cards collected yet!"
        text_extents = ctx.text_extents(message)
        message_x = (width - text_extents.width) / 2
        ctx.move_to(message_x, height // 2)
        ctx.show_text(message)
        
        # Draw suggestion
        ctx.set_font_size(14)
        suggestion = "Use /spawn to get your first cards!"
        text_extents = ctx.text_extents(suggestion)
        suggestion_x = (width - text_extents.width) / 2
        ctx.move_to(suggestion_x, height // 2 + 30)
        ctx.show_text(suggestion)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        surface.write_to_png(temp_file.name)
        temp_file.close()
        
        return temp_file.name
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """Get information about an image file"""
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size_mb': os.path.getsize(image_path) / (1024 * 1024)
                }
        except Exception as e:
            logger.error(f"Error getting image info for {image_path}: {e}")
            return {'error': str(e)}