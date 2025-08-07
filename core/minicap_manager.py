"""
Minicap Manager for efficient screen capture without memory leaks
"""

import subprocess
import time
import os
import socket
import threading
import struct
from typing import Optional, Tuple
from pathlib import Path


class MinicapManager:
    """Manages minicap for efficient screen capture"""
    
    def __init__(self, minicap_path: str = "minicap"):
        self.minicap_path = minicap_path
        self.minicap_process = None
        self.socket_connection = None
        self.device_info = {}
        self.is_running = False
        self.persistent_socket = None  # Maintain persistent socket connection
        self.port_forwarded = False  # Track if port forwarding is active
        self.device_ports = {}  # Track unique ports for each device
        self.base_port = 1313  # Base port number 
    
    def _get_device_port(self, device_id: str) -> int:
        """Get unique port for device"""
        if device_id not in self.device_ports:
            # Find next available port starting from base_port
            used_ports = set(self.device_ports.values())
            port = self.base_port
            while port in used_ports:
                port += 1
            self.device_ports[device_id] = port
        return self.device_ports[device_id]
    
    def _remove_device_port(self, device_id: str):
        """Remove device port mapping"""
        if device_id in self.device_ports:
            del self.device_ports[device_id]
        
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
    
    def _ensure_port_forwarded(self, device_id: str) -> bool:
        """Ensure port forwarding is active for the device"""
        # Check if port forwarding is already active for this device
        if hasattr(self, '_forwarded_ports') and device_id in getattr(self, '_forwarded_ports', set()):
            return True
            
        try:
            port = self._get_device_port(device_id)
            # Use faster timeout and capture_output=False for speed
            result = subprocess.run([
                'adb', '-s', device_id, 'forward', f'tcp:{port}', 'localabstract:minicap'
            ], capture_output=True, timeout=2)  # Further reduced timeout
            
            if result.returncode == 0:
                # Cache the forwarded port
                if not hasattr(self, '_forwarded_ports'):
                    self._forwarded_ports = set()
                self._forwarded_ports.add(device_id)
                return True
            else:
                print(f"❌ Port forwarding failed for {device_id}: {result.stderr.decode()}")
                return False
        except Exception as e:
            print(f"❌ Error forwarding port for {device_id}: {e}")
            return False

    def _get_persistent_socket(self, device_id: str) -> Optional[socket.socket]:
        """Get or create persistent socket connection"""
        if self.persistent_socket is None:
            if not self._ensure_port_forwarded(device_id):
                return None
            
            try:
                port = self._get_device_port(device_id)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)  # Reduced timeout for faster failure detection
                sock.connect(('localhost', port))
                self.persistent_socket = sock
                return sock
            except Exception as e:
                print(f"❌ Error creating socket connection for {device_id}: {e}")
                self.persistent_socket = None
                return None
        
        # Test if existing socket is still valid (faster test)
        try:
            # Quick test without blocking
            sock = self.persistent_socket
            sock.settimeout(0.1)
            sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            sock.settimeout(3)  # Reset timeout
            return sock
        except:
            # Socket is dead, create new one
            self.persistent_socket = None
            return self._get_persistent_socket(device_id) 

    def cleanup(self, device_id: str):
        """Cleanup minicap for device"""
        try:
            # Close persistent socket
            self._close_persistent_socket()
            
            # Stop minicap process
            if self.minicap_process:
                self.minicap_process.terminate()
                self.minicap_process = None
            
            # Kill minicap on device
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'pkill', '-f', 'minicap'
            ], capture_output=True, timeout=5)
            
            # Remove device-specific port forwarding
            port = self._get_device_port(device_id)
            subprocess.run([
                'adb', '-s', device_id, 'forward', '--remove', f'tcp:{port}'
            ], capture_output=True, timeout=5)
            
            # Remove device port mapping
            self._remove_device_port(device_id)
            
            self.is_running = False
            print(f"✅ Cleaned up minicap for {device_id} (port {port})")
            
        except Exception as e:
            print(f"❌ Error cleaning up minicap for {device_id}: {e}") 

    def setup_minicap(self, device_id: str) -> bool:
        """Setup minicap on the device"""
        try:
            # Get device info
            device_info = self.get_device_info(device_id)
            if not device_info:
                print(f"❌ Failed to get device info for {device_id}")
                return False
            
            self.device_info = device_info
            
            # Push minicap binary to device
            minicap_binary = Path(self.minicap_path) / "minicap"
            minicap_so = Path(self.minicap_path) / "minicap.so"
            
            if not minicap_binary.exists() or not minicap_so.exists():
                print(f"❌ Minicap files not found in {self.minicap_path}")
                return False
            
            # Push files to device
            result = subprocess.run([
                'adb', '-s', device_id, 'push', str(minicap_binary), '/data/local/tmp/'
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                print(f"❌ Failed to push minicap binary: {result.stderr.decode()}")
                return False
            
            result = subprocess.run([
                'adb', '-s', device_id, 'push', str(minicap_so), '/data/local/tmp/'
            ], capture_output=True, timeout=10)
            
            if result.returncode != 0:
                print(f"❌ Failed to push minicap.so: {result.stderr.decode()}")
                return False
            
            # Set permissions
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'chmod', '777', '/data/local/tmp/minicap'
            ], capture_output=True, timeout=5)
            
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'chmod', '777', '/data/local/tmp/minicap.so'
            ], capture_output=True, timeout=5)
            
            print(f"✅ Minicap setup completed for {device_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up minicap for {device_id}: {e}")
            return False
    
    def start_minicap(self, device_id: str) -> bool:
        """Start minicap service on device"""
        try:
            if not self.device_info:
                if not self.setup_minicap(device_id):
                    return False
            
            # Kill any existing minicap processes
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'pkill', '-f', 'minicap'
            ], capture_output=True, timeout=5)
            
            time.sleep(1)
            
            # Start minicap with device dimensions
            width = self.device_info['width']
            height = self.device_info['height']
            density = self.device_info['density']
            
            # Start minicap in background with LD_LIBRARY_PATH set
            self.minicap_process = subprocess.Popen([
                'adb', '-s', device_id, 'shell',
                f'LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap -P {width}x{height}@{width}x{height}/0'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for minicap to start
            time.sleep(2)
            
            # Check if minicap is running
            result = subprocess.run([
                'adb', '-s', device_id, 'shell', 'ps', '|', 'grep', 'minicap'
            ], capture_output=True, timeout=5)
            
            if result.returncode == 0 and 'minicap' in result.stdout.decode():
                self.is_running = True
                print(f"✅ Minicap started successfully for {device_id}")
                return True
            else:
                print(f"❌ Failed to start minicap for {device_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting minicap for {device_id}: {e}")
            return False
    
    def get_screenshot_via_socket(self, device_id: str) -> Optional[bytes]:
        """Get screenshot via minicap socket connection"""
        try:
            port = self._get_device_port(device_id)
            # Forward minicap port
            subprocess.run([
                'adb', '-s', device_id, 'forward', f'tcp:{port}', 'localabstract:minicap'
            ], capture_output=True, timeout=5)
            
            # Connect to minicap socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', port))
            
            # Read banner - read in smaller chunks to handle different sizes
            banner = b''
            while len(banner) < 28:  # Read up to 28 bytes
                chunk = sock.recv(1)
                if not chunk:
                    break
                banner += chunk
                
                # Try to parse as we go
                if len(banner) >= 5:  # We have version + length
                    try:
                        version = banner[0]
                        length = struct.unpack('<I', banner[1:5])[0]
                        
                        # If we have enough data, try to read the image
                        if len(banner) >= 24 and length > 0:
                            break
                    except:
                        pass
            
            if len(banner) < 5:
                sock.close()
                return None
            
            # Parse banner
            version = banner[0]
            length = struct.unpack('<I', banner[1:5])[0]
            
            # Read image data
            image_data = b''
            while len(image_data) < length:
                chunk = sock.recv(length - len(image_data))
                if not chunk:
                    break
                image_data += chunk
            
            sock.close()
            
            if len(image_data) == length:
                return image_data
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error getting screenshot via socket for {device_id}: {e}")
            return None
    
    def get_screenshot_via_file(self, device_id: str, save_to_file: bool = True) -> Optional[bytes]:
        """Get screenshot via minicap socket connection (single frame) - FRESH CONNECTION VERSION"""
        import time
        import os
        start_time = time.time()
        
        try:
            # Use device info for correct resolution
            if not self.device_info:
                if not self.setup_minicap(device_id):
                    return None
            
            # Start minicap if not running
            if not self.is_running:
                if not self.start_minicap(device_id):
                    return None
            
            # Create fresh connection for each screenshot to ensure latest frame
            port = self._get_device_port(device_id)
            if not self._ensure_port_forwarded(device_id):
                return None
            
            # Create new socket connection with optimized settings
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # Shorter timeout for faster response
            sock.connect(('localhost', port))
            
            # Read banner (24 bytes) - minicap protocol
            banner = b''
            while len(banner) < 24:
                chunk = sock.recv(24 - len(banner))
                if not chunk:
                    sock.close()
                    return None
                banner += chunk
            
            if len(banner) != 24:
                sock.close()
                return None
            
            # Parse banner according to minicap protocol
            try:
                version = banner[0]
                header_size = banner[1]
                pid = struct.unpack('<I', banner[2:6])[0]
                real_width = struct.unpack('<I', banner[6:10])[0]
                real_height = struct.unpack('<I', banner[10:14])[0]
                virtual_width = struct.unpack('<I', banner[14:18])[0]
                virtual_height = struct.unpack('<I', banner[18:22])[0]
                orientation = banner[22]
                quirk = banner[23]
                
            except Exception as e:
                print(f"❌ Error parsing banner: {e}")
                sock.close()
                return None
            
            # Read frame size (4 bytes)
            frame_size_data = b''
            while len(frame_size_data) < 4:
                chunk = sock.recv(4 - len(frame_size_data))
                if not chunk:
                    sock.close()
                    return None
                frame_size_data += chunk
            
            if len(frame_size_data) != 4:
                sock.close()
                return None
            
            try:
                frame_size = struct.unpack('<I', frame_size_data)[0]
            except Exception as e:
                print(f"❌ Error parsing frame size: {e}")
                sock.close()
                return None
            
            # Read frame data efficiently
            frame_data = b''
            while len(frame_data) < frame_size:
                chunk = sock.recv(min(frame_size - len(frame_data), 32768))  # 32KB chunks for speed
                if not chunk:
                    break
                frame_data += chunk
            
            # Close socket immediately after reading
            sock.close()
            
            if len(frame_data) == frame_size:
                elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
                print(f"📸 Captured screenshot for {device_id} in {elapsed:.1f}ms")
                
                # Save screenshot to tmp folder only if requested
                if save_to_file:
                    try:
                        # Create tmp folder if it doesn't exist
                        tmp_dir = Path("tmp")
                        tmp_dir.mkdir(exist_ok=True)
                        
                        # Save screenshot with device ID and timestamp
                        timestamp = int(time.time() * 1000)  # Milliseconds timestamp
                        screenshot_path = tmp_dir / f"screenshot_{device_id}.jpg"
                        
                        with open(screenshot_path, 'wb') as f:
                            f.write(frame_data)
                        
                        # print(f"💾 Saved screenshot to {screenshot_path}")
                        
                    except Exception as e:
                        print(f"⚠️ Failed to save screenshot to file: {e}")
                
                return frame_data
            else:
                elapsed = (time.time() - start_time) * 1000
                print(f"❌ Failed to capture screenshot for {device_id} (took {elapsed:.1f}ms)")
                return None
                
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ Error getting screenshot via socket for {device_id} (took {elapsed:.1f}ms): {e}")
            return None
    
    def get_screenshot(self, device_id: str, save_to_file: bool = True) -> Optional[bytes]:
        """Get screenshot using minicap"""
        try:
            # Try file method first (preferred)
            image_data = self.get_screenshot_via_file(device_id, save_to_file)
            if image_data:
                return image_data
            
            # Fallback to socket method
            return self.get_screenshot_via_socket(device_id)
            
        except Exception as e:
            print(f"❌ Error getting minicap screenshot for {device_id}: {e}")
            return None
    
    def stop_minicap(self, device_id: str):
        """Stop minicap service"""
        try:
            if self.minicap_process:
                self.minicap_process.terminate()
                self.minicap_process = None
            
            # Kill minicap process on device
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'pkill', '-f', 'minicap'
            ], capture_output=True, timeout=5)
            
            # Remove device-specific port forwarding
            port = self._get_device_port(device_id)
            subprocess.run([
                'adb', '-s', device_id, 'forward', '--remove', f'tcp:{port}'
            ], capture_output=True, timeout=5)
            
            self.is_running = False
            print(f"✅ Minicap stopped for {device_id} (port {port})")
            
        except Exception as e:
            print(f"❌ Error stopping minicap for {device_id}: {e}")
    
    def _close_persistent_socket(self):
        """Close persistent socket connection"""
        if self.persistent_socket:
            try:
                self.persistent_socket.close()
            except Exception:
                pass
            self.persistent_socket = None
        self.port_forwarded = False
        # Reset banner read flag when closing connection
        if hasattr(self, '_banner_read'):
            delattr(self, '_banner_read') 