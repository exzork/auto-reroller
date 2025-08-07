# FMJP Macros Directory

This directory should contain macro files for automated actions.

## Required Macros:
- `start.txt` - Macro for starting the game/process
- `loop_action.txt` - Macro for the main loop action

## Macro Format:
Each macro file should contain a series of actions, one per line:

```
# Example macro format
TAP 500 300  # Tap at coordinates (500, 300)
WAIT 1000    # Wait 1000ms
TAP 600 400  # Tap at coordinates (600, 400)
WAIT 2000    # Wait 2000ms
```

## Available Actions:
- `TAP x y` - Tap at screen coordinates (x, y)
- `WAIT ms` - Wait for specified milliseconds
- `SWIPE x1 y1 x2 y2 duration` - Swipe from (x1,y1) to (x2,y2) over duration ms
- `TYPE text` - Type the specified text
- `KEY keycode` - Press a specific key (e.g., BACK, HOME, etc.)

## Adding New Macros:
1. Create a new .txt file in this directory
2. Write the macro actions using the format above
3. Update the macro names in `fmjp_game.py` automation states
4. Test the macro to ensure it works correctly 