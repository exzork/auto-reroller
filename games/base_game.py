"""
Base Game Class for automation framework
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import json
import os
from pathlib import Path


class BaseGame(ABC):
    """Abstract base class for game automation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.game_name = self.__class__.__name__.lower().replace('game', '')
        self.display_name = self.game_name.title()
        self.config_path = config_path
        self.config = {}
        self.cycles_per_session = 9  # Default value
        self.discord_webhook_url = None
        self.project_root = Path(__file__).parent.parent
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """Load game configuration from file"""
        try:
            # Try custom config path first
            if self.config_path and os.path.exists(self.config_path):
                config_file = self.config_path
            else:
                # Use default game config
                config_file = self.project_root / "games" / self.game_name / "config.json"
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
                    
                # Update settings from config
                if 'cycles_per_session' in self.config:
                    self.cycles_per_session = self.config['cycles_per_session']
                if 'display_name' in self.config:
                    self.display_name = self.config['display_name']
                if 'discord_webhook_url' in self.config:
                    self.discord_webhook_url = self.config['discord_webhook_url']
                    
                print(f"✅ Loaded config for {self.display_name}")
            else:
                print(f"⚠️ No config file found for {self.game_name}, using defaults")
                
        except Exception as e:
            print(f"❌ Error loading config for {self.game_name}: {e}")
    
    # Abstract methods that must be implemented by each game
    
    @abstractmethod
    def get_automation_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Return dictionary of automation states and their configurations
        Format: {
            "state_name": {
                "timeout": 60,
                "templates": ["template1", "template2"],
                "macros": ["macro1"],
                "next_states": ["next_state1", "next_state2"]
            }
        }
        """
        pass
    
    @abstractmethod
    def get_app_package(self) -> str:
        """Return the app package name"""
        pass
    
    @abstractmethod
    def get_app_activity(self) -> str:
        """Return the app activity name"""
        pass
    
    @abstractmethod
    def calculate_score(self, detected_items: List[str]) -> Tuple[int, Dict[str, int]]:
        """
        Calculate score for detected items
        Returns: (total_score, score_breakdown)
        """
        pass
    
    @abstractmethod
    def get_minimum_score_threshold(self) -> int:
        """Return minimum score threshold for Discord notifications"""
        pass
    
    @abstractmethod
    def process_screenshot_for_items(self, screenshot, instance_data: Dict[str, Any]) -> List[str]:
        """
        Process screenshot to detect items/cards
        Returns: List of detected item names
        """
        pass
    
    @abstractmethod
    def is_new_cycle(self, screenshot, instance_data: Dict[str, Any]) -> bool:
        """
        Determine if this is a new cycle/pull
        Returns: True if new cycle, False if same cycle
        """
        pass
    
    # Common methods with default implementations
    
    def get_device_resolution(self) -> Tuple[int, int]:
        """Get device resolution (width, height)"""
        return self.config.get('device_resolution', (540, 960))
    
    def get_detection_regions(self) -> Dict[str, Tuple[float, float, float, float]]:
        """Get relative detection regions (x, y, width, height) as 0.0-1.0"""
        return self.config.get('detection_regions', {})
    
    def get_card_scoring(self) -> Dict[str, int]:
        """Get card/item scoring configuration"""
        return self.config.get('card_scoring', {})
    
    def get_default_item_score(self) -> int:
        """Get default score for unspecified items"""
        return self.config.get('default_item_score', 5)
    
    def get_state_timeouts(self) -> Dict[str, int]:
        """Get timeout configuration for each state"""
        automation_states = self.get_automation_states()
        timeouts = {}
        for state, config in automation_states.items():
            timeouts[state] = config.get('timeout', 60)
        return timeouts
    
    def get_template_threshold(self, template_name: str) -> float:
        """Get detection threshold for specific template"""
        thresholds = self.config.get('template_thresholds', {})
        return thresholds.get(template_name, 0.8)
    
    # Configuration setters
    
    def set_cycles_per_session(self, cycles: int):
        """Set number of cycles per automation session"""
        self.cycles_per_session = cycles
    
    def get_cycles_per_session(self) -> int:
        """Get number of cycles per automation session"""
        return self.cycles_per_session
    
    def set_discord_webhook(self, webhook_url: str):
        """Set Discord webhook URL"""
        self.discord_webhook_url = webhook_url
    
    def has_discord_webhook(self) -> bool:
        """Check if Discord webhook is configured"""
        return self.discord_webhook_url is not None and self.discord_webhook_url.strip() != ""
    
    def get_discord_webhook(self) -> Optional[str]:
        """Get Discord webhook URL"""
        return self.discord_webhook_url
    
    def get_game_name(self) -> str:
        """Get internal game name"""
        return self.game_name
    
    def get_display_name(self) -> str:
        """Get display name for the game"""
        return self.display_name
    
    # Utility methods
    
    def create_instance_data(self, device_id: str, instance_number: int, verbose: bool = False) -> Dict[str, Any]:
        """Create initial instance data structure"""
        return {
            'device_id': device_id,
            'instance_number': instance_number,
            'detected_items': [],
            'cycle_count': 0,
            'session_count': 0,
            'current_state': self.get_initial_state(),
            'last_state_change': 0,
            'account_id': None,
            'game_specific_data': {},
            'verbose': verbose
        }
    
    def get_initial_state(self) -> str:
        """Get the initial automation state"""
        states = self.get_automation_states()
        # Return the first state that has no dependencies
        for state_name, state_config in states.items():
            if not state_config.get('requires_previous_state', False):
                return state_name
        # Fallback to first state
        return list(states.keys())[0] if states else "initial"
    
    def should_send_discord_notification(self, detected_items: List[str]) -> bool:
        """Check if results meet Discord notification criteria"""
        if not self.has_discord_webhook():
            return False
        
        total_score, _ = self.calculate_score(detected_items)
        return total_score >= self.get_minimum_score_threshold()
    
    def format_results_for_discord(self, instance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format results for Discord notification"""
        detected_items = instance_data.get('detected_items', [])
        total_score, score_breakdown = self.calculate_score(detected_items)
        
        return {
            'total_score': total_score,
            'score_breakdown': score_breakdown,
            'detected_items': detected_items,
            'cycles_completed': instance_data.get('cycle_count', 0),
            'sessions_completed': instance_data.get('session_count', 0)
        } 