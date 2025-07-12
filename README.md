# Cardcaptor# CardCaptor Discord Bot

A Discord bot for spawning, claiming, and collecting cards from images in your art folder.

## Features

- **Card Spawning**: Spawn 3 random cards from your art folder
- **Card Claiming**: Interactive buttons to claim cards
- **Card Collection**: View your personal card collection
- **Rarity System**: Cards have different rarities (Common, Uncommon, Rare, Epic, Legendary)
- **Image Generation**: Uses PyCairo to create beautiful card displays
- **Database Support**: SQLite by default, ready for MySQL migration
- **Announcement System**: Announces when cards are claimed

## Directory Structure

```
CARDCAPTOR/
├── .env
├── main.py
├── requirements.txt
├── README.md
├── art/                    # Put your card images here
│   ├── card1.png
│   ├── card2.jpg
│   └── ...
├── database/
│   ├── __init__.py
│   ├── db_manager.py
│   └── cardcaptor.db      # SQLite database (auto-created)
├── modules/
│   ├── __init__.py
│   ├── card_manager.py
│   └── image_generator.py
├── utils/
│   ├── __init__.py
│   └── logger.py
├── logs/                   # Log files (auto-created)
├── docs/                   # Documentation
└── cogs/                   # Future Discord cogs
```

## Setup

### 1. Prerequisites

- Python 3.8+
- Discord Bot Token
- PyCairo dependencies

### 2. Install Dependencies

#### On Ubuntu/Debian:
```bash
sudo apt-get install python3-dev libcairo2-dev libgirepository1.0-dev
```

#### On macOS:
```bash
brew install cairo pkg-config
```

#### On Windows:
- Download and install GTK+ development libraries
- Or use conda: `conda install -c conda-forge pycairo`

### 3. Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Discord bot token:
```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

3. Create the `art` folder and add your card images:
```bash
mkdir art
# Add your PNG, JPG, JPEG, GIF, WEBP, or BMP files to the art folder
```

### 5. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section
4. Create a bot and copy the token to your `.env` file
5. Enable "Message Content Intent" in bot settings
6. Invite the bot to your server with appropriate permissions

### 6. Run the Bot

```bash
python main.py
```

## Commands

### Slash Commands

- `/spawn` - Spawn 3 random cards for claiming
- `/mycards` - View your personal card collection

### Interactive Features

- **Card Claiming**: Click buttons under spawned cards to claim them
- **Disabled Buttons**: Already claimed cards show as disabled
- **Announcements**: When a card is claimed, an announcement is sent to the channel

## Card System

### Rarity System

Cards are randomly assigned rarities with different probabilities:
- **Common** (Gray): 50% chance
- **Uncommon** (Green): 30% chance  
- **Rare** (Blue): 15% chance
- **Epic** (Purple): 4% chance
- **Legendary** (Gold): 1% chance

### Card Naming

Card names are automatically generated from image filenames:
- `awesome_dragon.png` → "Awesome Dragon"
- `fire-elemental.jpg` → "Fire Elemental"
- `mystic_warrior_v2.png` → "Mystic Warrior V2"

## Database

### SQLite (Default)

The bot uses SQLite by default with the following tables:
- `cards` - Card definitions
- `user_cards` - User collections
- `spawned_cards` - Tracking spawned cards and claims

### MySQL Migration (Future)

The database manager is designed to be easily migrated to MySQL:

```python
# In your .env file
DB_HOST=localhost
DB_PORT=3306
DB_NAME=cardcaptor
DB_USER=cardcaptor_user
DB_PASSWORD=your_mysql_password
```

## Logging

Logs are stored in the `logs/` directory:
- `cardcaptor.log` - All logs
- `cardcaptor_errors.log` - Error logs only

## Image Generation

The bot uses PyCairo to generate card images with:
- Rounded corners
- Rarity-colored borders
- Card images from your art folder
- Card names
- Rarity indicators

## Customization

### Card Dimensions

Edit `modules/image_generator.py`:
```python
self.card_width = 200
self.card_height = 280
self.spacing = 20
```

### Rarity Colors

Edit `modules/card_manager.py`:
```python
self.rarity_colors = {
    'common': (128, 128, 128),     # Gray
    'uncommon': (0, 255, 0),       # Green
    'rare': (0, 128, 255),         # Blue
    'epic': (128, 0, 255),         # Purple
    'legendary': (255, 215, 0)     # Gold
}
```

### Spawn Count

Edit your `.env` file:
```
CARDS_PER_SPAWN=3
```

## Troubleshooting

### Common Issues

1. **PyCairo Installation Issues**
   - Make sure you have the system dependencies installed
   - Try using conda instead of pip for PyCairo

2. **Art Folder Empty**
   - Make sure you have image files in the `art/` folder
   - Supported formats: PNG, JPG, JPEG, GIF, WEBP, BMP

3. **Database Errors**
   - Check file permissions on the database directory
   - Make sure SQLite is installed

4. **Discord Permissions**
   - Ensure the bot has "Send Messages" and "Use Slash Commands" permissions
   - Enable "Message Content Intent" in Discord Developer Portal

### Debug Mode

Enable debug logging in your `.env`:
```
LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue on the GitHub repository or contact the maintainers.