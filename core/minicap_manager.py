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
            # Forward minicap port
            subprocess.run([
                'adb', '-s', device_id, 'forward', 'tcp:1313', 'localabstract:minicap'
            ], capture_output=True, timeout=5)
            
            # Connect to minicap socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', 1313))
            
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
    
    def get_screenshot_via_file(self, device_id: str) -> Optional[bytes]:
        """Get screenshot via minicap socket connection (single frame)"""
        import time
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
            
            # Forward minicap port
            subprocess.run([
                'adb', '-s', device_id, 'forward', 'tcp:1313', 'localabstract:minicap'
            ], capture_output=True, timeout=5)
            
            # Connect to minicap socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('localhost', 1313))
            
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
            # Format: [version(1), header_size(1), pid(4), real_width(4), real_height(4), virtual_width(4), virtual_height(4), orientation(1), quirk(1)]
            try:
                version = banner[0]
                header_size = banner[1]  # This is 1 byte, not 4 bytes
                pid = struct.unpack('<I', banner[2:6])[0]  # Bytes 2-5
                real_width = struct.unpack('<I', banner[6:10])[0]  # Bytes 6-9
                real_height = struct.unpack('<I', banner[10:14])[0]  # Bytes 10-13
                virtual_width = struct.unpack('<I', banner[14:18])[0]  # Bytes 14-17
                virtual_height = struct.unpack('<I', banner[18:22])[0]  # Bytes 18-21
                orientation = banner[22]  # Byte 22
                quirk = banner[23]  # Byte 23
                
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
            
            # Read frame data
            frame_data = b''
            while len(frame_data) < frame_size:
                chunk = sock.recv(min(frame_size - len(frame_data), 4096))  # Read in chunks
                if not chunk:
                    break
                frame_data += chunk
            
            sock.close()
            
            if len(frame_data) == frame_size:
                elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
                print(f"📸 Captured screenshot for {device_id} in {elapsed:.1f}ms")
                return frame_data
            else:
                elapsed = (time.time() - start_time) * 1000
                print(f"❌ Failed to capture screenshot for {device_id} (took {elapsed:.1f}ms)")
                return None
                
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"❌ Error getting screenshot via socket for {device_id} (took {elapsed:.1f}ms): {e}")
            return None
    
    def get_screenshot(self, device_id: str) -> Optional[bytes]:
        """Get screenshot using minicap"""
        try:
            # Try file method first (preferred)
            image_data = self.get_screenshot_via_file(device_id)
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
            
            # Remove port forwarding
            subprocess.run([
                'adb', '-s', device_id, 'forward', '--remove', 'tcp:1313'
            ], capture_output=True, timeout=5)
            
            self.is_running = False
            print(f"✅ Minicap stopped for {device_id}")
            
        except Exception as e:
            print(f"❌ Error stopping minicap for {device_id}: {e}")
    
    def cleanup(self, device_id: str):
        """Cleanup minicap files and processes"""
        try:
            self.stop_minicap(device_id)
            
            # Remove minicap files from device
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'rm', '-f', '/data/local/tmp/minicap'
            ], capture_output=True, timeout=5)
            
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'rm', '-f', '/data/local/tmp/minicap.so'
            ], capture_output=True, timeout=5)
            
        except Exception as e:
            print(f"❌ Error cleaning up minicap for {device_id}: {e}") 