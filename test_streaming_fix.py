#!/usr/bin/env python3
"""
Quick test for the streaming fix
"""

import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.minicap_stream_manager import MinicapStreamManager
from core.device_manager import DeviceManager


def test_streaming_fix():
    """Test the streaming fix"""
    print("🧪 Testing Streaming Fix")
    print("=" * 30)
    
    # Initialize device manager
    device_manager = DeviceManager()
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return False
    
    devices = device_manager.get_device_list()
    if not devices:
        print("❌ No devices found")
        return False
    
    print(f"📱 Found {len(devices)} device(s): {devices}")
    
    # Test with first device
    test_device = devices[0]
    print(f"🧪 Testing with device: {test_device}")
    
    # Initialize stream manager
    stream_manager = MinicapStreamManager()
    
    try:
        # Setup minicap
        print("🔧 Setting up minicap...")
        if not stream_manager.setup_minicap(test_device):
            print("❌ Minicap setup failed")
            return False
        print("✅ Minicap setup successful")
        
        # Start streaming
        print("🎥 Starting streaming...")
        if not stream_manager.start_streaming(test_device, 1313):
            print("❌ Streaming start failed")
            return False
        print("✅ Streaming start successful")
        
        # Test frame reading
        print("📸 Testing frame reading...")
        success_count = 0
        for i in range(10):  # Test 10 frames
            frame = stream_manager.read_minicap_frame(test_device)
            if frame is not None:
                success_count += 1
                print(f"✅ Frame {i+1} captured: {frame.shape}")
            else:
                print(f"❌ Frame {i+1} failed")
            time.sleep(0.1)
        
        print(f"📊 Success rate: {success_count}/10 frames")
        
        if success_count > 0:
            print("✅ Streaming fix working!")
            return True
        else:
            print("❌ No frames captured")
            return False
        
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
    success = test_streaming_fix()
    if success:
        print("\n🎉 Streaming fix test passed!")
    else:
        print("\n💥 Streaming fix test failed!")
        sys.exit(1) 