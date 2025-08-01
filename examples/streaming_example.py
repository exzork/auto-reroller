#!/usr/bin/env python3
"""
Example: Streaming Devices with Minicap
Demonstrates how to use the MinicapStreamManager for real-time device streaming
"""

import sys
import time
import threading
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.minicap_stream_manager import MinicapStreamManager
from core.device_manager import DeviceManager


def example_basic_streaming():
    """Basic streaming example"""
    print("🎥 Basic Streaming Example")
    print("=" * 40)
    
    # Initialize device manager
    device_manager = DeviceManager()
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return
    
    devices = device_manager.get_device_list()
    if not devices:
        print("❌ No devices found")
        return
    
    print(f"📱 Found {len(devices)} device(s): {devices}")
    
    # Initialize stream manager
    stream_manager = MinicapStreamManager()
    
    try:
        # Start streaming for all devices
        print("🚀 Starting streaming for all devices...")
        stream_manager.start_multi_device_streaming(devices)
        
    except KeyboardInterrupt:
        print("\n🛑 Streaming interrupted")
    finally:
        stream_manager.stop_all_streaming()


def example_custom_streaming():
    """Custom streaming example with specific configuration"""
    print("🎥 Custom Streaming Example")
    print("=" * 40)
    
    # Initialize device manager
    device_manager = DeviceManager()
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return
    
    devices = device_manager.get_device_list()
    if not devices:
        print("❌ No devices found")
        return
    
    # Use only first 2 devices for this example
    devices = devices[:2]
    print(f"📱 Using {len(devices)} device(s): {devices}")
    
    # Initialize stream manager with custom port start
    stream_manager = MinicapStreamManager()
    stream_manager.base_port = 1320  # Start from port 1320
    
    try:
        # Start streaming for each device individually
        for i, device_id in enumerate(devices):
            port = 1320 + i
            print(f"🎥 Starting stream for {device_id} on port {port}")
            
            if stream_manager.start_streaming(device_id, port):
                # Start display thread with custom name
                display_name = f"Custom Stream {i+1} ({device_id})"
                stream_manager.start_streaming_thread(device_id, display_name)
            else:
                print(f"❌ Failed to start streaming for {device_id}")
        
        print("✅ All streams started. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        while any(info.get('running', False) for info in stream_manager.streaming_devices.values()):
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping all streams...")
    finally:
        stream_manager.stop_all_streaming()


def example_frame_processing():
    """Example of processing frames from the stream"""
    print("🎥 Frame Processing Example")
    print("=" * 40)
    
    # Initialize device manager
    device_manager = DeviceManager()
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return
    
    devices = device_manager.get_device_list()
    if not devices:
        print("❌ No devices found")
        return
    
    # Use only first device for this example
    device_id = devices[0]
    print(f"📱 Using device: {device_id}")
    
    # Initialize stream manager
    stream_manager = MinicapStreamManager()
    
    try:
        # Start streaming
        if not stream_manager.start_streaming(device_id, 1313):
            print("❌ Failed to start streaming")
            return
        
        print("📸 Processing frames for 10 seconds...")
        
        # Process frames for 10 seconds
        start_time = time.time()
        frame_count = 0
        
        while time.time() - start_time < 10:
            frame = stream_manager.read_minicap_frame(device_id)
            if frame is not None:
                frame_count += 1
                
                # Example: Add timestamp to frame
                import cv2
                timestamp = time.strftime("%H:%M:%S")
                cv2.putText(frame, timestamp, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Display frame
                cv2.imshow("Frame Processing", frame)
                
                # Handle key press
                if cv2.waitKey(1) & 0xFF == 27:  # ESC
                    break
            else:
                print("❌ Failed to read frame")
            
            time.sleep(1/30)  # Maintain 30fps
        
        print(f"✅ Processed {frame_count} frames in 10 seconds")
        cv2.destroyAllWindows()
        
    except KeyboardInterrupt:
        print("\n🛑 Processing interrupted")
    finally:
        stream_manager.stop_all_streaming()


def main():
    """Main function to run examples"""
    print("🎥 Minicap Streaming Examples")
    print("=" * 50)
    
    while True:
        print("\nChoose an example:")
        print("1. Basic streaming (all devices)")
        print("2. Custom streaming (specific devices, custom ports)")
        print("3. Frame processing example")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            example_basic_streaming()
        elif choice == "2":
            example_custom_streaming()
        elif choice == "3":
            example_frame_processing()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")


if __name__ == "__main__":
    main() 