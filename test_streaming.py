#!/usr/bin/env python3
"""
Test script for minicap streaming functionality
"""

import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.minicap_stream_manager import MinicapStreamManager
from core.device_manager import DeviceManager


def test_streaming():
    """Test the streaming functionality"""
    print("🧪 Testing Minicap Streaming")
    print("=" * 40)
    
    # Initialize device manager
    device_manager = DeviceManager()
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return False
    
    # Get device list
    devices = device_manager.get_device_list()
    if not devices:
        print("❌ No devices found")
        return False
    
    print(f"📱 Found {len(devices)} device(s): {devices}")
    
    # Test with first device only
    test_device = devices[0]
    print(f"🧪 Testing with device: {test_device}")
    
    # Initialize stream manager
    stream_manager = MinicapStreamManager()
    
    try:
        # Test setup
        print("🔧 Testing minicap setup...")
        if not stream_manager.setup_minicap(test_device):
            print("❌ Minicap setup failed")
            return False
        print("✅ Minicap setup successful")
        
        # Test streaming start
        print("🎥 Testing streaming start...")
        if not stream_manager.start_streaming(test_device, 1313):
            print("❌ Streaming start failed")
            return False
        print("✅ Streaming start successful")
        
        # Test frame reading
        print("📸 Testing frame reading...")
        for i in range(5):  # Test 5 frames
            frame = stream_manager.read_minicap_frame(test_device)
            if frame is not None:
                print(f"✅ Frame {i+1} captured: {frame.shape}")
            else:
                print(f"❌ Frame {i+1} failed")
            time.sleep(0.1)
        
        # Test streaming thread
        print("🎬 Testing streaming thread...")
        stream_thread = stream_manager.start_streaming_thread(test_device, "Test Stream")
        
        # Let it run for a few seconds
        print("⏱️ Running stream for 5 seconds...")
        time.sleep(5)
        
        # Stop streaming
        print("🛑 Stopping streaming...")
        stream_manager.stop_streaming(test_device)
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        stream_manager.stop_all_streaming()
        stream_manager.cleanup(test_device)


if __name__ == "__main__":
    success = test_streaming()
    if success:
        print("\n🎉 Streaming test completed successfully!")
    else:
        print("\n💥 Streaming test failed!")
        sys.exit(1) 