# Generic Mobile Game Automation Framework

A modular, extensible framework for automating mobile games with parallel execution support.

## Features

- **Game-agnostic architecture**: Easily add support for new games
- **Parallel execution**: Run multiple instances simultaneously  
- **Configurable parameters**: Adjust speed, instances, cycles via command line
- **Discord notifications**: Automatic webhook notifications for high scores
- **Template-based detection**: Flexible image recognition system
- **Macro automation**: Execute recorded macros with configurable timing
- **State machine**: Robust automation flow with timeout handling
- **Efficient screen capture**: Uses minicap for memory-efficient screen capture without leaks
- **Real-time streaming**: Stream all devices at 30fps with OpenCV display using different ports

## Quick Start

### Prerequisites

- Python 3.7+
- ADB (Android Debug Bridge)
- Connected Android devices/emulators
- Required Python packages: `cv2`, `numpy`, `requests`, `pytesseract`
- Minicap files (included in `minicap/` directory)

### Installation

```bash
# Clone the repository
git clone <repository_url>
cd mobile-game-automation

# Install dependencies
pip install opencv-python numpy requests pytesseract

# Ensure ADB is in your PATH
adb devices

# Verify minicap files are present
ls minicap/
# Should show: minicap  minicap.so
```

### Screen Capture & Streaming

The framework uses **minicap** for efficient screen capture instead of the standard `screencap` command to prevent memory leaks during long-running automation sessions.

**Benefits of minicap:**
- No memory leaks during extended use
- Faster screen capture
- More reliable for overnight automation
- Automatic fallback to screencap if minicap fails
- **Real-time streaming at 30fps with OpenCV display**
- **Multiple device support with different ports**

**Minicap Setup:**
- Minicap files are automatically pushed to devices
- Automatic device detection and configuration
- Graceful fallback to screencap if minicap setup fails

**Streaming Features:**
- Real-time 30fps streaming for all connected devices
- OpenCV display windows for each device
- Different ports for each device (1313, 1314, 1315, etc.)
- Press ESC in any window to stop streaming
- Headless mode available for automation integration

### Basic Usage

```bash
# List available games
python main.py --list-games

# Run Uma Musume automation with default settings
python main.py umamusume

# Run with custom parameters
python main.py umamusume --speed 2.0 --instances 4 --cycles 10

# Use specific device
python main.py umamusume --device emulator-5554 --speed 1.5

# Add Discord webhook
python main.py umamusume --discord-webhook "https://discord.com/api/webhooks/..."

# Enable verbose logging for debugging
python main.py umamusume --verbose --instances 1 --speed 1.0

# Short form verbose flag
python main.py umamusume -v --device emulator-5554

# Stream all devices at 30fps with OpenCV display
python main.py --stream

# Stream with custom port start
python main.py --stream --stream-port-start 1320

# Test minicap integration
python test_minicap.py

# Test streaming functionality
python test_streaming.py

# Dedicated streaming tool
python stream_devices.py
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--speed` | Macro speed multiplier (higher = slower) | 2.4 |
| `--instances` | Number of parallel instances | 8 |
| `--cycles` | Cycles/pulls per session | Game default |
| `--device` | Specific device ID | Auto-detect |
| `--delay` | Inter-macro delay (seconds) | 1.0 |
| `--config` | Custom config file path | None |
| `--discord-webhook` | Discord webhook URL | None |
| `--verbose`, `-v` | Enable verbose logging for debugging | False |
| `--stream` | Stream all devices at 30fps with OpenCV display | False |
| `--stream-port-start` | Starting port for minicap streaming | 1313 |

## Architecture

### Project Structure

```
├── main.py                 # Main entry point
├── core/                   # Core framework components
│   ├── automation_engine.py   # Main automation orchestrator
│   ├── device_manager.py      # ADB device management
│   ├── image_detection.py     # Template matching & image processing
│   ├── macro_executor.py      # Macro execution system
│   └── discord_notifier.py    # Discord webhook notifications
├── games/                  # Game-specific implementations
│   ├── base_game.py           # Abstract base class
│   ├── game_factory.py       # Game instance factory
│   └── umamusume/            # Uma Musume implementation
│       ├── umamusume_game.py  # Game logic
│       ├── config.json        # Game configuration
│       ├── templates/         # Template images
│       ├── macros/           # Game-specific macros
│       └── cards/            # Reference card images
└── README.md
```

