"""
Action Types for Automation Framework
Defines comprehensive typing for automation actions
"""

from typing import Dict, Any, List, Union, Literal, TypedDict, Optional
from enum import Enum


class ActionType(str, Enum):
    """Supported action types"""
    MACRO = "macro"
    TAP = "tap"
    SWIPE = "swipe"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    TYPING = "typing"
    RESTART = "restart"
    COUNTER = "counter"


class MacroAction(TypedDict):
    """Macro action configuration"""
    type: Literal["macro"]
    name: str
    timeout: Optional[int]
    speed_multiplier: Optional[float]


class TapAction(TypedDict):
    """Tap action configuration"""
    type: Literal["tap"]
    template: str
    coordinates: Optional[tuple[int, int]]
    delay_before: Optional[float]
    delay_after: Optional[float]
    likelihood: Optional[float]  # Custom detection threshold (0.0-1.0)
    timeout: Optional[float]  # Timeout in seconds before skipping to next action (None = forever)
    offset_x: Optional[int]  # Offset from template center in X direction
    offset_y: Optional[int]  # Offset from template center in Y direction
    tap_times: Optional[int]  # Number of times to tap (default: 1)
    tap_delay: Optional[float]  # Delay between taps in seconds (default: 0.1)


class SwipeAction(TypedDict):
    """Swipe action configuration"""
    type: Literal["swipe"]
    start_template: Optional[str]
    end_template: Optional[str]
    start_coordinates: Optional[tuple[int, int]]
    end_coordinates: Optional[tuple[int, int]]
    duration: Optional[int]  # milliseconds
    delay_before: Optional[float]
    delay_after: Optional[float]
    start_likelihood: Optional[float]  # Custom detection threshold for start template
    end_likelihood: Optional[float]  # Custom detection threshold for end template


class WaitAction(TypedDict):
    """Wait action configuration"""
    type: Literal["wait"]
    duration: float  # seconds
    condition: Optional[str]  # template to wait for
    timeout: Optional[float]


class ScreenshotAction(TypedDict):
    """Screenshot action configuration"""
    type: Literal["screenshot"]
    save_path: Optional[str]
    process_items: Optional[bool]


class TypingAction(TypedDict):
    """Keyboard typing action configuration"""
    type: Literal["typing"]
    text: str
    clear_first: Optional[bool]  # Whether to clear existing text first
    delay_before: Optional[float]
    delay_after: Optional[float]
    press_enter: Optional[bool]  # Whether to press Enter after typing


class ConditionalAction(TypedDict):
    """Conditional action configuration"""
    type: Literal["conditional"]
    condition: str  # template name
    if_true: List["ActionConfig"]
    if_false: Optional[List["ActionConfig"]]
    timeout: Optional[float]
    likelihood: Optional[float]  # Custom detection threshold for condition template
    if_true_state: Optional[str]  # State to jump to if condition is true
    if_false_state: Optional[str]  # State to jump to if condition is false


class LoopAction(TypedDict):
    """Loop action configuration"""
    type: Literal["loop"]
    actions: List["ActionConfig"]
    max_iterations: Optional[int]
    condition: Optional[str]  # template to check for loop exit
    timeout: Optional[float]
    condition_likelihood: Optional[float]  # Custom detection threshold for condition template
    use_single_screenshot: Optional[bool]  # Use one screenshot for entire loop instead of per action


class RestartAction(TypedDict):
    """Restart app action configuration"""
    type: Literal["restart"]
    delay_before: Optional[float]  # Delay before restarting
    delay_after: Optional[float]   # Delay after restarting
    timeout: Optional[float]       # Timeout for restart operation


class CounterAction(TypedDict):
    """Counter increment action configuration"""
    type: Literal["counter"]
    delay_before: Optional[float]  # Delay before incrementing
    delay_after: Optional[float]   # Delay after incrementing


# Union type for all action configurations
ActionConfig = Union[
    MacroAction,
    TapAction,
    SwipeAction,
    WaitAction,
    ScreenshotAction,
    TypingAction,
    ConditionalAction,
    LoopAction,
    RestartAction,
    CounterAction
]


class StateConfig(TypedDict):
    """Automation state configuration"""
    timeout: int
    templates: List[str]
    actions: List[ActionConfig]
    macros: Optional[List[str]]  # Legacy support
    processes_items: Optional[bool]
    next_states: List[str]
    description: Optional[str]
    if_condition: Optional[str]  # Template to check for conditional execution
    if_true_actions: Optional[List[ActionConfig]]  # Actions to execute if condition is met
    if_false_actions: Optional[List[ActionConfig]]  # Actions to execute if condition is not met
    if_likelihood: Optional[float]  # Custom detection threshold for if condition
    timeout_state: Optional[str]  # State to transition to on timeout (instead of restarting)


class AutomationStates(TypedDict):
    """Complete automation states configuration"""
    __root__: Dict[str, StateConfig]


# Helper functions for action creation
def create_macro_action(name: str, timeout: Optional[int] = None, speed_multiplier: Optional[float] = None) -> MacroAction:
    """Create a macro action"""
    return {
        "type": "macro",
        "name": name,
        "timeout": timeout,
        "speed_multiplier": speed_multiplier
    }


