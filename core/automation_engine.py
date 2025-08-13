"""
Automation Engine for Mobile Game Automation Framework
Handles the core automation logic and state management
"""

import time
import threading
import msvcrt
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from games.base_game import BaseGame
from core.device_manager import DeviceManager
from core.macro_executor import MacroExecutor
from core.image_detection import ImageDetector
from core.discord_notifier import DiscordNotifier
from core.minicap_stream_manager import MinicapStreamManager
from .action_types import ActionType, validate_action_config, create_typing_action


class AutomationInstance:
    """Individual automation instance for a specific device"""
    
    def __init__(self, device_id: str, instance_number: int, game: BaseGame, 
                 macro_executor: MacroExecutor, image_detector: ImageDetector,
                 device_manager: DeviceManager, discord_notifier: DiscordNotifier,
                 stream_manager: MinicapStreamManager = None, verbose: bool = False):
        self.device_id = device_id
        self.instance_number = instance_number
        self.game = game
        self.macro_executor = macro_executor
        self.image_detector = image_detector
        self.device_manager = device_manager
        self.discord_notifier = discord_notifier
        self.stream_manager = stream_manager
        self.verbose = verbose
        
        # Instance state
        self.running = True
        self.instance_data = game.create_instance_data(device_id, instance_number, verbose)
        
        # Timeout tracking
        self.current_state_start_time = time.time()
        self.timeout_thread = None
        
        # Action tracking within states
        self.current_action_index = 0
        
        if self.verbose:
            print(f"🔍 Instance #{instance_number}: Detailed initialization for device: {device_id}")
            print(f"   Game: {game.get_display_name()}")
            print(f"   Initial state: {self.instance_data['current_state']}")
            print(f"   Streaming enabled: {'✅' if stream_manager else '❌'}")
            # Log game-specific verbose configuration if available
            if hasattr(game, 'log_verbose_config'):
                game.log_verbose_config(device_id)
        else:
            print(f"🤖 Instance #{instance_number} initialized for device: {device_id}")
            if stream_manager:
                print(f"   🎥 Streaming enabled")
    
    def start_background_timeout_checker(self):
        """Start background timeout checker"""
        self.timeout_thread = threading.Thread(target=self._timeout_checker_loop, daemon=True)
        self.timeout_thread.start()
    
    def stop_background_timeout_checker(self):
        """Stop background timeout checker"""
        if self.timeout_thread and self.timeout_thread.is_alive():
            self.timeout_thread.join(timeout=1)
    
    def _timeout_checker_loop(self):
        """Background loop to check for timeouts"""
        print(f"🔍 Instance #{self.instance_number}: Timeout checker thread started")
        
        while self.running:
            try:
                if self.check_state_timeout():
                    print(f"🚨 Instance #{self.instance_number}: TIMEOUT detected! Restarting app...")
                    if self.handle_timeout():
                        print(f"✅ Instance #{self.instance_number}: Timeout recovery successful")
                    else:
                        print(f"❌ Instance #{self.instance_number}: Timeout recovery failed")
                        self.running = False
                        break
                
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"❌ Instance #{self.instance_number}: Error in timeout checker: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print(f"🔍 Instance #{self.instance_number}: Timeout checker thread stopped")
    
    def check_state_timeout(self) -> bool:
        """Check if current state has been running too long"""
        current_time = time.time()
        time_in_state = current_time - self.current_state_start_time
        
        # Get timeout for current state
        state_timeouts = self.game.get_state_timeouts()
        current_state = self.instance_data['current_state']
        base_timeout = state_timeouts.get(current_state, None)  # Default 4 minutes
        
        # If timeout is None or 0, this state has no timeout (runs indefinitely)
        if base_timeout is None or base_timeout <= 0:
            return False
        
        # Adjust timeout based on macro speed multiplier
        adjusted_timeout = base_timeout * self.macro_executor.speed_multiplier
        
        # Debug logging every 30 seconds
        if int(time_in_state) % 30 == 0 and time_in_state > 0:
            print(f"🔍 Instance #{self.instance_number}: Timeout check - State: {current_state}, Time: {time_in_state:.1f}s, Limit: {adjusted_timeout:.1f}s")
        
        if time_in_state > adjusted_timeout:
            print(f"⏰ Instance #{self.instance_number}: TIMEOUT! State '{current_state}' stuck for {time_in_state:.1f}s (limit: {adjusted_timeout:.1f}s)")
            return True
        return False
    
    def change_state(self, new_state: str):
        """Change to a new automation state"""
        old_state = self.instance_data['current_state']
        self.instance_data['current_state'] = new_state
        self.current_state_start_time = time.time()
        
        # Reset action index when changing states
        self.current_action_index = 0
        
        if self.verbose:
            print(f"🔄 Instance #{self.instance_number}: State transition: {old_state} → {new_state}")
        else:
            print(f"🔄 Instance #{self.instance_number}: {old_state} → {new_state}")
    
    def handle_timeout(self) -> bool:
        """Handle timeout by checking for timeout_state or restarting app"""
        try:
            current_state = self.instance_data['current_state']
            
            # Get automation states to check for timeout_state
            automation_states = self.game.get_automation_states()
            state_config = automation_states.get(current_state, {})
            timeout_state = state_config.get('timeout_state')
            
            if timeout_state:
                # Transition to timeout_state instead of restarting
                if self.verbose:
                    print(f"⏰ Instance #{self.instance_number}: Timeout occurred in state '{current_state}', transitioning to timeout_state: '{timeout_state}'")
                else:
                    print(f"⏰ Instance #{self.instance_number}: Timeout in '{current_state}' → '{timeout_state}'")
                
                self.change_state(timeout_state)
                return True
            else:
                # Default behavior: restart app
                if self.verbose:
                    print(f"🔧 Instance #{self.instance_number}: Attempting app restart due to timeout")
                
                # Restart the app
                if self.device_manager.restart_app(
                    self.device_id, 
                    self.game.get_app_package(), 
                    self.game.get_app_activity()
                ):
                    # Reset to initial state
                    initial_state = self.game.get_initial_state()
                    self.change_state(initial_state)
                    
                    # Force reset timeout timer (fix for bug where timeout doesn't reset after app restart)
                    self.current_state_start_time = time.time()
                    
                    # Reset action index and other instance data
                    self.current_action_index = 0
                    self.instance_data['cycle_count'] = 0
                    self.instance_data['detected_items'] = []
                    self.instance_data['account_id'] = None
                    
                    if self.verbose:
                        print(f"✅ Instance #{self.instance_number}: App restart successful, reset to state: {initial_state}")
                    
                    return True
                else:
                    if self.verbose:
                        print(f"❌ Instance #{self.instance_number}: App restart failed")
                    return False
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error handling timeout: {e}")
            return False
    
    def get_screenshot(self, save_to_file: bool = False):
        """Get screenshot for this device using streaming if available, otherwise file-based"""
        if self.verbose:
            print(f"📸 Instance #{self.instance_number}: Capturing screenshot")
        
        # Try streaming first if available
        if self.stream_manager:
            frame = self.stream_manager.get_latest_frame(self.device_id)
            if frame is not None:
                if self.verbose:
                    h, w = frame.shape[:2]
                    print(f"📸 Instance #{self.instance_number}: Streaming frame captured ({w}x{h})")
                return frame
            elif self.verbose:
                print(f"⚠️ Instance #{self.instance_number}: Streaming frame failed, falling back to file-based")
        
        # Fallback to file-based screenshot
        screenshot_bytes = self.device_manager.get_screenshot(self.device_id, save_to_file)
        if screenshot_bytes:
            screenshot = self.image_detector.bytes_to_image(screenshot_bytes)
            if self.verbose and screenshot is not None:
                h, w = screenshot.shape[:2]
                print(f"📸 Instance #{self.instance_number}: File-based screenshot captured ({w}x{h})")
            return screenshot
        elif self.verbose:
            print(f"❌ Instance #{self.instance_number}: Failed to capture screenshot")
        return None
    
    def execute_macro(self, macro_name: str) -> bool:
        """Execute a macro for this game"""
        if self.verbose:
            print(f"🎬 Instance #{self.instance_number}: Executing macro: {macro_name}")
        
        width, height = self.game.get_device_resolution()
        success = self.macro_executor.execute_game_macro(
            self.device_id, self.game.get_game_name(), macro_name, width, height
        )
        
        if self.verbose:
            if success:
                print(f"✅ Instance #{self.instance_number}: Macro '{macro_name}' executed successfully")
            else:
                print(f"❌ Instance #{self.instance_number}: Macro '{macro_name}' execution failed")
        
        return success
    
    def execute_tap(self, template_name: Optional[str] = None, offset_x: Optional[int] = None, offset_y: Optional[int] = None, coordinates: Optional[tuple[int, int]] = None, tap_times: Optional[int] = None, tap_delay: Optional[float] = None, screenshot: Optional[np.ndarray] = None) -> bool:
        """Execute a tap at the saved coordinates for a detected template, with optional offset from center, or at explicit coordinates"""
        
        tap_start_time = time.time()
        if self.verbose:
            print(f"👆 Instance #{self.instance_number}: Starting tap execution for '{template_name}'")
        
        # Use provided screenshot or get a new one
        if screenshot is None:
            screenshot = getattr(self, '_current_screenshot', None)
            if screenshot is None:
                screenshot = self.get_screenshot()
        
        if screenshot is None:
            if self.verbose:
                print(f"❌ Instance #{self.instance_number}: Failed to get screenshot for template detection")
            return False
        
        # If template_name is None, skip template detection and use coordinates directly
        if template_name is None:
            if coordinates is None:
                if self.verbose:
                    print(f"❌ Instance #{self.instance_number}: No template specified and no coordinates provided")
                return False
            
            x, y = coordinates
            # Apply offsets if specified
            if offset_x is not None:
                x += offset_x
            if offset_y is not None:
                y += offset_y
            
            if self.verbose:
                offset_info = ""
                if offset_x is not None or offset_y is not None:
                    offset_info = f" (with offset: x={offset_x or 0}, y={offset_y or 0})"
                print(f"👆 Instance #{self.instance_number}: Executing tap at coordinates ({x}, {y}) without template check{offset_info}")
            
            # Execute multiple taps if specified
            tap_count = tap_times or 1
            tap_delay_seconds = tap_delay or 0.1
            
            if self.verbose and tap_count > 1:
                print(f"👆 Instance #{self.instance_number}: Executing {tap_count} taps with {tap_delay_seconds}s delay")
            
            success = True
            for i in range(tap_count):
                if i > 0:  # Don't delay before first tap
                    time.sleep(tap_delay_seconds)
                
                tap_success = self.device_manager.tap(self.device_id, x, y)
                if not tap_success:
                    success = False
                    if self.verbose:
                        print(f"❌ Instance #{self.instance_number}: Tap {i+1}/{tap_count} failed")
                    break
                elif self.verbose and tap_count > 1:
                    print(f"✅ Instance #{self.instance_number}: Tap {i+1}/{tap_count} executed successfully")
            
            if self.verbose:
                if success:
                    print(f"✅ Instance #{self.instance_number}: All {tap_count} taps executed successfully")
                else:
                    print(f"❌ Instance #{self.instance_number}: Tap execution failed")
            
            tap_total_time = (time.time() - tap_start_time) * 1000
            if self.verbose:
                print(f"⏱️ Instance #{self.instance_number}: Total tap execution took {tap_total_time:.1f}ms")
            return success
        
        # Detect the template for validation
        template_detect_start = time.time()
        if not self.detect_template(screenshot, template_name):
            if self.verbose:
                print(f"❌ Instance #{self.instance_number}: Template '{template_name}' not found in screenshot")
            return False
        
        template_detect_time = (time.time() - template_detect_start) * 1000
        if self.verbose:
            print(f"⏱️ Instance #{self.instance_number}: Template detection for tap took {template_detect_time:.1f}ms")
        
        if self.verbose:
            print(f"✅ Instance #{self.instance_number}: Template '{template_name}' found, proceeding with tap")
        
        # If explicit coordinates are provided, use them directly
        if coordinates is not None:
            x, y = coordinates
            
            # Apply offsets if specified
            if offset_x is not None:
                x += offset_x
            if offset_y is not None:
                y += offset_y
            
            if self.verbose:
                offset_info = ""
                if offset_x is not None or offset_y is not None:
                    offset_info = f" (with offset: x={offset_x or 0}, y={offset_y or 0})"
                print(f"👆 Instance #{self.instance_number}: Executing tap at explicit coordinates ({x}, {y}){offset_info}")
            
            # Execute multiple taps if specified
            tap_count = tap_times or 1
            tap_delay_seconds = tap_delay or 0.1
            
            if self.verbose and tap_count > 1:
                print(f"👆 Instance #{self.instance_number}: Executing {tap_count} taps with {tap_delay_seconds}s delay")
            
            success = True
            for i in range(tap_count):
                if i > 0:  # Don't delay before first tap
                    time.sleep(tap_delay_seconds)
                
                tap_success = self.device_manager.tap(self.device_id, x, y)
                if not tap_success:
                    success = False
                    if self.verbose:
                        print(f"❌ Instance #{self.instance_number}: Tap {i+1}/{tap_count} failed")
                    break
                elif self.verbose and tap_count > 1:
                    print(f"✅ Instance #{self.instance_number}: Tap {i+1}/{tap_count} executed successfully")
            
            if self.verbose:
                if success:
                    print(f"✅ Instance #{self.instance_number}: All {tap_count} taps executed successfully")
                else:
                    print(f"❌ Instance #{self.instance_number}: Tap execution failed")
            
            tap_total_time = (time.time() - tap_start_time) * 1000
            if self.verbose:
                print(f"⏱️ Instance #{self.instance_number}: Total tap execution took {tap_total_time:.1f}ms")
            return success
        
        # Otherwise, use template matching to find coordinates
        coordinates = self.image_detector.get_detected_coordinates(template_name)
        
        if coordinates is None:
            if self.verbose:
                print(f"❌ Instance #{self.instance_number}: No coordinates found for template '{template_name}'")
            return False
        
        x, y = coordinates
        
        # Apply offsets if specified
        if offset_x is not None:
            x += offset_x
        if offset_y is not None:
            y += offset_y
        
        if self.verbose:
            offset_info = ""
            if offset_x is not None or offset_y is not None:
                offset_info = f" (with offset: x={offset_x or 0}, y={offset_y or 0})"
            print(f"👆 Instance #{self.instance_number}: Executing tap at ({x}, {y}) for template '{template_name}'{offset_info}")
        
        # Execute multiple taps if specified
        tap_count = tap_times or 1
        tap_delay_seconds = tap_delay or 0.1
        
        if self.verbose and tap_count > 1:
            print(f"👆 Instance #{self.instance_number}: Executing {tap_count} taps with {tap_delay_seconds}s delay")
        
        success = True
        for i in range(tap_count):
            if i > 0:  # Don't delay before first tap
                time.sleep(tap_delay_seconds)
            
            tap_success = self.device_manager.tap(self.device_id, x, y)
            if not tap_success:
                success = False
                if self.verbose:
                    print(f"❌ Instance #{self.instance_number}: Tap {i+1}/{tap_count} failed")
                break
            elif self.verbose and tap_count > 1:
                print(f"✅ Instance #{self.instance_number}: Tap {i+1}/{tap_count} executed successfully")
        
        if self.verbose:
            if success:
                print(f"✅ Instance #{self.instance_number}: All {tap_count} taps executed successfully")
            else:
                print(f"❌ Instance #{self.instance_number}: Tap execution failed")
        
        tap_total_time = (time.time() - tap_start_time) * 1000
        if self.verbose:
            print(f"⏱️ Instance #{self.instance_number}: Total tap execution took {tap_total_time:.1f}ms")
        return success
    
    def execute_action(self, action_config: Dict[str, Any], screenshot: Optional[np.ndarray] = None) -> bool:
        """Execute an action based on the action configuration"""
        # Validate action configuration
        validation_errors = validate_action_config(action_config)
        if validation_errors:
            print(f"❌ Instance #{self.instance_number}: Invalid action configuration:")
            for error in validation_errors:
                print(f"   • {error}")
            return False
        
        action_type = action_config.get('type', 'macro')
        
        if action_type == ActionType.MACRO:
            macro_name = action_config.get('name')
            timeout = action_config.get('timeout')
            speed_multiplier = action_config.get('speed_multiplier')
            
            if self.verbose:
                print(f"🎬 Instance #{self.instance_number}: Executing macro '{macro_name}'")
                if timeout:
                    print(f"   ⏱️ Timeout: {timeout}s")
                if speed_multiplier:
                    print(f"   ⚡ Speed multiplier: {speed_multiplier}x")
            
            return self.execute_macro(macro_name)
            
        elif action_type == ActionType.TAP:
            tap_action_start = time.time()
            if self.verbose:
                print(f"👆 Instance #{self.instance_number}: Starting TAP action execution")
            
            template_name = action_config.get('template')
            coordinates = action_config.get('coordinates')
            delay_before = action_config.get('delay_before')
            delay_after = action_config.get('delay_after')
            likelihood = action_config.get('likelihood')
            timeout = action_config.get('timeout')
            offset_x = action_config.get('offset_x')
            offset_y = action_config.get('offset_y')
            tap_times = action_config.get('tap_times')
            tap_delay = action_config.get('tap_delay')
            
            if self.verbose:
                print(f"👆 Instance #{self.instance_number}: Executing tap action")
                print(f"   🎯 Template: {template_name}")
                if coordinates:
                    print(f"   📍 Coordinates: {coordinates}")
                if delay_before:
                    print(f"   ⏱️ Delay before: {delay_before}s")
                if delay_after:
                    print(f"   ⏱️ Delay after: {delay_after}s")
                if likelihood:
                    print(f"   🎯 Likelihood: {likelihood}")
                if timeout:
                    print(f"   ⏱️ Timeout: {timeout}s")
                if offset_x is not None or offset_y is not None:
                    print(f"   📍 Offset: x={offset_x or 0}, y={offset_y or 0}")
                if tap_times and tap_times > 1:
                    print(f"   👆 Tap times: {tap_times}")
                if tap_delay:
                    print(f"   ⏱️ Tap delay: {tap_delay}s")
            
            # Apply delays if specified
            if delay_before:
                delay_before_start = time.time()
                if self.verbose:
                    print(f"⏱️ Instance #{self.instance_number}: Applying delay_before: {delay_before}s")
                time.sleep(delay_before)
                delay_before_time = (time.time() - delay_before_start) * 1000
                if self.verbose:
                    print(f"⏱️ Instance #{self.instance_number}: delay_before took {delay_before_time:.1f}ms")
            
            # Execute tap with timeout handling
            tap_exec_start = time.time()
            if timeout is not None:
                if self.verbose:
                    print(f"⏱️ Instance #{self.instance_number}: Executing tap with timeout: {timeout}s")
                # Try to execute tap with timeout
                tap_start_time = time.time()
                while time.time() - tap_start_time < timeout:
                    # Get fresh screenshot for each retry attempt
                    fresh_screenshot = self.get_screenshot()
                    if fresh_screenshot is None:
                        if self.verbose:
                            print(f"❌ Instance #{self.instance_number}: Failed to get fresh screenshot for retry")
                        # Brief delay before retry to avoid hammering
                        time.sleep(0.1)
                        continue
                    
                    # Execute tap with custom likelihood if specified
                    if likelihood is not None:
                        success = self.execute_tap_with_likelihood(template_name, likelihood, offset_x, offset_y, coordinates, tap_times, tap_delay, fresh_screenshot)
                    else:
                        success = self.execute_tap(template_name, offset_x, offset_y, coordinates, tap_times, tap_delay, fresh_screenshot)
                    
                    if success:
                        break
                    
                    # No delay - retry immediately for faster response
                    # time.sleep(0.5)  # Removed delay for faster retry
                else:
                    # Tap timeout reached, log and continue (don't fail the action)
                    if self.verbose:
                        print(f"⏱️ Instance #{self.instance_number}: Tap action '{template_name}' timed out after {timeout}s, continuing to next action")
                    success = True  # Return True to continue to next action
            else:
                # Execute tap without timeout (original behavior)
                if likelihood is not None:
                    success = self.execute_tap_with_likelihood(template_name, likelihood, offset_x, offset_y, coordinates, tap_times, tap_delay, screenshot)
                else:
                    success = self.execute_tap(template_name, offset_x, offset_y, coordinates, tap_times, tap_delay, screenshot)
            
            tap_exec_time = (time.time() - tap_exec_start) * 1000
            if self.verbose:
                print(f"⏱️ Instance #{self.instance_number}: Tap execution took {tap_exec_time:.1f}ms")
            
            if delay_after:
                delay_after_start = time.time()
                if self.verbose:
                    print(f"⏱️ Instance #{self.instance_number}: Applying delay_after: {delay_after}s")
                time.sleep(delay_after)
                delay_after_time = (time.time() - delay_after_start) * 1000
                if self.verbose:
                    print(f"⏱️ Instance #{self.instance_number}: delay_after took {delay_after_time:.1f}ms")
            
            tap_action_total = (time.time() - tap_action_start) * 1000
            if self.verbose:
                print(f"⏱️ Instance #{self.instance_number}: Total TAP action took {tap_action_total:.1f}ms")
            
            return success
            
        elif action_type == ActionType.SWIPE:
            start_template = action_config.get('start_template')
            end_template = action_config.get('end_template')
            start_coordinates = action_config.get('start_coordinates')
            end_coordinates = action_config.get('end_coordinates')
            duration = action_config.get('duration', 1000)  # Default 1 second
            delay_before = action_config.get('delay_before')
            delay_after = action_config.get('delay_after')
            start_likelihood = action_config.get('start_likelihood')
            end_likelihood = action_config.get('end_likelihood')
            
            if self.verbose:
                print(f"👆 Instance #{self.instance_number}: Executing swipe action")
                if start_template:
                    print(f"   🎯 Start template: {start_template}")
                if end_template:
                    print(f"   🎯 End template: {end_template}")
                if start_coordinates:
                    print(f"   📍 Start coordinates: {start_coordinates}")
                if end_coordinates:
                    print(f"   📍 End coordinates: {end_coordinates}")
                print(f"   ⏱️ Duration: {duration}ms")
                if start_likelihood:
                    print(f"   🎯 Start likelihood: {start_likelihood}")
                if end_likelihood:
                    print(f"   🎯 End likelihood: {end_likelihood}")
            
            # Apply delays if specified
            if delay_before:
                time.sleep(delay_before)
            
            # Execute swipe (this would need to be implemented in device_manager)
            # Extract coordinates from tuples or use defaults
            if start_coordinates:
                start_x, start_y = start_coordinates
            else:
                start_x, start_y = 0, 0
                
            if end_coordinates:
                end_x, end_y = end_coordinates
            else:
                end_x, end_y = 100, 100
            
            success = self.device_manager.swipe(
                self.device_id, 
                start_x, start_y, end_x, end_y, duration
            )
            
            if delay_after:
                time.sleep(delay_after)
            
            return success
            
        elif action_type == ActionType.WAIT:
            duration = action_config.get('duration')
            condition = action_config.get('condition')
            timeout = action_config.get('timeout')
            likelihood = action_config.get('likelihood')
            
            if self.verbose:
                print(f"⏱️ Instance #{self.instance_number}: Executing wait action")
                print(f"   ⏱️ Duration: {duration}s")
                if condition:
                    print(f"   🎯 Condition: {condition}")
                if timeout:
                    print(f"   ⏱️ Timeout: {timeout}s")
                if likelihood:
                    print(f"   🎯 Likelihood: {likelihood}")
            
            if condition:
                # Wait for specific template
                start_time = time.time()
                while time.time() - start_time < (timeout or 60):
                    # Use provided screenshot or get a new one
                    check_screenshot = screenshot if screenshot is not None else self.get_screenshot()
                    if check_screenshot is not None:
                        if likelihood is not None:
                            detected = self.detect_template_with_likelihood(check_screenshot, condition, likelihood)
                        else:
                            detected = self.detect_template(check_screenshot, condition)
                        if detected:
                            return True
                    # time.sleep(0.5)
                return False
            else:
                # Simple wait
                time.sleep(duration)
                return True
                
        elif action_type == ActionType.SCREENSHOT:
            save_path = action_config.get('save_path')
            process_items = action_config.get('process_items', False)
            
            if self.verbose:
                print(f"📸 Instance #{self.instance_number}: Executing screenshot action")
                if save_path:
                    print(f"   💾 Save path: {save_path}")
                print(f"   🔍 Process items: {process_items}")
            
            # Use provided screenshot or get a new one
            action_screenshot = screenshot if screenshot is not None else self.get_screenshot()
            if action_screenshot is not None:
                if save_path:
                    # Save screenshot (implementation needed)
                    pass
                if process_items:
                    self.process_screenshot_for_items(action_screenshot)
                return True
            return False
            
        elif action_type == ActionType.TYPING:
            text = action_config.get('text')
            clear_first = action_config.get('clear_first', False)
            delay_before = action_config.get('delay_before')
            delay_after = action_config.get('delay_after')
            press_enter = action_config.get('press_enter', False)
            
            if self.verbose:
                print(f"⌨️ Instance #{self.instance_number}: Executing typing action")
                print(f"   📝 Text: '{text}'")
                print(f"   🧹 Clear first: {clear_first}")
                print(f"   ⏱️ Delay before: {delay_before}s")
                print(f"   ⏱️ Delay after: {delay_after}s")
                print(f"   ↵ Press Enter: {press_enter}")
            
            # Apply delay before if specified
            if delay_before:
                time.sleep(delay_before)
            
            # Clear existing text if requested
            if clear_first:
                if self.verbose:
                    print(f"🧹 Instance #{self.instance_number}: Clearing existing text")
                # Select all text (Ctrl+A equivalent)
                self.device_manager.send_key(self.device_id, "KEYCODE_CTRL_LEFT")
                time.sleep(0.1)
                self.device_manager.send_key(self.device_id, "KEYCODE_A")
                time.sleep(0.1)
                # Delete selected text
                self.device_manager.send_key(self.device_id, "KEYCODE_DEL")
                time.sleep(0.2)
            
            # Type the text
            if self.verbose:
                print(f"⌨️ Instance #{self.instance_number}: Typing text: '{text}'")
            
            success = self.device_manager.input_text(self.device_id, text)
            
            if not success:
                print(f"❌ Instance #{self.instance_number}: Failed to type text")
                return False
            
            # Press Enter if requested
            if press_enter:
                if self.verbose:
                    print(f"↵ Instance #{self.instance_number}: Pressing Enter after typing")
                time.sleep(0.2)  # Brief pause before Enter
                self.device_manager.send_key(self.device_id, "KEYCODE_ENTER")
            
            # Apply delay after if specified
            if delay_after:
                time.sleep(delay_after)
            
            return True
            
        elif action_type == ActionType.CONDITIONAL:
            condition = action_config.get('condition')
            if_true = action_config.get('if_true', [])
            if_false = action_config.get('if_false', [])  # Default to empty list instead of None
            timeout = action_config.get('timeout')
            likelihood = action_config.get('likelihood')
            if_true_state = action_config.get('if_true_state')
            if_false_state = action_config.get('if_false_state')
            
            if self.verbose:
                print(f"🔀 Instance #{self.instance_number}: Executing conditional action")
                print(f"   🎯 Condition: {condition}")
                print(f"   ✅ If true actions: {len(if_true)}")
                print(f"   ❌ If false actions: {len(if_false)}")
                if timeout:
                    print(f"   ⏱️ Timeout: {timeout}s")
                if likelihood:
                    print(f"   🎯 Likelihood: {likelihood}")
                if if_true_state:
                    print(f"   🎯 If true state: {if_true_state}")
                if if_false_state:
                    print(f"   🎯 If false state: {if_false_state}")
            
            # Check condition
            # Use provided screenshot or get a new one
            check_screenshot = screenshot if screenshot is not None else self.get_screenshot()
            if check_screenshot is not None:
                if likelihood is not None:
                    condition_met = self.detect_template_with_likelihood(check_screenshot, condition, likelihood)
                else:
                    condition_met = self.detect_template(check_screenshot, condition)
                
                actions_to_execute = if_true if condition_met else if_false
                target_state = if_true_state if condition_met else if_false_state
                
                if self.verbose:
                    print(f"   {'✅' if condition_met else '❌'} Condition '{condition}' {'met' if condition_met else 'not met'}")
                    print(f"   🎬 Executing {len(actions_to_execute)} action(s)")
                    if target_state:
                        print(f"   🎯 Will jump to state: {target_state}")
                
                # Execute actions with timeout handling
                start_time = time.time()
                successful_actions = 0
                failed_actions = 0
                
                for i, action in enumerate(actions_to_execute):
                    # Check timeout before executing each action
                    if timeout and time.time() - start_time > timeout:
                        if self.verbose:
                            print(f"   ⏱️ Instance #{self.instance_number}: Conditional action timeout reached ({timeout}s)")
                        break
                    
                    if self.verbose:
                        print(f"   🎬 Instance #{self.instance_number}: Executing conditional action {i + 1}/{len(actions_to_execute)}")
                    
                    # Retry the action until it succeeds or timeout is reached
                    action_success = False
                    action_start_time = time.time()
                    
                    while not action_success:
                        # Check if we've exceeded the overall timeout
                        if timeout and time.time() - start_time > timeout:
                            if self.verbose:
                                print(f"   ⏱️ Instance #{self.instance_number}: Conditional action timeout reached ({timeout}s) during retry")
                            break
                        
                        # Check if this individual action has its own timeout
                        action_timeout = action.get('timeout')
                        if action_timeout and time.time() - action_start_time > action_timeout:
                            if self.verbose:
                                print(f"   ⏱️ Instance #{self.instance_number}: Action {i + 1} timeout reached ({action_timeout}s)")
                            break
                        
                        # Get fresh screenshot for each action attempt
                        fresh_screenshot = self.get_screenshot()
                        if fresh_screenshot is None:
                            if self.verbose:
                                print(f"   ❌ Instance #{self.instance_number}: Failed to get fresh screenshot for action {i + 1}")
                            # Brief delay before retry to avoid hammering
                            time.sleep(0.1)
                            continue
                        
                        action_success = self.execute_action(action, fresh_screenshot)
                        if action_success:
                            successful_actions += 1
                            if self.verbose:
                                print(f"   ✅ Instance #{self.instance_number}: Conditional action {i + 1} succeeded")
                        else:
                            if self.verbose:
                                print(f"   ❌ Instance #{self.instance_number}: Conditional action {i + 1} failed, retrying...")
                            # Brief delay before retry to avoid hammering
                            time.sleep(0.1)
                    
                    if not action_success:
                        failed_actions += 1
                        if self.verbose:
                            print(f"   ❌ Instance #{self.instance_number}: Conditional action {i + 1} failed after all retries")
                    
                    action_exec_time = (time.time() - action_start_time) * 1000
                    if self.verbose:
                        print(f"⏱️ Instance #{self.instance_number}: Conditional action {i + 1} took {action_exec_time:.1f}ms")
                
                # Log summary
                if self.verbose:
                    print(f"   📊 Instance #{self.instance_number}: Conditional action summary - {successful_actions} succeeded, {failed_actions} failed")
                
                # Set action_success based on whether at least one action succeeded
                action_success = successful_actions > 0 or len(actions_to_execute) == 0
                
                # Handle state jumping if specified
                if target_state:
                    if self.verbose:
                        print(f"   🎯 Instance #{self.instance_number}: Jumping to state: {target_state}")
                    self.change_state(target_state)
                    return True  # Return True since state change was successful
                
                # Return True if at least one action succeeded, or if no actions were executed
                return action_success
            else:
                print(f"❌ Instance #{self.instance_number}: Failed to get screenshot for conditional")
                return False
                
        elif action_type == ActionType.LOOP:
            actions = action_config.get('actions', [])
            max_iterations = action_config.get('max_iterations')
            condition = action_config.get('condition')
            timeout = action_config.get('timeout')
            condition_likelihood = action_config.get('condition_likelihood')
            use_single_screenshot = action_config.get('use_single_screenshot', False)
            
            if self.verbose:
                print(f"🔄 Instance #{self.instance_number}: Executing loop action")
                print(f"   🎬 Actions: {len(actions)}")
                if max_iterations:
                    print(f"   🔢 Max iterations: {max_iterations}")
                if condition:
                    print(f"   🎯 Exit condition: {condition}")
                if timeout:
                    print(f"   ⏱️ Timeout: {timeout}s")
                if condition_likelihood:
                    print(f"   🎯 Condition likelihood: {condition_likelihood}")
                if use_single_screenshot:
                    print(f"   📸 Using single screenshot per iteration")
            
            iteration = 0
            start_time = time.time()
            
            while True:
                # Check max iterations
                if max_iterations and iteration >= max_iterations:
                    if self.verbose:
                        print(f"   🔢 Instance #{self.instance_number}: Reached max iterations ({max_iterations})")
                    break
                
                # Check timeout
                if timeout and time.time() - start_time > timeout:
                    if self.verbose:
                        print(f"   ⏱️ Instance #{self.instance_number}: Loop timeout reached ({timeout}s), exiting loop")
                    break
                elif timeout and self.verbose:
                    # Debug logging to show timeout progress
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed
                    print(f"   ⏱️ Instance #{self.instance_number}: Loop timeout check - {elapsed:.1f}s elapsed, {remaining:.1f}s remaining")
                
                # Take screenshot for this iteration if using single screenshot mode
                loop_screenshot = None
                if use_single_screenshot:
                    if self.verbose:
                        print(f"   📸 Instance #{self.instance_number}: Taking screenshot for iteration {iteration + 1}")
                    loop_screenshot = self.get_screenshot()
                    if loop_screenshot is None:
                        print(f"❌ Instance #{self.instance_number}: Failed to get screenshot for loop iteration {iteration + 1}")
                        return False
                
                # Check exit condition
                if condition:
                    # Use loop screenshot if available, otherwise get new screenshot
                    check_screenshot = loop_screenshot if use_single_screenshot else self.get_screenshot()
                    if check_screenshot is not None:
                        if condition_likelihood is not None:
                            exit_condition_met = self.detect_template_with_likelihood(check_screenshot, condition, condition_likelihood)
                        else:
                            exit_condition_met = self.detect_template(check_screenshot, condition)
                        
                        if exit_condition_met:
                            if self.verbose:
                                print(f"   ✅ Instance #{self.instance_number}: Exit condition '{condition}' met")
                            break
                        elif self.verbose:
                            print(f"   🔍 Instance #{self.instance_number}: Exit condition '{condition}' not met, continuing loop")
                    elif self.verbose:
                        print(f"   ❌ Instance #{self.instance_number}: Failed to get screenshot for exit condition check")
                
                # Execute loop actions
                if self.verbose:
                    print(f"   🔄 Instance #{self.instance_number}: Loop iteration {iteration + 1}")
                
                for action in actions:
                    # Check timeout before each action
                    if timeout and time.time() - start_time > timeout:
                        if self.verbose:
                            print(f"   ⏱️ Instance #{self.instance_number}: Loop timeout reached ({timeout}s) during action execution, exiting loop")
                        break  # Break out of the action loop and then the main loop
                    
                    # Execute action with single screenshot if requested
                    if use_single_screenshot and loop_screenshot is not None:
                        # Temporarily store the loop screenshot for this action execution
                        original_screenshot = getattr(self, '_current_screenshot', None)
                        self._current_screenshot = loop_screenshot
                        
                        try:
                            if not self.execute_action(action, loop_screenshot):
                                print(f"❌ Instance #{self.instance_number}: Failed to execute action in loop iteration {iteration + 1}")
                                return False
                        finally:
                            # Restore original screenshot behavior
                            if original_screenshot is not None:
                                self._current_screenshot = original_screenshot
                            else:
                                delattr(self, '_current_screenshot')
                    else:
                        # Normal action execution
                        if not self.execute_action(action, loop_screenshot):
                            print(f"❌ Instance #{self.instance_number}: Failed to execute action in loop iteration {iteration + 1}")
                            return False
                
                # Check if we broke out of the action loop due to timeout
                if timeout and time.time() - start_time > timeout:
                    break  # Exit the main loop as well
                
                iteration += 1
            
            if self.verbose:
                print(f"   ✅ Instance #{self.instance_number}: Loop completed after {iteration} iterations")
            
            return True
            
        elif action_type == ActionType.RESTART:
            delay_before = action_config.get('delay_before')
            delay_after = action_config.get('delay_after')
            timeout = action_config.get('timeout')
            
            if self.verbose:
                print(f"🔄 Instance #{self.instance_number}: Executing restart action")
                if delay_before:
                    print(f"   ⏱️ Delay before: {delay_before}s")
                if delay_after:
                    print(f"   ⏱️ Delay after: {delay_after}s")
                if timeout:
                    print(f"   ⏱️ Timeout: {timeout}s")
            
            # Apply delay before if specified
            if delay_before:
                time.sleep(delay_before)
            
            # Execute app restart
            if self.verbose:
                print(f"🔄 Instance #{self.instance_number}: Restarting app...")
            
            success = self.device_manager.restart_app(
                self.device_id,
                self.game.get_app_package(),
                self.game.get_app_activity()
            )
            
            if not success:
                print(f"❌ Instance #{self.instance_number}: Failed to restart app")
                return False
            
            if self.verbose:
                print(f"✅ Instance #{self.instance_number}: App restart successful")
            
            # Apply delay after if specified
            if delay_after:
                time.sleep(delay_after)
            
            return True
            
        elif action_type == ActionType.COUNTER:
            delay_before = action_config.get('delay_before')
            delay_after = action_config.get('delay_after')
            
            if self.verbose:
                print(f"🔢 Instance #{self.instance_number}: Executing counter increment action")
                if delay_before:
                    print(f"   ⏱️ Delay before: {delay_before}s")
                if delay_after:
                    print(f"   ⏱️ Delay after: {delay_after}s")
            
            # Apply delay before if specified
            if delay_before:
                time.sleep(delay_before)
            
            # Increment the counter
            new_counter_value = self.game.create_increment_counter()
            
            if self.verbose:
                print(f"🔢 Instance #{self.instance_number}: Counter incremented to {new_counter_value}")
            
            # Apply delay after if specified
            if delay_after:
                time.sleep(delay_after)
            
            return True
            
        else:
            print(f"❌ Instance #{self.instance_number}: Unsupported action type: {action_type}")
            return False
    
    def detect_template(self, screenshot, template_name: str) -> bool:
        """Detect a template in the screenshot"""
        import time
        start_time = time.time()
        
        threshold = self.game.get_template_threshold(template_name)
        detected = self.image_detector.detect_game_template(
            screenshot, self.game.get_game_name(), template_name, threshold
        )
        
        detection_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"🔍 Instance #{self.instance_number}: Template '{template_name}' {'✅' if detected else '❌'} in {detection_time:.1f}ms (threshold: {threshold})")
        
        return detected
    
    def detect_template_with_likelihood(self, screenshot, template_name: str, likelihood: float) -> bool:
        """Detect a template in the screenshot with custom likelihood threshold"""
        import time
        start_time = time.time()
        
        detected = self.image_detector.detect_game_template(
            screenshot, self.game.get_game_name(), template_name, likelihood
        )
        
        detection_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"🔍 Instance #{self.instance_number}: Template '{template_name}' {'✅' if detected else '❌'} in {detection_time:.1f}ms (likelihood: {likelihood})")
        
        return detected
    
    def execute_tap_with_likelihood(self, template_name: str, likelihood: float, offset_x: Optional[int] = None, offset_y: Optional[int] = None, coordinates: Optional[tuple[int, int]] = None, tap_times: Optional[int] = None, tap_delay: Optional[float] = None, screenshot: Optional[np.ndarray] = None) -> bool:
        """Execute a tap at the saved coordinates for a detected template with custom likelihood and optional offset, or at explicit coordinates"""
        
        # Use provided screenshot or get a new one
        if screenshot is None:
            screenshot = getattr(self, '_current_screenshot', None)
            if screenshot is None:
                screenshot = self.get_screenshot()
        
        if screenshot is None:
            print(f"❌ Instance #{self.instance_number}: Failed to get screenshot for template detection")
            return False
        
        # If template_name is None, skip template detection and use coordinates directly
        if template_name is None:
            if coordinates is None:
                print(f"❌ Instance #{self.instance_number}: No template specified and no coordinates provided")
                return False
            
            x, y = coordinates
            # Apply offsets if specified
            if offset_x is not None:
                x += offset_x
            if offset_y is not None:
                y += offset_y
            
            if self.verbose:
                offset_info = ""
                if offset_x is not None or offset_y is not None:
                    offset_info = f" (with offset: x={offset_x or 0}, y={offset_y or 0})"
                print(f"👆 Instance #{self.instance_number}: Tapping at coordinates ({x}, {y}) without template check{offset_info}")
            
            # Execute multiple taps if specified
            tap_count = tap_times or 1
            tap_delay_seconds = tap_delay or 0.1
            
            if self.verbose and tap_count > 1:
                print(f"👆 Instance #{self.instance_number}: Executing {tap_count} taps with {tap_delay_seconds}s delay")
            
            success = True
            for i in range(tap_count):
                if i > 0:  # Don't delay before first tap
                    time.sleep(tap_delay_seconds)
                
                tap_success = self.device_manager.tap(self.device_id, x, y)
                if not tap_success:
                    success = False
                    if self.verbose:
                        print(f"❌ Instance #{self.instance_number}: Tap {i+1}/{tap_count} failed")
                    break
                elif self.verbose and tap_count > 1:
                    print(f"✅ Instance #{self.instance_number}: Tap {i+1}/{tap_count} executed successfully")
            
            if self.verbose:
                if success:
                    print(f"✅ Instance #{self.instance_number}: All {tap_count} taps executed successfully")
                else:
                    print(f"❌ Instance #{self.instance_number}: Tap execution failed")
            
            return success
        
        # Detect template with custom likelihood for validation
        if not self.detect_template_with_likelihood(screenshot, template_name, likelihood):
            print(f"❌ Instance #{self.instance_number}: Template '{template_name}' not detected with likelihood {likelihood}")
            return False
        
        if self.verbose:
            print(f"✅ Instance #{self.instance_number}: Template '{template_name}' found with likelihood {likelihood}, proceeding with tap")
        
        # If explicit coordinates are provided, use them directly
        if coordinates is not None:
            x, y = coordinates
            
            # Apply offsets if specified
            if offset_x is not None:
                x += offset_x
            if offset_y is not None:
                y += offset_y
            
            if self.verbose:
                offset_info = ""
                if offset_x is not None or offset_y is not None:
                    offset_info = f" (with offset: x={offset_x or 0}, y={offset_y or 0})"
                print(f"👆 Instance #{self.instance_number}: Tapping at explicit coordinates ({x}, {y}){offset_info}")
            
            # Execute multiple taps if specified
            tap_count = tap_times or 1
            tap_delay_seconds = tap_delay or 0.1
            
            if self.verbose and tap_count > 1:
                print(f"👆 Instance #{self.instance_number}: Executing {tap_count} taps with {tap_delay_seconds}s delay")
            
            success = True
            for i in range(tap_count):
                if i > 0:  # Don't delay before first tap
                    time.sleep(tap_delay_seconds)
                
                tap_success = self.device_manager.tap(self.device_id, x, y)
                if not tap_success:
                    success = False
                    if self.verbose:
                        print(f"❌ Instance #{self.instance_number}: Tap {i+1}/{tap_count} failed")
                    break
                elif self.verbose and tap_count > 1:
                    print(f"✅ Instance #{self.instance_number}: Tap {i+1}/{tap_count} executed successfully")
            
            if self.verbose:
                if success:
                    print(f"✅ Instance #{self.instance_number}: All {tap_count} taps executed successfully")
                else:
                    print(f"❌ Instance #{self.instance_number}: Tap execution failed")
            
            return success
        
        # Otherwise, use template matching to find coordinates
        coordinates = self.image_detector.get_detected_coordinates(template_name)
        if coordinates is None:
            print(f"❌ Instance #{self.instance_number}: No coordinates saved for template '{template_name}'")
            return False
        
        x, y = coordinates
        
        # Apply offsets if specified
        if offset_x is not None:
            x += offset_x
        if offset_y is not None:
            y += offset_y
        
        if self.verbose:
            offset_info = ""
            if offset_x is not None or offset_y is not None:
                offset_info = f" (with offset: x={offset_x or 0}, y={offset_y or 0})"
            print(f"👆 Instance #{self.instance_number}: Tapping at coordinates ({x}, {y}) for template '{template_name}'{offset_info}")
        
        # Execute multiple taps if specified
        tap_count = tap_times or 1
        tap_delay_seconds = tap_delay or 0.1
        
        if self.verbose and tap_count > 1:
            print(f"👆 Instance #{self.instance_number}: Executing {tap_count} taps with {tap_delay_seconds}s delay")
        
        success = True
        for i in range(tap_count):
            if i > 0:  # Don't delay before first tap
                time.sleep(tap_delay_seconds)
            
            tap_success = self.device_manager.tap(self.device_id, x, y)
            if not tap_success:
                success = False
                if self.verbose:
                    print(f"❌ Instance #{self.instance_number}: Tap {i+1}/{tap_count} failed")
                break
            elif self.verbose and tap_count > 1:
                print(f"✅ Instance #{self.instance_number}: Tap {i+1}/{tap_count} executed successfully")
        
        if self.verbose:
            if success:
                print(f"✅ Instance #{self.instance_number}: All {tap_count} taps executed successfully")
            else:
                print(f"❌ Instance #{self.instance_number}: Tap execution failed")
        
        return success
    
    def process_screenshot_for_items(self, screenshot) -> List[str]:
        """Process screenshot to detect items"""
        if self.verbose:
            print(f"🔍 Instance #{self.instance_number}: Processing screenshot for items")
        
        detected_items = self.game.process_screenshot_for_items(screenshot, self.instance_data)
        
        if self.verbose:
            if detected_items:
                print(f"🎁 Instance #{self.instance_number}: Detected {len(detected_items)} items: {detected_items}")
            else:
                print(f"🔍 Instance #{self.instance_number}: No items detected in screenshot")
        
        return detected_items
    
    def is_new_cycle(self, screenshot) -> bool:
        """Check if this is a new cycle"""
        is_new = self.game.is_new_cycle(screenshot, self.instance_data)
        
        if self.verbose:
            print(f"🔄 Instance #{self.instance_number}: Cycle check - {'New cycle detected' if is_new else 'Same cycle'}")
        
        return is_new
    
    def get_account_id(self) -> str:
        """Get account ID from device"""
        if self.verbose:
            print(f"📋 Instance #{self.instance_number}: Retrieving account ID from clipboard")
        
        account_id = self.device_manager.get_clipboard(self.device_id)
        
        if self.verbose:
            if account_id:
                print(f"✅ Instance #{self.instance_number}: Account ID retrieved: {account_id}")
            else:
                print(f"❌ Instance #{self.instance_number}: Failed to retrieve account ID")
        
        return account_id
    
    def run_automation(self):
        """Main automation loop for this instance"""
        self.start_background_timeout_checker()
        
        # Restart app for clean state
        # if not self.device_manager.restart_app(
        #     self.device_id, 
        #     self.game.get_app_package(), 
        #     self.game.get_app_activity()
        # ):
        #     print(f"❌ Instance #{self.instance_number}: Failed to restart app")
        #     self.stop_background_timeout_checker()
        #     return False
        
        # Get automation states from game
        automation_states = self.game.get_automation_states()
        
        try:
            while self.running:
                current_time = time.time()
                
                screenshot = self.get_screenshot()
                if screenshot is None:
                    continue
                
                current_state = self.instance_data['current_state']
                
                # Get state configuration
                if current_state not in automation_states:
                    print(f"❌ Instance #{self.instance_number}: Unknown state '{current_state}'")
                    break
                
                state_config = automation_states[current_state]
                
                if self.verbose and current_time - self.current_state_start_time > 30:  # Log current state every 30 seconds
                    time_in_state = current_time - self.current_state_start_time
                    print(f"🔄 Instance #{self.instance_number}: Current state: {current_state} ({time_in_state:.1f}s)")
                
                # Check for template detection
                templates = state_config.get('templates', [])
                actions = state_config.get('actions', [])  # New actions field
                macros = state_config.get('macros', [])  # Legacy macros field
                template_detected = False
                
                if self.verbose and templates:
                    print(f"🔍 Instance #{self.instance_number}: Checking templates: {templates}")
                
                for template in templates:
                    if self.detect_template(screenshot, template):
                        template_detected = True
                        if self.verbose:
                            print(f"✅ Instance #{self.instance_number}: Template '{template}' triggered state action")
                        break
                
                # Log timing after template detection
                template_time = time.time()
                if self.verbose:
                    print(f"⏱️ Instance #{self.instance_number}: Template detection completed in {((template_time - current_time) * 1000):.1f}ms")
                
                # Determine if we should execute actions
                # Execute if: (template detected) OR (state has actions/macros but no templates to detect)
                should_execute_actions = (
                    template_detected or
                    (not templates and (actions or macros))
                )
                
                # Special handling for "completed" state - trigger session completion
                if current_state == 'completed':
                    if self.verbose:
                        print(f"🏁 Instance #{self.instance_number}: Reached completed state, finishing session")
                    
                    # Complete the session (sends Discord notification and resets)
                    self.complete_session()
                    continue
                
                # Handle states with no templates and no actions (auto-transition)
                if not templates and not actions and not macros:
                    next_states = state_config.get('next_states', [])
                    if next_states:
                        next_state = next_states[0]
                        if self.verbose:
                            print(f"🔄 Instance #{self.instance_number}: Auto-transitioning from '{current_state}' to '{next_state}' (no actions required)")
                        self.change_state(next_state)
                    continue
                
                # Process state logic
                if should_execute_actions:
                    action_start_time = time.time()
                    if self.verbose:
                        print(f"🎬 Instance #{self.instance_number}: Starting action execution")
                    
                    if self.verbose:
                        reason = "template detected" if template_detected else "no templates, executing actions"
                        print(f"🎬 Instance #{self.instance_number}: Processing state '{current_state}' actions ({reason})")
                    
                    # Execute actions for this state
                    action_success = True
                    
                    # Handle if condition logic
                    if_condition = state_config.get('if_condition')
                    if_true_actions = state_config.get('if_true_actions', [])
                    if_false_actions = state_config.get('if_false_actions', [])
                    if_likelihood = state_config.get('if_likelihood')
                    
                    if if_condition:
                        condition_start_time = time.time()
                        if self.verbose:
                            print(f"🔀 Instance #{self.instance_number}: Checking if condition: {if_condition}")
                        
                        # Check if condition
                        condition_met = False
                        if screenshot is not None:
                            if if_likelihood is not None:
                                condition_met = self.detect_template_with_likelihood(screenshot, if_condition, if_likelihood)
                            else:
                                condition_met = self.detect_template(screenshot, if_condition)
                        
                        condition_time = (time.time() - condition_start_time) * 1000
                        if self.verbose:
                            print(f"⏱️ Instance #{self.instance_number}: Condition check took {condition_time:.1f}ms")
                        
                        if self.verbose:
                            print(f"   {'✅' if condition_met else '❌'} If condition '{if_condition}' {'met' if condition_met else 'not met'}")
                        
                        # Execute appropriate actions based on condition
                        actions_to_execute = if_true_actions if condition_met else if_false_actions
                        if self.verbose:
                            print(f"   🎬 Executing {len(actions_to_execute)} action(s) for {'true' if condition_met else 'false'} branch")
                        
                        # Execute conditional actions
                        successful_actions = 0
                        failed_actions = 0
                        
                        for i, action in enumerate(actions_to_execute):
                            action_exec_start = time.time()
                            if self.verbose:
                                print(f"🎬 Instance #{self.instance_number}: Executing conditional action {i + 1}/{len(actions_to_execute)}")
                            
                            # Retry the action until it succeeds or timeout is reached
                            action_success = False
                            action_start_time = time.time()
                            
                            while not action_success:
                                # Check if this individual action has its own timeout
                                action_timeout = action.get('timeout')
                                if action_timeout and time.time() - action_start_time > action_timeout:
                                    if self.verbose:
                                        print(f"   ⏱️ Instance #{self.instance_number}: Action {i + 1} timeout reached ({action_timeout}s)")
                                    break
                                
                                # Get fresh screenshot for each action attempt
                                fresh_screenshot = self.get_screenshot()
                                if fresh_screenshot is None:
                                    if self.verbose:
                                        print(f"   ❌ Instance #{self.instance_number}: Failed to get fresh screenshot for action {i + 1}")
                                    # Brief delay before retry to avoid hammering
                                    time.sleep(0.1)
                                    continue
                                
                                action_success = self.execute_action(action, fresh_screenshot)
                                if action_success:
                                    successful_actions += 1
                                    if self.verbose:
                                        print(f"   ✅ Instance #{self.instance_number}: Conditional action {i + 1} succeeded")
                                else:
                                    if self.verbose:
                                        print(f"   ❌ Instance #{self.instance_number}: Conditional action {i + 1} failed, retrying...")
                                    # Brief delay before retry to avoid hammering
                                    time.sleep(0.1)
                            
                            if not action_success:
                                failed_actions += 1
                                if self.verbose:
                                    print(f"   ❌ Instance #{self.instance_number}: Conditional action {i + 1} failed after all retries")
                            
                            action_exec_time = (time.time() - action_exec_start) * 1000
                            if self.verbose:
                                print(f"⏱️ Instance #{self.instance_number}: Conditional action {i + 1} took {action_exec_time:.1f}ms")
                        
                        # Log summary
                        if self.verbose:
                            print(f"   📊 Instance #{self.instance_number}: State conditional action summary - {successful_actions} succeeded, {failed_actions} failed")
                        
                        # Set action_success based on whether at least one action succeeded
                        action_success = successful_actions > 0 or len(actions_to_execute) == 0
                    else:
                        # Handle regular actions (existing logic)
                        if actions:
                            actions_start_time = time.time()
                            if self.verbose:
                                print(f"🎬 Instance #{self.instance_number}: Executing {len(actions)} action(s) starting from index {self.current_action_index}")
                            
                            # Execute actions starting from the current index
                            for i in range(self.current_action_index, len(actions)):
                                action = actions[i]
                                action_exec_start = time.time()
                                if self.verbose:
                                    print(f"🎬 Instance #{self.instance_number}: Executing action {i + 1}/{len(actions)}")
                                
                                if not self.execute_action(action, screenshot):
                                    # Action failed, stay at current index for next iteration
                                    if self.verbose:
                                        print(f"❌ Instance #{self.instance_number}: Action {i + 1} failed, will retry from this action")
                                    action_success = False
                                    break
                                else:
                                    # Action succeeded, move to next action
                                    self.current_action_index = i + 1
                                    
                                    # Get fresh screenshot after successful action execution
                                    if self.verbose:
                                        print(f"📸 Instance #{self.instance_number}: Getting fresh screenshot after successful action {i + 1}")
                                    fresh_screenshot = self.get_screenshot()
                                    if fresh_screenshot is not None:
                                        screenshot = fresh_screenshot
                                        if self.verbose:
                                            print(f"📸 Instance #{self.instance_number}: Fresh screenshot captured after action {i + 1}")
                                        
                                        # Clear stored template coordinates and re-detect with fresh screenshot
                                        self.image_detector.clear_detected_coordinates()
                                        if self.verbose:
                                            print(f"🧹 Instance #{self.instance_number}: Cleared stored coordinates after action {i + 1}")
                                        
                                        # Re-detect templates with the fresh screenshot
                                        if templates:
                                            if self.verbose:
                                                print(f"🔍 Instance #{self.instance_number}: Re-detecting templates after action {i + 1}")
                                            template_detected = False
                                            for template in templates:
                                                if self.detect_template(screenshot, template):
                                                    template_detected = True
                                                    if self.verbose:
                                                        print(f"✅ Instance #{self.instance_number}: Template '{template}' re-detected after action {i + 1}")
                                                    break
                                            if self.verbose and not template_detected:
                                                print(f"❌ Instance #{self.instance_number}: No templates re-detected after action {i + 1}")
                                    else:
                                        if self.verbose:
                                            print(f"⚠️ Instance #{self.instance_number}: Failed to get fresh screenshot after action {i + 1}")
                                
                                action_exec_time = (time.time() - action_exec_start) * 1000
                                if self.verbose:
                                    print(f"⏱️ Instance #{self.instance_number}: Action {i + 1} took {action_exec_time:.1f}ms")
                                
                                # Process items if this is a cycle where items are obtained
                                if state_config.get('processes_items', False):
                                    items_start_time = time.time()
                                    if self.verbose:
                                        print(f"🎁 Instance #{self.instance_number}: Processing items after action")
                                    
                                    # time.sleep(2 * self.macro_executor.speed_multiplier)  # Wait for items to appear (respects speed)
                                    new_screenshot = self.get_screenshot()
                                    if new_screenshot is not None and self.is_new_cycle(new_screenshot):
                                        # Increment cycle count regardless of item detection
                                        self.instance_data['cycle_count'] += 1
                                        
                                        # Try to detect items
                                        detected_items = self.process_screenshot_for_items(new_screenshot)
                                        if detected_items:
                                            self.instance_data['detected_items'].extend(detected_items)
                                            if self.verbose:
                                                print(f"🎁 Instance #{self.instance_number}: Cycle {self.instance_data['cycle_count']} complete, {len(detected_items)} items added")
                                        else:
                                            if self.verbose:
                                                print(f"🎁 Instance #{self.instance_number}: Cycle {self.instance_data['cycle_count']} complete, no items detected")
                                    
                                    items_time = (time.time() - items_start_time) * 1000
                                    if self.verbose:
                                        print(f"⏱️ Instance #{self.instance_number}: Items processing took {items_time:.1f}ms")
                            
                            actions_time = (time.time() - actions_start_time) * 1000
                            if self.verbose:
                                print(f"⏱️ Instance #{self.instance_number}: All actions took {actions_time:.1f}ms")
                            
                            # If all actions completed successfully, reset action index
                            if action_success:
                                self.current_action_index = 0
                        
                        # Handle legacy macro system
                        elif macros:
                            macros_start_time = time.time()
                            if self.verbose:
                                print(f"🎬 Instance #{self.instance_number}: Executing {len(macros)} macro(s) starting from index {self.current_action_index}: {macros}")
                            
                            # Execute macros starting from the current index
                            for i in range(self.current_action_index, len(macros)):
                                macro = macros[i]
                                macro_exec_start = time.time()
                                if self.verbose:
                                    print(f"🎬 Instance #{self.instance_number}: Executing macro {i + 1}/{len(macros)}: {macro}")
                                
                                if not self.execute_macro(macro):
                                    # Macro failed, stay at current index for next iteration
                                    if self.verbose:
                                        print(f"❌ Instance #{self.instance_number}: Macro {i + 1} '{macro}' failed, will retry from this macro")
                                    action_success = False
                                    break
                                else:
                                    # Macro succeeded, move to next macro
                                    self.current_action_index = i + 1
                                    
                                    # Get fresh screenshot after successful macro execution
                                    if self.verbose:
                                        print(f"📸 Instance #{self.instance_number}: Getting fresh screenshot after successful macro {i + 1}")
                                    fresh_screenshot = self.get_screenshot()
                                    if fresh_screenshot is not None:
                                        screenshot = fresh_screenshot
                                        if self.verbose:
                                            print(f"📸 Instance #{self.instance_number}: Fresh screenshot captured after macro {i + 1}")
                                        
                                        # Clear stored template coordinates and re-detect with fresh screenshot
                                        self.image_detector.clear_detected_coordinates()
                                        if self.verbose:
                                            print(f"🧹 Instance #{self.instance_number}: Cleared stored coordinates after macro {i + 1}")
                                        
                                        # Re-detect templates with the fresh screenshot
                                        if templates:
                                            if self.verbose:
                                                print(f"🔍 Instance #{self.instance_number}: Re-detecting templates after macro {i + 1}")
                                            template_detected = False
                                            for template in templates:
                                                if self.detect_template(screenshot, template):
                                                    template_detected = True
                                                    if self.verbose:
                                                        print(f"✅ Instance #{self.instance_number}: Template '{template}' re-detected after macro {i + 1}")
                                                    break
                                            if self.verbose and not template_detected:
                                                print(f"❌ Instance #{self.instance_number}: No templates re-detected after macro {i + 1}")
                                    else:
                                        if self.verbose:
                                            print(f"⚠️ Instance #{self.instance_number}: Failed to get fresh screenshot after macro {i + 1}")
                                
                                macro_exec_time = (time.time() - macro_exec_start) * 1000
                                if self.verbose:
                                    print(f"⏱️ Instance #{self.instance_number}: Macro {i + 1} took {macro_exec_time:.1f}ms")
                                
                                # Process items if this is a cycle where items are obtained
                                if state_config.get('processes_items', False):
                                    items_start_time = time.time()
                                    if self.verbose:
                                        print(f"🎁 Instance #{self.instance_number}: Processing items after macro '{macro}'")
                                    
                                    # time.sleep(2 * self.macro_executor.speed_multiplier)  # Wait for items to appear (respects speed)
                                    new_screenshot = self.get_screenshot()
                                    if new_screenshot is not None and self.is_new_cycle(new_screenshot):
                                        # Increment cycle count regardless of item detection
                                        self.instance_data['cycle_count'] += 1
                                        
                                        # Try to detect items
                                        detected_items = self.process_screenshot_for_items(new_screenshot)
                                        if detected_items:
                                            self.instance_data['detected_items'].extend(detected_items)
                                            if self.verbose:
                                                print(f"🎁 Instance #{self.instance_number}: Cycle {self.instance_data['cycle_count']} complete, {len(detected_items)} items added")
                                        else:
                                            if self.verbose:
                                                print(f"🎁 Instance #{self.instance_number}: Cycle {self.instance_data['cycle_count']} complete, no items detected")
                                    
                                    items_time = (time.time() - items_start_time) * 1000
                                    if self.verbose:
                                        print(f"⏱️ Instance #{self.instance_number}: Items processing took {items_time:.1f}ms")
                            
                            macros_time = (time.time() - macros_start_time) * 1000
                            if self.verbose:
                                print(f"⏱️ Instance #{self.instance_number}: All macros took {macros_time:.1f}ms")
                            
                            # If all macros completed successfully, reset action index
                            if action_success:
                                self.current_action_index = 0
                    
                    # Transition to next state
                    if action_success:
                        state_transition_start = time.time()
                        if self.verbose:
                            print(f"🔄 Instance #{self.instance_number}: Starting state transition")
                        
                        next_states = state_config.get('next_states', [])
                        if next_states:
                            # Smart state selection based on cycles remaining
                            cycles_completed = self.instance_data['cycle_count']
                            cycles_needed = self.game.get_cycles_per_session()
                            current_state = self.instance_data['current_state']
                            
                            # For pulling_gacha state, decide whether to continue or finish
                            if current_state == 'pulling_gacha' and len(next_states) >= 2:
                                if cycles_completed < cycles_needed:
                                    # Continue pulling - go to pulling_gacha (usually index 1)
                                    next_state = 'pulling_gacha' if 'pulling_gacha' in next_states else next_states[1]
                                    if self.verbose:
                                        print(f"🎰 Instance #{self.instance_number}: Continuing gacha pulls ({cycles_completed}/{cycles_needed})")
                                else:
                                    # Finish pulling - go to completion state (usually index 0)
                                    next_state = next_states[0] if next_states[0] != 'pulling_gacha' else next_states[1]
                                    if self.verbose:
                                        print(f"🏁 Instance #{self.instance_number}: Gacha pull limit reached ({cycles_completed}/{cycles_needed}), finishing")
                            else:
                                # Default behavior for other states
                                next_state = next_states[0]
                            
                            if self.verbose:
                                print(f"🔄 Instance #{self.instance_number}: Transitioning to next state: {next_state}")
                            self.change_state(next_state)
                        
                        state_transition_time = (time.time() - state_transition_start) * 1000
                        if self.verbose:
                            print(f"⏱️ Instance #{self.instance_number}: State transition took {state_transition_time:.1f}ms")
                        
                        # Get fresh screenshot after successful state transition to prevent detecting previous state's templates
                        if self.verbose:
                            print(f"📸 Instance #{self.instance_number}: Getting fresh screenshot after successful state transition")
                        fresh_screenshot = self.get_screenshot()
                        if fresh_screenshot is not None:
                            screenshot = fresh_screenshot
                            if self.verbose:
                                print(f"📸 Instance #{self.instance_number}: Fresh screenshot captured for next iteration")
                            
                            # Clear stored template coordinates so they get re-detected with the fresh screenshot
                            self.image_detector.clear_detected_coordinates()
                            if self.verbose:
                                print(f"🧹 Instance #{self.instance_number}: Cleared stored template coordinates for fresh detection")
                            
                            # Re-detect templates with the fresh screenshot to get updated detection results
                            if templates:
                                if self.verbose:
                                    print(f"🔍 Instance #{self.instance_number}: Re-detecting templates with fresh screenshot")
                                template_detected = False
                                for template in templates:
                                    if self.detect_template(screenshot, template):
                                        template_detected = True
                                        if self.verbose:
                                            print(f"✅ Instance #{self.instance_number}: Template '{template}' re-detected with fresh screenshot")
                                        break
                                if self.verbose and not template_detected:
                                    print(f"❌ Instance #{self.instance_number}: No templates re-detected with fresh screenshot")
                        else:
                            if self.verbose:
                                print(f"⚠️ Instance #{self.instance_number}: Failed to get fresh screenshot after state transition")
                    else:
                        if self.verbose:
                            print(f"❌ Instance #{self.instance_number}: Action execution failed, staying in current state")
                    
                    action_total_time = (time.time() - action_start_time) * 1000
                    if self.verbose:
                        print(f"⏱️ Instance #{self.instance_number}: Total action execution took {action_total_time:.1f}ms")
                    
                    # last_detection_time = current_time # This line was removed as per the new_code, as the original code had it.
                
                # Log total loop time
                loop_end_time = time.time()
                total_loop_time = (loop_end_time - current_time) * 1000
                if self.verbose:
                    print(f"⏱️ Instance #{self.instance_number}: Total loop time: {total_loop_time:.1f}ms")
                
                # time.sleep(0.5 * self.macro_executor.speed_multiplier)  # Main loop delay (respects speed)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Instance #{self.instance_number}: Interrupted by user")
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Unexpected error: {e}")
        finally:
            self.stop_background_timeout_checker()
        
        return True
    
    def complete_session(self):
        """Complete the current automation session"""
        try:
            if self.verbose:
                print(f"🏁 Instance #{self.instance_number}: Starting session completion")
            
            # Get account ID
            account_id = self.get_account_id()
            if account_id:
                self.instance_data['account_id'] = account_id
                print(f"✅ Instance #{self.instance_number}: Account ID: {account_id}")
            
            # Calculate and show results
            detected_items = self.instance_data['detected_items']
            total_score, score_breakdown = self.game.calculate_score(detected_items)
            
            if self.verbose:
                print(f"📊 Instance #{self.instance_number}: Session results:")
                print(f"   Total items: {len(detected_items)}")
                print(f"   Total score: {total_score}")
                print(f"   Score breakdown: {score_breakdown}")
                print(f"   Cycles completed: {self.instance_data['cycle_count']}")
            
            print(f"🎉 Instance #{self.instance_number}: Session completed!")
            print(f"   Score: {total_score}, Items: {len(detected_items)}, Account: {account_id or 'None'}")
            
            # Send Discord notification if score is high enough
            if self.game.should_send_discord_notification(detected_items):
                if self.verbose:
                    print(f"📤 Instance #{self.instance_number}: Score {total_score} meets threshold, sending Discord notification")
                
                results = self.game.format_results_for_discord(self.instance_data)
                self.discord_notifier.send_game_result(
                    self.game.get_display_name(),
                    f"#{self.instance_number}",
                    self.device_id,
                    account_id,
                    results
                )
            elif self.verbose:
                threshold = self.game.get_minimum_score_threshold()
                print(f"📊 Instance #{self.instance_number}: Score {total_score} < {threshold}, not sending Discord notification")
            
            # Reset for next session
            self.reset_for_next_session()
            
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error completing session: {e}")
    
    def reset_for_next_session(self):
        """Reset instance for next automation session"""
        old_session = self.instance_data['session_count']
        self.instance_data['session_count'] += 1
        self.instance_data['cycle_count'] = 0
        self.instance_data['detected_items'] = []
        self.instance_data['account_id'] = None
        self.current_action_index = 0
        self.change_state(self.game.get_initial_state())
        
        if self.verbose:
            print(f"🔄 Instance #{self.instance_number}: Session reset complete")
            print(f"   Previous session: #{old_session}")
            print(f"   New session: #{self.instance_data['session_count']}")
            print(f"   Reset to state: {self.instance_data['current_state']}")
        
        print(f"🔄 Instance #{self.instance_number}: Starting session #{self.instance_data['session_count']}")
        time.sleep(3 * self.macro_executor.speed_multiplier)  # Brief pause between sessions (respects speed)


