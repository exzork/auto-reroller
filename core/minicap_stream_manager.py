"""
Minicap Stream Manager for real-time 30fps streaming with OpenCV display
"""

import subprocess
import time
import os
import socket
import threading
import struct
import cv2
import numpy as np
from typing import Optional, Dict, List
from pathlib import Path


class MinicapStreamManager:
    """Manages minicap streaming for real-time screen capture with OpenCV display"""
    
    def __init__(self, minicap_path: str = "minicap"):
        self.minicap_path = minicap_path
        self.device_info = {}
        self.streaming_devices = {}  # device_id -> stream info
        self.base_port = 1313  # Base port for minicap
        self.port_offset = 0  # Offset for multiple devices
        self.last_frames = {}  # device_id -> last frame
        # Removed frame_locks for simplicity
        
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
            
            self.device_info[device_id] = device_info
            
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
    
    def start_streaming(self, device_id: str, port: int = None) -> bool:
        """Start minicap streaming service on device"""
        try:
            if device_id not in self.device_info:
                if not self.setup_minicap(device_id):
                    return False
            
            # Assign port if not provided
            if port is None:
                port = self.base_port + self.port_offset
                self.port_offset += 1
            
            # Kill any existing minicap processes
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'pkill', '-f', 'minicap'
            ], capture_output=True, timeout=5)
            
            time.sleep(1)
            
            # Remove existing port forwarding
            subprocess.run([
                'adb', '-s', device_id, 'forward', '--remove', f'tcp:{port}'
            ], capture_output=True, timeout=5)
            
            # Start minicap with device dimensions
            width = self.device_info[device_id]['width']
            height = self.device_info[device_id]['height']
            
            # Start minicap in background with LD_LIBRARY_PATH set
            minicap_cmd = f'LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/minicap -P {width}x{height}@{width}x{height}/0'
            
            # Start minicap process
            process = subprocess.Popen([
                'adb', '-s', device_id, 'shell', minicap_cmd
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for minicap to start
            time.sleep(2)
            
            # Check if minicap is running
            result = subprocess.run([
                'adb', '-s', device_id, 'shell', 'ps', '|', 'grep', 'minicap'
            ], capture_output=True, timeout=5)
            
            if result.returncode == 0 and 'minicap' in result.stdout.decode():
                # Setup port forwarding
                subprocess.run([
                    'adb', '-s', device_id, 'forward', f'tcp:{port}', 'localabstract:minicap'
                ], capture_output=True, timeout=5)
                
                # Test connection with retries
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        # Test if we can connect to the socket
                        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_sock.settimeout(2)
                        test_sock.connect(('localhost', port))
                        test_sock.close()
                        break
                    except Exception as e:
                        if retry == max_retries - 1:
                            print(f"❌ Failed to connect to minicap socket after {max_retries} retries")
                            return False
                        print(f"⚠️ Connection attempt {retry + 1} failed, retrying...")
                        time.sleep(1)
                
                # Initialize frame storage
                self.last_frames[device_id] = None
                
                # Store stream info
                self.streaming_devices[device_id] = {
                    'port': port,
                    'process': process,
                    'width': width,
                    'height': height,
                    'running': True,
                    'socket': None,  # Will be created on first frame read
                    'banner_read': False
                }
                
                print(f"✅ Minicap streaming started for {device_id} on port {port}")
                return True
            else:
                print(f"❌ Failed to start minicap for {device_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting minicap streaming for {device_id}: {e}")
            return False
    
    def read_minicap_frame(self, device_id: str) -> Optional[np.ndarray]:
        """Read a single frame from minicap stream"""
        try:
            if device_id not in self.streaming_devices:
                return None
            
            stream_info = self.streaming_devices[device_id]
            port = stream_info['port']
            
            # Create or reuse socket connection
            if stream_info['socket'] is None:
                # Create new connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                try:
                    sock.connect(('localhost', port))
                    stream_info['socket'] = sock
                    stream_info['banner_read'] = False
                except Exception as e:
                    sock.close()
                    return None
            else:
                sock = stream_info['socket']
            
            # Read banner only once
            if not stream_info['banner_read']:
                # Read banner (24 bytes) - minicap protocol
                banner = b''
                while len(banner) < 24:
                    chunk = sock.recv(24 - len(banner))
                    if not chunk:
                        sock.close()
                        stream_info['socket'] = None
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
                    
                    stream_info['banner_read'] = True
                    
                except Exception as e:
                    print(f"❌ Error parsing banner: {e}")
                    sock.close()
                    stream_info['socket'] = None
                    return None
            
            # Read frame size (4 bytes)
            frame_size_data = b''
            while len(frame_size_data) < 4:
                chunk = sock.recv(4 - len(frame_size_data))
                if not chunk:
                    sock.close()
                    stream_info['socket'] = None
                    return None
                frame_size_data += chunk
            
            if len(frame_size_data) != 4:
                print(f"❌ Incomplete frame size data: {len(frame_size_data)} bytes")
                sock.close()
                stream_info['socket'] = None
                return None
            
            try:
                frame_size = struct.unpack('<I', frame_size_data)[0]
            except Exception as e:
                print(f"❌ Error parsing frame size: {e}")
                sock.close()
                stream_info['socket'] = None
                return None
            
            # Read frame data
            frame_data = b''
            while len(frame_data) < frame_size:
                chunk = sock.recv(min(frame_size - len(frame_data), 4096))  # Read in chunks
                if not chunk:
                    break
                frame_data += chunk
            
            if len(frame_data) == frame_size:
                # Convert to OpenCV image
                nparr = np.frombuffer(frame_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    return img
                else:
                    print("❌ Failed to decode frame as image")
                    return None
            
            return None
            
        except Exception as e:
            print(f"❌ Error reading frame for {device_id}: {e}")
            # Reset socket on error
            if device_id in self.streaming_devices:
                try:
                    self.streaming_devices[device_id]['socket'].close()
                except:
                    pass
                self.streaming_devices[device_id]['socket'] = None
                self.streaming_devices[device_id]['banner_read'] = False
            return None
    
    def get_latest_frame(self, device_id: str) -> Optional[np.ndarray]:
        """Get the latest frame for a device"""
        import time
        start_time = time.time()
        
        frame = self.last_frames.get(device_id)
        
        if frame is not None:
            elapsed = (time.time() - start_time) * 1000  # Convert to milliseconds
            print(f"📸 Retrieved frame for {device_id} in {elapsed:.1f}ms")
        else:
            elapsed = (time.time() - start_time) * 1000
            print(f"⚠️ No frame available for {device_id} (took {elapsed:.1f}ms)")
            
        return frame
    
    def start_streaming_thread(self, device_id: str, display_name: str = None):
        """Start streaming thread for a device with OpenCV display"""
        if display_name is None:
            display_name = f"Device {device_id}"
        
        def stream_loop():
            print(f"🎥 Starting stream for {device_id} - {display_name}")
            
            consecutive_failures = 0
            max_failures = 10  # Max consecutive failures before giving up
            
            while self.streaming_devices.get(device_id, {}).get('running', False):
                try:
                    frame_start_time = time.time()
                    frame = self.read_minicap_frame(device_id)
                    if frame is not None:
                        consecutive_failures = 0  # Reset failure counter
                        
                        # Store the latest frame
                        self.last_frames[device_id] = frame.copy()
                        
                        frame_elapsed = (time.time() - frame_start_time) * 1000
                        print(f"💾 Stored frame for {device_id} in {frame_elapsed:.1f}ms")
                        
                        # Resize frame for display (optional)
                        height, width = frame.shape[:2]
                        if width > 800:  # Resize if too large
                            scale = 800 / width
                            new_width = int(width * scale)
                            new_height = int(height * scale)
                            frame = cv2.resize(frame, (new_width, new_height))
                        
                        # Add device info overlay
                        cv2.putText(frame, f"{display_name}", (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        # Display frame
                        cv2.imshow(display_name, frame)
                        
                        # Handle key press (ESC to exit)
                        key = cv2.waitKey(1) & 0xFF
                        if key == 27:  # ESC
                            break
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            print(f"❌ Too many consecutive failures for {device_id}, stopping stream")
                            break
                        time.sleep(0.1)  # Short delay on failure
                        continue
                    
                    # Maintain 30fps
                    time.sleep(1/30)
                    
                except Exception as e:
                    consecutive_failures += 1
                    print(f"❌ Error in stream loop for {device_id}: {e}")
                    if consecutive_failures >= max_failures:
                        print(f"❌ Too many consecutive failures for {device_id}, stopping stream")
                        break
                    time.sleep(1)
            
            # Clean up window
            try:
                cv2.destroyWindow(display_name)
            except:
                pass
            print(f"🎥 Stream ended for {device_id}")
        
        # Start streaming thread
        stream_thread = threading.Thread(target=stream_loop, daemon=True)
        stream_thread.start()
        
        return stream_thread
    
    def start_multi_device_streaming(self, device_list: List[str]):
        """Start streaming for multiple devices with different ports"""
        print(f"🚀 Starting streaming for {len(device_list)} devices...")
        
        # Start streaming for each device
        for i, device_id in enumerate(device_list):
            port = self.base_port + i
            if self.start_streaming(device_id, port):
                # Start display thread
                display_name = f"Device {i+1} ({device_id})"
                self.start_streaming_thread(device_id, display_name)
        
        print(f"✅ Streaming started for {len(device_list)} devices")
        print("Press ESC in any window to stop streaming")
        
        # Wait for user to stop
        try:
            while any(info.get('running', False) for info in self.streaming_devices.values()):
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping all streams...")
            self.stop_all_streaming()
    
    def stop_streaming(self, device_id: str):
        """Stop streaming for a specific device"""
        try:
            if device_id in self.streaming_devices:
                stream_info = self.streaming_devices[device_id]
                
                # Stop the stream
                stream_info['running'] = False
                
                # Close socket connection
                if stream_info.get('socket'):
                    try:
                        stream_info['socket'].close()
                    except:
                        pass
                    stream_info['socket'] = None
                
                # Kill minicap process
                if stream_info.get('process'):
                    stream_info['process'].terminate()
                
                # Kill minicap process on device
                subprocess.run([
                    'adb', '-s', device_id, 'shell', 'pkill', '-f', 'minicap'
                ], capture_output=True, timeout=5)
                
                # Remove port forwarding
                port = stream_info['port']
                subprocess.run([
                    'adb', '-s', device_id, 'forward', '--remove', f'tcp:{port}'
                ], capture_output=True, timeout=5)
                
                # Clean up frame storage
                if device_id in self.last_frames:
                    del self.last_frames[device_id]
                
                del self.streaming_devices[device_id]
                print(f"✅ Streaming stopped for {device_id}")
            
        except Exception as e:
            print(f"❌ Error stopping streaming for {device_id}: {e}")
    
    def stop_all_streaming(self):
        """Stop streaming for all devices"""
        device_ids = list(self.streaming_devices.keys())
        for device_id in device_ids:
            self.stop_streaming(device_id)
        
        # Close all OpenCV windows
        cv2.destroyAllWindows()
        print("✅ All streaming stopped")
    
    def cleanup(self, device_id: str):
        """Cleanup minicap files and processes"""
        try:
            self.stop_streaming(device_id)
            
            # Remove minicap files from device
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'rm', '-f', '/data/local/tmp/minicap'
            ], capture_output=True, timeout=5)
            
            subprocess.run([
                'adb', '-s', device_id, 'shell', 'rm', '-f', '/data/local/tmp/minicap.so'
            ], capture_output=True, timeout=5)
            
        except Exception as e:
            print(f"❌ Error cleaning up minicap for {device_id}: {e}") 