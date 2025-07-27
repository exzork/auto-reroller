# 🌐 Web Interface for Mobile Game Automation

This web interface provides real-time monitoring of your mobile game automation, including device screenshots and automation statistics. It can be accessed locally or exposed to the internet using ngrok.

## ✨ Features

- **Real-time Device Screenshots**: View live screenshots from connected devices at 1 FPS
- **Automation Statistics**: Monitor uptime, cycles, success rates, and connected devices
- **Remote Access**: Access the dashboard from anywhere using ngrok
- **Modern UI**: Beautiful, responsive dashboard with real-time updates
- **Device Management**: View connection status of all devices
- **Automation Controls**: Start/stop automation remotely (when automation engine is available)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup ngrok (for internet access)

Run the setup script to install and configure ngrok:

```bash
python setup_ngrok.py
```

Or install manually:
1. Download from [ngrok.com](https://ngrok.com/download)
2. Create a free account at [ngrok.com](https://ngrok.com)
3. Get your authtoken from the dashboard
4. Run: `ngrok authtoken YOUR_TOKEN`

### 3. Start the Web Interface

#### Option A: Web Interface Only
```bash
python main.py --web-only
```

#### Option B: With Automation
```bash
python main.py umamusume --web --speed 2.0 --instances 4
```

#### Option C: Standalone Web Interface
```bash
python web_interface.py
```

### 4. Access the Dashboard

- **Local**: http://localhost:5000
- **Public**: https://your-ngrok-url.ngrok.io (if ngrok is configured)

## 📊 Dashboard Features

### Statistics Cards
- **Uptime**: Total running time of the automation
- **Total Cycles**: Number of completed automation cycles
- **Success Rate**: Percentage of successful operations
- **Connected Devices**: Number of active devices

### Device Screenshots
- Real-time screenshots from each connected device
- Device connection status indicators
- Automatic refresh at 1 FPS

### Automation Controls
- Start/stop automation remotely
- Real-time status updates
- Error handling and feedback

## 🔧 Configuration Options

### Command Line Arguments

```bash
# Basic web interface
python main.py --web-only

# Web interface with automation
python main.py umamusume --web --speed 2.0 --instances 4

# Custom port and host
python main.py --web-only --web-port 8080 --web-host 127.0.0.1

# Disable ngrok (local only)
python main.py --web-only --no-ngrok

# Verbose mode
python main.py --web-only --verbose
```

### Environment Variables

```bash
# Set ngrok authtoken
export NGROK_AUTHTOKEN=your_token_here

# Set Flask environment
export FLASK_ENV=development
```

## 🌐 Internet Access with ngrok

### Automatic Setup
The web interface automatically creates an ngrok tunnel when available:

1. **Install ngrok**: Run `python setup_ngrok.py`
2. **Authenticate**: Enter your authtoken when prompted
3. **Start interface**: The public URL will be displayed automatically

### Manual Setup
If you prefer to set up ngrok manually:

```bash
# Install ngrok
# Download from https://ngrok.com/download

# Authenticate
ngrok authtoken YOUR_TOKEN

# Start tunnel (in separate terminal)
ngrok http 5000
```

### Public URL
Once ngrok is running, you'll see output like:
```
🌐 Public URL: https://abc123.ngrok.io
🔗 Local URL: http://localhost:5000
```

## 🔒 Security Considerations

### For Internet Exposure
- **HTTPS**: ngrok provides automatic HTTPS encryption
- **Temporary URLs**: ngrok URLs change each time you restart (unless you have a paid plan)
- **Access Control**: Consider adding authentication for production use
- **Firewall**: Ensure your firewall allows the ngrok connection

### For Local Use
- **Localhost Only**: Use `--no-ngrok` flag for local-only access
- **Network Access**: Use `--web-host 0.0.0.0` to allow network access

## 🛠️ Troubleshooting

### ngrok Issues
```bash
# Check ngrok installation
ngrok version

# Test ngrok connection
ngrok http 5000

# Re-authenticate
ngrok authtoken YOUR_TOKEN
```

### ADB Issues
```bash
# Check ADB installation
adb version

# List connected devices
adb devices

# Restart ADB server
adb kill-server
adb start-server
```

### Web Interface Issues
```bash
# Check if port is available
netstat -an | grep 5000

# Try different port
python main.py --web-only --web-port 8080

# Check logs
python main.py --web-only --verbose
```

## 📱 Mobile Access

The dashboard is fully responsive and works great on mobile devices:

- **Touch-friendly**: Large buttons and touch targets
- **Responsive design**: Adapts to different screen sizes
- **Real-time updates**: Works seamlessly on mobile browsers

## 🔄 API Endpoints

The web interface provides REST API endpoints:

- `GET /api/stats` - Get automation statistics
- `GET /api/screenshots` - Get all device screenshots
- `GET /api/devices` - Get connected devices list
- `GET /api/status` - Get system status
- `POST /api/control/start` - Start automation
- `POST /api/control/stop` - Stop automation

## 🎯 Use Cases

### Remote Monitoring
- Monitor automation from anywhere in the world
- Share dashboard with team members
- Real-time alerts and notifications

### Development and Testing
- Debug automation issues remotely
- Test automation on different devices
- Monitor performance and statistics

### Production Deployment
- Monitor automation in production environments
- Provide status updates to stakeholders
- Remote troubleshooting and maintenance

## 📈 Performance

- **Screenshot FPS**: 1 FPS (configurable)
- **Update Frequency**: Stats every 5 seconds, screenshots every 1 second
- **Memory Usage**: Minimal overhead with efficient caching
- **Network**: Optimized image compression for web display

## 🔮 Future Enhancements

- [ ] User authentication and access control
- [ ] Custom dashboard layouts
- [ ] Historical data and charts
- [ ] Push notifications
- [ ] Multi-user support
- [ ] Advanced device management
- [ ] Automation scheduling
- [ ] Performance analytics

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify all dependencies are installed
3. Check the console output for error messages
4. Ensure ngrok and ADB are properly configured

For more help, check the main project README or create an issue in the repository. 