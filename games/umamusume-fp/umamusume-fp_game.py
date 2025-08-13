"""
Uma Musume Friend Point Spam Service
Automation for friend point spam using support cards
"""

import time
import cv2
import os
import names
import pytesseract
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from games.base_game import BaseGame
from core.action_types import (
    create_counter_action, create_loop_action, create_macro_action, create_restart_action, create_state_with_if_condition, create_swipe_action, create_tap_action, create_wait_action, create_typing_action,
    ActionConfig, StateConfig, create_conditional_action
)


class UmamusumeFpGame(BaseGame):
    """Uma Musume Friend Point Spam specific game implementation"""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)
        # Override game_name to match directory name
        self.game_name = "umamusume-fp"
        self.display_name = "Uma Musume Friend Point Spam"
        
        # Friend point specific constants
        self.support_points_region = (400, 805, 435, 830)  # (x1, y1, x2, y2)
        self.friend_list_region = (50, 200, 650, 1200)  # Friend list area
        self.support_card_region = (100, 300, 600, 800)  # Support card area
        self.last_support_points = {}  # Per-instance tracking
        self.friend_points_earned = {}  # Track points earned per session
        
    def log_verbose_config(self, device_id: str = 'system'):
        """Log detailed configuration information for debugging"""
        print(f"🔧 Instance {device_id}: Uma Musume FP verbose configuration:")
        print(f"   📱 App package: {self.get_app_package()}")
        print(f"   📱 App activity: {self.get_app_activity()}")
        print(f"   🎯 Cycles per session: {self.get_cycles_per_session()}")
        print(f"   📐 Device resolution: {self.get_device_resolution()}")
        print(f"   🎯 Support points region: {self.support_points_region}")
        print(f"   👥 Friend list region: {self.friend_list_region}")
        print(f"   🎴 Support card region: {self.support_card_region}")
        print(f"   💎 Card scoring: {self.get_card_scoring()}")
        print(f"   📊 Default item score: {self.get_default_item_score()}")
        print(f"   🎯 Score threshold: {self.get_minimum_score_threshold()}")
        
        detection_regions = self.get_detection_regions()
        if detection_regions:
            print(f"   🔍 Detection regions: {len(detection_regions)} slots configured")
        else:
            print(f"   🔍 Detection regions: Using default positions")
            
        template_thresholds = self.config.get('template_thresholds', {})
        if template_thresholds:
            print(f"   🖼️ Template thresholds: {template_thresholds}")
        
        # Check card reference folder
        card_folder = self.project_root / "games" / "umamusume-fp" / "cards"
        if card_folder.exists():
            card_files = [f for f in card_folder.iterdir() if f.suffix.lower() in ['.png', '.jpg', '.jpeg']]
            print(f"   🎴 Card references: {len(card_files)} images available")
        else:
            print(f"   ❌ Card references: Folder not found at {card_folder}")
        
        print(f"   🔗 Discord webhook: {'✅ Configured' if self.has_discord_webhook() else '❌ Not configured'}")
        
        automation_states = self.get_automation_states()
        print(f"   🔄 Automation states: {len(automation_states)} states configured")
        for state_name, state_config in automation_states.items():
            templates = state_config.get('templates', [])
            macros = state_config.get('macros', [])
            timeout = state_config.get('timeout', 60)
            processes_items = state_config.get('processes_items', False)
            next_states = state_config.get('next_states', [])
            
            print(f"     • {state_name}: timeout={timeout}s, templates={templates}, macros={macros}")
            print(f"       processes_items={processes_items}, next_states={next_states}")
    
    def get_automation_states(self) -> Dict[str, Dict[str, Any]]:
        """Define Uma Musume Friend Point automation states"""
        return {
            "waiting_for_main_menu": {
                "timeout": 180,
                "templates": [],
                "actions": [
                    create_tap_action(
                        template="main_menu",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="delete_data",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="delete_data_2",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="delete_data_2",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="close",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="umamusume",
                        likelihood=0.7,
                        delay_after=2.0,
                        timeout=30
                    ),
                    create_tap_action(
                        template="agree",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="agree",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="change_country",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="write",
                        likelihood=0.8,
                        delay_after=2.0
                    ),
                    create_typing_action(
                        text="200001",
                        clear_first=False,
                        press_enter=True,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="cancel",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="later",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="skip btn",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="write name",
                        likelihood=0.8,
                        delay_after=2.0
                    ),
                    create_typing_action(
                        text=names.get_first_name(),
                        clear_first=False,
                        press_enter=True,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="register",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="register",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="skip sm",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=0.1
                            ),
                        ],
                        condition="close",
                        timeout=60
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=3.0,
                                timeout=0.1
                            ),
                        ],
                        condition="home_screen",
                        timeout=60
                    )
                ],
                "next_states": ["claim_reward"]
            },
            "claim_reward": {
                "timeout": 20,
                "templates": ["home_screen"],
                "actions": [
                    create_tap_action(
                        template="reward_button",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="collect_all_button",
                        likelihood=0.9,
                        delay_before=2.0,
                        delay_after=5
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=0.1
                            )
                        ],
                        condition="home_screen",
                        timeout=10
                    ),
                    
                ],
                "next_states": ["navigating_to_friends"]
            },
            "navigating_to_friends": {
                "timeout": 20,
                "templates": ["home_screen"],
                "actions": [create_macro_action("id friend")],
                "next_states": ["typing_friend_id"]
            },
            "typing_friend_id": {
                "timeout": 30,
                "templates": [],
                "actions": [
                    create_typing_action(
                        text="692799833506",
                        clear_first=True,
                        press_enter=True,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="search_friend_id",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="search_friend_id",
                        likelihood=0.9,
                        delay_after=4.0
                    ),
                    create_tap_action(
                        template="follow",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_tap_action(
                        template="close",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_tap_action(
                        template="close",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                ],
                "next_states": ["back_to_home"]
            },
            "back_to_home": {
                "timeout": 30,
                "templates": ["home"],
                "actions": [
                    create_tap_action(
                        template="home",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                ],
                "next_states": ["options"]
            },
            "options": {
                "timeout": 60,
                "templates": ["home_screen"],
                "actions": [create_macro_action("options")],
                "next_states": ["start career tutorial"]
            },
            "start career tutorial": {
                "timeout": 240,
                "templates": [],
                "actions": [
                    create_tap_action(
                        template="career",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_before=5.0,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="confirm",
                        likelihood=0.9,
                        delay_after=5.0,
                        timeout=5
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="auto select",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="auto select",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="start career",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="start career 2",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                ],
                "next_states": ["career tutorial"]
            },
            "career tutorial": {
                "timeout": 240,
                "templates": [],
                "actions": [
                    create_tap_action(
                        template="skip sm",
                        likelihood=0.9,
                        delay_before=5.0,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="shorten all",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="confirm",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="skip off",
                                likelihood=0.9,
                                delay_before=2.0,
                                delay_after=2.0,
                                timeout=2,
                                tap_times=2,
                                tap_delay=0.5
                            ),
                            create_tap_action(
                                template="skip 1x",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        condition="next",
                        timeout=60,
                        use_single_screenshot=True
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="next",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        condition="close",
                        timeout=30
                    ),
                    create_tap_action(
                        template="close",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                ],
                "next_states": ["career race tutorial"]
            },
            "career race tutorial": {
                "timeout": 540,
                "templates": [],
                "actions": [
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="rest",
                                likelihood=0.9,
                                timeout=0.1,
                            ),
                            create_tap_action(
                                template="skip off",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=2,
                                tap_times=2,
                                tap_delay=0.5
                            ),
                            create_tap_action(
                                template="skip 1x",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="upper choice",
                                likelihood=0.9,
                                timeout=0.1,
                            )
                        ],
                        condition="race",
                        use_single_screenshot=True,
                    ),
                    create_tap_action(
                        template="race",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="next",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )],
                        condition="close",
                        timeout=10,
                    ),
                    create_tap_action(
                        template="close",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=0.1
                    ),
                    create_tap_action(
                        template="race 2",
                        likelihood=0.9,
                        delay_after=2.0,
                        timeout=10
                    ),
                    create_tap_action(
                        template="race 2",
                        likelihood=0.9,
                        delay_after=5.0,
                        timeout=10
                    ),
                    create_tap_action(
                        template="skip off",
                        likelihood=0.9,
                        delay_before=2.0,
                        delay_after=1.0,
                        timeout=10,
                        tap_times=2,
                        tap_delay=1
                    ),
                    create_tap_action(
                        template="skip 1x",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=0.1
                    ),
                    create_tap_action(
                        template="race 2",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=10
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_before=2.0,
                        delay_after=5.0
                    ),
                    create_tap_action(
                        template="race 3",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=20
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="skip sm",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="concert menu",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        condition="next",
                        use_single_screenshot=True,
                        timeout=120,
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="next 2",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                     create_tap_action(
                        template="skip off",
                        likelihood=0.9,
                        delay_after=1.0,
                        tap_times=2,
                        tap_delay=2
                    ),
                    create_tap_action(
                        template="skip 1x",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=0.1
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="rest",
                                likelihood=0.9,
                                timeout=0.1,
                            ),
                            create_tap_action(
                                template="skip off",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1,
                                tap_times=2,
                                tap_delay=1
                            ),
                            create_tap_action(
                                template="skip 1x",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="upper choice",
                                likelihood=0.9,
                                timeout=0.1,
                            ),
                            create_tap_action(
                                template="cancel",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        use_single_screenshot=True,
                        condition="next",
                        condition_likelihood=0.8
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=3.0,
                        timeout=0.1
                    ),
                    create_tap_action(
                        template="complete career",
                        likelihood=0.9,
                        delay_after=3.0
                    ),
                    create_tap_action(
                        template="finish",
                        likelihood=0.9,
                        delay_after=3.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="next",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="cancel",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        use_single_screenshot=True,
                        condition="to home",
                    ),
                    create_tap_action(
                        template="to home",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=0.1
                    ),
                ],
                "next_states": ["start career"]
            },
            "start career": {
                "timeout": 600,
                "templates": [],
                "actions": [
                    create_tap_action(
                        template="career",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="confirm",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=1
                            ),
                            create_tap_action(
                                template="next",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=1
                            ),
                        ],
                        condition="auto select",
                        timeout=20
                    ),
                    create_tap_action(
                        template="auto select",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="add support",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_loop_action(
                        actions=[
                            create_swipe_action(
                                start_coordinates=(270, 400),
                                end_coordinates=(270, 200),
                                duration=1000,
                                delay_after=2.0
                            )
                        ],
                        condition="following",
                        timeout=20
                    ),
                    create_tap_action(
                        template="following",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="start career",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_conditional_action(
                        condition="restore",
                        if_true=[
                            create_tap_action(
                                template="restore",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=3
                            ),
                            create_conditional_action(
                                condition="no drink",
                                if_true=[
                                    create_tap_action(
                                        template="close",
                                        likelihood=0.9,
                                        delay_after=2.0,
                                        timeout=3
                                    ),
                                    create_tap_action(
                                        template="home_screen",
                                        likelihood=0.9,
                                        delay_after=2.0,
                                        timeout=3
                                    ),
                                ],
                                if_false=[  
                                    create_tap_action(
                                        template="use drink",
                                        likelihood=0.9,
                                        delay_after=2.0,
                                        timeout=3
                                    ),
                                    create_tap_action(
                                        template="ok",
                                        likelihood=0.9,
                                        delay_after=2.0,
                                        timeout=3
                                    ),
                                    create_tap_action(
                                        template="close",
                                        likelihood=0.9,
                                        delay_after=2.0,
                                        timeout=3
                                    ),
                                ],
                                likelihood=0.99,
                                if_true_state="complete", #complete current account as no stamina left
                                timeout=10
                            ),
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=3
                            ),
                            create_tap_action(
                                template="start career",
                                likelihood=0.9,
                                delay_after=2.0
                            ),
                        ],
                    ),
                    create_tap_action(
                        template="start career 2",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_tap_action(
                        template="skip sm",
                        likelihood=0.9,
                        delay_before=5.0,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="shorten all",
                        likelihood=0.9,
                        delay_after=2.0
                    ),
                    create_tap_action(
                        template="confirm",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="skip off",
                                likelihood=0.9,
                                delay_before=2.0,
                                delay_after=2.0,
                                timeout=0.1,
                                tap_times=2,
                                tap_delay=1
                            ),
                        ],
                        condition="next",
                        timeout=30,
                        use_single_screenshot=True
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="rest",
                                likelihood=0.9,
                                timeout=0.1,
                            ),
                            create_tap_action(
                                template="skip off",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1,
                                tap_times=2,
                                tap_delay=1
                            ),
                            create_tap_action(
                                template="skip 1x",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="upper choice",
                                likelihood=0.9,
                                timeout=0.1,
                            )
                        ],
                        condition="race",
                        use_single_screenshot=True,
                    ),
                    create_tap_action(
                        template="race",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="next",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )],
                        condition="close",
                        timeout=10,
                    ),
                    create_tap_action(
                        template="close",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=0.1
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="race 2",
                                likelihood=0.9,
                                timeout=0.1,
                                delay_after=3.0
                            )
                        ],
                        condition="ok"
                    ),
                    create_tap_action(
                        template="ok",
                        likelihood=0.9,
                        delay_after=5.0
                    ),
                    create_tap_action(
                        template="race 3",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=20
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="skip sm",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="concert menu",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        condition="next",
                        use_single_screenshot=True,
                        timeout=120,
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="next 2",
                        likelihood=0.9,
                        delay_before=5.0,
                        delay_after=5.0
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_before=3.0,
                        delay_after=1.0
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_before=3.0,
                        delay_after=1.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="rest",
                                likelihood=0.9,
                                timeout=0.1,
                            ),
                            create_tap_action(
                                template="skip off",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1,
                                tap_times=2,
                                tap_delay=1
                            ),
                            create_tap_action(
                                template="skip 1x",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="upper choice",
                                likelihood=0.9,
                                timeout=0.1,
                            ),
                            create_tap_action(
                                template="cancel",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        use_single_screenshot=True,
                        condition="next",
                        condition_likelihood=0.8
                    ),
                    create_tap_action(
                        template="next",
                        likelihood=0.9,
                        delay_after=3.0,
                        timeout=0.1
                    ),
                    create_tap_action(
                        template="complete career",
                        likelihood=0.9,
                        delay_after=3.0
                    ),
                    create_tap_action(
                        template="finish",
                        likelihood=0.9,
                        delay_after=3.0
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="next",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            ),
                            create_tap_action(
                                template="cancel",
                                likelihood=0.9,
                                delay_after=1.0,
                                timeout=0.1
                            )
                        ],
                        use_single_screenshot=True,
                        condition="to home",
                    ),
                    create_tap_action(
                        template="to home",
                        likelihood=0.9,
                        delay_after=1.0,
                        timeout=0.1
                    ),
                    create_counter_action()
                ],
                "next_states": ["start career"],
                "timeout_state":"restart career"
            },
            "restart career": {
                "timeout": 60,
                "templates": [],
                "actions": [
                    create_restart_action(timeout=20),
                    create_tap_action(
                        template="umamusume",
                        likelihood=0.9,
                        delay_after=2.0,
                        timeout=30
                    ),
                    create_tap_action(
                        template="later",
                        likelihood=0.9,
                        delay_after=2.0,
                        timeout=10
                    ),
                    create_loop_action(
                        actions=[
                            create_tap_action(
                                template="skip sm",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=0.1
                            ),
                        ],
                        condition="home_screen",
                        timeout=20
                    ),
                    create_conditional_action(
                        condition="continue career",
                        if_true=[
                            create_tap_action(
                                template="continue career",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=5
                            ),
                            create_tap_action(
                                template="delete career",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=5
                            ),
                            create_tap_action(
                                template="ok",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=5
                            ),
                            create_tap_action(
                                template="close",
                                likelihood=0.9,
                                delay_after=2.0,
                                timeout=5
                            )
                        ],
                        if_false=[
                            create_tap_action(
                                template="career",
                                likelihood=0.7,
                                delay_after=2.0,
                                timeout=30
                            ),
                        ]
                    )
                ],
                "next_states": ["start career"]
            },
            "complete": {
                "timeout": 60,
                "templates": ["home_screen"],
                "actions": [
                    create_macro_action(name="unfollow", timeout=30),
                    create_restart_action(timeout=10)
                ],
                "next_states": ["waiting_for_main_menu"]
            },
            
        }
    
    def get_app_package(self) -> str:
        """Return Uma Musume app package"""
        return "com.cygames.umamusume"
    
    def get_app_activity(self) -> str:
        """Return Uma Musume app activity"""
        return "com.cygames.umamusume/jp.co.cygames.umamusume_activity.UmamusumeActivity"
    
    def calculate_score(self, detected_items: List[str]) -> Tuple[int, Dict[str, int]]:
        """
        Calculate score for detected support cards and friend points
        Returns: (total_score, score_breakdown)
        """
        score_breakdown = {}
        total_score = 0
        
        # Scoring for different types of support cards
        card_scoring = self.get_card_scoring()
        
        for item in detected_items:
            item_lower = item.lower()
            
            # Check for support card types
            if 'ssr' in item_lower or 'ur' in item_lower:
                score = card_scoring.get('ssr_support', 100)
            elif 'sr' in item_lower:
                score = card_scoring.get('sr_support', 50)
            elif 'r' in item_lower:
                score = card_scoring.get('r_support', 25)
            elif 'friend_point' in item_lower or 'support_point' in item_lower:
                # Extract points value if possible
                try:
                    points = int(''.join(filter(str.isdigit, item)))
                    score = points * card_scoring.get('point_multiplier', 1)
                except:
                    score = card_scoring.get('friend_point', 10)
            else:
                score = self.get_default_item_score()
            
            score_breakdown[item] = score
            total_score += score
        
        return total_score, score_breakdown
    
    def get_minimum_score_threshold(self) -> int:
        """Return minimum score threshold for Discord notifications"""
        return self.config.get('minimum_score_threshold', 50)
    
    def process_screenshot_for_items(self, screenshot, instance_data: Dict[str, Any]) -> List[str]:
        """
        Process screenshot to detect support cards and friend points
        Returns: List of detected item names
        """
        detected_items = []
        device_id = instance_data.get('device_id', 'unknown')
        
        try:
            # Convert to numpy array if needed
            if isinstance(screenshot, np.ndarray):
                img = screenshot
            else:
                img = np.array(screenshot)
            
            # Extract support points from the designated region
            support_points = self._extract_support_points(img, device_id=device_id)
            if support_points is not None:
                detected_items.append(f"support_points_{support_points}")
            
            # Detect support cards in the support card region
            support_cards = self._detect_support_cards(img, device_id=device_id)
            detected_items.extend(support_cards)
            
            # Detect friend points earned
            friend_points = self._extract_friend_points(img, device_id=device_id)
            if friend_points is not None:
                detected_items.append(f"friend_points_{friend_points}")
            
            # Update instance tracking
            if support_points is not None:
                self.last_support_points[device_id] = support_points
            
            if friend_points is not None:
                if device_id not in self.friend_points_earned:
                    self.friend_points_earned[device_id] = 0
                self.friend_points_earned[device_id] += friend_points
            
        except Exception as e:
            print(f"❌ Error processing screenshot for items: {e}")
        
        return detected_items
    
    def is_new_cycle(self, screenshot, instance_data: Dict[str, Any]) -> bool:
        """
        Determine if this is the start of a new friend point cycle
        """
        device_id = instance_data.get('device_id', 'unknown')
        
        try:
            # Convert to numpy array if needed
            if isinstance(screenshot, np.ndarray):
                img = screenshot
            else:
                img = np.array(screenshot)
            
            # Check if we're back at the friend list (indicating cycle completion)
            friend_list_detected = self._detect_friend_list(img, device_id=device_id)
            
            # Check if support points have changed (indicating new cycle)
            current_points = self._extract_support_points(img, device_id=device_id)
            if current_points is not None:
                last_points = self.last_support_points.get(device_id, 0)
                if current_points != last_points:
                    return True
            
            return friend_list_detected
            
        except Exception as e:
            print(f"❌ Error checking for new cycle: {e}")
            return False
    
    def _get_default_slot_positions(self) -> Dict[str, Tuple[float, float, float, float]]:
        """Get default positions for support card detection slots"""
        return {
            "support_card_1": (0.2, 0.3, 0.4, 0.5),
            "support_card_2": (0.4, 0.3, 0.6, 0.5),
            "support_card_3": (0.6, 0.3, 0.8, 0.5),
            "support_card_4": (0.2, 0.5, 0.4, 0.7),
            "support_card_5": (0.4, 0.5, 0.6, 0.7),
            "support_card_6": (0.6, 0.5, 0.8, 0.7)
        }
    
    def _crop_relative_region(self, image: np.ndarray, rel_coords: Tuple[float, float, float, float], 
                             verbose: bool = False, device_id: str = 'unknown') -> Optional[np.ndarray]:
        """Crop a region from image using relative coordinates"""
        try:
            height, width = image.shape[:2]
            x1 = int(rel_coords[0] * width)
            y1 = int(rel_coords[1] * height)
            x2 = int(rel_coords[2] * width)
            y2 = int(rel_coords[3] * height)
            
            cropped = image[y1:y2, x1:x2]
            
            if verbose:
                print(f"🔍 {device_id}: Cropped region {rel_coords} -> {cropped.shape}")
            
            return cropped
            
        except Exception as e:
            if verbose:
                print(f"❌ {device_id}: Error cropping region {rel_coords}: {e}")
            return None
    
    def _detect_support_cards(self, image: np.ndarray, device_id: str = 'unknown') -> List[str]:
        """Detect support cards in the image"""
        detected_cards = []
        
        try:
            # Get detection regions
            detection_regions = self.get_detection_regions()
            if not detection_regions:
                detection_regions = self._get_default_slot_positions()
            
            # Check each region for support cards
            for slot_name, rel_coords in detection_regions.items():
                slot_img = self._crop_relative_region(image, rel_coords, device_id=device_id)
                if slot_img is not None:
                    card_type = self._match_support_card(slot_img, device_id=device_id, slot_name=slot_name)
                    if card_type:
                        detected_cards.append(card_type)
            
        except Exception as e:
            print(f"❌ Error detecting support cards: {e}")
        
        return detected_cards
    
    def _match_support_card(self, slot_img: np.ndarray, device_id: str = 'unknown', slot_name: str = 'unknown') -> Optional[str]:
        """Match a support card in the given slot image"""
        try:
            # Get card reference folder
            card_folder = self.project_root / "games" / "umamusume-fp" / "cards"
            if not card_folder.exists():
                return None
            
            # Template matching for support cards
            best_match = None
            best_score = 0
            threshold = self.get_template_threshold('support_card')
            
            for card_file in card_folder.iterdir():
                if card_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    template = cv2.imread(str(card_file))
                    if template is not None:
                        # Resize template to match slot size
                        template_resized = cv2.resize(template, (slot_img.shape[1], slot_img.shape[0]))
                        
                        # Template matching
                        result = cv2.matchTemplate(slot_img, template_resized, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(result)
                        
                        if max_val > threshold and max_val > best_score:
                            best_score = max_val
                            best_match = card_file.stem
            
            return best_match
            
        except Exception as e:
            print(f"❌ Error matching support card in {slot_name}: {e}")
            return None
    
    def _extract_support_points(self, screenshot: np.ndarray, verbose: bool = False, device_id: str = 'unknown') -> Optional[int]:
        """Extract support points from the designated region"""
        try:
            # Crop the support points region
            x1, y1, x2, y2 = self.support_points_region
            points_img = screenshot[y1:y2, x1:x2]
            
            # Convert to grayscale for better OCR
            gray = cv2.cvtColor(points_img, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing for better OCR
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR to extract text
            text = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789')
            
            # Clean and parse the text
            text = text.strip()
            if text and text.isdigit():
                points = int(text)
                if verbose:
                    print(f"💎 {device_id}: Extracted support points: {points}")
                return points
            
        except Exception as e:
            if verbose:
                print(f"❌ {device_id}: Error extracting support points: {e}")
        
        return None
    
    def _extract_friend_points(self, screenshot: np.ndarray, verbose: bool = False, device_id: str = 'unknown') -> Optional[int]:
        """Extract friend points earned from support card usage"""
        try:
            # Look for friend points in the support result area
            height, width = screenshot.shape[:2]
            result_region = (int(width * 0.3), int(height * 0.4), int(width * 0.7), int(height * 0.6))
            
            x1, y1, x2, y2 = result_region
            result_img = screenshot[y1:y2, x1:x2]
            
            # Convert to grayscale for OCR
            gray = cv2.cvtColor(result_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR to extract text
            text = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789+')
            
            # Clean and parse the text
            text = text.strip()
            if text and any(c.isdigit() for c in text):
                # Extract numbers from text like "10+", "5", etc.
                import re
                numbers = re.findall(r'\d+', text)
                if numbers:
                    points = int(numbers[0])
                    if verbose:
                        print(f"👥 {device_id}: Extracted friend points: {points}")
                    return points
            
        except Exception as e:
            if verbose:
                print(f"❌ {device_id}: Error extracting friend points: {e}")
        
        return None
    
    def _detect_friend_list(self, screenshot: np.ndarray, device_id: str = 'unknown') -> bool:
        """Detect if we're on the friend list screen"""
        try:
            # Crop the friend list region
            x1, y1, x2, y2 = self.friend_list_region
            friend_list_img = screenshot[y1:y2, x1:x2]
            
            # Simple template matching or feature detection
            # For now, use a simple heuristic based on color/pattern
            # This can be improved with actual template images
            
            # Check for common friend list UI elements
            gray = cv2.cvtColor(friend_list_img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Count edge pixels as a simple heuristic
            edge_density = np.sum(edges > 0) / edges.size
            
            # Friend list typically has more structured UI elements
            return edge_density > 0.1
            
        except Exception as e:
            print(f"❌ Error detecting friend list: {e}")
            return False
    
    def get_friend_points_earned(self, device_id: str = 'unknown') -> int:
        """Get total friend points earned for a device"""
        return self.friend_points_earned.get(device_id, 0)
    
    def reset_friend_points_tracking(self, device_id: str = 'unknown'):
        """Reset friend points tracking for a device"""
        if device_id in self.friend_points_earned:
            del self.friend_points_earned[device_id]
        if device_id in self.last_support_points:
            del self.last_support_points[device_id] 