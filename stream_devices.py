#!/usr/bin/env python3
"""
Device Streaming Script
Streams all connected devices using minicap at 30fps with OpenCV display
"""

import sys
import os
import argparse
import time
import threading
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.minicap_stream_manager import MinicapStreamManager
from core.device_manager import DeviceManager


def parse_arguments():
    """Parse command-line arguments for device streaming"""
    parser = argparse.ArgumentParser(
        description="Stream all connected devices using minicap at 30fps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python stream_devices.py  # Stream all devices
  python stream_devices.py --devices emulator-5554,emulator-5556  # Stream specific devices
  python stream_devices.py --port-start 1313  # Start from specific port
  python stream_devices.py --no-display  # Stream without OpenCV display
        """
    )
    
    parser.add_argument('--devices',
                       type=str,
                       help='Comma-separated list of device IDs to stream')
    
    parser.add_argument('--port-start',
                       type=int,
                       default=1313,
                       help='Starting port for minicap (default: 1313)')
    
    parser.add_argument('--no-display',
                       action='store_true',
                       help='Stream without OpenCV display (for headless operation)')
    
    parser.add_argument('--fps',
                       type=int,
                       default=30,
                       help='Target FPS for streaming (default: 30)')
    
    parser.add_argument('--minicap-path',
                       type=str,
                       default='minicap',
                       help='Path to minicap binaries (default: minicap)')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose logging')
    
    return parser.parse_args()


def main():
    """Main entry point for device streaming"""
    args = parse_arguments()
    
    print("🎥 Device Streaming Tool")
    print("=" * 50)
    
    # Initialize device manager
    device_manager = DeviceManager()
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return
    
    # Get device list
    if args.devices:
        device_list = [d.strip() for d in args.devices.split(',')]
        # Validate devices
        available_devices = device_manager.get_device_list()
        invalid_devices = [d for d in device_list if d not in available_devices]
        if invalid_devices:
            print(f"❌ Invalid devices: {invalid_devices}")
            print(f"Available devices: {available_devices}")
            return
    else:
        device_list = device_manager.get_device_list()
    
    if not device_list:
        print("❌ No devices available for streaming")
        return
    
    print(f"📱 Found {len(device_list)} device(s): {device_list}")
    
    # Initialize minicap stream manager
    stream_manager = MinicapStreamManager(minicap_path=args.minicap_path)
    stream_manager.base_port = args.port_start
    
    try:
        if args.no_display:
            # Headless streaming mode
            print("🎥 Starting headless streaming...")
            for i, device_id in enumerate(device_list):
                port = args.port_start + i
                if stream_manager.start_streaming(device_id, port):
                    print(f"✅ Device {device_id} streaming on port {port}")
                else:
                    print(f"❌ Failed to start streaming for {device_id}")
            
            print("\n🎥 Headless streaming active. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping all streams...")
                stream_manager.stop_all_streaming()
        else:
            # Interactive streaming mode with OpenCV display
            print("🎥 Starting interactive streaming with OpenCV display...")
            stream_manager.start_multi_device_streaming(device_list)
    
    except KeyboardInterrupt:
        print("\n🛑 Streaming interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🏁 Streaming session ended")


if __name__ == "__main__":
    main() 