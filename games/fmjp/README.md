# FMJP Game Automation

This is a minimal implementation of the FMJP game automation framework. The files are set up with placeholder values that need to be customized for your specific FMJP game.

## Files Created:

### Core Files:
- `fmjp_game.py` - Main game implementation with placeholder methods
- `config.json` - Configuration file with default settings
- `__init__.py` - Package initialization

### Directories:
- `templates/` - For UI element recognition images
- `macros/` - For automated action sequences

## New Feature: Tap Action Offsets

The framework now supports `offset_x` and `offset_y` parameters for tap actions, allowing you to tap at a specific offset from the center of detected templates. Additionally, you can provide explicit coordinates to bypass template matching entirely.

### Template Matching Mode (Default):
```python
# Tap 10 pixels above the center of a detected button
create_tap_action("button_template", offset_x=0, offset_y=-10)

# Tap 5 pixels to the right of the center
create_tap_action("button_template", offset_x=5, offset_y=0)

# Tap at a specific offset with other parameters
create_tap_action(
    "button_template", 
    offset_x=-20, 
    offset_y=15,
    delay_before=0.5,
    likelihood=0.8
)

# Multiple taps with delay
create_tap_action("button_template", tap_times=3, tap_delay=0.2)  # Triple tap with 0.2s delay
create_tap_action("button_template", tap_times=5, tap_delay=0.1)  # Rapid 5 taps
```

### Explicit Coordinates Mode:
```python
# Tap at exact coordinates (ignores template matching)
create_tap_action("button_template", coordinates=(270, 480), offset_x=0, offset_y=70)

# Tap at exact coordinates with offset
create_tap_action("button_template", coordinates=(270, 480), offset_x=10, offset_y=-5)

# Tap at exact coordinates with all parameters
create_tap_action(
    "button_template", 
    coordinates=(270, 480),
    offset_x=0, 
    offset_y=70,
    delay_before=0.5,
    delay_after=2.0
)

# Multiple taps at exact coordinates
create_tap_action("button_template", coordinates=(270, 480), tap_times=2, tap_delay=0.5)  # Double tap
create_tap_action("button_template", coordinates=(270, 480), tap_times=3, tap_delay=0.2)  # Triple tap
```

### Offset Parameters:
- **`offset_x`**: Horizontal offset from template center or coordinates (positive = right, negative = left)
- **`offset_y`**: Vertical offset from template center or coordinates (positive = down, negative = up)
- **`coordinates`**: Explicit coordinates to tap at (bypasses template matching when provided)
- **`tap_times`**: Number of times to tap (default: 1)
- **`tap_delay`**: Delay between taps in seconds (default: 0.1)

### Behavior Rules:
1. **Template Validation**: Always searches for the template first for validation
2. **With `coordinates`**: Validates template exists, then taps at exact coordinates + offset
3. **Without `coordinates`**: Validates template exists, then taps at detected center + offset
4. **Template name**: Required for validation and logging purposes
5. **Multiple Taps**: Executes specified number of taps with configurable delay between taps

## TODO Items (What you need to customize):

### 1. App Package Information
In `fmjp_game.py`, update these methods:
```python
def get_app_package(self) -> str:
    return "com.fmjp.game"  # TODO: Replace with actual package name

def get_app_activity(self) -> str:
    return "com.fmjp.game.MainActivity"  # TODO: Replace with actual activity name
```

### 2. Automation States
Update the `get_automation_states()` method in `fmjp_game.py` to match your game's flow:
- Define the correct states for your game
- Set appropriate timeouts
- Configure template names and macro names
- Set up the state transition logic
- Use offset parameters for precise tapping

### 3. Item Detection
Implement these methods in `fmjp_game.py`:
- `process_screenshot_for_items()` - Detect items/cards in screenshots
- `is_new_cycle()` - Determine when a new cycle starts

### 4. Configuration
Update `config.json`:
- Set correct device resolution
- Configure detection regions for your game
- Set up card/item scoring values
- Add Discord webhook URL if desired
- Adjust template thresholds

### 5. Templates
Add template images to `templates/` directory:
- Screenshot buttons and UI elements
- Crop to just the element you want to detect
- Use PNG format for best quality

### 6. Macros
Create macro files in `macros/` directory:
- Define the exact tap/swipe sequences for your game
- Test each macro to ensure it works correctly

## Testing the Setup:

1. **Validate Game Structure:**
   ```python
   from games.game_factory import GameFactory
   GameFactory.validate_game_structure('fmjp')
   ```

2. **Create Game Instance:**
   ```python
   from games.game_factory import GameFactory
   game = GameFactory.create_game('fmjp')
   ```

3. **Test Configuration:**
   ```python
   game.log_verbose_config()
   ```

## Next Steps:

1. Identify the correct app package and activity names
2. Take screenshots of key UI elements for templates
3. Create macros for the automation sequences
4. Implement item detection logic
5. Test and refine the automation flow
6. Configure Discord notifications if desired
7. Use offset parameters for precise UI interaction

## Notes:

- The current implementation includes basic placeholder methods
- All TODO comments indicate where customization is needed
- The framework follows the same pattern as other games in the project
- Refer to `games/umamusume/` for a complete working example
- The new offset feature allows for more precise UI interaction 