class AutomationEngine:
    """Main automation engine that manages multiple instances"""
    
    def __init__(self, game: BaseGame, device_manager: DeviceManager,
                 speed_multiplier: float = 1.0, inter_macro_delay: float = 0.0,
                 max_instances: int = 8, verbose: bool = False, use_streaming: bool = False,
                 force_resume: bool = False):
        self.game = game
        self.device_manager = device_manager
        self.macro_executor = MacroExecutor(speed_multiplier, inter_macro_delay, verbose)
        self.image_detector = ImageDetector()
        self.discord_notifier = DiscordNotifier(game.get_discord_webhook())
        self.max_instances = max_instances
        self.verbose = verbose
        self.use_streaming = use_streaming
        self.force_resume = force_resume
        self.instances = []
        self.running = True
        self.last_status_write = 0  # Track last status write time
        
        # Initialize stream manager if streaming is enabled
        self.stream_manager = None
        if self.use_streaming:
            self.stream_manager = MinicapStreamManager()
            print("🎥 Streaming mode enabled - using real-time frames for automation")
        
        if self.verbose:
            print(f"🔧 AutomationEngine: Initialized with verbose logging")
            print(f"   Speed multiplier: {speed_multiplier}x")
            print(f"   Inter-macro delay: {inter_macro_delay}s")
            print(f"   Max instances: {max_instances}")
            print(f"   Streaming enabled: {'✅' if use_streaming else '❌'}")
    
    def write_status_to_file(self, start_time: float):
        """Write current status to status.txt file"""
        try:
            elapsed_time = time.time() - start_time
            total_sessions = sum(instance.instance_data['session_count'] for instance in self.instances)
            sessions_per_hour = (total_sessions / elapsed_time) * 3600 if elapsed_time > 0 else 0
            
            status_lines = []
            status_lines.append(f"📊 STATUS ({len(self.instances)} instances) - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            status_lines.append(f"🎮 Game: {self.game.get_display_name()}")
            status_lines.append(f"⏱️  Runtime: {elapsed_time/3600:.1f} hours")
            status_lines.append(f"🔄 Total sessions: {total_sessions}")
            status_lines.append(f"⚡ Speed: {sessions_per_hour:.1f} sessions/hour")
            status_lines.append(f"🔢 Counter: {self.game.get_counter()}")
            status_lines.append("")
            
            if self.verbose:
                status_lines.append(f"🔧 Verbose mode: Active")
                status_lines.append(f"📊 Detailed Instance Status:")
            
            for instance in self.instances:
                data = instance.instance_data
                total_score = 0
                if data['detected_items']:
                    total_score, _ = self.game.calculate_score(data['detected_items'])
                
                # Calculate time in current state
                time_in_state = time.time() - instance.current_state_start_time
                
                if self.verbose:
                    status_lines.append(f"   Instance #{instance.instance_number}:")
                    status_lines.append(f"     • Device: {instance.device_id}")
                    status_lines.append(f"     • Sessions: {data['session_count']}")
                    status_lines.append(f"     • Current cycle: {data['cycle_count']}/{self.game.get_cycles_per_session()}")
                    status_lines.append(f"     • State: {data['current_state']} ({time_in_state:.1f}s)")
                    status_lines.append(f"     • Score: {total_score} ({len(data['detected_items'])} items)")
                    status_lines.append(f"     • Account: {data['account_id'] or 'None'}")
                    status_lines.append(f"     • Running: {'✅' if instance.running else '❌'}")
                else:
                    status_lines.append(f"   Instance #{instance.instance_number}: {data['session_count']} sessions, "
                                      f"Score: {total_score}, State: {data['current_state']} ({time_in_state:.0f}s)")
            
            if self.verbose:
                status_lines.append(f"")
                status_lines.append(f"📊 System Status:")
                status_lines.append(f"   • Macro speed: {self.macro_executor.speed_multiplier}x")
                status_lines.append(f"   • Inter-macro delay: {self.macro_executor.inter_macro_delay}s")
                status_lines.append(f"   • Discord webhook: {'✅' if self.discord_notifier.has_webhook() else '❌'}")
                status_lines.append(f"   • Score threshold: {self.game.get_minimum_score_threshold()}")
            
            # Write to status.txt file
            with open("status.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(status_lines))
                
        except Exception as e:
            print(f"❌ Error writing status to file: {e}")
    
    def save_state_to_file(self):
        """Save detailed state information to resume.json for resuming automation"""
        try:
            state_data = {
                "timestamp": time.time(),
                "game_name": self.game.get_display_name(),
                "game_counter": self.game.get_counter(),
                "instances": []
            }
            
            for instance in self.instances:
                instance_state = {
                    "device_id": instance.device_id,
                    "instance_number": instance.instance_number,
                    "current_state": instance.instance_data['current_state'],
                    "session_count": instance.instance_data['session_count'],
                    "cycle_count": instance.instance_data['cycle_count'],
                    "detected_items": instance.instance_data['detected_items'],
                    "account_id": instance.instance_data['account_id'],
                    "current_action_index": instance.current_action_index,
                    "current_state_start_time": instance.current_state_start_time,
                    "running": instance.running
                }
                state_data["instances"].append(instance_state)
            
            with open("resume.json", "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
            if self.verbose:
                print(f"💾 State saved to resume.json")
                
        except Exception as e:
            print(f"❌ Error saving state to file: {e}")
    
    def load_state_from_file(self) -> Optional[Dict[str, Any]]:
        """Load detailed state information from resume.json for resuming automation"""
        try:
            resume_file = Path("resume.json")
            if not resume_file.exists():
                if self.verbose:
                    print("📄 No resume.json file found - starting fresh")
                return None
            
            with open(resume_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            
            if self.verbose:
                print(f"📄 Loaded state from resume.json")
                print(f"   Game: {state_data.get('game_name', 'Unknown')}")
                print(f"   Counter: {state_data.get('game_counter', 0)}")
                print(f"   Instances: {len(state_data.get('instances', []))}")
            
            return state_data
            
        except Exception as e:
            print(f"❌ Error loading state from file: {e}")
            return None
    
    def can_resume(self) -> bool:
        """Check if we can resume from a saved state"""
        state_data = self.load_state_from_file()
        if not state_data:
            return False
        
        # Check if the game name matches
        if state_data.get('game_name') != self.game.get_display_name():
            if self.verbose:
                print(f"⚠️ Game mismatch: saved '{state_data.get('game_name')}' vs current '{self.game.get_display_name()}'")
            return False
        
        # Check if we have any instances to resume
        instances = state_data.get('instances', [])
        if not instances:
            if self.verbose:
                print("⚠️ No instances found in saved state")
            return False
        
        return True
    
    def cleanup_resume_file(self):
        """Remove the resume.json file when automation completes successfully"""
        try:
            resume_file = Path("resume.json")
            if resume_file.exists():
                resume_file.unlink()
                if self.verbose:
                    print("🗑️ Cleaned up resume.json file")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Could not clean up resume.json: {e}")
    
    def check_completion_and_cleanup(self):
        """Check if all instances have completed their sessions and cleanup if so"""
        # Check if all instances have completed their target sessions
        total_sessions = sum(instance.instance_data['session_count'] for instance in self.instances)
        target_sessions = len(self.instances) * self.game.get_cycles_per_session()
        
        if total_sessions >= target_sessions:
            print("🎉 All target sessions completed! Cleaning up resume file...")
            self.cleanup_resume_file()
            return True
        return False
    
    def show_status(self, start_time: float):
        """Show current status of all instances (legacy method for manual key press)"""
        elapsed_time = time.time() - start_time
        total_sessions = sum(instance.instance_data['session_count'] for instance in self.instances)
        sessions_per_hour = (total_sessions / elapsed_time) * 3600 if elapsed_time > 0 else 0
        
        print(f"\n📊 STATUS ({len(self.instances)} instances):")
        print(f"🎮 Game: {self.game.get_display_name()}")
        print(f"⏱️  Runtime: {elapsed_time/3600:.1f} hours")
        print(f"🔄 Total sessions: {total_sessions}")
        print(f"⚡ Speed: {sessions_per_hour:.1f} sessions/hour")
        print(f"🔢 Counter: {self.game.get_counter()}")
        
        if self.verbose:
            print(f"🔧 Verbose mode: Active")
            print(f"📊 Detailed Instance Status:")
        
        for instance in self.instances:
            data = instance.instance_data
            total_score = 0
            if data['detected_items']:
                total_score, _ = self.game.calculate_score(data['detected_items'])
            
            # Calculate time in current state
            time_in_state = time.time() - instance.current_state_start_time
            
            if self.verbose:
                print(f"   Instance #{instance.instance_number}:")
                print(f"     • Device: {instance.device_id}")
                print(f"     • Sessions: {data['session_count']}")
                print(f"     • Current cycle: {data['cycle_count']}/{self.game.get_cycles_per_session()}")
                print(f"     • State: {data['current_state']} ({time_in_state:.1f}s)")
                print(f"     • Score: {total_score} ({len(data['detected_items'])} items)")
                print(f"     • Account: {data['account_id'] or 'None'}")
                print(f"     • Running: {'✅' if instance.running else '❌'}")
            else:
                print(f"   Instance #{instance.instance_number}: {data['session_count']} sessions, "
                      f"Score: {total_score}, State: {data['current_state']} ({time_in_state:.0f}s)")
        
        if self.verbose:
            print(f"\n📊 System Status:")
            print(f"   • Macro speed: {self.macro_executor.speed_multiplier}x")
            print(f"   • Inter-macro delay: {self.macro_executor.inter_macro_delay}s")
            print(f"   • Discord webhook: {'✅' if self.discord_notifier.has_webhook() else '❌'}")
            print(f"   • Score threshold: {self.game.get_minimum_score_threshold()}")
    
    def create_instances(self):
        """Create automation instances for available devices"""
        device_list = self.device_manager.get_device_list()[:self.max_instances]
        
        if self.verbose:
            print(f"🔧 AutomationEngine: Creating {len(device_list)} instances")
        
        # Check if we can resume from saved state
        saved_state = self.load_state_from_file()
        resume_mode = False
        
        if saved_state and (self.can_resume() or self.force_resume):
            if self.force_resume:
                print("🔄 Force resume mode - attempting to restore from saved state")
            else:
                print("🔄 Resume mode detected - attempting to restore from saved state")
            resume_mode = True
        
        # Setup streaming if enabled
        if self.use_streaming and self.stream_manager:
            print("🎥 Setting up streaming for all devices...")
            for i, device_id in enumerate(device_list):
                port = 1313 + i  # Each device gets a different port
                if self.stream_manager.start_streaming(device_id, port):
                    if self.verbose:
                        print(f"   ✅ Streaming started for device: {device_id} on port {port}")
                    # Start the streaming thread to capture frames
                    display_name = f"Device {i+1} ({device_id})"
                    self.stream_manager.start_streaming_thread(device_id, display_name)
                else:
                    print(f"   ⚠️ Failed to start streaming for device: {device_id}")
        
        # Create automation instances
        for i, device_id in enumerate(device_list, 1):
            instance = AutomationInstance(
                device_id, i, self.game, self.macro_executor,
                self.image_detector, self.device_manager, self.discord_notifier,
                self.stream_manager, self.verbose
            )
            
            # Restore state if resuming
            if resume_mode and saved_state:
                saved_instances = saved_state.get('instances', [])
                # Find matching instance by device_id or instance_number
                saved_instance = None
                for saved_inst in saved_instances:
                    if (saved_inst.get('device_id') == device_id or 
                        saved_inst.get('instance_number') == i):
                        saved_instance = saved_inst
                        break
                
                if saved_instance:
                    # Restore instance data
                    instance.instance_data.update({
                        'current_state': saved_instance.get('current_state', self.game.get_initial_state()),
                        'session_count': saved_instance.get('session_count', 0),
                        'cycle_count': saved_instance.get('cycle_count', 0),
                        'detected_items': saved_instance.get('detected_items', []),
                        'account_id': saved_instance.get('account_id')
                    })
                    instance.current_action_index = saved_instance.get('current_action_index', 0)
                    instance.current_state_start_time = time.time()  # Reset timer for current state
                    instance.running = saved_instance.get('running', True)
                    
                    if self.verbose:
                        print(f"   🔄 Restored Instance #{i} ({device_id}):")
                        print(f"      State: {instance.instance_data['current_state']}")
                        print(f"      Sessions: {instance.instance_data['session_count']}")
                        print(f"      Cycles: {instance.instance_data['cycle_count']}")
                        print(f"      Action index: {instance.current_action_index}")
                else:
                    if self.verbose:
                        print(f"   ⚠️ No saved state found for Instance #{i} ({device_id}) - starting fresh")
            
            self.instances.append(instance)
        
        # Restore game counter if resuming
        if resume_mode and saved_state:
            saved_counter = saved_state.get('game_counter', 0)
            self.game.set_counter(saved_counter)
            if self.verbose:
                print(f"   🔄 Restored game counter: {saved_counter}")
        
        if resume_mode:
            print(f"🔄 Resumed {len(self.instances)} automation instances from saved state")
        else:
            print(f"🚀 Created {len(self.instances)} automation instances")
    
    def start(self):
        """Start the automation engine"""
        self.create_instances()
        
        if not self.instances:
            print("❌ No instances created")
            return False
        
        # Start instance threads
        threads = []
        for instance in self.instances:
            if self.verbose:
                print(f"🚀 Starting thread for Instance #{instance.instance_number}")
            thread = threading.Thread(target=instance.run_automation, daemon=True)
            threads.append(thread)
            thread.start()
        
        if self.verbose:
            print("✅ All instance threads started!")
            print("Keyboard commands:")
            print("  'q' - Quit all instances")
            print("  's' - Show detailed status (extra detail in verbose mode)")
        else:
            print("✅ All instances started! Press 'q' to stop, 's' for status")
        
        # Track start time for statistics
        start_time = time.time()
        
        # Main keyboard listener loop
        try:
            while self.running:
                # Check if any instance is still running
                any_running = any(instance.running for instance in self.instances)
                if not any_running:
                    if self.verbose:
                        print("🏁 All instances have stopped")
                    break
                
                # Write status to file every 5 seconds
                current_time = time.time()
                if current_time - self.last_status_write >= 5.0:
                    self.write_status_to_file(start_time)
                    self.last_status_write = current_time
                
                # Save state every 30 seconds for resume capability
                if not hasattr(self, 'last_state_save'):
                    self.last_state_save = current_time
                elif current_time - self.last_state_save >= 30.0:
                    self.save_state_to_file()
                    self.last_state_save = current_time
                
                # Check for completion and cleanup
                if not hasattr(self, 'last_completion_check'):
                    self.last_completion_check = current_time
                elif current_time - self.last_completion_check >= 10.0:  # Check every 10 seconds
                    if self.check_completion_and_cleanup():
                        if self.verbose:
                            print("🎉 Automation completed successfully!")
                    self.last_completion_check = current_time
                
                # Check for keyboard input
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8').lower()
                    if key == 'q':
                        print("\n🛑 Stopping all instances...")
                        if self.verbose:
                            print("🛑 Sending stop signal to all instances...")
                        self.running = False
                        for instance in self.instances:
                            instance.running = False
                        break
                    elif key == 's':
                        self.show_status(start_time)
                
                # time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt - stopping all instances...")
            if self.verbose:
                print("🛑 Handling keyboard interrupt...")
            self.running = False
            for instance in self.instances:
                instance.running = False
        
        # Save final state before exiting
        print("💾 Saving final state...")
        self.save_state_to_file()
        
        # Wait for threads to finish
        print("⏳ Waiting for all instances to stop...")
        if self.verbose:
            print("⏳ Joining instance threads...")
        
        for i, thread in enumerate(threads, 1):
            if self.verbose:
                print(f"⏳ Waiting for Instance #{i} thread...")
            thread.join(timeout=5)
        
        # Show final summary
        self.show_final_summary(start_time)
        
        return True
    
    def show_final_summary(self, start_time: float):
        """Show final summary statistics"""
        elapsed_time = time.time() - start_time
        total_sessions = sum(instance.instance_data['session_count'] for instance in self.instances)
        sessions_per_hour = (total_sessions / elapsed_time) * 3600 if elapsed_time > 0 else 0
        
        print(f"\n📊 FINAL SUMMARY:")
        print(f"🎮 Game: {self.game.get_display_name()}")
        print(f"🤖 Instances: {len(self.instances)} parallel")
        print(f"⏱️  Total runtime: {elapsed_time/3600:.1f} hours")
        print(f"🔄 Total sessions: {total_sessions}")
        print(f"⚡ Average speed: {sessions_per_hour:.1f} sessions/hour")
        
        # Cleanup minicap for all devices
        print("🧹 Cleaning up minicap for all devices...")
        device_list = self.device_manager.get_device_list()
        for device_id in device_list:
            if self.verbose:
                print(f"   Cleaning up minicap for device: {device_id}")
            self.device_manager.cleanup_minicap_for_device(device_id)
        
        # Cleanup streaming if enabled
        if self.use_streaming and self.stream_manager:
            print("🧹 Cleaning up streaming...")
            self.stream_manager.stop_all_streaming()
        
        print("✅ Cleanup completed") 