### Core Components

#### AutomationEngine
- Orchestrates all components
- Manages multiple parallel instances
- Handles keyboard input and status display

#### DeviceManager  
- ADB device detection and management
- Screenshot capture
- App restart functionality
- Clipboard access

#### ImageDetector
- Template matching using OpenCV
- Image preprocessing for OCR
- Relative coordinate cropping

#### MacroExecutor
- Executes recorded macro files
- Configurable speed and delays
- Game-specific macro resolution

#### DiscordNotifier
- Webhook-based notifications
- Rich embed formatting
- Error and status reporting

## Adding New Games

### 1. Create Game Directory Structure

```bash
mkdir games/yourgame
mkdir games/yourgame/templates
mkdir games/yourgame/macros
```

### 2. Implement Game Class

Create `games/yourgame/yourgame_game.py`:

```python
from games.base_game import BaseGame
from typing import Dict, Any, List, Tuple

class YourgameGame(BaseGame):
    def get_automation_states(self) -> Dict[str, Dict[str, Any]]:
        return {
            "initial_state": {
                "timeout": 60,
                "templates": ["start_button"],
                "macros": ["start_automation"],
                "next_states": ["next_state"]
            }
        }
    
    def get_app_package(self) -> str:
        return "com.example.yourgame"
    
    def get_app_activity(self) -> str:
        return "com.example.yourgame/.MainActivity"
    
    def calculate_score(self, detected_items: List[str]) -> Tuple[int, Dict[str, int]]:
        # Implement scoring logic
        pass
    
    def get_minimum_score_threshold(self) -> int:
        return 50
    
    def process_screenshot_for_items(self, screenshot, instance_data: Dict[str, Any]) -> List[str]:
        # Implement item detection logic
        pass
    
    def is_new_cycle(self, screenshot, instance_data: Dict[str, Any]) -> bool:
        # Implement cycle detection logic
        pass
```

### 3. Create Configuration File

Create `games/yourgame/config.json`:

```json
{
    "display_name": "Your Game Name",
    "cycles_per_session": 10,
    "device_resolution": [540, 960],
    "card_scoring": {
        "rare_item": 20,
        "common_item": 5
    },
    "default_item_score": 1,
    "template_thresholds": {
        "start_button": 0.8
    },
    "detection_regions": {
        "slot1": [0.1, 0.2, 0.2, 0.1]
    }
}
```

### 4. Add Assets

- Place template images in `games/yourgame/templates/`
- Place macro files in `games/yourgame/macros/`
- Place reference images in `games/yourgame/items/` or similar

### 5. Test Your Implementation

```bash
python main.py yourgame --instances 1 --speed 1.0
```

## Configuration

### Game Configuration (config.json)

| Field | Description | Type |
|-------|-------------|------|
| `display_name` | Human-readable game name | string |
| `cycles_per_session` | Default cycles per automation session | number |
| `device_resolution` | Target device resolution [width, height] | array |
| `card_scoring` | Item name to score mapping | object |
| `default_item_score` | Default score for unknown items | number |
| `template_thresholds` | Template detection thresholds (0.0-1.0) | object |
| `detection_regions` | Relative coordinates for item detection | object |

### Detection Regions

Coordinates are specified as relative values (0.0-1.0):
- `[x, y, width, height]`
- `x, y`: Top-left corner position  
- `width, height`: Region dimensions

Example: `[0.1, 0.2, 0.3, 0.4]` means:
- Start at 10% from left, 20% from top
- Width: 30% of screen width
- Height: 40% of screen height

## Automation States

Each game defines a state machine for automation flow:

