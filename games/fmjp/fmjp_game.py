"""
FMJP Game Implementation
Minimal implementation of the BaseGame class for FMJP automation
"""

import time
from turtle import delay
import cv2
import os
import pytesseract
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from games.base_game import BaseGame
from core.action_types import (
    create_conditional_action, create_loop_action, create_macro_action, create_swipe_action, create_tap_action, create_wait_action, create_typing_action,
    create_counter_action, ActionConfig, StateConfig
)


class FmjpGame(BaseGame):
    """FMJP specific game implementation"""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)
        self.display_name = "FMJP"
        
        # FMJP specific constants
        self.last_score = {}  # Per-instance tracking
    
    def log_verbose_config(self, device_id: str = 'system'):
        """Log detailed configuration information for debugging"""
        print(f"🔧 Instance {device_id}: FMJP verbose configuration:")
        print(f"   📱 App package: {self.get_app_package()}")
        print(f"   📱 App activity: {self.get_app_activity()}")
        print(f"   🎯 Cycles per session: {self.get_cycles_per_session()}")
        print(f"   📐 Device resolution: {self.get_device_resolution()}")
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
        """Define FMJP automation states"""
        return {
            "start": {
                "timeout": 0,
                "templates": [],
                "actions": [
                    create_tap_action("start_text", offset_y=70, delay_after=2),  
                    create_tap_action("guest_icon", offset_y=0, delay_after=2),   
                    create_tap_action("confirm_positive_icon", delay_after=10),  
                    create_tap_action("start_text", offset_y=70, delay_after=2),
                    create_tap_action("auto_0", delay_after=2, delay_before=5),
                    create_loop_action(
                        condition="tutorial_move_text",
                        condition_likelihood=0.8,
                        actions=[],
                    ),
                    create_swipe_action(start_coordinates=(100, 400), end_coordinates=(200, 400), duration=3000, delay_after=2),
                    create_tap_action("focus_icon", delay_after=2, delay_before=2),
                    create_tap_action("tutorial_action_text", coordinates=(900, 440), delay_after=5),
                    create_tap_action("tutorial_quest_text", coordinates=(900, 440), delay_after=5),
                    create_loop_action(
                        condition="focus_icon",
                        condition_likelihood=0.8,
                        actions=[
                            create_swipe_action(start_coordinates=(100, 400), end_coordinates=(200, 400), duration=1000),
                        ],
                    ),
                    create_tap_action("focus_icon", coordinates=(900, 440), delay_after=5),
                    create_loop_action(
                        condition="tutorial_auto_icon",
                        condition_likelihood=0.8,
                        actions=[
                            create_swipe_action(start_coordinates=(100, 400), end_coordinates=(200, 400), duration=1000),
                        ],
                    ),
                    create_tap_action("tutorial_auto_icon", delay_after=2),
                    create_tap_action("tutorial_auto_icon", delay_after=2),
                    create_tap_action("auto_0", delay_after=2),
                    create_tap_action("close_popup_icon", delay_after=2),
                    create_tap_action("auto_0", delay_after=2, tap_times=3, tap_delay=1),
                    create_tap_action("dialog_icon", delay_after=2),
                    create_tap_action("tutorial_battle_text_1", delay_after=5, tap_times=3, tap_delay=2),
                    create_tap_action("input_name_text", delay_after=2),
                    create_typing_action("exzork"),
                    create_tap_action(None, coordinates=(470, 420), delay_after=2, timeout=5),
                    create_tap_action(None, coordinates=(470, 420), delay_after=2, timeout=5),
                    create_tap_action("tutorial_battle_text_2", delay_after=5, tap_times=2, tap_delay=2),
                    create_tap_action("dialog_icon", delay_after=1),
                    create_tap_action("tutorial_battle_text_3", delay_after=5, tap_times=3, tap_delay=2),
                    create_loop_action(
                        condition="tutorial_inside_battle_text_1",
                        condition_likelihood=0.8,
                        actions=[
                            create_tap_action("skip_btn", delay_after=2, timeout=1),
                            create_tap_action("confirm_positive_icon", delay_after=2, timeout=1),
                            create_swipe_action(start_coordinates=(100, 400), end_coordinates=(200, 400), duration=1000),
                        ],
                    ),
                    create_tap_action("tutorial_inside_battle_text_1", delay_after=2, tap_times=8, tap_delay=1),
                    create_tap_action("tutorial_battle_skill_1", delay_before=2,delay_after=5, tap_times=5, tap_delay=2),
                    create_tap_action("tutorial_battle_skill_2", delay_before=2, delay_after=5, tap_times=2, tap_delay=2),
                    create_tap_action("tutorial_battle_target_right_1", coordinates=(900, 280), delay_after=5),
                    create_tap_action("tutorial_battle_skill_3", delay_after=5, tap_times=2, tap_delay=2),
                    create_tap_action("tutorial_battle_target_right_2", coordinates=(900, 280), delay_after=5),
                    create_tap_action("tutorial_battle_skill_4", delay_after=5, tap_times=3, tap_delay=2),
                    create_loop_action(
                        condition="battle_2_1_text",
                        condition_likelihood=0.8,
                        actions=[
                            create_tap_action("skip_btn", delay_after=2, timeout=1),
                            create_tap_action("confirm_positive_icon", delay_after=2, timeout=1),
                            create_tap_action("dialog_icon", delay_after=2, timeout=1),
                        ],
                    ),
                    create_tap_action("battle_2_1_text", delay_after=2),
                    create_tap_action("battle_2_select_char_1", delay_after=2),
                    create_tap_action("battle_2_skill_1", delay_after=2),
                    create_tap_action("battle_2_select_char_2", delay_after=2),
                    create_tap_action("battle_2_2_text", delay_after=2, tap_times=4, tap_delay=2),
                    create_tap_action("close_popup_icon", delay_after=2, delay_before=2),
                    create_loop_action(
                        condition="battle_2_3_text",
                        condition_likelihood=0.8,
                        actions=[
                            create_tap_action("battle_char_1_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_2_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_3_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_4_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_1_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_2_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_3_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_4_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                        ],
                    ),
                    create_loop_action(
                        condition="focus_icon",
                        condition_likelihood=0.8,
                        actions=[
                            create_swipe_action(start_coordinates=(200, 400), end_coordinates=(100, 400), duration=100),
                        ],
                    ),
                    create_tap_action(None,coordinates=(900, 440), delay_after=5),
                    create_loop_action(
                        condition="tutorial_recruit_open",
                        actions=[
                            create_tap_action("skip_btn", delay_after=2, timeout=1),
                            create_tap_action("confirm_positive_icon", delay_after=2, timeout=1),
                            create_tap_action("dialog_icon", delay_after=2, timeout=1),
                        ]
                    ),
                    create_tap_action("tutorial_recruit_open", delay_after=2),
                    create_tap_action("battle_2_done_btn", likelihood=0.6, delay_after=2),
                    create_tap_action("tutorial_gacha_btn", tap_times=3, tap_delay=2, delay_after=2),
                    create_tap_action("gacha_machine"),
                    create_swipe_action(start_coordinates=(630, 140), end_coordinates=(630, 340), duration=1000, delay_after=5), #pull gacha
                    create_tap_action(None, coordinates=(630, 140), delay_before=4, delay_after=2, tap_times=3, tap_delay=2, timeout=5),
                    create_tap_action("auto_big_0", delay_after=2, tap_times=3, tap_delay=2),
                    create_tap_action("battle_btn", delay_after=2, tap_times=3, tap_delay=2),
                    create_tap_action("focus_map_icon", delay_after=2),
                    create_tap_action("battle_map_go_btn", delay_after=2),
                    create_tap_action("confirm_positive_icon", delay_after=2),
                    create_tap_action("battle_3_1_text", delay_after=2, tap_times=3, tap_delay=2),
                    create_tap_action("battle_add_support",coordinates=(180,230), delay_after=5, tap_times=3, tap_delay=2),
                    create_tap_action("support_default_char_1",coordinates=(80,120),delay_after=2),
                    create_tap_action("confirm_add_support", delay_after=2),
                    create_tap_action("battle_ready_btn",delay_after=2),
                    create_tap_action("battle_char_1_skill_1", delay_after=2, tap_times=3, tap_delay=2),
                    create_loop_action(
                        condition="tutorial_member_open",
                        condition_likelihood=0.6,
                        actions=[
                            create_tap_action("battle_char_1_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_2_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_3_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_4_skill_1", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_1_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_2_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_3_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_tap_action("battle_char_4_skill_2", likelihood=0.6, timeout=1, tap_times=2, tap_delay=1),
                            create_conditional_action(
                                condition="battle_2_link_1",
                                if_true=[
                                    create_tap_action("battle_2_link_1", tap_times=3, tap_delay=1),
                                    create_tap_action("battle_2_link_2",tap_times=3, tap_delay=1),
                                    create_tap_action("battle_2_4_text", coordinates=(500,240), delay_after=2, tap_times=3, tap_delay=2, timeout=5),
                                    create_tap_action("battle_char_1_skill_1", tap_times=2, tap_delay=1, timeout=5),
                                    create_tap_action("battle_2_next", delay_after=2, tap_times=3, tap_delay=2, timeout=5),
                                    create_tap_action("close_popup_icon", delay_after=2, delay_before=2, timeout=5)
                                ]
                            )

                        ]
                    ),
                    create_tap_action("tutorial_member_open", delay_after=2, tap_times=3, tap_delay=1),
                    create_tap_action("battle_2_done_btn", likelihood=0.6, delay_after=2, tap_times=2, tap_delay=1),
                    create_tap_action("battle_home_btn", delay_after=2, tap_times=2, tap_delay=1),
                    create_tap_action("tutorial_member_1_text", coordinates=(400,500), delay_after=2, tap_times=3, tap_delay=2),
                    create_tap_action("tutorial_member_char_1", delay_after=2, tap_times=2, tap_delay=2),
                    create_tap_action("tutorial_member_info_1", delay_after=2),
                    create_tap_action("tutorial_member_info_2", delay_after=2),
                    create_tap_action("tutorial_level_up_btn_1", delay_after=2, tap_times=2, tap_delay=2),
                    create_tap_action("tutorial_level_up_btn_2", delay_after=2, tap_times=2, tap_delay=2),
                    create_tap_action("confirm_positive_icon",likelihood=0.6, delay_after=2, tap_times=2, tap_delay=2),
                    create_tap_action("battle_2_next", delay_after=2, tap_times=3, tap_delay=2),
                    create_tap_action("close_popup_icon", delay_after=2, delay_before=2),
                    create_tap_action("battle_home_btn", delay_after=2, tap_times=2, tap_delay=1),
                    create_tap_action("battle_btn", delay_after=2, tap_times=2, tap_delay=1),
                    create_tap_action("battle_home_btn", delay_after=2, tap_times=2, tap_delay=1),
                ],
                "next_states": ["main_loop"]
            },
            "main_loop": {
                "timeout": 60,
                "templates": ["loop_button"],
                "actions": [
                    create_counter_action(delay_before=0.5), 
                    create_tap_action("loop_button", offset_x=5, offset_y=0)  # Template matching with offset
                ],
                "next_states": ["main_loop", "completed"]
            },
            "completed": {
                "timeout": 10,
                "templates": [],
                "actions": [],
                "next_states": ["start"]
            }
        }
    
    def get_app_package(self) -> str:
        """Return the Android app package name for FMJP"""
        return "com.fmjp.game"  # TODO: Replace with actual package name
    
    def get_app_activity(self) -> str:
        """Return the Android app activity name for FMJP"""
        return "com.fmjp.game.MainActivity"  # TODO: Replace with actual activity name
    
    def calculate_score(self, detected_items: List[str]) -> Tuple[int, Dict[str, int]]:
        """Calculate score based on detected items"""
        card_scoring = self.get_card_scoring()
        total_score = 0
        item_scores = {}
        
        for item in detected_items:
            score = card_scoring.get(item, self.get_default_item_score())
            item_scores[item] = score
            total_score += score
        
        return total_score, item_scores
    
    def get_minimum_score_threshold(self) -> int:
        """Return minimum score threshold for notifications"""
        return self.config.get('minimum_score_threshold', 10)
    
    def process_screenshot_for_items(self, screenshot, instance_data: Dict[str, Any]) -> List[str]:
        """Process screenshot to detect items/cards"""
        # TODO: Implement item detection logic
        # This is a placeholder implementation
        detected_items = []
        
        # Example: Check detection regions for items
        detection_regions = self.get_detection_regions()
        if detection_regions:
            for slot_name, region in detection_regions.items():
                # TODO: Implement actual item detection in each region
                pass
        
        return detected_items
    
    def is_new_cycle(self, screenshot, instance_data: Dict[str, Any]) -> bool:
        """Determine if this is the start of a new cycle"""
        # TODO: Implement cycle detection logic
        # This is a placeholder implementation
        return False
    
    def get_device_resolution(self) -> Tuple[int, int]:
        """Return the expected device resolution for FMJP"""
        resolution = self.config.get('device_resolution', [540, 960])
        return tuple(resolution)
    
    def get_detection_regions(self) -> Dict[str, Tuple[float, float, float, float]]:
        """Return detection regions for item recognition"""
        return self.config.get('detection_regions', {})
    
    def get_card_scoring(self) -> Dict[str, int]:
        """Return scoring values for different cards/items"""
        return self.config.get('card_scoring', {})
    
    def get_default_item_score(self) -> int:
        """Return default score for unrecognized items"""
        return self.config.get('default_item_score', 5)
    
    def get_state_timeouts(self) -> Dict[str, Optional[int]]:
        """Return custom timeouts for different states"""
        return self.config.get('state_timeouts', {})
    
    def get_template_threshold(self, template_name: str) -> float:
        """Return template matching threshold for specific templates"""
        template_thresholds = self.config.get('template_thresholds', {})
        return template_thresholds.get(template_name, 0.8)
    
    def get_initial_state(self) -> str:
        """Return the initial state for automation"""
        return "start"
    
    def should_send_discord_notification(self, detected_items: List[str]) -> bool:
        """Determine if Discord notification should be sent"""
        if not self.has_discord_webhook():
            return False
        
        total_score, _ = self.calculate_score(detected_items)
        return total_score >= self.get_minimum_score_threshold()
    
    def format_results_for_discord(self, instance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format results for Discord notification"""
        detected_items = instance_data.get('detected_items', [])
        total_score, item_scores = self.calculate_score(detected_items)
        
        return {
            "title": f"🎮 {self.get_display_name()} Results",
            "description": f"Instance {instance_data.get('instance_number', 'unknown')} completed",
            "fields": [
                {
                    "name": "📊 Total Score",
                    "value": str(total_score),
                    "inline": True
                },
                {
                    "name": "🎴 Items Found",
                    "value": str(len(detected_items)),
                    "inline": True
                },
                {
                    "name": "🔄 Cycles Completed",
                    "value": str(instance_data.get('cycles_completed', 0)),
                    "inline": True
                }
            ],
            "color": 0x00ff00 if total_score >= self.get_minimum_score_threshold() else 0xff0000
        } 