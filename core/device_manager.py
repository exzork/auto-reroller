"""
Device Manager for handling ADB connections and device management
"""

import subprocess
import time
from typing import List, Optional
from .minicap_manager import ScreencapManager


class DeviceManager:
    """Manages ADB devices for automation"""
    
    def __init__(self):
        self.device_list = []
        self.initialized = False
        self.screencap_managers = {}  # Store screencap managers per device
    
    def initialize(self) -> bool:
        """Initialize ADB and detect connected devices"""
        try:
            # Check if ADB is available
            result = subprocess.run(['adb', 'version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                print("❌ ADB not available")
                return False
            
            # Get connected devices
            result = subprocess.run(['adb', 'devices'], capture_output=True, timeout=5)
            if result.returncode != 0:
                print("❌ Failed to get device list")
                return False
            
            # Parse device list
            lines = result.stdout.decode().strip().split('\n')[1:]  # Skip header
            connected_devices = [line.split('\t')[0] for line in lines 
                               if line.strip() and not line.endswith('offline')]
            
            self.device_list = connected_devices
            self.initialized = True
            
            if connected_devices:
                print(f"✅ Connected devices: {connected_devices}")
                return True
            else:
                print("❌ No devices connected")
                return False
                
        except Exception as e:
            print(f"❌ Error initializing ADB: {e}")
            return False
    
    def get_device_list(self) -> List[str]:
        """Get list of available device IDs"""
        return self.device_list.copy()
    
    def set_device_list(self, devices: List[str]):
        """Override device list with specific devices"""
        self.device_list = devices.copy()
    
    def is_device_connected(self, device_id: str) -> bool:
        """Check if a specific device is connected"""
        try:
            result = subprocess.run(
                ['adb', '-s', device_id, 'get-state'], 
                capture_output=True, timeout=5
            )
            return result.returncode == 0 and result.stdout.decode().strip() == 'device'
        except Exception:
            return False
    
    def _get_screencap_manager(self, device_id: str) -> ScreencapManager:
        """Get or create screencap manager for device"""
        if device_id not in self.screencap_managers:
            self.screencap_managers[device_id] = ScreencapManager()
        return self.screencap_managers[device_id]
    
    def get_screenshot(self, device_id: str, save_to_file: bool = True) -> Optional[bytes]:
        """Get screenshot from specific device using screencap"""
        try:
            screencap_manager = self._get_screencap_manager(device_id)
            
            # Get screenshot using screencap
            screenshot_data = screencap_manager.get_screenshot(device_id, save_to_file)
            
            if screenshot_data:
                return screenshot_data
            else:
                print(f"❌ Failed to get screenshot from device {device_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting screenshot for {device_id}: {e}")
            return None
    
    def get_screenshot_as_image(self, device_id: str):
        """Get screenshot as OpenCV image array"""
        screencap_manager = self._get_screencap_manager(device_id)
        return screencap_manager.get_screenshot_as_image(device_id)
    
    def get_multiple_screenshots(self, device_id: str, count: int = 5, delay: float = 0.1) -> list[bytes]:
        """Get multiple screenshots with optional delay"""
        screencap_manager = self._get_screencap_manager(device_id)
        return screencap_manager.get_multiple_screenshots(device_id, count, delay)
    
    def start_screenshot_session(self, device_id: str) -> bool:
        """Start a screenshot session for multiple captures"""
        screencap_manager = self._get_screencap_manager(device_id)
        return screencap_manager.start_session(device_id)
    
    def end_screenshot_session(self, device_id: str):
        """End screenshot session and cleanup"""
        screencap_manager = self._get_screencap_manager(device_id)
        screencap_manager.end_session(device_id)
    
    def get_screenshot_stats(self, device_id: str) -> dict:
        """Get screenshot statistics for device"""
        screencap_manager = self._get_screencap_manager(device_id)
        return screencap_manager.get_stats(device_id)
    
    def cleanup_screencap_for_device(self, device_id: str):
        """Cleanup screencap for device"""
        if device_id in self.screencap_managers:
            self.screencap_managers[device_id].cleanup(device_id)
            del self.screencap_managers[device_id]
    
    def execute_adb_command(self, device_id: str, command: List[str], timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """Execute ADB command on specific device"""
        try:
            full_command = ['adb', '-s', device_id] + command
            result = subprocess.run(full_command, capture_output=True, timeout=timeout)
            return result
        except Exception as e:
            print(f"❌ Error executing ADB command for {device_id}: {e}")
            return None
    
    def kill_app(self, device_id: str, package_name: str) -> bool:
        """Kill app on device"""
        try:
            result = self.execute_adb_command(device_id, ['shell', 'am', 'force-stop', package_name])
            return result.returncode == 0 if result else False
        except Exception as e:
            print(f"❌ Error killing app {package_name} on {device_id}: {e}")
            return False
    
    def start_app(self, device_id: str, activity_name: str) -> bool:
        """Start app on device"""
        try:
            result = self.execute_adb_command(device_id, ['shell', 'am', 'start', '-n', activity_name])
            return result.returncode == 0 if result else False
        except Exception as e:
            print(f"❌ Error starting app {activity_name} on {device_id}: {e}")
            return False
    
    def restart_app(self, device_id: str, package_name: str, activity_name: str) -> bool:
        """Restart app on device"""
        try:
            # Kill app first
            if self.kill_app(device_id, package_name):
                time.sleep(1)  # Wait a moment
                
                # Start app
                return self.start_app(device_id, activity_name)
            else:
                print(f"❌ Failed to kill app {package_name} on {device_id}")
                return False
        except Exception as e:
            print(f"❌ Error restarting app {package_name} on {device_id}: {e}")
            return False
    
    def get_clipboard(self, device_id: str) -> Optional[str]:
        """Get clipboard content from device"""
        try:
            result = self.execute_adb_command(device_id, ['shell', 'am', 'broadcast', '-a', 'clipper.get'])
            if result and result.returncode == 0:
                # Parse clipboard content from broadcast output
                output = result.stdout.decode()
                # This is a simplified parser - you might need to adjust based on your clipper app
                return output.strip()
            return None
        except Exception as e:
            print(f"❌ Error getting clipboard from {device_id}: {e}")
            return None
    
    def tap(self, device_id: str, x: int, y: int) -> bool:
        """Tap at coordinates on device"""
        try:
            result = self.execute_adb_command(device_id, ['shell', 'input', 'tap', str(x), str(y)])
            return result.returncode == 0 if result else False
        except Exception as e:
            print(f"❌ Error tapping at ({x}, {y}) on {device_id}: {e}")
            return False
    
    def swipe(self, device_id: str, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 1000) -> bool:
        """Swipe on device"""
        try:
            result = self.execute_adb_command(device_id, [
                'shell', 'input', 'swipe', 
                str(start_x), str(start_y), 
                str(end_x), str(end_y), 
                str(duration)
            ])
            return result.returncode == 0 if result else False
        except Exception as e:
            print(f"❌ Error swiping on {device_id}: {e}")
            return False
    
    def input_text(self, device_id: str, text: str) -> bool:
        """Input text on device"""
        try:
            result = self.execute_adb_command(device_id, ['shell', 'input', 'text', text])
            return result.returncode == 0 if result else False
        except Exception as e:
            print(f"❌ Error inputting text on {device_id}: {e}")
            return False
    
    def send_key(self, device_id: str, keycode: str) -> bool:
        """Send key event to device"""
        try:
            result = self.execute_adb_command(device_id, ['shell', 'input', 'keyevent', keycode])
            return result.returncode == 0 if result else False
        except Exception as e:
            print(f"❌ Error sending key {keycode} to {device_id}: {e}")
            return False 