```json
{
    "state_name": {
        "timeout": 60,                    // Max time in seconds (optional)
        "templates": ["template1"],       // Templates to detect
        "macros": ["macro1", "macro2"],   // Macros to execute
        "processes_items": true,          // Whether to detect items
        "next_states": ["next_state"]     // Possible next states
    }
}
```

### Timeout Behavior

- **With timeout**: States with a `timeout` value will automatically restart the app if they run longer than the specified time
- **Without timeout**: States without a `timeout` field or with `timeout: 0` will run indefinitely without timing out
- **Default behavior**: If no timeout is specified, the state runs indefinitely
- **Timeout adjustment**: Timeouts are automatically adjusted based on the macro speed multiplier

## Keyboard Controls

During automation:
- `q` - Quit all instances
- `s` - Show status of all instances

## Verbose Logging

Enable verbose logging with `--verbose` or `-v` for detailed debugging information:

### What Verbose Mode Provides

- **Detailed initialization**: Shows complete configuration and automation states
- **State transitions**: Logs every state change with timestamps
- **Template detection**: Reports detection attempts and results with thresholds
- **Macro execution**: Shows each macro being executed and success/failure
- **Item processing**: Detailed item detection and scoring information
- **Screenshot capture**: Logs when screenshots are taken and their dimensions
- **Session management**: Complete session lifecycle information
- **Account retrieval**: Clipboard access attempts and results
- **Timeout handling**: App restart procedures and recovery steps

### When to Use Verbose Mode

- **Debugging issues**: When automation gets stuck or behaves unexpectedly
- **Performance analysis**: Understanding where time is spent in automation
- **Configuration testing**: Verifying templates and macros are working correctly
- **Development**: When adding support for new games
- **Troubleshooting**: Diagnosing template detection or macro execution problems

### Example Verbose Output

```bash
python main.py umamusume --verbose --instances 1

🔍 Verbose mode enabled - detailed logging active
📊 Detailed Configuration:
   • App package: com.cygames.umamusume
   • Automation states: 6 defined
     - waiting_for_until_gacha: timeout=30s, templates=['until gacha'], macros=[]
🔍 Instance #1: Detailed initialization for device: emulator-5554
🔄 Instance #1: State transition: waiting_for_until_gacha → executing_until_gacha
🎬 Instance #1: Executing macro: until gacha
✅ Instance #1: Macro 'until gacha' executed successfully
```

### Verbose Status Display

Press `s` during automation for enhanced status in verbose mode:

```
📊 STATUS (1 instances):
🔧 Verbose mode: Active
📊 Detailed Instance Status:
   Instance #1:
     • Device: emulator-5554
     • Sessions: 3
     • Current cycle: 5/9
     • State: pulling_gacha (15.2s)
     • Score: 25 (7 items)
     • Account: 123456789
     • Running: ✅
```

## Discord Integration

Configure webhook URL to receive notifications for high scores:

```bash
python main.py yourgame --discord-webhook "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
```

Notifications include:
- Score breakdown
- Items obtained
- Account information
- Instance details

## Testing Macro Execution

Before running full automation, test macro execution to ensure everything works:

### Quick Macro Test

```bash
# Test macro path resolution and execution
python test_macro.py
```

This test will:
- Check if all expected macro files exist
- Verify macro.py script is working
- Test actual macro execution (with confirmation)
- Show detailed debugging information

### Manual Macro Test

```bash
# Test individual macro execution
python macro.py games/umamusume/macros/gacha.record --width 540 --height 960 --device emulator-5554 --dry-run
```

### Common Macro Issues

1. **Macro files missing**: Check `games/yourgame/macros/` directory
2. **macro.py not found**: Ensure `macro.py` exists in project root
3. **Python path issues**: Run from project root directory
4. **ADB conflicts**: Framework handles ADB, macro.py uses `--skip-adb-check`
5. **Resolution mismatch**: Verify device resolution matches game configuration

## Troubleshooting

### Common Issues

1. **No devices detected**
   - Ensure ADB is installed and in PATH
   - Enable USB debugging on devices
   - Run `adb devices` to verify connection

