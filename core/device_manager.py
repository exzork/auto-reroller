"""
Device Manager for handling ADB connections and device management
"""

import subprocess
import time
from typing import List, Optional


class DeviceManager:
    """Manages ADB devices for automation"""
    
    def __init__(self):
        self.device_list = []
        self.initialized = False
    
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
    
    def get_screenshot(self, device_id: str) -> Optional[bytes]:
        """Get screenshot from specific device"""
        try:
            result = subprocess.run([
                'adb', '-s', device_id, 'exec-out', 'screencap', '-p'
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                return result.stdout
            else:
                print(f"❌ Failed to get screenshot from device {device_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting screenshot from {device_id}: {e}")
            return None
    
    def execute_adb_command(self, device_id: str, command: List[str], timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """Execute ADB command on specific device"""
        try:
            full_command = ['adb', '-s', device_id] + command
            result = subprocess.run(full_command, capture_output=True, timeout=timeout)
            return result
        except Exception as e:
            print(f"❌ Error executing ADB command on {device_id}: {e}")
            return None
    
    def kill_app(self, device_id: str, package_name: str) -> bool:
        """Kill an app on specific device"""
        result = self.execute_adb_command(
            device_id, 
            ['shell', 'am', 'force-stop', package_name]
        )
        return result and result.returncode == 0
    
    def start_app(self, device_id: str, activity_name: str) -> bool:
        """Start an app on specific device"""
        result = self.execute_adb_command(
            device_id,
            ['shell', 'am', 'start', '-W', '-n', activity_name],
            timeout=15
        )
        return result and result.returncode == 0
    
    def restart_app(self, device_id: str, package_name: str, activity_name: str) -> bool:
        """Restart an app on specific device"""
        # Kill the app
        if not self.kill_app(device_id, package_name):
            print(f"❌ Failed to kill app {package_name} on {device_id}")
            return False
        
        # Wait a moment
        time.sleep(2)
        
        # Start the app
        if not self.start_app(device_id, activity_name):
            print(f"❌ Failed to start app {activity_name} on {device_id}")
            return False
        
        # Wait for app to load
        time.sleep(5)
        return True
    
    def get_clipboard(self, device_id: str) -> Optional[str]:
        """Get clipboard content from device via clipper broadcast"""
        try:
            result = self.execute_adb_command(
                device_id,
                ['shell', 'am', 'broadcast', '-a', 'clipper.get']
            )
            
            if result and result.returncode == 0:
                import re
                match = re.search(r'data="([^"]+)"', result.stdout.decode())
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            print(f"❌ Error getting clipboard from {device_id}: {e}")
            return None
    
    def tap(self, device_id: str, x: int, y: int) -> bool:
        """Tap at specific coordinates on device"""
        result = self.execute_adb_command(
            device_id, 
            ['shell', 'input', 'tap', str(x), str(y)]
        )
        return result is not None and result.returncode == 0
    
    def swipe(self, device_id: str, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 1000) -> bool:
        """Swipe from start to end coordinates on device"""
        result = self.execute_adb_command(
            device_id,
            ['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration)]
        )
        return result is not None and result.returncode == 0
    
    def input_text(self, device_id: str, text: str) -> bool:
        """Input text on device"""
        # Escape special characters for shell
        escaped_text = text.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
        result = self.execute_adb_command(
            device_id,
            ['shell', 'input', 'text', f'"{escaped_text}"']
        )
        return result is not None and result.returncode == 0
    
    def send_key(self, device_id: str, keycode: str) -> bool:
        """Send a keycode to device"""
        result = self.execute_adb_command(
            device_id,
            ['shell', 'input', 'keyevent', keycode]
        )
        return result is not None and result.returncode == 0 