def create_tap_action(template: str, coordinates: Optional[tuple[int, int]] = None, 
                     delay_before: Optional[float] = None, delay_after: Optional[float] = None,
                     likelihood: Optional[float] = None, timeout: Optional[float] = None,
                     offset_x: Optional[int] = None, offset_y: Optional[int] = None,
                     tap_times: Optional[int] = None, tap_delay: Optional[float] = None) -> TapAction:
    """Create a tap action"""
    return {
        "type": "tap",
        "template": template,
        "coordinates": coordinates,
        "delay_before": delay_before,
        "delay_after": delay_after,
        "likelihood": likelihood,
        "timeout": timeout,
        "offset_x": offset_x,
        "offset_y": offset_y,
        "tap_times": tap_times,
        "tap_delay": tap_delay
    }


def create_swipe_action(start_template: Optional[str] = None, end_template: Optional[str] = None,
                       start_coordinates: Optional[tuple[int, int]] = None, 
                       end_coordinates: Optional[tuple[int, int]] = None,
                       duration: Optional[int] = None, delay_before: Optional[float] = None,
                       delay_after: Optional[float] = None, start_likelihood: Optional[float] = None,
                       end_likelihood: Optional[float] = None) -> SwipeAction:
    """Create a swipe action"""
    return {
        "type": "swipe",
        "start_template": start_template,
        "end_template": end_template,
        "start_coordinates": start_coordinates,
        "end_coordinates": end_coordinates,
        "duration": duration,
        "delay_before": delay_before,
        "delay_after": delay_after,
        "start_likelihood": start_likelihood,
        "end_likelihood": end_likelihood
    }


def create_wait_action(duration: float, condition: Optional[str] = None, timeout: Optional[float] = None) -> WaitAction:
    """Create a wait action"""
    return {
        "type": "wait",
        "duration": duration,
        "condition": condition,
        "timeout": timeout
    }


def create_screenshot_action(save_path: Optional[str] = None, process_items: Optional[bool] = None) -> ScreenshotAction:
    """Create a screenshot action"""
    return {
        "type": "screenshot",
        "save_path": save_path,
        "process_items": process_items
    }


def create_typing_action(text: str, clear_first: Optional[bool] = None, delay_before: Optional[float] = None,
                        delay_after: Optional[float] = None, press_enter: Optional[bool] = None) -> TypingAction:
    """Create a typing action"""
    return {
        "type": "typing",
        "text": text,
        "clear_first": clear_first,
        "delay_before": delay_before,
        "delay_after": delay_after,
        "press_enter": press_enter
    }


def create_conditional_action(condition: str, if_true: List[ActionConfig], 
                           if_false: Optional[List[ActionConfig]] = None, timeout: Optional[float] = None,
                           likelihood: Optional[float] = None, if_true_state: Optional[str] = None,
                           if_false_state: Optional[str] = None) -> ConditionalAction:
    """Create a conditional action"""
    return {
        "type": "conditional",
        "condition": condition,
        "if_true": if_true,
        "if_false": if_false or [],  # Ensure if_false is never None
        "timeout": timeout,
        "likelihood": likelihood,
        "if_true_state": if_true_state,
        "if_false_state": if_false_state
    }


def create_loop_action(actions: List[ActionConfig], max_iterations: Optional[int] = None,
                      condition: Optional[str] = None, timeout: Optional[float] = None,
                      condition_likelihood: Optional[float] = None, use_single_screenshot: Optional[bool] = None) -> LoopAction:
    """Create a loop action"""
    return {
        "type": "loop",
        "actions": actions,
        "max_iterations": max_iterations,
        "condition": condition,
        "timeout": timeout,
        "condition_likelihood": condition_likelihood,
        "use_single_screenshot": use_single_screenshot
    }


def create_restart_action(delay_before: Optional[float] = None, delay_after: Optional[float] = None, 
                         timeout: Optional[float] = None) -> RestartAction:
    """Create a restart app action"""
    return {
        "type": "restart",
        "delay_before": delay_before,
        "delay_after": delay_after,
        "timeout": timeout
    }


def create_counter_action(delay_before: Optional[float] = None, delay_after: Optional[float] = None) -> CounterAction:
    """Create a counter increment action"""
    return {
        "type": "counter",
        "delay_before": delay_before,
        "delay_after": delay_after
    }


def create_loop_action_with_single_screenshot(actions: List[ActionConfig], max_iterations: Optional[int] = None,
                                            condition: Optional[str] = None, timeout: Optional[float] = None,
                                            condition_likelihood: Optional[float] = None) -> LoopAction:
    """Create a loop action that uses a single screenshot for the entire loop"""
    return create_loop_action(
        actions=actions,
        max_iterations=max_iterations,
        condition=condition,
        timeout=timeout,
        condition_likelihood=condition_likelihood,
        use_single_screenshot=True
    )


