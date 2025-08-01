import cv2
import numpy as np
import json
import subprocess
import sys
import os
from pathlib import Path
from .minicap_manager import MinicapManager

rectangles = []
slot_index = 1

def get_first_device():
    """Get the first available ADB device"""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        devices = [line.split('\t')[0] for line in lines if '\tdevice' in line]
        if not devices:
            raise Exception("No ADB devices found")
        return devices[0]
    except Exception as e:
        raise Exception(f"Failed to get ADB devices: {e}")

def get_screenshot():
    """Get screenshot from first ADB device using minicap"""
    device_id = get_first_device()
    print(f"📱 Taking screenshot from device: {device_id}")
    
    try:
        # Try minicap first
        minicap_manager = MinicapManager()
        
        # Setup and start minicap
        if minicap_manager.setup_minicap(device_id):
            if minicap_manager.start_minicap(device_id):
                # Get screenshot via minicap
                image_data = minicap_manager.get_screenshot(device_id)
                if image_data:
                    # Convert binary PNG data to a NumPy array
                    image_array = np.frombuffer(image_data, dtype=np.uint8)
                    
                    # Decode the image
                    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    if img is not None:
                        print(f"✅ Screenshot captured using minicap")
                        return img
                
                # Cleanup minicap
                minicap_manager.stop_minicap(device_id)
        
        # Fallback to screencap if minicap fails
        print(f"⚠️ Minicap failed, falling back to screencap")
        result = subprocess.run([
            "adb", "-s", device_id, "exec-out", "screencap", "-p"
        ], stdout=subprocess.PIPE, check=True)
        image_data = result.stdout

        # Convert binary PNG data to a NumPy array
        image_array = np.frombuffer(image_data, dtype=np.uint8)

        # Decode the image
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if img is None:
            raise Exception("Failed to decode screenshot")
        return img
    except subprocess.CalledProcessError as e:
        raise Exception(f"ADB screenshot failed: {e}")
    except Exception as e:
        raise Exception(f"Screenshot error: {e}")

def mouse_callback(event, x, y, flags, param):
    global rectangles, slot_index
    if event == cv2.EVENT_LBUTTONDOWN:
        rectangles.append([(x, y)])
    elif event == cv2.EVENT_LBUTTONUP:
        rectangles[-1].append((x, y))
        print(f"Slot {slot_index} drawn: {rectangles[-1]}")
        slot_index += 1

def main():
    if len(sys.argv) != 2:
        print("Usage: python picker.py <game_name>")
        print("Example: python picker.py umamusume")
        sys.exit(1)
    
    game_name = sys.argv[1]
    
    # Get project root and ensure games directory exists
    project_root = Path(__file__).parent.parent
    games_dir = project_root / "games" / game_name
    
    if not games_dir.exists():
        print(f"❌ Game directory not found: {games_dir}")
        print("Available games:")
        for item in (project_root / "games").iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                print(f"   • {item.name}")
        sys.exit(1)
    
    print(f"🎮 Launching picker for game: {game_name}")
    
    try:
        img = get_screenshot()
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    clone = img.copy()

    cv2.namedWindow("Draw Slots (Press Enter When Done)")
    cv2.setMouseCallback("Draw Slots (Press Enter When Done)", mouse_callback)

    print("📝 Instructions:")
    print("   • Click and drag to draw slots")
    print("   • Press Enter when finished")
    print("   • Press ESC to cancel")

    while True:
        temp = clone.copy()
        for i, box in enumerate(rectangles):
            if len(box) == 2:
                x1, y1 = box[0]
                x2, y2 = box[1]
                cv2.rectangle(temp, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Add slot number label
                cv2.putText(temp, f"Slot {i+1}", (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Draw Slots (Press Enter When Done)", temp)
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter
            break
        elif key == 27:  # ESC
            print("❌ Cancelled by user")
            cv2.destroyAllWindows()
            sys.exit(0)

    cv2.destroyAllWindows()

    if not rectangles:
        print("❌ No slots were drawn")
        sys.exit(1)

    # Convert to JSON format with relative coordinates
    height, width = img.shape[:2]
    config_data = {
        "slots": {},
        "screen_resolution": {
            "width": width,
            "height": height
        },
        "metadata": {
            "game": game_name,
            "total_slots": len(rectangles),
            "coordinate_format": "relative"
        }
    }

    for i, box in enumerate(rectangles):
        if len(box) == 2:
            x1, y1 = box[0]
            x2, y2 = box[1]
            x, y = min(x1, x2), min(y1, y2)
            w, h = abs(x2 - x1), abs(y2 - y1)
            
            # Calculate relative coordinates
            rel_x = x / width
            rel_y = y / height
            rel_w = w / width
            rel_h = h / height
            
            config_data["slots"][f"slot_{i+1}"] = {
                "x": round(rel_x, 4),
                "y": round(rel_y, 4),
                "width": round(rel_w, 4),
                "height": round(rel_h, 4),
                "absolute": {
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h
                }
            }

    # Save to games/<game_name>/config.json
    config_path = games_dir / "config.json"
    
    # If config.json already exists, try to preserve other settings
    existing_config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
            print(f"📄 Found existing config.json, preserving other settings")
        except Exception as e:
            print(f"⚠️ Could not read existing config: {e}")
    
    # Merge with existing config, slots section will be overwritten
    final_config = {**existing_config, **config_data}
    
    try:
        with open(config_path, 'w') as f:
            json.dump(final_config, f, indent=2)
        
        print(f"✅ Config saved to: {config_path}")
        print(f"📊 Summary:")
        print(f"   • Game: {game_name}")
        print(f"   • Slots defined: {len(rectangles)}")
        print(f"   • Screen resolution: {width}x{height}")
        print(f"   • Format: JSON with relative coordinates")
        
    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()