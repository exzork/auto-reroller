"""
Device Manager for handling ADB connections and device management
"""

import subprocess
import time
from typing import List, Optional
from .minicap_manager import MinicapManager


class DeviceManager:
    """Manages ADB devices for automation"""
    
    def __init__(self):
        self.device_list = []
        self.initialized = False
        self.minicap_managers = {}  # Store minicap managers per device
    
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
    
    def _get_minicap_manager(self, device_id: str) -> MinicapManager:
        """Get or create minicap manager for device"""
        if device_id not in self.minicap_managers:
            self.minicap_managers[device_id] = MinicapManager()
        return self.minicap_managers[device_id]
    
    def get_screenshot(self, device_id: str, save_to_file: bool = True) -> Optional[bytes]:
        """Get screenshot from specific device using minicap"""
        try:
            minicap_manager = self._get_minicap_manager(device_id)
            
            # Try to get screenshot using minicap
            screenshot_data = minicap_manager.get_screenshot(device_id, save_to_file)
            
            if screenshot_data:
                return screenshot_data
            else:
                # Fallback to screencap if minicap fails
                print(f"⚠️ Minicap failed for {device_id}, falling back to screencap")
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
    
    def setup_minicap_for_device(self, device_id: str) -> bool:
        """Setup minicap for a specific device"""
        try:
            minicap_manager = self._get_minicap_manager(device_id)
            return minicap_manager.setup_minicap(device_id)
        except Exception as e:
            print(f"❌ Error setting up minicap for {device_id}: {e}")
            return False
    
    def start_minicap_for_device(self, device_id: str) -> bool:
        """Start minicap service for a specific device"""
        try:
            minicap_manager = self._get_minicap_manager(device_id)
            return minicap_manager.start_minicap(device_id)
        except Exception as e:
            print(f"❌ Error starting minicap for {device_id}: {e}")
            return False
    
    def stop_minicap_for_device(self, device_id: str):
        """Stop minicap service for a specific device"""
        try:
            if device_id in self.minicap_managers:
                self.minicap_managers[device_id].stop_minicap(device_id)
        except Exception as e:
            print(f"❌ Error stopping minicap for {device_id}: {e}")
    
    def cleanup_minicap_for_device(self, device_id: str):
        """Cleanup minicap for a specific device"""
        try:
            if device_id in self.minicap_managers:
                self.minicap_managers[device_id].cleanup(device_id)
                del self.minicap_managers[device_id]
        except Exception as e:
            print(f"❌ Error cleaning up minicap for {device_id}: {e}")
    
    def execute_adb_command(self, device_id: str, command: List[str], timeout: int = 10) -> Optional[subprocess.CompletedProcess]:
        """Execute ADB command on specific device"""
        import time
        adb_start_time = time.time()
        
        try:
            full_command = ['adb', '-s', device_id] + command
            result = subprocess.run(full_command, capture_output=True, timeout=timeout)
            
            adb_time = (time.time() - adb_start_time) * 1000
            
            return result
        except Exception as e:
            adb_time = (time.time() - adb_start_time) * 1000
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
        import time
        tap_start_time = time.time()
        
        result = self.execute_adb_command(
            device_id, 
            ['shell', 'input', 'tap', str(x), str(y)]
        )
        
        tap_time = (time.time() - tap_start_time) * 1000
        
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