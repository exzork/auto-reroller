#!/usr/bin/env python3
"""
Setup script for minicap integration
Helps users organize minicap files and test streaming functionality
"""

import os
import sys
import subprocess
from pathlib import Path

def check_minicap_files():
    """Check if minicap files are properly organized"""
    project_root = Path(__file__).parent
    minicap_dir = project_root / "minicap"
    
    if not minicap_dir.exists():
        print("❌ Minicap directory not found")
        print("💡 Please create the following directory structure:")
        print("   minicap/")
        print("   ├── arm64-v8a/")
        print("   │   ├── minicap")
        print("   │   └── minicap.so")
        print("   ├── armeabi-v7a/")
        print("   │   ├── minicap")
        print("   │   └── minicap.so")
        print("   └── x86/")
        print("       ├── minicap")
        print("       └── minicap.so")
        return False
    
    # Check for common architectures
    architectures = ['arm64-v8a', 'armeabi-v7a', 'x86']
    missing_archs = []
    
    for arch in architectures:
        arch_dir = minicap_dir / arch
        if not arch_dir.exists():
            missing_archs.append(arch)
            continue
        
        minicap_bin = arch_dir / "minicap"
        minicap_so = arch_dir / "minicap.so"
        
        if not minicap_bin.exists():
            print(f"❌ Minicap binary missing for {arch}")
            missing_archs.append(arch)
        elif not minicap_so.exists():
            print(f"❌ Minicap library missing for {arch}")
            missing_archs.append(arch)
        else:
            print(f"✅ Minicap files found for {arch}")
    
    if missing_archs:
        print(f"\n⚠️ Missing minicap files for: {', '.join(missing_archs)}")
        print("💡 Please add the missing minicap files to continue")
        return False
    
    return True

def test_minicap_installation():
    """Test minicap installation on connected devices"""
    print("\n🧪 Testing minicap installation...")
    
    try:
        # Import device manager
        sys.path.insert(0, str(Path(__file__).parent))
        from core.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        if not device_manager.initialize():
            print("❌ Failed to initialize device manager")
            return False
        
        devices = device_manager.get_device_list()
        if not devices:
            print("❌ No devices connected")
            return False
        
        print(f"📱 Found {len(devices)} device(s): {devices}")
        
        for device_id in devices:
            print(f"\n🔧 Testing minicap on {device_id}...")
            
            # Get device info
            device_info = device_manager.get_device_info(device_id)
            if device_info:
                print(f"   Screen resolution: {device_info['size']}")
            
            # Test minicap installation
            if device_manager.install_minicap(device_id):
                print(f"✅ Minicap installed successfully on {device_id}")
                
                # Test streaming
                print(f"🚀 Testing stream on {device_id}...")
                if device_manager.start_minicap_stream(device_id):
                    print(f"✅ Stream started successfully on {device_id}")
                    
                    # Get stream URL
                    stream_url = device_manager.get_minicap_stream_url(device_id)
                    if stream_url:
                        print(f"🌐 Stream URL: {stream_url}")
                    else:
                        print(f"❌ Failed to get stream URL for {device_id}")
                    
                    # Stop stream
                    device_manager.stop_minicap_stream(device_id)
                    print(f"🛑 Stream stopped on {device_id}")
                else:
                    print(f"❌ Failed to start stream on {device_id}")
            else:
                print(f"❌ Failed to install minicap on {device_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing minicap: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Minicap Setup for Mobile Game Automation")
    print("=" * 50)
    
    # Check minicap files
    if not check_minicap_files():
        print("\n📋 Setup Instructions:")
        print("1. Create the minicap directory structure shown above")
        print("2. Place your minicap binary and library files in the appropriate architecture folders")
        print("3. Run this script again to test the installation")
        return
    
    print("✅ Minicap files are properly organized")
    
    # Test installation
    if test_minicap_installation():
        print("\n🎉 Minicap setup complete!")
        print("You can now use streaming in the web interface:")
        print("  python main.py --web-only")
        print("  python web_interface.py")
    else:
        print("\n❌ Minicap setup failed")
        print("Please check the error messages above and try again")

if __name__ == "__main__":
    main() 