2. **Template detection fails**
   - Check template image quality and format
   - Adjust detection thresholds in config
   - Verify template placement in correct directory

3. **Macro execution fails**
   - Ensure macro files exist and are accessible
   - Check macro.py script is available
   - Verify device resolution matches macro recordings
   - Use test script: `python test_macro.py`
   - Enable verbose mode: `python main.py game --verbose`

4. **OCR not working**
   - Install Tesseract OCR
   - Check image preprocessing in game implementation
   - Verify detection regions are correctly positioned

### Debug Tips

- **Use verbose mode**: Start with `--verbose` for detailed logging (`python main.py game --verbose`)
- Start with single instance (`--instances 1`)
- Use slower speed (`--speed 1.0`) for debugging
- Check console output for error messages
- Verify file paths and permissions
- Monitor state transitions and timing with verbose logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your game support
4. Test thoroughly
5. Submit a pull request

## License

This project is provided as-is for educational purposes. Ensure compliance with game terms of service and local laws when using automation tools. 

## Action Types

The framework supports multiple action types for automation:

### Macro Actions
Execute pre-recorded macro files:
```python
create_macro_action("macro_name", timeout=30, speed_multiplier=1.5)
```

### Tap Actions
Tap at template locations or coordinates:
```python
create_tap_action("button_template", coordinates=(100, 200), delay_before=0.5)
```

### Typing Actions
Input text with keyboard:
```python
create_typing_action(
    text="123456789",
    template="input_field",  # Template to tap before typing
    clear_first=True,        # Clear existing text first
    press_enter=True,        # Press Enter after typing
    delay_after=1.0
)
```

### Wait Actions
Wait for specified duration or condition:
```python
create_wait_action(2.5, condition="loading_screen", timeout=30)
```

### Swipe Actions
Perform swipe gestures:
```python
create_swipe_action(
    start_coordinates=(100, 200),
    end_coordinates=(300, 400),
    duration=1000  # milliseconds
)
```

### Screenshot Actions
Capture and optionally process screenshots:
```python
create_screenshot_action(save_path="debug.png", process_items=True)
```

### Restart Actions
Restart the Android app:
```python
create_restart_action(delay_before=2.0, delay_after=5.0, timeout=30)
```

## Improved Template Detection

The framework now includes improved template detection for tap actions:

- **Automatic Scanning**: If coordinates aren't available, the system automatically scans the current screenshot for the template
- **Real-time Detection**: Templates are detected in real-time before executing taps
- **Coordinate Storage**: Detected coordinates are stored for future use
- **Fallback Handling**: If template detection fails, the action is marked as failed

This ensures more reliable automation even when UI elements move or change positions.

## Action Index Tracking

The framework now includes intelligent action index tracking that prevents unnecessary restarts:

- **Resume from Failure**: When a template is not detected or an action fails, the system stays at the current action index instead of resetting to the beginning of the state
- **Progressive Execution**: Actions are executed sequentially, and successful actions advance the index while failed actions remain at the current position
- **State Persistence**: The action index is maintained within each state, allowing for more efficient automation flows
- **Automatic Reset**: When all actions in a state complete successfully, the index resets to 0 for the next state

### Example Scenario

Consider a state with multiple tap actions:
```python
"career_started": {
    "timeout": 240,
    "templates": [],
    "actions": [
        create_tap_action("skip_sm", likelihood=0.9),
        create_tap_action("shorten_all", likelihood=0.9),
        create_tap_action("confirm", likelihood=0.9),
        create_tap_action("skip_off", likelihood=0.9),
        create_tap_action("skip_1x", likelihood=0.9)
    ],
    "next_states": ["next_state"]
}
```

**Before**: If action 3 ("confirm") fails, the entire state would restart from action 1 on the next iteration.

**After**: If action 3 ("confirm") fails, the system will retry action 3 on the next iteration, preserving the progress of actions 1 and 2.

This feature significantly improves automation reliability and reduces unnecessary repetition of successful actions. 