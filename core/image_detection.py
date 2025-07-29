"""
Image Detection and Processing for automation
"""

import cv2
import numpy as np
import os
from typing import Optional, Tuple, List, Dict
from pathlib import Path


class ImageDetector:
    """Handles image detection, template matching, and image processing"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        # Store detected template coordinates
        self.detected_coordinates = {}
    
    def detect_template(self, screenshot: np.ndarray, template_path: str, 
                       threshold: float = 0.8) -> bool:
        """Detect if a template image is present in the screenshot"""
        try:
            # Load template image
            template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if template is None:
                print(f"❌ Could not load template: {template_path}")
                return False
            
            # Perform template matching
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # Save center coordinates of detected template
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                
                # Store coordinates with template name as key
                template_name = Path(template_path).stem
                self.detected_coordinates[template_name] = (center_x, center_y)
                
                print(f"✅ Template '{template_name}' detected at center coordinates: ({center_x}, {center_y})")
                return True
            
            return False
        except Exception as e:
            print(f"❌ Error in template detection: {e}")
            return False
    
    def detect_template_location(self, screenshot: np.ndarray, template_path: str, 
                                threshold: float = 0.8) -> Optional[Tuple[int, int, int, int]]:
        """Detect template location and return bounding box (x, y, width, height)"""
        try:
            template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if template is None:
                return None
            
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                h, w = template.shape[:2]
                # Save center coordinates
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                template_name = Path(template_path).stem
                self.detected_coordinates[template_name] = (center_x, center_y)
                
                return (max_loc[0], max_loc[1], w, h)
            
            return None
        except Exception as e:
            print(f"❌ Error in template location detection: {e}")
            return None
    
    def get_detected_coordinates(self, template_name: str) -> Optional[Tuple[int, int]]:
        """Get saved center coordinates for a detected template"""
        return self.detected_coordinates.get(template_name)
    
    def clear_detected_coordinates(self):
        """Clear all saved coordinates"""
        self.detected_coordinates.clear()
    
    def get_all_detected_coordinates(self) -> Dict[str, Tuple[int, int]]:
        """Get all saved coordinates"""
        return self.detected_coordinates.copy()
    
    def crop_image_region(self, image: np.ndarray, x: int, y: int, 
                         width: int, height: int) -> Optional[np.ndarray]:
        """Crop a specific region from an image"""
        try:
            img_height, img_width = image.shape[:2]
            
            # Ensure coordinates are within image bounds
            x = max(0, min(x, img_width))
            y = max(0, min(y, img_height))
            x2 = max(0, min(x + width, img_width))
            y2 = max(0, min(y + height, img_height))
            
            if x2 > x and y2 > y:
                return image[y:y2, x:x2]
            else:
                return None
        except Exception as e:
            print(f"❌ Error cropping image region: {e}")
            return None
    
    def crop_relative_region(self, image: np.ndarray, rel_x: float, rel_y: float, 
                           rel_width: float, rel_height: float) -> Optional[np.ndarray]:
        """Crop region using relative coordinates (0.0 to 1.0)"""
        try:
            img_height, img_width = image.shape[:2]
            
            x = int(rel_x * img_width)
            y = int(rel_y * img_height)
            width = int(rel_width * img_width)
            height = int(rel_height * img_height)
            
            return self.crop_image_region(image, x, y, width, height)
        except Exception as e:
            print(f"❌ Error cropping relative region: {e}")
            return None
    
    def preprocess_for_ocr(self, image: np.ndarray, scale_factor: int = 3) -> np.ndarray:
        """Preprocess image for better OCR recognition"""
        try:
            # Scale up the image
            height, width = image.shape[:2]
            scaled = cv2.resize(
                image, 
                (width * scale_factor, height * scale_factor), 
                interpolation=cv2.INTER_CUBIC
            )
            
            # Convert to grayscale if needed
            if len(scaled.shape) == 3:
                gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
            else:
                gray = scaled
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Apply contrast enhancement and OTSU thresholding
            enhanced = cv2.convertScaleAbs(blurred, alpha=2.0, beta=10)
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
        except Exception as e:
            print(f"❌ Error preprocessing image for OCR: {e}")
            return image
    
    def bytes_to_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Convert bytes to OpenCV image"""
        try:
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            print(f"❌ Error converting bytes to image: {e}")
            return None
    
    def get_template_path(self, game_name: str, template_name: str) -> Optional[Path]:
        """Get the full path to a game-specific template image"""
        # Try game-specific template first
        game_template_path = self.project_root / "games" / game_name / "templates" / f"{template_name}.png"
        if game_template_path.exists():
            return game_template_path
        
        # Try with different extensions
        for ext in ['.jpg', '.jpeg']:
            game_template_path = self.project_root / "games" / game_name / "templates" / f"{template_name}{ext}"
            if game_template_path.exists():
                return game_template_path
        
        # Fall back to global template directory
        global_template_path = self.project_root / "templates" / f"{template_name}.png"
        if global_template_path.exists():
            return global_template_path
        
        # Try global with different extensions
        for ext in ['.jpg', '.jpeg']:
            global_template_path = self.project_root / "templates" / f"{template_name}{ext}"
            if global_template_path.exists():
                return global_template_path
        
        # Legacy support - check old directory structure
        legacy_template_path = self.project_root / "step" / f"{template_name}.png"
        if legacy_template_path.exists():
            return legacy_template_path
        
        return None
    
    def detect_game_template(self, screenshot: np.ndarray, game_name: str, 
                           template_name: str, threshold: float = 0.8) -> bool:
        """Detect a game-specific template in screenshot"""
        template_path = self.get_template_path(game_name, template_name)
        
        if template_path is None:
            print(f"❌ Template '{template_name}' not found for game '{game_name}'")
            return False
        
        return self.detect_template(screenshot, str(template_path), threshold)
    
    def list_available_templates(self, game_name: str) -> List[str]:
        """List all available templates for a game"""
        templates = []
        
        # Check game-specific templates
        game_template_dir = self.project_root / "games" / game_name / "templates"
        if game_template_dir.exists():
            for file in game_template_dir.glob("*"):
                if file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    templates.append(file.stem)
        
        # Check global templates
        global_template_dir = self.project_root / "templates"
        if global_template_dir.exists():
            for file in global_template_dir.glob("*"):
                if file.suffix.lower() in ['.png', '.jpg', '.jpeg'] and file.stem not in templates:
                    templates.append(file.stem)
        
        # Check legacy templates
        legacy_template_dir = self.project_root / "step"
        if legacy_template_dir.exists():
            for file in legacy_template_dir.glob("*"):
                if file.suffix.lower() in ['.png', '.jpg', '.jpeg'] and file.stem not in templates:
                    templates.append(file.stem)
        
        return sorted(templates) 