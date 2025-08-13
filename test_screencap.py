#!/usr/bin/env python3
"""
Test script for minicap exec-out screenshot implementation

This script tests the manager that uses minicap via adb exec-out -s
instead of sockets.
"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.minicap_manager import ScreencapManager
from core.device_manager import DeviceManager


def test_screencap_manager(device_id: str):
    """Test the minicap exec-out manager"""
    print(f"🧪 Testing Minicap (exec-out) for device: {device_id}")
    print("=" * 50)
    
    manager = ScreencapManager()
    
    # Run test
    results = manager.test_screencap(device_id)
    
    print(f"\n📊 Test Results:")
    print(f"   Device Info: {'✅' if results['device_info'] else '❌'}")
    print(f"   Screenshot: {'✅' if results['screenshot'] else '❌'}")
    print(f"   Image Decode: {'✅' if results['image_decode'] else '❌'}")
    print(f"   Timing: {results['timing']:.1f}ms")
    
    if results['errors']:
        print(f"   Errors: {results['errors']}")
    
    return results


def test_device_manager(device_id: str):
    """Test the device manager with screencap"""
    print(f"\n🔧 Testing DeviceManager for device: {device_id}")
    print("-" * 50)
    
    device_manager = DeviceManager()
    
    # Initialize device manager
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return
    
    # Test screenshot
    print("📸 Testing screenshot capture...")
    screenshot = device_manager.get_screenshot(device_id, save_to_file=True)
    
    if screenshot:
        print(f"✅ Screenshot captured: {len(screenshot)} bytes")
        
        # Test image decoding
        try:
            image_array = np.frombuffer(screenshot, dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                print(f"✅ Image decoded: {w}x{h}")
            else:
                print("❌ Failed to decode image")
        except Exception as e:
            print(f"❌ Error decoding image: {e}")
    else:
        print("❌ Failed to capture screenshot")
    
    # Test multiple screenshots
    print("\n📸 Testing multiple screenshots...")
    screenshots = device_manager.get_multiple_screenshots(device_id, 3, 0.1)
    print(f"✅ Captured {len(screenshots)} screenshots")
    
    # Test session functionality
    print("\n🔄 Testing session functionality...")
    if device_manager.start_screenshot_session(device_id):
        print("✅ Session started")
        
        # Get a few screenshots in session
        for i in range(3):
            screenshot = device_manager.get_screenshot(device_id)
            if screenshot:
                print(f"   Screenshot {i+1}: {len(screenshot)} bytes")
        
        # Get stats
        stats = device_manager.get_screenshot_stats(device_id)
        print(f"   Stats: {stats}")
        
        device_manager.end_screenshot_session(device_id)
        print("✅ Session ended")
    else:
        print("❌ Failed to start session")


def test_performance(device_id: str, count: int = 10):
    """Test performance of screencap"""
    print(f"\n⚡ Performance test for device: {device_id}")
    print("-" * 50)
    
    manager = ScreencapManager()
    
    # Start session
    if not manager.start_session(device_id):
        print("❌ Failed to start session")
        return
    
    print(f"📸 Capturing {count} screenshots...")
    start_time = time.time()
    
    screenshots = []
    for i in range(count):
        screenshot = manager.get_screenshot(device_id)
        if screenshot:
            screenshots.append(screenshot)
            elapsed = time.time() - start_time
            fps = len(screenshots) / elapsed
            print(f"   Screenshot {i+1}: {len(screenshot)} bytes (FPS: {fps:.1f})")
        else:
            print(f"   ❌ Failed to capture screenshot {i+1}")
    
    total_time = time.time() - start_time
    avg_time = total_time / len(screenshots) if screenshots else 0
    avg_fps = len(screenshots) / total_time if total_time > 0 else 0
    
    print(f"\n📊 Performance Summary:")
    print(f"   Screenshots: {len(screenshots)}/{count}")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average time: {avg_time:.3f}s per screenshot")
    print(f"   Average FPS: {avg_fps:.1f}")
    
    # End session
    manager.end_session(device_id)


def main():
    """Main test function"""
    print("🧪 Screencap Test Suite")
    print("=" * 50)
    
    # Get available devices
    device_manager = DeviceManager()
    
    # Initialize device manager
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager. Please check ADB connection.")
        return
    
    devices = device_manager.get_device_list()
    
    if not devices:
        print("❌ No devices found. Please connect a device and try again.")
        return
    
    print(f"📱 Found {len(devices)} device(s):")
    for i, device in enumerate(devices):
        print(f"   {i+1}. {device}")
    
    # Test with first device
    device_id = devices[0]
    print(f"\n🎯 Testing with device: {device_id}")
    
    # Run tests
    test_screencap_manager(device_id)
    test_device_manager(device_id)
    test_performance(device_id, 5)
    
    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    main() 