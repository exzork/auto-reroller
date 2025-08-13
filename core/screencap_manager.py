"""
Screencap Manager for basic screen capture using exec-out screencap

This module provides a simple and reliable way to capture screenshots
using the standard Android screencap command.
"""

import subprocess
import time
import cv2
import numpy as np
from typing import Optional, Tuple
from pathlib import Path


class ScreencapManager:
    """Manages basic screen capture using exec-out screencap"""
    
    def __init__(self):
        self.device_info = {}
        self.last_screenshot_time = {}
        self.screenshot_count = {}
    
    def get_device_info(self, device_id: str) -> Optional[dict]:
        """Get device screen dimensions and density"""
        try:
            # Get screen dimensions
            result = subprocess.run([
                'adb', '-s', device_id, 'shell', 'wm', 'size'
            ], capture_output=True, timeout=5)
            
            if result.returncode != 0:
                return None
                
            size_output = result.stdout.decode().strip()
            width, height = map(int, size_output.split()[-1].split('x'))
            
            # Get screen density
            result = subprocess.run([
                'adb', '-s', device_id, 'shell', 'wm', 'density'
            ], capture_output=True, timeout=5)
            
            if result.returncode != 0:
                density = 420  # Default density
            else:
                density_output = result.stdout.decode().strip()
                density = int(density_output.split()[-1])
            
            return {
                'width': width,
                'height': height,
                'density': density
            }
            
        except Exception as e:
            print(f"❌ Error getting device info for {device_id}: {e}")
            return None
    
    def get_screenshot(self, device_id: str, save_to_file: bool = False) -> Optional[bytes]:
        """Get screenshot using exec-out screencap"""
        import time
        start_time = time.time()
        
        try:
            # Use exec-out screencap for direct binary output
            result = subprocess.run([
                'adb', '-s', device_id, 'exec-out', 'screencap', '-p'
            ], capture_output=True, timeout=15)
            
            elapsed = (time.time() - start_time) * 1000
            
            if result.returncode == 0 and result.stdout:
                # Validate the image data
                image_array = np.frombuffer(result.stdout, dtype=np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                
                if img is not None:
                    h, w = img.shape[:2]
                    
                    # Update stats
                    if device_id not in self.screenshot_count:
                        self.screenshot_count[device_id] = 0
                    self.screenshot_count[device_id] += 1
                    self.last_screenshot_time[device_id] = time.time()
                    
                    print(f"📸 Screenshot captured for {device_id}: {w}x{h} in {elapsed:.1f}ms")
                    
                    # Save to file if requested
                    if save_to_file:
                        self._save_screenshot(device_id, result.stdout)
                    
                    return result.stdout
                else:
                    print(f"❌ Failed to decode screenshot for {device_id} (took {elapsed:.1f}ms)")
                    return None
            else:
                error_msg = result.stderr.decode() if result.stderr else 'unknown error'
                print(f"❌ Screencap failed for {device_id} (took {elapsed:.1f}ms): {error_msg}")
                return None
                
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ Error getting screenshot for {device_id} (took {elapsed:.1f}ms): {e}")
            return None
    
    def get_screenshot_as_image(self, device_id: str) -> Optional[np.ndarray]:
        """Get screenshot as OpenCV image array"""
        screenshot_data = self.get_screenshot(device_id)
        if screenshot_data:
            image_array = np.frombuffer(screenshot_data, dtype=np.uint8)
            return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return None
    
    def get_multiple_screenshots(self, device_id: str, count: int = 5, delay: float = 0.1) -> list[bytes]:
        """Get multiple screenshots with optional delay"""
        screenshots = []
        
        for i in range(count):
            screenshot = self.get_screenshot(device_id)
            if screenshot:
                screenshots.append(screenshot)
                if i < count - 1:  # Don't delay after last screenshot
                    time.sleep(delay)
            else:
                break
        
        return screenshots
    
    def _save_screenshot(self, device_id: str, screenshot_data: bytes):
        """Save screenshot to file"""
        try:
            # Create tmp folder if it doesn't exist
            tmp_dir = Path("tmp")
            tmp_dir.mkdir(exist_ok=True)
            
            # Save screenshot with device ID and timestamp
            timestamp = int(time.time() * 1000)  # Milliseconds timestamp
            screenshot_path = tmp_dir / f"screenshot_{device_id}_{timestamp}.jpg"
            
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot_data)
            
            print(f"💾 Screenshot saved: {screenshot_path}")
            
        except Exception as e:
            print(f"⚠️ Failed to save screenshot: {e}")
    
    def get_stats(self, device_id: str) -> dict:
        """Get screenshot statistics for device"""
        stats = {
            'total_screenshots': self.screenshot_count.get(device_id, 0),
            'last_screenshot_time': self.last_screenshot_time.get(device_id),
            'device_info': self.device_info.get(device_id)
        }
        
        if stats['last_screenshot_time']:
            stats['time_since_last'] = time.time() - stats['last_screenshot_time']
        
        return stats
    
    def test_screencap(self, device_id: str) -> dict:
        """Test screencap functionality"""
        print(f"🧪 Testing screencap for device: {device_id}")
        
        results = {
            'device_info': False,
            'screenshot': False,
            'image_decode': False,
            'timing': 0,
            'errors': []
        }
        
        try:
            # Test device info
            device_info = self.get_device_info(device_id)
            if device_info:
                results['device_info'] = True
                self.device_info[device_id] = device_info
                print(f"✅ Device info: {device_info['width']}x{device_info['height']}")
            else:
                results['errors'].append("Failed to get device info")
            
            # Test screenshot
            start_time = time.time()
            screenshot = self.get_screenshot(device_id)
            results['timing'] = (time.time() - start_time) * 1000
            
            if screenshot:
                results['screenshot'] = True
                print(f"✅ Screenshot captured: {len(screenshot)} bytes")
                
                # Test image decoding
                try:
                    image_array = np.frombuffer(screenshot, dtype=np.uint8)
                    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    if img is not None:
                        results['image_decode'] = True
                        print(f"✅ Image decoded: {img.shape[1]}x{img.shape[0]}")
                    else:
                        results['errors'].append("Failed to decode image")
                except Exception as e:
                    results['errors'].append(f"Image decode error: {e}")
            else:
                results['errors'].append("Failed to capture screenshot")
            
        except Exception as e:
            results['errors'].append(f"Test error: {e}")
        
        return results


def test_screencap_manager(device_id: str):
    """Test the screencap manager"""
    print(f"🧪 Testing ScreencapManager for device: {device_id}")
    print("=" * 50)
    
    manager = ScreencapManager()
    
    # Run test
    results = manager.test_screencap(device_id)
    
    print(f"\n📊 Test Results:")
    print(f"   Device Info: {'✅' if results['device_info'] else '❌'}")
    print(f"   Screenshot: {'✅' if results['screenshot'] else '❌'}")
    print(f"   Image Decode: {'✅' if results['image_decode'] else '❌'}")
    print(f"   Timing: {results['timing']:.1f}ms")
    
    if results['errors']:
        print(f"   Errors: {results['errors']}")
    
    return results


if __name__ == "__main__":
    # Simple test when run directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Get device ID from command line or use default
    device_id = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
    
    test_screencap_manager(device_id) 