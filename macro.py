#!/usr/bin/env python3
"""
LDPlayer Macro to ADB Executor
Translates and executes LDPlayer operation files (.record) as ADB shell input commands
"""

import json
import sys
import argparse
import time
import subprocess
from typing import List, Dict, Any

class MacroToADBExecutor:
    def __init__(self, resolution_width=1920, resolution_height=1080, dry_run=False, device_id=None, speed_multiplier=1.0):
        """
        Initialize the executor with screen resolution parameters
        
        Args:
            resolution_width: Target device width (default: 1920 for 1080p)
            resolution_height: Target device height (default: 1080 for 1080p)
            dry_run: If True, print commands instead of executing them
            device_id: ADB device ID for targeting specific device (optional)
            speed_multiplier: Speed multiplier for macro execution (1.0 = normal, 2.0 = 2x slower)
        """
        self.resolution_width = resolution_width
        self.resolution_height = resolution_height
        self.dry_run = dry_run
        self.device_id = device_id
        self.speed_multiplier = speed_multiplier
        
        # These will be set after analyzing the coordinate range
        self.scale_x = None
        self.scale_y = None
        self.coord_ranges = None
        
        # Scancode to Android keycode mapping (common ones)
        self.scancode_to_keycode = {
            28: 66,   # Enter
            1: 4,     # ESC -> Back
            14: 67,   # Backspace
            57: 62,   # Space
            15: 61,   # Tab
            72: 19,   # Up arrow
            80: 20,   # Down arrow
            75: 21,   # Left arrow
            77: 22,   # Right arrow
            # Add more mappings as needed
        }
        
        self.active_touches = {}  # Track active touch points for swipe detection
    
    def build_adb_command(self, adb_args):
        """
        Build ADB command with device specification if provided
        
        Args:
            adb_args: List of ADB arguments (e.g., ['shell', 'input', 'tap', '100', '200'])
            
        Returns:
            Complete command string with device specification if needed
        """
        if self.device_id:
            cmd_parts = ['adb', '-s', self.device_id] + adb_args
        else:
            cmd_parts = ['adb'] + adb_args
        
        return ' '.join(cmd_parts)
    
    def analyze_coordinates(self, operations: List[Dict[str, Any]]):
        """Analyze coordinate ranges from the macro file to determine LDPlayer's coordinate system"""
        print("Analyzing LDPlayer coordinate system...")
        
        x_coords = []
        y_coords = []
        
        for operation in operations:
            if operation.get('operationId') == 'PutMultiTouch':
                points = operation.get('points', [])
                for point in points:
                    x = point.get('x')
                    y = point.get('y')
                    if x is not None and y is not None:
                        x_coords.append(x)
                        y_coords.append(y)
        
        if not x_coords or not y_coords:
            print("Warning: No coordinates found in macro file!")
            # Use discovered LDPlayer coordinate system (based on 540x960 → 19160x10760)
            ldplayer_width = 19200  # Rounded up from 19160
            ldplayer_height = 10800  # Rounded up from 10760
            self.scale_x = self.resolution_width / ldplayer_width
            self.scale_y = self.resolution_height / ldplayer_height
            return
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # Based on the pull2.record analysis, we know LDPlayer uses approximately 19200x10800 coordinates
        # where (19160, 10760) maps to bottom right of 540x960 screen
        
        # Use the known LDPlayer coordinate system
        ldplayer_width = 19200
        ldplayer_height = 10800
        
        # Calculate independent scale factors for X and Y
        self.scale_x = self.resolution_width / ldplayer_width
        self.scale_y = self.resolution_height / ldplayer_height
        
        # Store coordinate ranges for conversion (use full LDPlayer coordinate space)
        self.coord_ranges = {
            'min_x': 0,
            'max_x': ldplayer_width,
            'min_y': 0,
            'max_y': ldplayer_height,
            'width': ldplayer_width,
            'height': ldplayer_height
        }
        
        print(f"Detected coordinate ranges in macro:")
        print(f"  X: {min_x} to {max_x}")
        print(f"  Y: {min_y} to {max_y}")
        print(f"LDPlayer coordinate system: {ldplayer_width}x{ldplayer_height}")
        print(f"Target resolution: {self.resolution_width}x{self.resolution_height}")
        print(f"Scale factors: X={self.scale_x:.4f}, Y={self.scale_y:.4f}")
        print(f"Output will use full screen: {self.resolution_width}x{self.resolution_height}")
    
    def convert_coordinates(self, x: int, y: int) -> tuple:
        """Convert LDPlayer coordinates to device coordinates"""
        if self.scale_x is None or self.scale_y is None:
            raise ValueError("Coordinate system not analyzed yet. Call analyze_coordinates first.")
        
        # Scale LDPlayer coordinates directly to target resolution
        # LDPlayer uses 19200x10800 coordinate system
        device_x = int(x * self.scale_x)
        device_y = int(y * self.scale_y)
        
        # Ensure coordinates are within bounds
        device_x = max(0, min(device_x, self.resolution_width - 1))
        device_y = max(0, min(device_y, self.resolution_height - 1))
        
        return device_x, device_y
    
    def execute_command(self, command: str) -> bool:
        """Execute a single ADB command or sleep"""
        if self.dry_run:
            print(f"[DRY RUN] {command}")
            return True
        
        if command.startswith("sleep "):
            delay = float(command.split()[1])
            print(f"Waiting {delay:.3f} seconds...")
            time.sleep(delay)
            return True
        
        try:
            print(f"Executing: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print(f"Warning: Command failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr.strip()}")
                return False
            return True
        except subprocess.TimeoutExpired:
            print(f"Warning: Command timed out: {command}")
            return False
        except Exception as e:
            print(f"Error executing command: {e}")
            return False
    
    def execute_operations(self, operations: List[Dict[str, Any]]) -> bool:
        """Execute operations as ADB commands in real-time"""
        # First analyze the coordinate system
        self.analyze_coordinates(operations)
        
        last_timing = 0
        success_count = 0
        total_commands = 0
        
        print(f"Starting macro execution with {len(operations)} operations...")
        print(f"Target resolution: {self.resolution_width}x{self.resolution_height}")
        print(f"Speed multiplier: {self.speed_multiplier}x (slower is more stable for parallel execution)")
        
        for i, operation in enumerate(operations):
            timing = operation.get('timing', 0)
            operation_id = operation.get('operationId', '')
            
            # Add sleep for timing if needed (convert ms to seconds and apply speed multiplier)
            if timing > last_timing:
                delay = (timing - last_timing) / 1000.0 * self.speed_multiplier
                if delay > 0.01:  # Only add delay if more than 10ms
                    if self.execute_command(f"sleep {delay:.3f}"):
                        success_count += 1
                    total_commands += 1
            
            # Execute the operation
            commands = []
            if operation_id == "PutMultiTouch":
                commands = self._handle_multitouch(operation)
            elif operation_id == "ImeCommit":
                commands = self._handle_ime_commit(operation)
            elif operation_id == "ImeEnterAction":
                commands = self.handle_enter(operation)
            elif operation_id == "PutScancode":
                commands = self._handle_scancode(operation)
            
            # Execute all commands for this operation
            for command in commands:
                if self.execute_command(command):
                    success_count += 1
                total_commands += 1
            
            last_timing = timing
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{len(operations)} operations processed")
        
        print(f"\nMacro execution completed!")
        print(f"Total commands: {total_commands}")
        print(f"Successful: {success_count}")
        print(f"Failed: {total_commands - success_count}")
        
        return success_count == total_commands
    
    def _handle_multitouch(self, operation: Dict[str, Any]) -> List[str]:
        """Handle PutMultiTouch operations"""
        commands = []
        points = operation.get('points', [])
        
        for point in points:
            point_id = point.get('id')
            x = point.get('x')
            y = point.get('y')
            state = point.get('state')
            
            device_x, device_y = self.convert_coordinates(x, y)
            
            if state == 1:  # Touch down
                self.active_touches[point_id] = {'x': device_x, 'y': device_y, 'start_time': operation.get('timing', 0)}
            elif state == 0 and point_id in self.active_touches:  # Touch up
                start_pos = self.active_touches[point_id]
                start_x, start_y = start_pos['x'], start_pos['y']
                
                # Check if this is a tap or swipe
                distance = ((device_x - start_x) ** 2 + (device_y - start_y) ** 2) ** 0.5
                duration = operation.get('timing', 0) - start_pos['start_time']
                
                if distance < 10:  # Small movement, treat as tap
                    commands.append(self.build_adb_command(['shell', 'input', 'tap', str(start_x), str(start_y)]))
                else:  # Larger movement, treat as swipe
                    duration_ms = max(100, min(duration, 2000))  # Clamp duration between 100-2000ms
                    commands.append(self.build_adb_command(['shell', 'input', 'swipe', str(start_x), str(start_y), str(device_x), str(device_y), str(duration_ms)]))
                
                del self.active_touches[point_id]
        
        return commands
    
    def _handle_ime_commit(self, operation: Dict[str, Any]) -> List[str]:
        """Handle ImeCommit operations (text input)"""
        text = operation.get('text', '')
        if text:
            # Escape special characters for shell
            escaped_text = text.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            return [self.build_adb_command(['shell', 'input', 'text', f'"{escaped_text}"'])]
        return []
    
    def _handle_scancode(self, operation: Dict[str, Any]) -> List[str]:
        """Handle PutScancode operations (key presses)"""
        commands = []
        code = operation.get('code')
        down = operation.get('down', True)
        
        # Only process key down events to avoid duplicate key presses
        if down and code in self.scancode_to_keycode:
            android_keycode = self.scancode_to_keycode[code]
            commands.append(self.build_adb_command(['shell', 'input', 'keyevent', str(android_keycode)]))
        
        return commands
    
    def handle_enter(self, operation: Dict[str, Any]) -> List[str]:
        """Handle Enter key press operations"""
        commands = [self.build_adb_command(['shell', 'input', 'keyevent', '66'])]  # Enter key
        return commands
    
    def execute_file(self, filename: str) -> bool:
        """Execute a macro file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            operations = data.get('operations', [])
            return self.execute_operations(operations)
            
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            return False
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in '{filename}': {e}")
            return False
        except Exception as e:
            print(f"Error processing file: {e}")
            return False

def check_adb_connection():
    """Check if ADB is available and device is connected"""
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("Error: ADB is not available or not in PATH")
            return False
        
        lines = result.stdout.strip().split('\n')[1:]  # Skip header line
        connected_devices = [line for line in lines if line.strip() and not line.endswith('offline')]
        
        if not connected_devices:
            print("Error: No devices connected via ADB")
            print("Please ensure:")
            print("1. USB debugging is enabled on your device")
            print("2. Device is connected via USB or WiFi ADB")
            print("3. Device is authorized for debugging")
            return False
        
        print(f"Found {len(connected_devices)} connected device(s)")
        return True
        
    except subprocess.TimeoutExpired:
        print("Error: ADB command timed out")
        return False
    except FileNotFoundError:
        print("Error: ADB not found. Please install Android SDK platform tools")
        return False

def main():
    parser = argparse.ArgumentParser(description='Execute LDPlayer macro files as ADB shell commands')
    parser.add_argument('filename', help='Path to the LDPlayer .record file')
    parser.add_argument('-w', '--width', type=int, default=1920, help='Target device width (default: 1920)')
    parser.add_argument('--height', type=int, default=1080, help='Target device height (default: 1080)')
    parser.add_argument('--dry-run', action='store_true', help='Print commands instead of executing them')
    parser.add_argument('--skip-adb-check', action='store_true', help='Skip ADB connection check')
    parser.add_argument('--device', type=str, help='ADB device ID (e.g., emulator-5554)')
    parser.add_argument('--speed', type=float, default=1.0, help='Speed multiplier (1.0=normal, 2.0=2x slower, 0.5=2x faster)')
    
    args = parser.parse_args()
    
    # Check ADB connection unless skipped
    if not args.skip_adb_check and not args.dry_run:
        if not check_adb_connection():
            sys.exit(1)
    
    executor = MacroToADBExecutor(
        resolution_width=args.width,
        resolution_height=args.height,
        dry_run=args.dry_run,
        device_id=args.device,
        speed_multiplier=args.speed
    )
    
    try:
        success = executor.execute_file(args.filename)
        if success:
            print("Macro execution completed successfully!")
        else:
            print("Macro execution completed with errors.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nMacro execution interrupted by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
