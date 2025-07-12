import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import app_commands
import asyncio
import os
from dotenv import load_dotenv
from database.db_manager import DatabaseManager
from modules.card_manager import CardManager
from modules.image_generator import ImageGenerator
from utils.logger import setup_logger

load_dotenv()

# Setup logging
logger = setup_logger()

# Bot setup
intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize managers
db_manager = DatabaseManager()
card_manager = CardManager(db_manager)
image_generator = ImageGenerator()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    await db_manager.initialize_database()
    
    # Sync slash commands
    try:
        TEST_GUILD = discord.Object(id=763985439118852148)
        bot.tree.copy_global_to(guild=TEST_GUILD)
        synced = await bot.tree.sync(guild=TEST_GUILD)
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.tree.command(name="spawn", description="Spawn 3 random cards to claim")
async def spawn_cards(interaction: discord.Interaction):
    try:
        # Defer the initial response to prevent timeout
        await interaction.response.defer()

        # Generate card spawn
        card_data = await card_manager.spawn_cards()

        if not card_data:
            # If no cards are available, edit the original "thinking..." message
            await interaction.edit_original_response(content="⚠️ **All unique cards have been claimed!** There are no new cards to spawn right now.")
            return

        # Generate image
        image_path = await image_generator.create_card_image(card_data)

        # Create embed and view
        embed = discord.Embed(
            title="🎴 New Cards Spawned!",
            description="Click the buttons below to claim your cards!",
            color=0x00ff00
        )
        embed.set_image(url="attachment://cards.png")
        
        view = CardClaimView(card_data, card_manager, interaction.guild_id)

        # Edit the original response with the final content
        with open(image_path, 'rb') as f:
            file = discord.File(f, filename="cards.png")
            await interaction.edit_original_response(embed=embed, view=view, attachments=[file])

        # Clean up temporary image
        os.remove(image_path)

    except Exception as e:
        logger.error(f"An unexpected error occurred during spawn: {e}", exc_info=True)
        # Try to edit the response with an error message, but handle cases where it might fail
        try:
            await interaction.edit_original_response(content="An unexpected error occurred while spawning cards.")
        except discord.errors.NotFound:
            # If the interaction is gone, we can't do anything
            pass

