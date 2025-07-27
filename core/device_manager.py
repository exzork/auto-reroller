"""
Device Manager for handling ADB connections and device management
"""

import subprocess
import time
import os
from typing import List, Optional
from pathlib import Path


class DeviceManager:
    """Manages ADB devices for automation"""
    
    def __init__(self):
        self.device_list = []
        self.initialized = False
        self.minicap_installed = {}  # Track minicap installation per device
        self.minicap_processes = {}  # Track minicap processes per device
        
        # Minicap paths
        self.minicap_bin = "minicap"
        self.minicap_so = "minicap.so"
    
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
    
    def get_device_info(self, device_id: str) -> Optional[dict]:
        """Get device information including screen resolution"""
        try:
            # Get screen resolution
            result = self.execute_adb_command(
                device_id, 
                ['shell', 'wm', 'size']
            )
            if result and result.returncode == 0:
                size_output = result.stdout.decode().strip()
                if 'Physical size:' in size_output:
                    size = size_output.split(': ')[1]
                    width, height = map(int, size.split('x'))
                    return {
                        'width': width,
                        'height': height,
                        'size': size
                    }
            
            # Fallback to default resolution
            return {
                'width': 1080,
                'height': 1920,
                'size': '1080x1920'
            }
        except Exception as e:
            print(f"Error getting device info for {device_id}: {e}")
            return None
    
    def install_minicap(self, device_id: str) -> bool:
        """Install minicap on the device"""
        try:
            print(f"🔧 Installing minicap on {device_id}...")
            
            # Get device info
            device_info = self.get_device_info(device_id)
            if not device_info:
                print(f"❌ Failed to get device info for {device_id}")
                return False
            
            # Get device architecture
            arch_result = self.execute_adb_command(
                device_id, 
                ['shell', 'getprop', 'ro.product.cpu.abi']
            )
            if not arch_result or arch_result.returncode != 0:
                print(f"❌ Failed to get device architecture for {device_id}")
                return False
            
            arch = arch_result.stdout.decode().strip()
            print(f"📱 Device architecture: {arch}")
            
            # Determine minicap binary and library paths
            minicap_path = Path(__file__).parent.parent / "minicap" / arch
            minicap_bin_path = minicap_path / self.minicap_bin
            minicap_so_path = minicap_path / self.minicap_so
            
            if not minicap_bin_path.exists():
                print(f"❌ Minicap binary not found at {minicap_bin_path}")
                return False
            
            if not minicap_so_path.exists():
                print(f"❌ Minicap library not found at {minicap_so_path}")
                return False
            
            # Push minicap binary to device
            print(f"📤 Pushing minicap binary to {device_id}...")
            push_bin_result = self.execute_adb_command(
                device_id,
                ['push', str(minicap_bin_path), '/data/local/tmp/minicap']
            )
            if not push_bin_result or push_bin_result.returncode != 0:
                print(f"❌ Failed to push minicap binary to {device_id}")
                return False
            
            # Push minicap library to device
            print(f"📤 Pushing minicap library to {device_id}...")
            push_so_result = self.execute_adb_command(
                device_id,
                ['push', str(minicap_so_path), '/data/local/tmp/minicap.so']
            )
            if not push_so_result or push_so_result.returncode != 0:
                print(f"❌ Failed to push minicap library to {device_id}")
                return False
            
            # Set permissions
            print(f"🔐 Setting permissions on {device_id}...")
            chmod_result = self.execute_adb_command(
                device_id,
                ['shell', 'chmod', '777', '/data/local/tmp/minicap']
            )
            if not chmod_result or chmod_result.returncode != 0:
                print(f"❌ Failed to set permissions on {device_id}")
                return False
            
            # Test minicap
            print(f"🧪 Testing minicap on {device_id}...")
            test_result = self.execute_adb_command(
                device_id,
                ['shell', 'LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap -h']
            )
            if not test_result or test_result.returncode != 0:
                print(f"❌ Minicap test failed on {device_id}")
                return False
            
            self.minicap_installed[device_id] = True
            print(f"✅ Minicap installed successfully on {device_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error installing minicap on {device_id}: {e}")
            return False
    
    def start_minicap_stream(self, device_id: str, port: int = 1313) -> bool:
        """Start minicap streaming on the device"""
        try:
            if device_id not in self.minicap_installed:
                if not self.install_minicap(device_id):
                    return False
            
            # Get device info
            device_info = self.get_device_info(device_id)
            if not device_info:
                return False
            
            # Kill any existing minicap process
            self.stop_minicap_stream(device_id)
            
            # Start minicap with streaming
            print(f"🚀 Starting minicap stream on {device_id}...")
            cmd = [
                'shell',
                'LD_LIBRARY_PATH=/data/local/tmp',
                '/data/local/tmp/minicap',
                '-P', f'{device_info["width"]}x{device_info["height"]}@{device_info["width"]}x{device_info["height"]}/0',
                '-S'
            ]
            
            # Start minicap process
            process = subprocess.Popen(
                ['adb', '-s', device_id] + cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.minicap_processes[device_id] = process
            
            # Wait a moment for minicap to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                print(f"✅ Minicap stream started on {device_id}")
                return True
            else:
                print(f"❌ Minicap stream failed to start on {device_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting minicap stream on {device_id}: {e}")
            return False
    
    def stop_minicap_stream(self, device_id: str):
        """Stop minicap streaming on the device"""
        try:
            # Kill minicap process if running
            if device_id in self.minicap_processes:
                process = self.minicap_processes[device_id]
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                del self.minicap_processes[device_id]
            
            # Kill any remaining minicap processes
            self.execute_adb_command(
                device_id,
                ['shell', 'pkill', '-f', 'minicap']
            )
            
            print(f"🛑 Minicap stream stopped on {device_id}")
            
        except Exception as e:
            print(f"❌ Error stopping minicap stream on {device_id}: {e}")
    
    def get_minicap_stream_url(self, device_id: str, port: int = 1313) -> Optional[str]:
        """Get the URL for minicap stream"""
        try:
            # Forward port to device
            forward_result = self.execute_adb_command(
                device_id,
                ['forward', f'tcp:{port}', 'localabstract:minicap']
            )
            
            if forward_result and forward_result.returncode == 0:
                return f"http://localhost:{port}"
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error getting minicap stream URL for {device_id}: {e}")
            return None
    
    def get_screenshot(self, device_id: str) -> Optional[bytes]:
        """Get screenshot from specific device (fallback to ADB)"""
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
    
    def cleanup(self):
        """Cleanup minicap processes on all devices"""
        for device_id in self.device_list:
            self.stop_minicap_stream(device_id) 