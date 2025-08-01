# Minicap Streaming Guide

This guide explains how to use the new real-time streaming functionality that replaces the file-based screenshot capture to eliminate delays and provide 30fps streaming with OpenCV display.

## Overview

The new streaming system provides:
- **30fps real-time streaming** instead of file-based capture
- **OpenCV display windows** for each device
- **Different ports for each device** (1313, 1314, 1315, etc.)
- **No delays** compared to the previous file-based method
- **Multiple device support** with individual windows

## Quick Start

### Basic Streaming

Stream all connected devices:
```bash
python main.py --stream
```

Stream with custom port start:
```bash
python main.py --stream --stream-port-start 1320
```

### Dedicated Streaming Tool

Use the dedicated streaming script:
```bash
python stream_devices.py
```

Stream specific devices:
```bash
python stream_devices.py --devices emulator-5554,emulator-5556
```

Headless streaming (no display):
```bash
python stream_devices.py --no-display
```

## Features

### 1. Real-time 30fps Streaming
- Eliminates delays from file-based capture
- Maintains consistent 30fps frame rate
- Uses minicap socket interface for efficiency

### 2. Multi-device Support
- Each device gets its own port (1313, 1314, 1315, etc.)
- Individual OpenCV windows for each device
- Automatic device detection and setup

### 3. OpenCV Display
- Real-time display of device screens
- Device information overlay
- ESC key to stop streaming
- Automatic window cleanup

### 4. Port Management
- Automatic port assignment
- Configurable starting port
- Port conflict avoidance
- Clean port forwarding setup/teardown

## Usage Examples

### Command Line Usage

```bash
# Stream all devices
python main.py --stream

# Stream with custom port start
python main.py --stream --stream-port-start 1320

# Dedicated streaming tool
python stream_devices.py

# Stream specific devices
python stream_devices.py --devices emulator-5554,emulator-5556

# Headless streaming
python stream_devices.py --no-display
```

### Programmatic Usage

```python
from core.minicap_stream_manager import MinicapStreamManager
from core.device_manager import DeviceManager

# Initialize
device_manager = DeviceManager()
device_manager.initialize()
devices = device_manager.get_device_list()

# Create stream manager
stream_manager = MinicapStreamManager()

# Start streaming for all devices
stream_manager.start_multi_device_streaming(devices)

# Or start individual streams
for i, device_id in enumerate(devices):
    port = 1313 + i
    stream_manager.start_streaming(device_id, port)
    stream_manager.start_streaming_thread(device_id, f"Device {i+1}")
```

### Frame Processing

```python
# Read individual frames
frame = stream_manager.read_minicap_frame(device_id)
if frame is not None:
    # Process frame (OpenCV numpy array)
    cv2.imshow("Frame", frame)
    cv2.waitKey(1)
```

## Architecture

### MinicapStreamManager
- **setup_minicap()**: Push minicap files to device
- **start_streaming()**: Start minicap service on device
- **read_minicap_frame()**: Read single frame from stream
- **start_streaming_thread()**: Start display thread with OpenCV
- **start_multi_device_streaming()**: Stream all devices
- **stop_streaming()**: Stop streaming for device
- **stop_all_streaming()**: Stop all streams

### Port Management
- Base port: 1313
- Each device gets port + offset
- Automatic port forwarding setup
- Clean teardown on stop

### Threading
- Each device runs in separate thread
- OpenCV windows in separate threads
- Non-blocking main thread
- Graceful shutdown handling

## Configuration

### Port Configuration
```python
stream_manager = MinicapStreamManager()
stream_manager.base_port = 1320  # Start from port 1320
```

### Display Configuration
```python
# Custom display name
stream_manager.start_streaming_thread(device_id, "My Device")

# Frame processing
frame = stream_manager.read_minicap_frame(device_id)
if frame is not None:
    # Resize for display
    frame = cv2.resize(frame, (800, 600))
    cv2.imshow("Custom Window", frame)
```

## Troubleshooting

### Common Issues

1. **No devices found**
   - Check ADB connection: `adb devices`
   - Ensure devices are authorized

2. **Minicap setup fails**
   - Verify minicap files exist in `minicap/` directory
   - Check device compatibility
   - Try manual setup: `python test_streaming.py`

3. **Port conflicts**
   - Use different port start: `--stream-port-start 1320`
   - Check for existing minicap processes

4. **Display issues**
   - Use headless mode: `--no-display`
   - Check OpenCV installation
   - Verify display environment

### Testing

Test the streaming functionality:
```bash
python test_streaming.py
```

Run examples:
```bash
python examples/streaming_example.py
```

## Performance

### Benchmarks
- **File-based method**: 1-3 seconds delay
- **Streaming method**: Real-time (30fps)
- **Memory usage**: Minimal (no file I/O)
- **CPU usage**: Optimized for 30fps

### Optimization Tips
- Use headless mode for automation
- Limit number of devices if performance issues
- Adjust frame rate if needed
- Monitor system resources

## Integration

### With Automation Engine
The streaming can be integrated with the automation engine for real-time monitoring:

```python
# During automation
stream_manager = MinicapStreamManager()
stream_manager.start_streaming(device_id, port)

# Monitor in real-time
while automation_running:
    frame = stream_manager.read_minicap_frame(device_id)
    if frame is not None:
        # Process frame for automation
        process_frame_for_automation(frame)
```

### With Web Interface
Streaming can be integrated with the web interface for remote monitoring:

```python
# Web interface integration
@app.route('/stream/<device_id>')
def stream_device(device_id):
    frame = stream_manager.read_minicap_frame(device_id)
    if frame is not None:
        # Convert to web-friendly format
        return send_frame_as_response(frame)
```

## Migration from File-based Method

### Before (File-based)
```python
# Old method with delays
image_data = minicap_manager.get_screenshot_via_file(device_id)
# 1-3 second delay
```

### After (Streaming)
```python
# New method - real-time
frame = stream_manager.read_minicap_frame(device_id)
# No delay, 30fps
```

## Future Enhancements

- WebRTC streaming for remote access
- Recording functionality
- Advanced frame processing
- Integration with automation states
- Performance monitoring dashboard 