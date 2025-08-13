"""
Simple Screencap Manager for basic screen capture

This module provides a simple and reliable way to capture screenshots
using the standard Android screencap command instead of minicap.
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
        self.session_active = {}
        self.session_stats = {}
        self._minicap_ready_devices = set()
    
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
    
    def _ensure_minicap_setup(self, device_id: str) -> bool:
        """Ensure minicap binaries are on the device and executable"""
        if device_id in self._minicap_ready_devices:
            return True
        try:
            minicap_dir = Path('minicap')
            minicap_bin = minicap_dir / 'minicap'
            minicap_so = minicap_dir / 'minicap.so'
            if not minicap_bin.exists() or not minicap_so.exists():
                print(f"❌ Minicap binaries not found in {minicap_dir}")
                return False
            
            # Push binaries
            r1 = subprocess.run(['adb','-s',device_id,'push',str(minicap_bin),'/data/local/tmp/'], capture_output=True, timeout=15)
            if r1.returncode != 0:
                print(f"❌ Failed to push minicap: {r1.stderr.decode(errors='ignore')}")
                return False
            r2 = subprocess.run(['adb','-s',device_id,'push',str(minicap_so),'/data/local/tmp/'], capture_output=True, timeout=15)
            if r2.returncode != 0:
                print(f"❌ Failed to push minicap.so: {r2.stderr.decode(errors='ignore')}")
                return False
            
            # Permissions
            subprocess.run(['adb','-s',device_id,'shell','chmod','755','/data/local/tmp/minicap'], capture_output=True, timeout=5)
            subprocess.run(['adb','-s',device_id,'shell','chmod','644','/data/local/tmp/minicap.so'], capture_output=True, timeout=5)
            
            self._minicap_ready_devices.add(device_id)
            return True
        except Exception as e:
            print(f"❌ Minicap setup error for {device_id}: {e}")
            return False
    
    def start_session(self, device_id: str) -> bool:
        """Start a screenshot session for multiple captures"""
        try:
            # Check if session is already active
            if device_id in self.session_active and self.session_active[device_id]:
                return True
            
            # Get device info if not already cached
            if device_id not in self.device_info:
                device_info = self.get_device_info(device_id)
                if device_info:
                    self.device_info[device_id] = device_info
                else:
                    return False
            
            # Initialize session stats
            self.session_stats[device_id] = {
                'screenshots_taken': 0,
                'total_time': 0,
                'session_start': time.time(),
                'last_screenshot': None
            }
            
            # Mark session as active
            self.session_active[device_id] = True
            print(f"🔄 Screenshot session started for {device_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error starting session for {device_id}: {e}")
            return False
    
    def end_session(self, device_id: str):
        """End screenshot session and cleanup"""
        try:
            if device_id in self.session_active:
                # Print session stats
                if device_id in self.session_stats:
                    stats = self.session_stats[device_id]
                    session_duration = time.time() - stats['session_start']
                    if stats['screenshots_taken'] > 0:
                        avg_time = stats['total_time'] / stats['screenshots_taken']
                        fps = stats['screenshots_taken'] / session_duration
                        print(f"📊 Session stats for {device_id}:")
                        print(f"   Screenshots: {stats['screenshots_taken']}")
                        print(f"   Avg time: {avg_time:.1f}ms")
                        print(f"   Session FPS: {fps:.1f}")
                
                # Cleanup session
                del self.session_active[device_id]
                if device_id in self.session_stats:
                    del self.session_stats[device_id]
            
            print(f"🔚 Screenshot session ended for {device_id}")
            
        except Exception as e:
            print(f"❌ Error ending session for {device_id}: {e}")
    
    def get_screenshot(self, device_id: str, save_to_file: bool = False) -> Optional[bytes]:
        """Get screenshot using minicap via adb exec-out (single frame)"""
        import time
        start_time = time.time()
        
        try:
            # Ensure minicap is available on device
            if not self._ensure_minicap_setup(device_id):
                return None
            
            # Resolve device info
            info = self.device_info.get(device_id)
            if not info:
                info = self.get_device_info(device_id)
                if not info:
                    print(f"❌ Could not get device info for {device_id}")
                    return None
                self.device_info[device_id] = info
            width, height = info['width'], info['height']
            
            # Exec-out minicap single frame (-s)
            # Use sh -c to set LD_LIBRARY_PATH
            # Suppress stderr logs on device to avoid mixing with stdout
            cmd = (
                f"LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap "
                f"-P {width}x{height}@{width}x{height}/0 -s 2>/dev/null"
            )
            result = subprocess.run(
                ['adb','-s',device_id,'exec-out','sh','-c',cmd],
                capture_output=True,
                timeout=15
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            if result.returncode == 0 and result.stdout:
                # Extract JPEG payload in case any stray bytes are present
                data = result.stdout
                soi = data.find(b'\xFF\xD8')
                eoi = data.rfind(b'\xFF\xD9')
                if soi != -1 and eoi != -1 and eoi > soi:
                    jpg_bytes = data[soi:eoi+2]
                else:
                    jpg_bytes = data

                # Validate image
                image_array = np.frombuffer(jpg_bytes, dtype=np.uint8)
                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                if img is None:
                    print(f"❌ Minicap image decode failed for {device_id} (took {elapsed:.1f}ms)")
                    return None
                h, w = img.shape[:2]
                
                # Update counters
                if device_id not in self.screenshot_count:
                    self.screenshot_count[device_id] = 0
                self.screenshot_count[device_id] += 1
                self.last_screenshot_time[device_id] = time.time()
                
                # Update session stats if active
                if device_id in self.session_active and self.session_active[device_id]:
                    if device_id in self.session_stats:
                        stats = self.session_stats[device_id]
                        stats['screenshots_taken'] += 1
                        stats['total_time'] += elapsed
                        stats['last_screenshot'] = time.time()
                
                print(f"📸 Minicap screenshot for {device_id}: {w}x{h} in {elapsed:.1f}ms")
                if save_to_file:
                    self._save_screenshot(device_id, jpg_bytes)
                return jpg_bytes
            else:
                err = result.stderr.decode(errors='ignore') if result.stderr else 'unknown error'
                print(f"❌ Minicap exec-out failed for {device_id} (took {elapsed:.1f}ms): {err}")
                return None
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ Error getting minicap screenshot for {device_id} (took {elapsed:.1f}ms): {e}")
            return None
    
    def get_session_screenshot(self, device_id: str, save_to_file: bool = False) -> Optional[bytes]:
        """Get screenshot from active session (optimized for multiple captures)"""
        # Ensure session is active
        if device_id not in self.session_active or not self.session_active[device_id]:
            if not self.start_session(device_id):
                return None
        
        return self.get_screenshot(device_id, save_to_file)
    
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
            'device_info': self.device_info.get(device_id),
            'session_active': self.session_active.get(device_id, False)
        }
        
        if stats['last_screenshot_time']:
            stats['time_since_last'] = time.time() - stats['last_screenshot_time']
        
        if device_id in self.session_stats:
            stats['session_stats'] = self.session_stats[device_id]
        
        return stats
    
    def cleanup(self, device_id: str):
        """Cleanup for device"""
        try:
            # End any active session
            if device_id in self.session_active:
                self.end_session(device_id)
            
            print(f"✅ Cleaned up screencap for {device_id}")
            
        except Exception as e:
            print(f"❌ Error cleaning up screencap for {device_id}: {e}")
    
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


# Alias for backward compatibility
MinicapManager = ScreencapManager 