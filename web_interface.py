#!/usr/bin/env python3
"""
Web Interface for Mobile Game Automation Framework
Provides real-time monitoring of automation status and device screenshots
"""

import os
import time
import threading
import base64
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
from PIL import Image
import cv2
import numpy as np

# Add the project root to Python path
project_root = Path(__file__).parent
import sys
sys.path.insert(0, str(project_root))

from core.device_manager import DeviceManager
from core.automation_engine import AutomationEngine

# Import ngrok for internet exposure
try:
    from pyngrok import ngrok
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False
    print("⚠️ pyngrok not available. Install with: pip install pyngrok")


class WebInterface:
    """Web interface for monitoring automation status"""
    
    def __init__(self, automation_engine: Optional[AutomationEngine] = None, verbose: bool = False):
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Store automation engine reference
        self.automation_engine = automation_engine
        self.device_manager = DeviceManager()
        self.verbose = verbose
        
        # Stats tracking
        self.stats = {
            'start_time': datetime.now(),
            'total_cycles': 0,
            'successful_cycles': 0,
            'failed_cycles': 0,
            'current_state': 'idle',
            'devices': {},
            'last_update': datetime.now()
        }
        
        # ngrok tunnel
        self.ngrok_tunnel = None
        self.public_url = None
        
        # Setup routes
        self.setup_routes()
        
        # No screenshot thread needed since we fetch on demand
        self.running = False
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/stats')
        def get_stats():
            """Get current automation statistics"""
            return jsonify(self.get_current_stats())
        
        @self.app.route('/api/screenshots')
        def get_screenshots():
            """Get fresh screenshots from all devices"""
            screenshots = {}
            try:
                # Fetch fresh screenshots for each device
                for device_id in self.device_manager.get_device_list():
                    if self.device_manager.is_device_connected(device_id):
                        screenshot_data = self.get_device_screenshot(device_id)
                        if screenshot_data:
                            screenshots[device_id] = screenshot_data
                        elif self.verbose:
                            print(f"⚠️ Failed to get screenshot for {device_id}")
            except Exception as e:
                print(f"Error getting screenshots: {e}")
            
            return jsonify({
                'screenshots': screenshots,
                'timestamp': datetime.now().isoformat(),
                'total_devices': len(self.device_manager.get_device_list()),
                'successful_screenshots': len(screenshots)
            })
        
        @self.app.route('/api/screenshot/<device_id>')
        def get_device_screenshot_route(device_id):
            """Get screenshot for specific device"""
            screenshot_data = self.get_device_screenshot(device_id)
            if screenshot_data:
                return jsonify(screenshot_data)
            else:
                return jsonify({'error': 'Screenshot not available'}), 404
        
        @self.app.route('/api/screenshot/<device_id>/refresh', methods=['POST'])
        def refresh_device_screenshot(device_id):
            """Force refresh screenshot for specific device"""
            try:
                screenshot_data = self.get_device_screenshot(device_id)
                if screenshot_data:
                    return jsonify({
                        'status': 'success',
                        'device_id': device_id,
                        'screenshot': screenshot_data
                    })
                else:
                    return jsonify({'error': 'Failed to get screenshot'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/devices')
        def get_devices():
            """Get list of connected devices"""
            devices = []
            try:
                for device_id in self.device_manager.get_device_list():
                    devices.append({
                        'id': device_id,
                        'connected': self.device_manager.is_device_connected(device_id)
                    })
            except Exception as e:
                print(f"Error getting devices: {e}")
                # Return mock data if ADB is not available
                devices = [
                    {'id': 'emulator-5554', 'connected': False},
                    {'id': 'emulator-5556', 'connected': False}
                ]
            return jsonify({'devices': devices})
        
        @self.app.route('/api/control/start', methods=['POST'])
        def start_automation():
            """Start automation (if automation engine is available)"""
            if not self.automation_engine:
                return jsonify({'error': 'Automation engine not available'}), 400
            
            try:
                # This would need to be implemented based on your automation engine
                return jsonify({'status': 'started'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/control/stop', methods=['POST'])
        def stop_automation():
            """Stop automation"""
            if not self.automation_engine:
                return jsonify({'error': 'Automation engine not available'}), 400
            
            try:
                # This would need to be implemented based on your automation engine
                return jsonify({'status': 'stopped'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/status')
        def get_status():
            """Get overall system status"""
            return jsonify({
                'ngrok_available': NGROK_AVAILABLE,
                'public_url': self.public_url,
                'adb_available': self.device_manager.initialized,
                'automation_engine_available': self.automation_engine is not None
            })
    
    def get_device_screenshot(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get screenshot for a specific device"""
        try:
            # Get raw screenshot data
            screenshot_data = self.device_manager.get_screenshot(device_id)
            if not screenshot_data:
                if self.verbose:
                    print(f"⚠️ No screenshot data received for device {device_id}")
                return None
            
            # Convert to PIL Image for processing
            image = Image.open(io.BytesIO(screenshot_data))
            
            # Log image details for debugging
            if self.verbose:
                print(f"📸 Processing screenshot for {device_id}: {image.size} {image.mode}")
            
            # Convert RGBA to RGB if necessary (JPEG doesn't support alpha channel)
            if image.mode == 'RGBA':
                # Create a white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                # Paste the image onto the background
                background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                image = background
                if self.verbose:
                    print(f"   Converted RGBA to RGB for {device_id}")
            elif image.mode != 'RGB':
                # Convert other modes to RGB
                original_mode = image.mode
                image = image.convert('RGB')
                if self.verbose:
                    print(f"   Converted {original_mode} to RGB for {device_id}")
            
            # Optimize image size for web display
            max_width = 600  # Reduced from 800 for better performance
            max_height = 450  # Reduced from 600 for better performance
            
            # Calculate new dimensions
            width, height = image.size
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                if self.verbose:
                    print(f"   Resized from {width}x{height} to {new_width}x{new_height}")
            
            # Apply additional compression and optimization
            # Convert to base64 with higher compression
            buffer = io.BytesIO()
            
            # Use progressive JPEG for better web loading
            image.save(buffer, format='JPEG', quality=70, optimize=True, progressive=True)
            
            # Get the compressed data
            compressed_data = buffer.getvalue()
            img_str = base64.b64encode(compressed_data).decode()
            
            if self.verbose:
                original_size = len(screenshot_data)
                compressed_size = len(compressed_data)
                compression_ratio = (1 - compressed_size / original_size) * 100
                print(f"   Compressed: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% reduction)")
            
            return {
                'device_id': device_id,
                'image': f"data:image/jpeg;base64,{img_str}",
                'timestamp': datetime.now().isoformat(),
                'size': image.size,
                'compressed_size': len(compressed_data)
            }
            
        except Exception as e:
            print(f"❌ Error getting screenshot for {device_id}: {e}")
            import traceback
            if self.verbose:
                traceback.print_exc()
            return None
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current automation statistics"""
        stats = self.stats.copy()
        
        # Update with real-time data if automation engine is available
        if self.automation_engine:
            # This would need to be implemented based on your automation engine structure
            pass
        
        # Calculate uptime
        if stats['start_time']:
            uptime = datetime.now() - stats['start_time']
            stats['uptime'] = str(uptime).split('.')[0]  # Remove microseconds
        else:
            stats['uptime'] = '00:00:00'
        
        # Calculate success rate
        total = stats['successful_cycles'] + stats['failed_cycles']
        if total > 0:
            stats['success_rate'] = round((stats['successful_cycles'] / total) * 100, 2)
        else:
            stats['success_rate'] = 0.0
        
        # Count connected devices
        try:
            connected_count = sum(1 for device_id in self.device_manager.get_device_list() 
                                if self.device_manager.is_device_connected(device_id))
            stats['connected_devices'] = connected_count
        except Exception:
            stats['connected_devices'] = 0
        
        stats['last_update'] = datetime.now().isoformat()
        return stats
    
    def update_stats(self, new_stats: Dict[str, Any]):
        """Update statistics from automation engine"""
        self.stats.update(new_stats)
        if 'start_time' in new_stats and new_stats['start_time']:
            self.stats['start_time'] = new_stats['start_time']
    
    def start_ngrok_tunnel(self, port: int):
        """Start ngrok tunnel to expose localhost to internet"""
        if not NGROK_AVAILABLE:
            print("❌ ngrok not available. Install with: pip install pyngrok")
            return False
        
        try:
            # Kill any existing tunnels
            ngrok.kill()
            
            # Start new tunnel
            self.ngrok_tunnel = ngrok.connect(port)
            self.public_url = self.ngrok_tunnel.public_url
            
            print(f"🌐 Public URL: {self.public_url}")
            print(f"🔗 Local URL: http://localhost:{port}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start ngrok tunnel: {e}")
            print("💡 Make sure you have ngrok installed and authenticated")
            print("   Download from: https://ngrok.com/download")
            print("   Then run: ngrok authtoken YOUR_TOKEN")
            return False
    
    def stop_ngrok_tunnel(self):
        """Stop ngrok tunnel"""
        if self.ngrok_tunnel:
            try:
                ngrok.kill()
                self.ngrok_tunnel = None
                self.public_url = None
                print("🛑 ngrok tunnel stopped")
            except Exception as e:
                print(f"❌ Error stopping ngrok tunnel: {e}")
    
    def start(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False, use_ngrok: bool = True):
        """Start the web interface"""
        print(f"🌐 Starting web interface on http://{host}:{port}")
        
        # Initialize device manager (don't fail if ADB not available)
        try:
            if not self.device_manager.initialize():
                print("⚠️ Failed to initialize device manager (ADB not available)")
                print("   The web interface will still work, but device screenshots may not be available")
        except Exception as e:
            print(f"⚠️ Device manager error: {e}")
        
        # Start ngrok tunnel if requested
        if use_ngrok and NGROK_AVAILABLE:
            if self.start_ngrok_tunnel(port):
                print(f"✅ ngrok tunnel started successfully")
            else:
                print("⚠️ ngrok tunnel failed, running locally only")
        
        try:
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except KeyboardInterrupt:
            print("\n🛑 Web interface stopped by user")
        finally:
            self.stop_ngrok_tunnel()
        
        return True


def create_web_interface(automation_engine: Optional[AutomationEngine] = None, verbose: bool = False) -> WebInterface:
    """Create and return a web interface instance"""
    return WebInterface(automation_engine, verbose)


if __name__ == "__main__":
    # Create web interface without automation engine for standalone testing
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    use_ngrok = True
    if len(sys.argv) > 1 and sys.argv[1] == '--no-ngrok':
        use_ngrok = False
    
    web_interface = create_web_interface(verbose=verbose)
    web_interface.start(host='0.0.0.0', port=5000, debug=True, use_ngrok=use_ngrok) 