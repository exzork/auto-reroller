"""
Game Factory for creating game instances
"""

import importlib
from typing import Optional
from pathlib import Path
from .base_game import BaseGame


class GameFactory:
    """Factory for creating game instances"""
    
    @staticmethod
    def create_game(game_name: str, config_path: Optional[str] = None) -> Optional[BaseGame]:
        """Create a game instance based on game name"""
        try:
            # Construct module and class names
            module_name = f"games.{game_name}.{game_name}_game"
            class_name = f"{game_name.title()}Game"
            
            # Import the game module
            game_module = importlib.import_module(module_name)
            
            # Get the game class
            game_class = getattr(game_module, class_name)
            
            # Create and return the game instance
            return game_class(config_path)
            
        except ImportError as e:
            print(f"❌ Could not import game module for '{game_name}': {e}")
            return None
        except AttributeError as e:
            print(f"❌ Could not find game class '{class_name}' for '{game_name}': {e}")
            return None
        except Exception as e:
            print(f"❌ Error creating game instance for '{game_name}': {e}")
            return None
    
    @staticmethod
    def list_available_games() -> list:
        """List all available games"""
        games = []
        games_dir = Path(__file__).parent
        
        for item in games_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                game_file = item / f"{item.name}_game.py"
                if game_file.exists():
                    games.append(item.name)
        
        return sorted(games)
    
    @staticmethod
    def validate_game_structure(game_name: str) -> bool:
        """Validate that a game has the required structure"""
        games_dir = Path(__file__).parent
        game_dir = games_dir / game_name
        
        if not game_dir.is_dir():
            return False
        
        # Check for required files
        required_files = [
            f"{game_name}_game.py",
            "config.json"
        ]
        
        for file in required_files:
            if not (game_dir / file).exists():
                print(f"❌ Missing required file: {game_dir / file}")
                return False
        
        # Check for recommended directories
        recommended_dirs = [
            "templates",
            "macros"
        ]
        
        for dir_name in recommended_dirs:
            if not (game_dir / dir_name).is_dir():
                print(f"⚠️ Recommended directory missing: {game_dir / dir_name}")
        
        return True 