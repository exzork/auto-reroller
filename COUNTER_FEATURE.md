# Counter Feature Documentation

## Overview

The counter feature allows you to track and increment a counter during automation. The counter starts at 0 and can be incremented using the `create_counter_action()` function in automation states.

## Features

- **Counter starts at 0**: Every game instance starts with a counter value of 0
- **Increment functionality**: Use `create_counter_action()` to increment the counter
- **Status display**: Counter value is shown in status output (press 's' key) regardless of verbose mode
- **Flexible timing**: Counter actions support delay_before and delay_after parameters

## Usage

### 1. Basic Counter Action

```python
from core.action_types import create_counter_action

# Simple counter increment
actions = [create_counter_action()]

# Counter increment with delays
actions = [
    create_counter_action(delay_before=1.0, delay_after=0.5)
]
```

### 2. In Automation States

```python
def get_automation_states(self) -> Dict[str, Dict[str, Any]]:
    return {
        "my_state": {
            "timeout": 30,
            "templates": ["my_template"],
            "actions": [
                create_counter_action(delay_before=0.5),  # Increment counter
                create_macro_action("my_macro")           # Execute macro
            ],
            "next_states": ["next_state"]
        }
    }
```

### 3. Programmatic Access

```python
# Get current counter value
current_value = game.get_counter()

# Increment counter manually
new_value = game.create_increment_counter()

# Reset counter to 0
game.reset_counter()
```

## Status Display

The automation engine automatically writes status to `status.txt` every 5 seconds, so you can monitor progress without needing to press keys. The status file includes:

- Game name and runtime
- Total sessions completed
- Sessions per hour speed
- Counter value
- Individual instance details (in verbose mode)

Example status.txt content:
```
📊 STATUS (2 instances) - 2024-01-15 14:30:25
🎮 Game: My Game
⏱️  Runtime: 0.5 hours
🔄 Total sessions: 10
⚡ Speed: 20.0 sessions/hour
🔢 Counter: 15

   Instance #1: 5 sessions, Score: 45, State: pulling_gacha (12s)
   Instance #2: 5 sessions, Score: 38, State: waiting_for_first_gacha (8s)
```

You can also still press 's' during automation to see the status in the console.

## Example Implementation

The Uma Musume game includes an example of counter usage in the `pulling_first_gacha` state:

```python
"pulling_first_gacha": {
    "timeout": 30,
    "templates": [],
    "actions": [
        create_counter_action(delay_before=1.0),  # Increment counter before gacha
        create_macro_action("first_gacha")
    ],
    "processes_items": True,
    "next_states": ["pulling_gacha"]
}
```

## Counter Action Parameters

- `delay_before` (optional): Delay in seconds before incrementing the counter
- `delay_after` (optional): Delay in seconds after incrementing the counter

## Integration with Existing Code

The counter feature is fully integrated with the existing automation framework:

- Works with all action types (macro, tap, wait, etc.)
- Supports conditional actions and loops
- Compatible with verbose and non-verbose modes
- Persists across state transitions
- Resets when starting new sessions 