def create_state_with_if_condition(if_condition: str, if_true_actions: List[ActionConfig], 
                                 timeout: Optional[int] = None, templates: Optional[List[str]] = None, 
                                 next_states: Optional[List[str]] = None,
                                 if_false_actions: Optional[List[ActionConfig]] = None,
                                 if_likelihood: Optional[float] = None,
                                 processes_items: Optional[bool] = None,
                                 description: Optional[str] = None) -> StateConfig:
    """Create a state configuration with if condition"""
    return {
        "timeout": timeout,
        "templates": templates or [],
        "actions": [],  # Empty since we're using conditional actions
        "next_states": next_states or [],
        "if_condition": if_condition,
        "if_true_actions": if_true_actions,
        "if_false_actions": if_false_actions or [],
        "if_likelihood": if_likelihood,
        "processes_items": processes_items,
        "description": description
    }


# Type validation functions
def is_valid_action_config(action: Dict[str, Any]) -> bool:
    """Validate if an action configuration is valid"""
    if not isinstance(action, dict):
        return False
    
    action_type = action.get("type")
    if not action_type:
        return False
    
    try:
        ActionType(action_type)
        return True
    except ValueError:
        return False


def validate_action_config(action: Dict[str, Any]) -> List[str]:
    """Validate action configuration and return list of errors"""
    errors = []
    
    if not isinstance(action, dict):
        errors.append("Action must be a dictionary")
        return errors
    
    action_type = action.get("type")
    if not action_type:
        errors.append("Action must have a 'type' field")
        return errors
    
    try:
        ActionType(action_type)
    except ValueError:
        errors.append(f"Invalid action type: {action_type}")
        return errors
    
    # Type-specific validation
    if action_type == "macro":
        if "name" not in action:
            errors.append("Macro action must have a 'name' field")
    
    elif action_type == "tap":
        if "template" not in action:
            errors.append("Tap action must have a 'template' field")
        # Validate likelihood if provided
        likelihood = action.get("likelihood")
        if likelihood is not None:
            if not isinstance(likelihood, (int, float)) or likelihood < 0.0 or likelihood > 1.0:
                errors.append("Tap action likelihood must be a number between 0.0 and 1.0")
        # Validate timeout if provided
        timeout = action.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0.0:
                errors.append("Tap action timeout must be a positive number")
    
    elif action_type == "swipe":
        if not action.get("start_template") and not action.get("start_coordinates"):
            errors.append("Swipe action must have either 'start_template' or 'start_coordinates'")
        if not action.get("end_template") and not action.get("end_coordinates"):
            errors.append("Swipe action must have either 'end_template' or 'end_coordinates'")
        # Validate likelihood parameters if provided
        for likelihood_param in ["start_likelihood", "end_likelihood"]:
            likelihood = action.get(likelihood_param)
            if likelihood is not None:
                if not isinstance(likelihood, (int, float)) or likelihood < 0.0 or likelihood > 1.0:
                    errors.append(f"Swipe action {likelihood_param} must be a number between 0.0 and 1.0")
    
    elif action_type == "wait":
        if "duration" not in action:
            errors.append("Wait action must have a 'duration' field")
        # Validate likelihood if provided
        likelihood = action.get("likelihood")
        if likelihood is not None:
            if not isinstance(likelihood, (int, float)) or likelihood < 0.0 or likelihood > 1.0:
                errors.append("Wait action likelihood must be a number between 0.0 and 1.0")
    
    elif action_type == "conditional":
        if "condition" not in action:
            errors.append("Conditional action must have a 'condition' field")
        if "if_true" not in action:
            errors.append("Conditional action must have an 'if_true' field")
        # Validate likelihood if provided
        likelihood = action.get("likelihood")
        if likelihood is not None:
            if not isinstance(likelihood, (int, float)) or likelihood < 0.0 or likelihood > 1.0:
                errors.append("Conditional action likelihood must be a number between 0.0 and 1.0")
    
    elif action_type == "loop":
        if "actions" not in action:
            errors.append("Loop action must have an 'actions' field")
        # Validate condition_likelihood if provided
        condition_likelihood = action.get("condition_likelihood")
        if condition_likelihood is not None:
            if not isinstance(condition_likelihood, (int, float)) or condition_likelihood < 0.0 or condition_likelihood > 1.0:
                errors.append("Loop action condition_likelihood must be a number between 0.0 and 1.0")
    
    elif action_type == "restart":
        # Validate delay_before if provided
        delay_before = action.get("delay_before")
        if delay_before is not None:
            if not isinstance(delay_before, (int, float)) or delay_before < 0.0:
                errors.append("Restart action delay_before must be a non-negative number")
        # Validate delay_after if provided
        delay_after = action.get("delay_after")
        if delay_after is not None:
            if not isinstance(delay_after, (int, float)) or delay_after < 0.0:
                errors.append("Restart action delay_after must be a non-negative number")
        # Validate timeout if provided
        timeout = action.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout <= 0.0:
                errors.append("Restart action timeout must be a positive number")
    
    elif action_type == "typing":
        if "text" not in action:
            errors.append("Typing action must have a 'text' field")
    
    return errors 