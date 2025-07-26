"""
Macro Executor for running automation macros on devices
"""

import subprocess
import os
import time
from typing import Optional
from pathlib import Path


class MacroExecutor:
    """Executes macros on devices with configurable parameters"""
    
    def __init__(self, speed_multiplier: float = 1.0, inter_macro_delay: float = 0.0, verbose: bool = False):
        self.speed_multiplier = speed_multiplier
        self.inter_macro_delay = inter_macro_delay
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        
        if self.verbose:
            print(f"🔧 MacroExecutor initialized:")
            print(f"   • Speed multiplier: {self.speed_multiplier}x")
            print(f"   • Inter-macro delay: {self.inter_macro_delay}s")
            print(f"   • Project root: {self.project_root}")
            print(f"   • macro.py path: {self.project_root / 'core' / 'macro.py'}")
    
    def execute_macro(self, device_id: str, macro_path: str, width: int = 540, height: int = 960, 
                     timeout: int = 300) -> bool:
        """Execute a macro file on the specified device"""
        try:
            # Resolve macro path relative to project root
            if not os.path.isabs(macro_path):
                macro_path = self.project_root / macro_path
            
            if not os.path.exists(macro_path):
                print(f"❌ Macro file not found: {macro_path}")
                return False
            
            # Check if macro.py exists
            macro_script = self.project_root / 'core' / 'macro.py'
            if not macro_script.exists():
                print(f"❌ macro.py script not found: {macro_script}")
                return False
            
            # Build command for macro execution
            cmd = [
                'python', str(macro_script), str(macro_path),
                '--width', str(width), 
                '--height', str(height),
                '--device', device_id,
                '--speed', str(self.speed_multiplier),
                '--skip-adb-check'  # Skip ADB check since framework handles it
            ]
            
            # Set environment variable for ADB device
            env = os.environ.copy()
            env['ADB_DEVICE_ID'] = device_id
            
            if self.verbose:
                print(f"🔧 Executing macro command: {' '.join(cmd)}")
            
            # Execute macro
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            
            if result.returncode == 0:
                if self.verbose and result.stdout.strip():
                    print(f"✅ Macro output: {result.stdout.strip()}")
                
                # Add inter-macro delay
                if self.inter_macro_delay > 0:
                    time.sleep(self.inter_macro_delay)
                return True
            else:
                print(f"❌ Macro execution failed (return code: {result.returncode})")
                print(f"   Macro file: {macro_path}")
                if self.verbose:
                    print(f"   Command: {' '.join(cmd)}")
                
                if result.stdout.strip():
                    print(f"   Stdout: {result.stdout.strip()}")
                if result.stderr.strip():
                    print(f"   Stderr: {result.stderr.strip()}")
                
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Macro execution timed out: {macro_path}")
            print(f"   Timeout: {timeout} seconds")
            if self.verbose and 'cmd' in locals():
                print(f"   Command: {' '.join(cmd)}")
            return False
        except Exception as e:
            print(f"❌ Error executing macro: {e}")
            print(f"   Macro file: {macro_path}")
            if self.verbose and 'cmd' in locals():
                print(f"   Command: {' '.join(cmd)}")
            return False
    
    def set_speed_multiplier(self, multiplier: float):
        """Update the speed multiplier for macro execution"""
        self.speed_multiplier = multiplier
    
    def set_inter_macro_delay(self, delay: float):
        """Update the delay between macro executions"""
        self.inter_macro_delay = delay
    
    def get_macro_path(self, game_name: str, macro_name: str) -> Optional[Path]:
        """Get the full path to a game-specific macro file"""
        # Try game-specific macro first
        game_macro_path = self.project_root / "games" / game_name / "macros" / f"{macro_name}.record"
        if game_macro_path.exists():
            return game_macro_path
        
        # Fall back to global macro directory
        global_macro_path = self.project_root / "macros" / f"{macro_name}.record"
        if global_macro_path.exists():
            return global_macro_path
        
        # Legacy support - check old macro directory structure
        legacy_macro_path = self.project_root / "macro" / f"{macro_name}.record"
        if legacy_macro_path.exists():
            return legacy_macro_path
        
        return None
    
    def execute_game_macro(self, device_id: str, game_name: str, macro_name: str, 
                          width: int = 540, height: int = 960, timeout: int = 300) -> bool:
        """Execute a game-specific macro"""
        print(f"🔍 Looking for macro '{macro_name}' for game '{game_name}'")
        
        macro_path = self.get_macro_path(game_name, macro_name)
        
        if macro_path is None:
            print(f"❌ Macro '{macro_name}' not found for game '{game_name}'")
            print(f"   Searched locations:")
            print(f"   • games/{game_name}/macros/{macro_name}.record")
            print(f"   • macros/{macro_name}.record")
            print(f"   • macro/{macro_name}.record (legacy)")
            return False
        
        print(f"✅ Found macro at: {macro_path}")
        return self.execute_macro(device_id, str(macro_path), width, height, timeout)
    
    def list_available_macros(self, game_name: str) -> list:
        """List all available macros for a game"""
        macros = []
        
        # Check game-specific macros
        game_macro_dir = self.project_root / "games" / game_name / "macros"
        if game_macro_dir.exists():
            for file in game_macro_dir.glob("*.record"):
                macros.append(file.stem)
        
        # Check global macros
        global_macro_dir = self.project_root / "macros"
        if global_macro_dir.exists():
            for file in global_macro_dir.glob("*.record"):
                if file.stem not in macros:  # Avoid duplicates
                    macros.append(file.stem)
        
        # Check legacy macros
        legacy_macro_dir = self.project_root / "macro"
        if legacy_macro_dir.exists():
            for file in legacy_macro_dir.glob("*.record"):
                if file.stem not in macros:  # Avoid duplicates
                    macros.append(file.stem)
        
        return sorted(macros) 