#!/usr/bin/env python3
"""
Setup script for ngrok configuration
Helps users install and configure ngrok for internet exposure
"""

import os
import sys
import subprocess
import platform

def check_ngrok_installed():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def install_ngrok():
    """Install ngrok based on the operating system"""
    system = platform.system().lower()
    
    print("🔧 Installing ngrok...")
    
    if system == "windows":
        # Download ngrok for Windows
        print("📥 Downloading ngrok for Windows...")
        try:
            import urllib.request
            url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
            filename = "ngrok.zip"
            urllib.request.urlretrieve(url, filename)
            
            # Extract and install
            import zipfile
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                zip_ref.extractall(".")
            
            # Move to PATH or current directory
            if os.path.exists("ngrok.exe"):
                print("✅ ngrok installed successfully")
                os.remove(filename)  # Clean up zip file
                return True
            else:
                print("❌ Failed to extract ngrok")
                return False
                
        except Exception as e:
            print(f"❌ Error installing ngrok: {e}")
            print("💡 Please download manually from: https://ngrok.com/download")
            return False
    
    elif system == "darwin":  # macOS
        print("📥 Installing ngrok via Homebrew...")
        try:
            subprocess.run(['brew', 'install', 'ngrok'], check=True)
            return True
        except subprocess.CalledProcessError:
            print("❌ Homebrew not available or installation failed")
            print("💡 Please install manually: brew install ngrok")
            return False
    
    elif system == "linux":
        print("📥 Installing ngrok for Linux...")
        try:
            # Download and install
            subprocess.run([
                'curl', '-s', 'https://ngrok-agent.s3.amazonaws.com/ngrok.asc', '|', 'sudo', 'tee', '/etc/apt/trusted.gpg.d/ngrok.asc', '>', '/dev/null'
            ], shell=True)
            subprocess.run(['echo', '"deb https://ngrok-agent.s3.amazonaws.com buster main"', '|', 'sudo', 'tee', '/etc/apt/sources.list.d/ngrok.list'], shell=True)
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            subprocess.run(['sudo', 'apt', 'install', 'ngrok'], check=True)
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install ngrok via package manager")
            print("💡 Please install manually from: https://ngrok.com/download")
            return False
    
    else:
        print(f"❌ Unsupported operating system: {system}")
        print("💡 Please install ngrok manually from: https://ngrok.com/download")
        return False

def setup_ngrok_auth():
    """Guide user through ngrok authentication"""
    print("\n🔐 ngrok Authentication Setup")
    print("=" * 40)
    print("To expose your localhost to the internet, you need to:")
    print("1. Create a free account at https://ngrok.com")
    print("2. Get your authtoken from the dashboard")
    print("3. Run the authentication command")
    print()
    
    token = input("Enter your ngrok authtoken (or press Enter to skip): ").strip()
    
    if token:
        try:
            subprocess.run(['ngrok', 'authtoken', token], check=True)
            print("✅ ngrok authentication successful!")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to authenticate ngrok")
            return False
    else:
        print("⚠️ Skipping authentication. ngrok will work with limited features.")
        return True

def main():
    """Main setup function"""
    print("🚀 ngrok Setup for Mobile Game Automation")
    print("=" * 50)
    
    # Check if ngrok is already installed
    if check_ngrok_installed():
        print("✅ ngrok is already installed")
    else:
        print("❌ ngrok not found")
        install = input("Would you like to install ngrok? (y/n): ").lower().strip()
        
        if install == 'y':
            if not install_ngrok():
                print("❌ Failed to install ngrok")
                return
        else:
            print("⚠️ ngrok is required for internet exposure")
            print("💡 You can install it manually from: https://ngrok.com/download")
            return
    
    # Setup authentication
    setup_ngrok_auth()
    
    print("\n🎉 Setup complete!")
    print("You can now run the web interface with:")
    print("  python main.py --web-only")
    print("  python web_interface.py")
    print("\nThe web interface will be available at:")
    print("  Local: http://localhost:5000")
    print("  Public: https://your-ngrok-url.ngrok.io")

if __name__ == "__main__":
    main() 