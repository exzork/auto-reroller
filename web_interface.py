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

# Import friend point service
try:
    import sys
    import importlib.util
    spec = importlib.util.spec_from_file_location("friend_point_service", "games/umamusume-fp/friend_point_service.py")
    friend_point_service = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(friend_point_service)
    FriendPointService = friend_point_service.FriendPointService
    FP_SERVICE_AVAILABLE = True
except ImportError as e:
    FP_SERVICE_AVAILABLE = False
    print(f"⚠️ Friend point service not available: {e}")


class WebInterface:
    """Web interface for monitoring automation status"""
    
    def __init__(self, automation_engine: Optional[AutomationEngine] = None, verbose: bool = False):
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Store automation engine reference
        self.automation_engine = automation_engine
        self.device_manager = DeviceManager()
        self.verbose = verbose
        
        # Initialize friend point service
        self.fp_service = None
        if FP_SERVICE_AVAILABLE:
            try:
                self.fp_service = FriendPointService()
                print("✅ Friend point service initialized")
            except Exception as e:
                print(f"❌ Error initializing friend point service: {e}")
        
        # Screenshot cache
        self.screenshot_cache = {}
        self.last_screenshot_time = {}
        
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
        
        # Start screenshot thread
        self.screenshot_thread = None
        self.running = False
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/fp')
        def fp_dashboard():
            """Friend point service dashboard"""
            return render_template('fp_dashboard.html')
        
        @self.app.route('/api/stats')
        def get_stats():
            """Get current automation statistics"""
            return jsonify(self.get_current_stats())
        
        @self.app.route('/api/screenshots')
        def get_screenshots():
            """Get all device screenshots"""
            screenshots = {}
            try:
                for device_id in self.device_manager.get_device_list():
                    screenshot_data = self.get_device_screenshot(device_id)
                    if screenshot_data:
                        screenshots[device_id] = screenshot_data
            except Exception as e:
                print(f"Error getting screenshots: {e}")
            
            return jsonify({
                'screenshots': screenshots,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/screenshot/<device_id>')
        def get_device_screenshot_route(device_id):
            """Get screenshot for specific device"""
            screenshot_data = self.get_device_screenshot(device_id)
            if screenshot_data:
                return jsonify(screenshot_data)
            else:
                return jsonify({'error': 'Screenshot not available'}), 404
        
        @self.app.route('/api/devices')
        def get_devices():
            """Get list of connected devices"""
            devices = []
            try:
                for device_id in self.device_manager.get_device_list():
                    devices.append({
                        'id': device_id,
                        'connected': self.device_manager.is_device_connected(device_id),
                        'last_screenshot': self.last_screenshot_time.get(device_id)
                    })
            except Exception as e:
                print(f"Error getting devices: {e}")
                # Return mock data if ADB is not available
                devices = [
                    {'id': 'emulator-5554', 'connected': False, 'last_screenshot': None},
                    {'id': 'emulator-5556', 'connected': False, 'last_screenshot': None}
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
                'automation_engine_available': self.automation_engine is not None,
                'fp_service_available': self.fp_service is not None
            })
        
        # Friend Point Service Routes
        @self.app.route('/api/fp/service/status')
        def get_fp_service_status():
            """Get friend point service status"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                queue_status = self.fp_service.get_queue_status()
                return jsonify(queue_status)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/fp/service/requests', methods=['GET'])
        def get_fp_requests():
            """Get all friend point requests"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                requests = []
                for request in self.fp_service.requests.values():
                    requests.append({
                        'request_id': request.request_id,
                        'buyer_id': request.buyer_id,
                        'target_points': request.target_points,
                        'support_card_type': request.support_card_type,
                        'priority': request.priority,
                        'status': request.status.value,
                        'points_earned': request.points_earned,
                        'cycles_completed': request.cycles_completed,
                        'created_at': request.created_at.isoformat(),
                        'completed_at': request.completed_at.isoformat() if request.completed_at else None,
                        'error_message': request.error_message
                    })
                
                return jsonify({'requests': requests})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/fp/service/request', methods=['POST'])
        def create_fp_request():
            """Create a new friend point request"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                data = request.get_json()
                buyer_id = data.get('buyer_id')
                target_points = data.get('target_points')
                support_card_type = data.get('support_card_type', 'auto')
                priority = data.get('priority', 'normal')
                
                if not buyer_id or not target_points:
                    return jsonify({'error': 'buyer_id and target_points are required'}), 400
                
                request_id = self.fp_service.create_request(
                    buyer_id=buyer_id,
                    target_points=target_points,
                    support_card_type=support_card_type,
                    priority=priority
                )
                
                return jsonify({
                    'request_id': request_id,
                    'status': 'created'
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/fp/service/request/<request_id>/start', methods=['POST'])
        def start_fp_request(request_id):
            """Start processing a friend point request"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                success = self.fp_service.start_request(request_id)
                if success:
                    return jsonify({'status': 'started'})
                else:
                    return jsonify({'error': 'Failed to start request'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/fp/service/request/<request_id>/pause', methods=['POST'])
        def pause_fp_request(request_id):
            """Pause processing a friend point request"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                success = self.fp_service.pause_request(request_id)
                if success:
                    return jsonify({'status': 'paused'})
                else:
                    return jsonify({'error': 'Failed to pause request'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/fp/service/request/<request_id>/resume', methods=['POST'])
        def resume_fp_request(request_id):
            """Resume processing a friend point request"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                success = self.fp_service.resume_request(request_id)
                if success:
                    return jsonify({'status': 'resumed'})
                else:
                    return jsonify({'error': 'Failed to resume request'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/fp/service/request/<request_id>', methods=['GET'])
        def get_fp_request(request_id):
            """Get a specific friend point request"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                request = self.fp_service.get_request(request_id)
                if request:
                    return jsonify({
                        'request_id': request.request_id,
                        'buyer_id': request.buyer_id,
                        'target_points': request.target_points,
                        'support_card_type': request.support_card_type,
                        'priority': request.priority,
                        'status': request.status.value,
                        'points_earned': request.points_earned,
                        'cycles_completed': request.cycles_completed,
                        'created_at': request.created_at.isoformat(),
                        'completed_at': request.completed_at.isoformat() if request.completed_at else None,
                        'error_message': request.error_message
                    })
                else:
                    return jsonify({'error': 'Request not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/fp/service/stats')
        def get_fp_stats():
            """Get friend point service statistics"""
            if not self.fp_service:
                return jsonify({'error': 'Friend point service not available'}), 400
            
            try:
                stats = self.fp_service.get_service_stats()
                return jsonify({
                    'total_requests': stats.total_requests,
                    'completed_requests': stats.completed_requests,
                    'failed_requests': stats.failed_requests,
                    'total_points_earned': stats.total_points_earned,
                    'average_points_per_request': stats.average_points_per_request,
                    'total_runtime_hours': stats.total_runtime_hours,
                    'last_updated': stats.last_updated.isoformat()
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def get_device_screenshot(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get screenshot for a specific device"""
        try:
            # Get raw screenshot data
            screenshot_data = self.device_manager.get_screenshot(device_id)
            if not screenshot_data:
                print(f"⚠️ No screenshot data received for device {device_id}")
                return None
            
            # Convert to PIL Image for processing
            image = Image.open(io.BytesIO(screenshot_data))
            
            # Log image details for debugging
            if hasattr(self, 'verbose') and self.verbose:
                print(f"📸 Processing screenshot for {device_id}: {image.size} {image.mode}")
            
            # Convert RGBA to RGB if necessary (JPEG doesn't support alpha channel)
            if image.mode == 'RGBA':
                # Create a white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                # Paste the image onto the background
                background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                image = background
                if hasattr(self, 'verbose') and self.verbose:
                    print(f"   Converted RGBA to RGB for {device_id}")
            elif image.mode != 'RGB':
                # Convert other modes to RGB
                original_mode = image.mode
                image = image.convert('RGB')
                if hasattr(self, 'verbose') and self.verbose:
                    print(f"   Converted {original_mode} to RGB for {device_id}")
            
            # Resize for web display (maintain aspect ratio)
            max_width = 800
            max_height = 600
            
            # Calculate new dimensions
            width, height = image.size
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                if hasattr(self, 'verbose') and self.verbose:
                    print(f"   Resized from {width}x{height} to {new_width}x{new_height}")
            
            # Convert to base64 for web display
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                'device_id': device_id,
                'image': f"data:image/jpeg;base64,{img_str}",
                'timestamp': datetime.now().isoformat(),
                'size': image.size
            }
            
        except Exception as e:
            print(f"❌ Error getting screenshot for {device_id}: {e}")
            import traceback
            if hasattr(self, 'verbose') and self.verbose:
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
    
    def start_screenshot_thread(self):
        """Start background thread for capturing screenshots"""
        if self.screenshot_thread and self.screenshot_thread.is_alive():
            return
        
        self.running = True
        self.screenshot_thread = threading.Thread(target=self._screenshot_loop, daemon=True)
        self.screenshot_thread.start()
    
    def stop_screenshot_thread(self):
        """Stop screenshot thread"""
        self.running = False
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=2)
    
    def _screenshot_loop(self):
        """Background loop for capturing screenshots at 1 FPS"""
        while self.running:
            try:
                for device_id in self.device_manager.get_device_list():
                    if self.device_manager.is_device_connected(device_id):
                        screenshot_data = self.get_device_screenshot(device_id)
                        if screenshot_data:
                            self.screenshot_cache[device_id] = screenshot_data
                            self.last_screenshot_time[device_id] = datetime.now()
                
                time.sleep(1)  # 1 FPS
                
            except Exception as e:
                print(f"Error in screenshot loop: {e}")
                time.sleep(5)  # Wait before retrying
    
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
        
        # Start screenshot thread
        self.start_screenshot_thread()
        
        try:
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except KeyboardInterrupt:
            print("\n🛑 Web interface stopped by user")
        finally:
            self.stop_screenshot_thread()
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