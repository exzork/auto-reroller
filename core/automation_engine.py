"""
Automation Engine for Mobile Game Automation Framework
Handles the core automation logic and state management
"""

import time
import threading
import msvcrt
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .device_manager import DeviceManager
from .macro_executor import MacroExecutor
from .image_detection import ImageDetector
from .discord_notifier import DiscordNotifier
from games.base_game import BaseGame
from .action_types import ActionType, validate_action_config, create_typing_action


class AutomationInstance:
    """Individual automation instance for a specific device"""
    
    def __init__(self, device_id: str, instance_number: int, game: BaseGame, 
                 macro_executor: MacroExecutor, image_detector: ImageDetector,
                 device_manager: DeviceManager, discord_notifier: DiscordNotifier,
                 verbose: bool = False):
        self.device_id = device_id
        self.instance_number = instance_number
        self.game = game
        self.macro_executor = macro_executor
        self.image_detector = image_detector
        self.device_manager = device_manager
        self.discord_notifier = discord_notifier
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
            # Log game-specific verbose configuration if available
            if hasattr(game, 'log_verbose_config'):
                game.log_verbose_config(device_id)
        else:
            print(f"🤖 Instance #{instance_number} initialized for device: {device_id}")
    
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
                break
    
    def check_state_timeout(self) -> bool:
        """Check if current state has been running too long"""
        current_time = time.time()
        time_in_state = current_time - self.current_state_start_time
        
        # Get timeout for current state
        state_timeouts = self.game.get_state_timeouts()
        current_state = self.instance_data['current_state']
        base_timeout = state_timeouts.get(current_state, 240)  # Default 4 minutes
        
        # If timeout is None or 0, this state has no timeout (runs indefinitely)
        if base_timeout is None or base_timeout <= 0:
            return False
        
        # Adjust timeout based on macro speed multiplier
        adjusted_timeout = base_timeout * self.macro_executor.speed_multiplier
        
        if time_in_state > adjusted_timeout:
            print(f"⏰ Instance #{self.instance_number}: TIMEOUT! State '{current_state}' stuck for {time_in_state:.1f}s")
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
        """Handle timeout by restarting app and resetting state"""
        try:
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
    
    def get_screenshot(self):
        """Get screenshot for this device"""
        if self.verbose:
            print(f"📸 Instance #{self.instance_number}: Capturing screenshot")
        
        screenshot_bytes = self.device_manager.get_screenshot(self.device_id)
        if screenshot_bytes:
            screenshot = self.image_detector.bytes_to_image(screenshot_bytes)
            if self.verbose and screenshot is not None:
                h, w = screenshot.shape[:2]
                print(f"📸 Instance #{self.instance_number}: Screenshot captured ({w}x{h})")
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
    
    def execute_tap(self, template_name: str) -> bool:
        """Execute a tap at the saved coordinates for a detected template"""
        coordinates = self.image_detector.get_detected_coordinates(template_name)
        
        # If coordinates not found, try to detect the template first
        if coordinates is None:
            if self.verbose:
                print(f"🔍 Instance #{self.instance_number}: No saved coordinates for template '{template_name}', scanning screenshot...")
            
            # Use stored screenshot if available (for single screenshot loops)
            screenshot = getattr(self, '_current_screenshot', None)
            if screenshot is None:
                screenshot = self.get_screenshot()
            
            if screenshot is None:
                if self.verbose:
                    print(f"❌ Instance #{self.instance_number}: Failed to get screenshot for template detection")
                return False
            
            # Detect the template in the current screenshot
            if self.detect_template(screenshot, template_name):
                # Get the coordinates from the fresh detection
                coordinates = self.image_detector.get_detected_coordinates(template_name)
                if self.verbose:
                    print(f"✅ Instance #{self.instance_number}: Template '{template_name}' detected in current screenshot")
            else:
                if self.verbose:
                    print(f"❌ Instance #{self.instance_number}: Template '{template_name}' not found in current screenshot")
                return False
        
        if coordinates is None:
            if self.verbose:
                print(f"❌ Instance #{self.instance_number}: No coordinates found for template '{template_name}'")
            return False
        
        x, y = coordinates
        if self.verbose:
            print(f"👆 Instance #{self.instance_number}: Executing tap at ({x}, {y}) for template '{template_name}'")
        
        success = self.device_manager.tap(self.device_id, x, y)
        
        if self.verbose:
            if success:
                print(f"✅ Instance #{self.instance_number}: Tap executed successfully")
            else:
                print(f"❌ Instance #{self.instance_number}: Tap execution failed")
        
        return success
    
    def execute_action(self, action_config: Dict[str, Any]) -> bool:
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
            template_name = action_config.get('template')
            coordinates = action_config.get('coordinates')
            delay_before = action_config.get('delay_before')
            delay_after = action_config.get('delay_after')
            likelihood = action_config.get('likelihood')
            timeout = action_config.get('timeout')
            
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
            
            # Apply delays if specified
            if delay_before:
                time.sleep(delay_before)
            
            # Execute tap with timeout handling
            if timeout is not None:
                # Try to execute tap with timeout
                tap_start_time = time.time()
                while time.time() - tap_start_time < timeout:
                    # Execute tap with custom likelihood if specified
                    if likelihood is not None:
                        success = self.execute_tap_with_likelihood(template_name, likelihood)
                    else:
                        success = self.execute_tap(template_name)
                    
                    if success:
                        break
                    
                    # Brief pause before retry
                    time.sleep(0.5)
                else:
                    # Tap timeout reached, log and continue (don't fail the action)
                    if self.verbose:
                        print(f"⏱️ Instance #{self.instance_number}: Tap action '{template_name}' timed out after {timeout}s, continuing to next action")
                    success = True  # Return True to continue to next action
            else:
                # Execute tap without timeout (original behavior)
                if likelihood is not None:
                    success = self.execute_tap_with_likelihood(template_name, likelihood)
                else:
                    success = self.execute_tap(template_name)
            
            if delay_after:
                time.sleep(delay_after)
            
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
            success = self.device_manager.swipe(
                self.device_id, 
                start_coordinates or (0, 0), 
                end_coordinates or (100, 100), 
                duration
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
                    screenshot = self.get_screenshot()
                    if screenshot is not None:
                        if likelihood is not None:
                            detected = self.detect_template_with_likelihood(screenshot, condition, likelihood)
                        else:
                            detected = self.detect_template(screenshot, condition)
                        if detected:
                            return True
                    time.sleep(0.5)
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
            
            screenshot = self.get_screenshot()
            if screenshot is not None:
                if save_path:
                    # Save screenshot (implementation needed)
                    pass
                if process_items:
                    self.process_screenshot_for_items(screenshot)
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
            screenshot = self.get_screenshot()
            if screenshot is not None:
                if likelihood is not None:
                    condition_met = self.detect_template_with_likelihood(screenshot, condition, likelihood)
                else:
                    condition_met = self.detect_template(screenshot, condition)
                
                actions_to_execute = if_true if condition_met else if_false
                target_state = if_true_state if condition_met else if_false_state
                
                if self.verbose:
                    print(f"   {'✅' if condition_met else '❌'} Condition '{condition}' {'met' if condition_met else 'not met'}")
                    print(f"   🎬 Executing {len(actions_to_execute)} action(s)")
                    if target_state:
                        print(f"   🎯 Will jump to state: {target_state}")
                
                # Execute actions
                for action in actions_to_execute:
                    if not self.execute_action(action):
                        print(f"❌ Instance #{self.instance_number}: Failed to execute action in conditional")
                        return False
                
                # Handle state jumping if specified
                if target_state:
                    if self.verbose:
                        print(f"   🎯 Instance #{self.instance_number}: Jumping to state: {target_state}")
                    self.change_state(target_state)
                    return True  # Return True since state change was successful
                
                return True
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
                            if not self.execute_action(action):
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
                        if not self.execute_action(action):
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
            
        else:
            print(f"❌ Instance #{self.instance_number}: Unsupported action type: {action_type}")
            return False
    
    def detect_template(self, screenshot, template_name: str) -> bool:
        """Detect a template in the screenshot"""
        if self.verbose:
            print(f"🔍 Instance #{self.instance_number}: Detecting template: {template_name}")
        
        threshold = self.game.get_template_threshold(template_name)
        detected = self.image_detector.detect_game_template(
            screenshot, self.game.get_game_name(), template_name, threshold
        )
        
        if self.verbose:
            if detected:
                print(f"✅ Instance #{self.instance_number}: Template '{template_name}' detected (threshold: {threshold})")
            else:
                print(f"❌ Instance #{self.instance_number}: Template '{template_name}' not found (threshold: {threshold})")
        
        return detected
    
    def detect_template_with_likelihood(self, screenshot, template_name: str, likelihood: float) -> bool:
        """Detect a template in the screenshot with custom likelihood threshold"""
        if self.verbose:
            print(f"🔍 Instance #{self.instance_number}: Detecting template: {template_name} (likelihood: {likelihood})")
        
        detected = self.image_detector.detect_game_template(
            screenshot, self.game.get_game_name(), template_name, likelihood
        )
        
        if self.verbose:
            if detected:
                print(f"✅ Instance #{self.instance_number}: Template '{template_name}' detected (likelihood: {likelihood})")
            else:
                print(f"❌ Instance #{self.instance_number}: Template '{template_name}' not found (likelihood: {likelihood})")
        
        return detected
    
    def execute_tap_with_likelihood(self, template_name: str, likelihood: float) -> bool:
        """Execute a tap at the saved coordinates for a detected template with custom likelihood"""
        # Use stored screenshot if available (for single screenshot loops)
        screenshot = getattr(self, '_current_screenshot', None)
        if screenshot is None:
            screenshot = self.get_screenshot()
        
        if screenshot is None:
            print(f"❌ Instance #{self.instance_number}: Failed to get screenshot for tap")
            return False
        
        # Detect template with custom likelihood
        if not self.detect_template_with_likelihood(screenshot, template_name, likelihood):
            print(f"❌ Instance #{self.instance_number}: Template '{template_name}' not detected with likelihood {likelihood}")
            return False
        
        # Get saved coordinates
        coordinates = self.image_detector.get_detected_coordinates(template_name)
        if coordinates is None:
            print(f"❌ Instance #{self.instance_number}: No coordinates saved for template '{template_name}'")
            return False
        
        x, y = coordinates
        if self.verbose:
            print(f"👆 Instance #{self.instance_number}: Tapping at coordinates ({x}, {y}) for template '{template_name}'")
        
        success = self.device_manager.tap(self.device_id, x, y)
        
        if self.verbose:
            if success:
                print(f"✅ Instance #{self.instance_number}: Tap executed successfully")
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
        if not self.device_manager.restart_app(
            self.device_id, 
            self.game.get_app_package(), 
            self.game.get_app_activity()
        ):
            print(f"❌ Instance #{self.instance_number}: Failed to restart app")
            self.stop_background_timeout_checker()
            return False
        
        # Get automation states from game
        automation_states = self.game.get_automation_states()
        
        # Track last detection time to avoid repeated processing
        last_detection_time = 0
        detection_cooldown = 2 * self.macro_executor.speed_multiplier  # Scale cooldown with speed
        
        try:
            while self.running:
                current_time = time.time()
                
                screenshot = self.get_screenshot()
                if screenshot is None:
                    time.sleep(0.5 * self.macro_executor.speed_multiplier)
                    continue
                
                current_state = self.instance_data['current_state']
                
                # Get state configuration
                if current_state not in automation_states:
                    print(f"❌ Instance #{self.instance_number}: Unknown state '{current_state}'")
                    break
                
                state_config = automation_states[current_state]
                
                if self.verbose and current_time - last_detection_time > 30:  # Log current state every 30 seconds
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
                
                # Determine if we should execute actions
                # Execute if: (template detected) OR (state has actions/macros but no templates to detect)
                should_execute_actions = (
                    (template_detected and current_time - last_detection_time > detection_cooldown) or
                    (not templates and (actions or macros) and current_time - last_detection_time > detection_cooldown)
                )
                
                # Special handling for "completed" state - trigger session completion
                if current_state == 'completed' and current_time - last_detection_time > detection_cooldown:
                    if self.verbose:
                        print(f"🏁 Instance #{self.instance_number}: Reached completed state, finishing session")
                    
                    # Complete the session (sends Discord notification and resets)
                    self.complete_session()
                    last_detection_time = current_time
                    continue
                
                # Handle states with no templates and no actions (auto-transition)
                if not templates and not actions and not macros and current_time - last_detection_time > detection_cooldown:
                    next_states = state_config.get('next_states', [])
                    if next_states:
                        next_state = next_states[0]
                        if self.verbose:
                            print(f"🔄 Instance #{self.instance_number}: Auto-transitioning from '{current_state}' to '{next_state}' (no actions required)")
                        self.change_state(next_state)
                        last_detection_time = current_time
                    continue
                
                # Process state logic
                if should_execute_actions:
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
                        if self.verbose:
                            print(f"🔀 Instance #{self.instance_number}: Checking if condition: {if_condition}")
                        
                        # Check if condition
                        condition_met = False
                        if screenshot is not None:
                            if if_likelihood is not None:
                                condition_met = self.detect_template_with_likelihood(screenshot, if_condition, if_likelihood)
                            else:
                                condition_met = self.detect_template(screenshot, if_condition)
                        
                        if self.verbose:
                            print(f"   {'✅' if condition_met else '❌'} If condition '{if_condition}' {'met' if condition_met else 'not met'}")
                        
                        # Execute appropriate actions based on condition
                        actions_to_execute = if_true_actions if condition_met else if_false_actions
                        if self.verbose:
                            print(f"   🎬 Executing {len(actions_to_execute)} action(s) for {'true' if condition_met else 'false'} branch")
                        
                        # Execute conditional actions
                        for i, action in enumerate(actions_to_execute):
                            if self.verbose:
                                print(f"🎬 Instance #{self.instance_number}: Executing conditional action {i + 1}/{len(actions_to_execute)}")
                            
                            if not self.execute_action(action):
                                if self.verbose:
                                    print(f"❌ Instance #{self.instance_number}: Conditional action {i + 1} failed")
                                action_success = False
                                break
                    else:
                        # Handle regular actions (existing logic)
                        if actions:
                            if self.verbose:
                                print(f"🎬 Instance #{self.instance_number}: Executing {len(actions)} action(s) starting from index {self.current_action_index}")
                            
                            # Execute actions starting from the current index
                            for i in range(self.current_action_index, len(actions)):
                                action = actions[i]
                                if self.verbose:
                                    print(f"🎬 Instance #{self.instance_number}: Executing action {i + 1}/{len(actions)}")
                                
                                if not self.execute_action(action):
                                    # Action failed, stay at current index for next iteration
                                    if self.verbose:
                                        print(f"❌ Instance #{self.instance_number}: Action {i + 1} failed, will retry from this action")
                                    action_success = False
                                    break
                                else:
                                    # Action succeeded, move to next action
                                    self.current_action_index = i + 1
                                
                                # Process items if this is a cycle where items are obtained
                                if state_config.get('processes_items', False):
                                    if self.verbose:
                                        print(f"🎁 Instance #{self.instance_number}: Processing items after action")
                                    
                                    time.sleep(2 * self.macro_executor.speed_multiplier)  # Wait for items to appear (respects speed)
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
                            
                            # If all actions completed successfully, reset action index
                            if action_success:
                                self.current_action_index = 0
                        
                        # Handle legacy macro system
                        elif macros:
                            if self.verbose:
                                print(f"🎬 Instance #{self.instance_number}: Executing {len(macros)} macro(s) starting from index {self.current_action_index}: {macros}")
                            
                            # Execute macros starting from the current index
                            for i in range(self.current_action_index, len(macros)):
                                macro = macros[i]
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
                                
                                # Process items if this is a cycle where items are obtained
                                if state_config.get('processes_items', False):
                                    if self.verbose:
                                        print(f"🎁 Instance #{self.instance_number}: Processing items after macro '{macro}'")
                                    
                                    time.sleep(2 * self.macro_executor.speed_multiplier)  # Wait for items to appear (respects speed)
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
                            
                            # If all macros completed successfully, reset action index
                            if action_success:
                                self.current_action_index = 0
                    
                    # Transition to next state
                    if action_success:
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
                    else:
                        if self.verbose:
                            print(f"❌ Instance #{self.instance_number}: Action execution failed, staying in current state")
                    
                    last_detection_time = current_time
                
                time.sleep(0.5 * self.macro_executor.speed_multiplier)  # Main loop delay (respects speed)
                
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
                 max_instances: int = 8, verbose: bool = False):
        self.game = game
        self.device_manager = device_manager
        self.macro_executor = MacroExecutor(speed_multiplier, inter_macro_delay, verbose)
        self.image_detector = ImageDetector()
        self.discord_notifier = DiscordNotifier(game.get_discord_webhook())
        self.max_instances = max_instances
        self.verbose = verbose
        self.instances = []
        self.running = True
        
        if self.verbose:
            print(f"🔧 AutomationEngine: Initialized with verbose logging")
            print(f"   Speed multiplier: {speed_multiplier}x")
            print(f"   Inter-macro delay: {inter_macro_delay}s")
            print(f"   Max instances: {max_instances}")
    
    def create_instances(self):
        """Create automation instances for available devices"""
        device_list = self.device_manager.get_device_list()[:self.max_instances]
        
        if self.verbose:
            print(f"🔧 AutomationEngine: Creating {len(device_list)} instances")
        
        # Initialize minicap for each device
        print("🔧 Setting up minicap for all devices...")
        for device_id in device_list:
            if self.verbose:
                print(f"   Setting up minicap for device: {device_id}")
            
            # Setup minicap for the device
            if self.device_manager.setup_minicap_for_device(device_id):
                # Start minicap service
                if self.device_manager.start_minicap_for_device(device_id):
                    if self.verbose:
                        print(f"   ✅ Minicap started for device: {device_id}")
                else:
                    print(f"   ⚠️ Failed to start minicap for device: {device_id}")
            else:
                print(f"   ⚠️ Failed to setup minicap for device: {device_id}")
        
        # Create automation instances
        for i, device_id in enumerate(device_list, 1):
            instance = AutomationInstance(
                device_id, i, self.game, self.macro_executor,
                self.image_detector, self.device_manager, self.discord_notifier,
                self.verbose
            )
            self.instances.append(instance)
        
        print(f"🚀 Created {len(self.instances)} automation instances")
    
    def show_status(self, start_time: float):
        """Show current status of all instances"""
        elapsed_time = time.time() - start_time
        total_sessions = sum(instance.instance_data['session_count'] for instance in self.instances)
        sessions_per_hour = (total_sessions / elapsed_time) * 3600 if elapsed_time > 0 else 0
        
        print(f"\n📊 STATUS ({len(self.instances)} instances):")
        print(f"🎮 Game: {self.game.get_display_name()}")
        print(f"⏱️  Runtime: {elapsed_time/3600:.1f} hours")
        print(f"🔄 Total sessions: {total_sessions}")
        print(f"⚡ Speed: {sessions_per_hour:.1f} sessions/hour")
        
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
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt - stopping all instances...")
            if self.verbose:
                print("🛑 Handling keyboard interrupt...")
            self.running = False
            for instance in self.instances:
                instance.running = False
        
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
        
        print("✅ Cleanup completed") 