@bot.tree.command(name="mycards", description="View your claimed cards")
async def my_cards(interaction: discord.Interaction):
    try:
        user_cards = await card_manager.get_user_cards(interaction.user.id)
        
        if not user_cards:
            embed = discord.Embed(
                title="Your Cards",
                description="You haven't claimed any cards yet!",
                color=0xff0000
            )
        else:
            cards_text = "\n".join([f"{card_manager.format_card_info(card)}" 
                                  for card in user_cards])
            embed = discord.Embed(
                title=f"Your Cards ({len(user_cards)})",
                description=cards_text,
                color=0x0099ff
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error getting user cards: {e}")
        await interaction.response.send_message("An error occurred while fetching your cards.", ephemeral=True)

@bot.tree.command(name="upload_card", description="[ADMIN] Upload a new card image")
@app_commands.describe(
    image="The image file to upload",
    name="Optional custom name for the card"
)
async def upload_card(interaction: discord.Interaction, image: discord.Attachment, name: str = None):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    try:
        # Validate file type
        if not any(image.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']):
            await interaction.response.send_message("❌ Invalid file type. Supported formats: PNG, JPG, JPEG, GIF, WEBP, BMP", ephemeral=True)
            return
        
        # Validate file size (e.g., max 10MB)
        if image.size > 10 * 1024 * 1024:
            await interaction.response.send_message("❌ File too large. Maximum size is 10MB.", ephemeral=True)
            return
        
        # Create art directory if it doesn't exist
        art_dir = "art"
        os.makedirs(art_dir, exist_ok=True)
        
        # Generate filename
        if name:
            # Use custom name
            file_extension = os.path.splitext(image.filename)[1]
            filename = f"{name.replace(' ', '_')}{file_extension}"
        else:
            # Use original filename
            filename = image.filename
        
        # Check if file already exists
        file_path = os.path.join(art_dir, filename)
        if os.path.exists(file_path):
            await interaction.response.send_message(f"❌ A card with the name '{filename}' already exists.", ephemeral=True)
            return
        
        # Download and save the image
        await image.save(file_path)

        # Add card to database
        card_name = card_manager._extract_card_name(filename)
        await db_manager.add_card(card_name, file_path)
        
        # Log the upload
        logger.info(f"Card image uploaded and added to DB: {filename} by {interaction.user.name}")
        
        # Send success message
        embed = discord.Embed(
            title="✅ Card Uploaded Successfully",
            description=f"**Filename:** {filename}\n**Size:** {image.size/1024:.1f} KB",
            color=0x00ff00
        )
        embed.set_image(url=image.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error uploading card: {e}")
        await interaction.response.send_message("❌ An error occurred while uploading the card.", ephemeral=True)

@bot.tree.command(name="list_cards", description="[ADMIN] List all available card images")
async def list_cards(interaction: discord.Interaction):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    try:
        art_info = card_manager.validate_art_folder()
        
        if not art_info['exists']:
            await interaction.response.send_message("❌ Art folder doesn't exist.", ephemeral=True)
            return
        
        valid_files = art_info['valid_files']
        invalid_files = art_info['invalid_files']
        
        embed = discord.Embed(
            title="📁 Card Images",
            color=0x0099ff
        )
        
        if valid_files:
            # Split into multiple fields if too many files
            files_text = "\n".join(valid_files)
            if len(files_text) > 1000:
                files_text = files_text[:1000] + f"\n... and {len(valid_files) - len(files_text.split(chr(10)))} more"
            
            embed.add_field(
                name=f"Valid Images ({len(valid_files)})",
                value=f"```{files_text}```",
                inline=False
            )
        
        if invalid_files:
            embed.add_field(
                name=f"Invalid Files ({len(invalid_files)})",
                value=f"```{chr(10).join(invalid_files[:10])}```",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error listing cards: {e}")
        await interaction.response.send_message("❌ An error occurred while listing cards.", ephemeral=True)

@bot.tree.command(name="delete_card", description="[ADMIN] Delete a card image")
@app_commands.describe(filename="The filename of the card to delete")
async def delete_card(interaction: discord.Interaction, filename: str):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    try:
        file_path = os.path.join("art", filename)
        
        if not os.path.exists(file_path):
            await interaction.response.send_message(f"❌ Card '{filename}' not found.", ephemeral=True)
            return
        
        # Delete the file
        os.remove(file_path)
        
        # Log the deletion
        logger.info(f"Card image deleted: {filename} by {interaction.user.name}")
        
        embed = discord.Embed(
            title="🗑️ Card Deleted",
            description=f"**{filename}** has been deleted successfully.",
            color=0xff9900
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error deleting card: {e}")
        await interaction.response.send_message("❌ An error occurred while deleting the card.", ephemeral=True)

@bot.tree.command(name="card_info", description="[ADMIN] Get information about the art folder")
async def card_info(interaction: discord.Interaction):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    try:
        art_info = card_manager.validate_art_folder()
        
        embed = discord.Embed(
            title="📊 Art Folder Information",
            color=0x9932cc
        )
        
        embed.add_field(name="Folder Exists", value="✅ Yes" if art_info['exists'] else "❌ No", inline=True)
        embed.add_field(name="Valid Images", value=str(art_info['file_count']), inline=True)
        embed.add_field(name="Invalid Files", value=str(len(art_info['invalid_files'])), inline=True)
        
        if art_info['exists']:
            # Calculate total size
            total_size = 0
            for file in art_info['valid_files']:
                file_path = os.path.join("art", file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
            
            embed.add_field(name="Total Size", value=f"{total_size / (1024*1024):.1f} MB", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error getting card info: {e}")
        await interaction.response.send_message("❌ An error occurred while getting card information.", ephemeral=True)

class CardClaimView(discord.ui.View):
    def __init__(self, card_data, card_manager, guild_id):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.card_data = card_data
        self.card_manager = card_manager
        self.guild_id = guild_id
        
        # Create buttons for each card
        for i, card in enumerate(card_data):
            button = CardClaimButton(card, i, self.card_manager, self.guild_id)
            self.add_item(button)

class CardClaimButton(discord.ui.Button):
    def __init__(self, card_data, index, card_manager, guild_id):
        super().__init__(
            label=f"Claim {card_data['name']}",
            style=discord.ButtonStyle.primary,
            custom_id=f"claim_{card_data['id']}_{index}"
        )
        self.card_data = card_data
        self.card_manager = card_manager
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        # Defer response to avoid interaction timeout
        await interaction.response.defer()
        
        # Attempt to claim the card
        result = await db_manager.claim_card(self.card_data['spawn_id'], interaction.user.id, interaction.user.name)
        
        if result == 'success':
            # Disable the button
            self.disabled = True
            
            # Update the original message
            await interaction.edit_original_response(view=self.view)
            
            # Send confirmation message
            embed = discord.Embed(
                title="🎉 Card Claimed!",
                description=f"{interaction.user.mention} claimed **{self.card_data['name']}** ({self.card_data['rarity']})!",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed)
            logger.info(f"Card {self.card_data['spawn_id']} claimed by {interaction.user.name} ({interaction.user.id})")
        elif result == 'already_claimed':
            # Send failure message
            await interaction.followup.send(
                f"❌ **{self.card_data['name']}** has already been claimed by someone else!", 
                ephemeral=True
            )
        elif result == 'user_owns':
            await interaction.followup.send(
                f"❌ You already own a **{self.card_data['rarity']}** version of **{self.card_data['name']}**!",
                ephemeral=True
            )

if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables")
        exit(1)
    
    bot.run(token)