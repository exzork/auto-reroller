"""
Uma Musume Game Implementation
Example implementation of the BaseGame class for Uma Musume gacha automation
"""

import cv2
import os
import pytesseract
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from games.base_game import BaseGame
from core.action_types import (
    create_macro_action, create_tap_action, create_wait_action, create_typing_action,
    ActionConfig, StateConfig
)


class UmamusumeGame(BaseGame):
    """Uma Musume specific game implementation"""
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)
        self.display_name = "Uma Musume Pretty Derby"
        
        # Uma Musume specific constants
        self.support_points_region = (400, 805, 435, 830)  # (x1, y1, x2, y2)
        self.last_support_points = {}  # Per-instance tracking
    
    def log_verbose_config(self, device_id: str = 'system'):
        """Log detailed configuration information for debugging"""
        print(f"🔧 Instance {device_id}: Uma Musume verbose configuration:")
        print(f"   📱 App package: {self.get_app_package()}")
        print(f"   📱 App activity: {self.get_app_activity()}")
        print(f"   🎯 Cycles per session: {self.get_cycles_per_session()}")
        print(f"   📐 Device resolution: {self.get_device_resolution()}")
        print(f"   🎯 Support points region: {self.support_points_region}")
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
        card_folder = self.project_root / "games" / "umamusume" / "cards"
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
        """Define Uma Musume automation states"""
        return {
            "waiting_for_until_gacha": {
                "timeout": 30,
                "templates": ["until gacha"],
                "actions": [],
                "next_states": ["executing_until_gacha"]
            },
            "executing_until_gacha": {
                "timeout": 110,
                "templates": [],
                "actions": [create_macro_action("until gacha")],
                "next_states": ["waiting_for_first_gacha"]
            },
            "waiting_for_first_gacha": {
                "timeout": 45,
                "templates": ["first_gacha"],
                "actions": [],
                "next_states": ["pulling_first_gacha"]
            },
            "pulling_first_gacha": {
                "timeout": 30,
                "templates": [],
                "actions": [create_macro_action("first_gacha")],
                "processes_items": True,
                "next_states": ["pulling_gacha"]
            },
            "pulling_gacha": {
                "timeout": 180,
                "templates": [],
                "actions": [create_macro_action("gacha")],
                "processes_items": True,
                "next_states": ["executing_bind_id", "pulling_gacha"]
            },
            "executing_bind_id": {
                "timeout": 120,
                "templates": [],
                "actions": [
                    create_macro_action("back_home"),
                    create_macro_action("bind_id")
                ],
                "next_states": ["completed"]
            },
            "completed": {
                "timeout": 30,
                "templates": [],
                "actions": [],
                "next_states": ["waiting_for_until_gacha"]
            }
        }
    
    def get_app_package(self) -> str:
        """Return Uma Musume app package"""
        return "com.cygames.umamusume"
    
    def get_app_activity(self) -> str:
        """Return Uma Musume app activity"""
        return "com.cygames.umamusume/jp.co.cygames.umamusume_activity.UmamusumeActivity"
    
    def calculate_score(self, detected_items: List[str]) -> Tuple[int, Dict[str, int]]:
        """Calculate score for Uma Musume cards"""
        card_scores = self.get_card_scoring()
        default_score = self.get_default_item_score()
        
        total = 0
        breakdown = {}
        
        for card in detected_items:
            score = card_scores.get(card.lower(), default_score)
            total += score
            breakdown[card] = breakdown.get(card, 0) + score
        
        return total, breakdown
    
    def get_minimum_score_threshold(self) -> int:
        """Return minimum score threshold for Discord notifications"""
        return 45
    
    def process_screenshot_for_items(self, screenshot, instance_data: Dict[str, Any]) -> List[str]:
        """Process screenshot to detect Uma Musume cards"""
        try:
            verbose = instance_data.get('verbose', False)
            device_id = instance_data.get('device_id', 'unknown')
            
            if verbose:
                print(f"🔍 Instance {device_id}: Starting card detection process")
            
            # Load slot positions from config
            slot_positions = self.get_detection_regions()
            
            if not slot_positions:
                # Use default slot positions if not in config
                slot_positions = self._get_default_slot_positions()
                if verbose:
                    print(f"🔍 Instance {device_id}: Using default slot positions ({len(slot_positions)} slots)")
            else:
                if verbose:
                    print(f"🔍 Instance {device_id}: Using config slot positions ({len(slot_positions)} slots)")
            
            detected_cards = []
            
            for slot_name, rel_coords in slot_positions.items():
                if not slot_name.startswith('slot'):
                    continue
                
                try:
                    if verbose:
                        print(f"🔍 Instance {device_id}: Processing {slot_name} at {rel_coords}")
                    
                    # Crop slot region
                    slot_img = self._crop_relative_region(screenshot, rel_coords, verbose, device_id)
                    if slot_img is None:
                        if verbose:
                            print(f"❌ Instance {device_id}: Failed to crop {slot_name}")
                        continue
                    
                    # Match against reference cards
                    card_name = self._match_card_in_slot(slot_img, verbose, device_id, slot_name)
                    if card_name:
                        detected_cards.append(card_name)
                        if verbose:
                            print(f"✅ Instance {device_id}: Found '{card_name}' in {slot_name}")
                    elif verbose:
                        print(f"🔍 Instance {device_id}: No card matched in {slot_name}")
                        
                except Exception as e:
                    if verbose:
                        print(f"❌ Instance {device_id}: Error processing {slot_name}: {e}")
                    continue
            
            if verbose:
                print(f"🎁 Instance {device_id}: Card detection complete - found {len(detected_cards)} cards: {detected_cards}")
            
            return detected_cards
            
        except Exception as e:
            print(f"❌ Error processing screenshot for cards: {e}")
            return []
    
    def is_new_cycle(self, screenshot, instance_data: Dict[str, Any]) -> bool:
        """Check if this is a new gacha pull by examining support points"""
        try:
            instance_id = instance_data['device_id']
            verbose = instance_data.get('verbose', False)
            
            if verbose:
                print(f"🔄 Instance {instance_id}: Checking for new cycle using support points")
            
            current_points = self._extract_support_points(screenshot, verbose, instance_id)
            
            if current_points is None:
                if verbose:
                    print(f"🔍 Instance {instance_id}: Could not extract support points from screenshot")
                else:
                    print(f"🔍 Instance {instance_id}: Could not extract support points from screenshot")
                return False  # Don't process if we can't read valid points
            
            # Compare with last known points for this instance
            last_points = self.last_support_points.get(instance_id)
            if last_points is not None and current_points == last_points:
                if verbose:
                    print(f"🔍 Instance {instance_id}: Same support points detected ({current_points}), same cycle")
                else:
                    print(f"🔍 Instance {instance_id}: Same support points detected ({current_points}), same cycle")
                return False  # Same pull detected
            
            # Update last known points for this instance
            self.last_support_points[instance_id] = current_points
            if verbose:
                print(f"✅ Instance {instance_id}: New cycle detected! Support points: {last_points} → {current_points}")
            else:
                print(f"✅ Instance {instance_id}: New cycle detected! Support points: {last_points} → {current_points}")
            return True  # New pull detected
            
        except Exception as e:
            print(f"❌ Error checking new cycle: {e}")
            return False
    
    def _get_default_slot_positions(self) -> Dict[str, Tuple[float, float, float, float]]:
        """Get default slot positions as relative coordinates"""
        # Default slot positions for 540x960 resolution, converted to relative
        return {
            "slot1": (50/540, 200/960, 100/540, 100/960),
            "slot2": (160/540, 200/960, 100/540, 100/960),
            "slot3": (270/540, 200/960, 100/540, 100/960),
            "slot4": (380/540, 200/960, 100/540, 100/960),
            "slot5": (50/540, 320/960, 100/540, 100/960),
            "slot6": (160/540, 320/960, 100/540, 100/960),
            "slot7": (270/540, 320/960, 100/540, 100/960),
            "slot8": (380/540, 320/960, 100/540, 100/960),
            "slot9": (50/540, 440/960, 100/540, 100/960),
            "slot10": (160/540, 440/960, 100/540, 100/960)
        }
    
    def _crop_relative_region(self, image: np.ndarray, rel_coords: Tuple[float, float, float, float], verbose: bool = False, device_id: str = 'unknown') -> Optional[np.ndarray]:
        """Crop region using relative coordinates"""
        try:
            rel_x, rel_y, rel_width, rel_height = rel_coords
            img_height, img_width = image.shape[:2]
            
            x = int(rel_x * img_width)
            y = int(rel_y * img_height)
            width = int(rel_width * img_width)
            height = int(rel_height * img_height)
            
            # Ensure coordinates are within bounds
            x = max(0, min(x, img_width))
            y = max(0, min(y, img_height))
            x2 = max(0, min(x + width, img_width))
            y2 = max(0, min(y + height, img_height))
            
            if x2 > x and y2 > y:
                cropped_img = image[y:y2, x:x2]
                if verbose:
                    print(f"✅ Instance {device_id}: Cropped {rel_coords} to {cropped_img.shape}")
                return cropped_img
            else:
                if verbose:
                    print(f"❌ Instance {device_id}: Cropped region out of bounds for {rel_coords}")
                return None
        except Exception as e:
            if verbose:
                print(f"❌ Instance {device_id}: Error cropping region {rel_coords}: {e}")
            return None
    
    def _match_card_in_slot(self, slot_img: np.ndarray, verbose: bool = False, device_id: str = 'unknown', slot_name: str = 'unknown') -> Optional[str]:
        """Match slot image against reference cards using ORB features"""
        try:
            # Path to card reference images
            slot_folder = self.project_root / "games" / "umamusume" / "cards"
            
            
            if not slot_folder.exists():
                if verbose:
                    print(f"❌ Instance {device_id}: Card reference folder not found: {slot_folder}")
                return None
            
            # Get reference files
            ref_files = [f for f in slot_folder.iterdir() 
                        if f.suffix.lower() in ['.png', '.jpg', '.jpeg']]
            
            if not ref_files:
                if verbose:
                    print(f"❌ Instance {device_id}: No reference card images found in {slot_folder}")
                return None
            
            # ORB feature matching
            orb = cv2.ORB_create(nfeatures=500)
            kp1, des1 = orb.detectAndCompute(slot_img, None)
            
            if des1 is None:
                if verbose:
                    print(f"❌ Instance {device_id}: No ORB features detected in {slot_name}")
                return None
            
            best_name, best_count = None, 0
            match_distance_threshold = 60
            min_good_matches = 45
            
            for ref_file in ref_files:
                ref_img = cv2.imread(str(ref_file))
                
                if ref_img is None:
                    if verbose:
                        print(f"❌ Instance {device_id}: Could not read reference image: {ref_file}")
                    continue
                
                # Resize reference to match slot size
                ref_resized = cv2.resize(ref_img, (slot_img.shape[1], slot_img.shape[0]))
                kp2, des2 = orb.detectAndCompute(ref_resized, None)
                
                if des2 is None:
                    if verbose:
                        print(f"❌ Instance {device_id}: No ORB features detected in reference image: {ref_file}")
                    continue
                
                # Match features
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = bf.match(des1, des2)
                good = [m for m in matches if m.distance < match_distance_threshold]
                
                match_count = len(good)
                
                # Track best match
                if match_count > best_count:
                    best_count = match_count
                    best_name = ref_file.stem
            
            # Return result
            if best_count >= min_good_matches:
                if verbose:
                    print(f"✅ Instance {device_id}: Found '{best_name}' in {slot_name} with {best_count} matches")
                return best_name
            else:
                if verbose:
                    print(f"❌ Instance {device_id}: No card matched in {slot_name} with enough matches ({best_count}/{min_good_matches})")
                return None
                
        except Exception as e:
            if verbose:
                print(f"❌ Instance {device_id}: Error matching card in {slot_name}: {e}")
            return None
    
    def _extract_support_points(self, screenshot: np.ndarray, verbose: bool = False, device_id: str = 'unknown') -> Optional[int]:
        """Extract support exchange points from screenshot using OCR"""
        try:
            if verbose:
                print(f"🔍 Instance {device_id}: Starting support points extraction")
            
            # Crop the support points region
            x1, y1, x2, y2 = self.support_points_region
            support_region = screenshot[y1:y2, x1:x2]
            
            if support_region.size == 0:
                if verbose:
                    print(f"❌ Instance {device_id}: Support region is empty")
                return None
            
            if verbose:
                print(f"🔍 Instance {device_id}: Cropped support region {self.support_points_region} - size: {support_region.shape}")
            
            # Scale up the image for better OCR (3x scale)
            scale_factor = 3
            height, width = support_region.shape[:2]
            scaled_region = cv2.resize(
                support_region, 
                (width * scale_factor, height * scale_factor), 
                interpolation=cv2.INTER_CUBIC
            )
            
            if verbose:
                print(f"🔍 Instance {device_id}: Scaled region to {scaled_region.shape}")
            
            # Convert to grayscale
            gray_region = cv2.cvtColor(scaled_region, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray_region, (3, 3), 0)
            
            # Try multiple preprocessing approaches
            processed_images = []
            
            # Method 1: OTSU thresholding with contrast enhancement
            enhanced = cv2.convertScaleAbs(blurred, alpha=2.0, beta=10)
            _, thresh1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(thresh1)
            
            # Method 2: Adaptive thresholding
            adaptive_thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            processed_images.append(adaptive_thresh)
            
            # Method 3: Simple binary threshold
            _, thresh2 = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
            processed_images.append(thresh2)
            
            if verbose:
                print(f"🔍 Instance {device_id}: Generated {len(processed_images)} preprocessed images for OCR")
            
            # Try OCR on each processed image
            ocr_configs = [
                '--psm 7 -c tessedit_char_whitelist=0123456789',
                '--psm 8 -c tessedit_char_whitelist=0123456789',
                '--psm 13 -c tessedit_char_whitelist=0123456789'
            ]
            
            results = []
            
            for i, processed_img in enumerate(processed_images):
                for j, config in enumerate(ocr_configs):
                    try:
                        text = pytesseract.image_to_string(processed_img, config=config).strip()
                        # Clean the text (remove any non-digit characters)
                        clean_text = ''.join(filter(str.isdigit, text))
                        
                        if verbose:
                            print(f"🔍 Instance {device_id}: OCR method {i+1}.{j+1} - raw: '{text}' → clean: '{clean_text}'")
                        
                        if clean_text and clean_text.isdigit():
                            points = int(clean_text)
                            # Reasonable range check (support points should be 0-99999)
                            if 0 <= points <= 99999:
                                results.append(points)
                                if verbose:
                                    print(f"✅ Instance {device_id}: Valid points found: {points}")
                            elif verbose:
                                print(f"❌ Instance {device_id}: Points {points} out of valid range (0-99999)")
                    except Exception as e:
                        if verbose:
                            print(f"❌ Instance {device_id}: OCR method {i+1}.{j+1} failed: {e}")
                        continue
            
            # Return the most common result or the first valid one
            if results:
                if len(results) > 1:
                    from collections import Counter
                    point_counts = Counter(results)
                    most_common_points = point_counts.most_common(1)[0][0]
                    if verbose:
                        print(f"✅ Instance {device_id}: Multiple results found {results}, using most common: {most_common_points}")
                    return most_common_points
                else:
                    if verbose:
                        print(f"✅ Instance {device_id}: Single result found: {results[0]}")
                    return results[0]
            
            if verbose:
                print(f"❌ Instance {device_id}: No valid support points extracted from OCR")
            return None
            
        except Exception as e:
            if verbose:
                print(f"❌ Instance {device_id}: Error extracting support points: {e}")
            return None 