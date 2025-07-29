# Uma Musume Friend Point Spam Service

A comprehensive automation service for Uma Musume friend point spam using support cards. This service allows you to sell friend point spam services to buyers who want to earn support points by using their support cards on friends.

## Features

- **Automated Friend Point Spam**: Automatically navigate through friends and use support cards
- **Service Management**: Create, track, and manage multiple service requests
- **Web Dashboard**: Beautiful web interface for managing the service
- **Progress Tracking**: Real-time tracking of points earned and cycles completed
- **Queue Management**: Handle multiple concurrent requests with priority system
- **Discord Integration**: Optional Discord notifications for service updates
- **Statistics**: Comprehensive service statistics and analytics

## Service Workflow

1. **Buyer submits request** with target points and support card preferences
2. **Service creates request** and adds it to the queue
3. **Automation starts** when a slot becomes available
4. **Bot navigates** through friend list and uses support cards
5. **Progress is tracked** in real-time
6. **Service completes** when target points are reached
7. **Buyer receives** their earned friend points

## Installation

1. Ensure you have the main automation framework installed
2. The friend point service is automatically included in the `games/umamusume-fp/` directory
3. Install required dependencies:
   ```bash
   pip install opencv-python pytesseract pillow flask flask-cors
   ```

## Configuration

The service is configured via `config.json`:

```json
{
    "display_name": "Uma Musume Friend Point Spam",
    "cycles_per_session": 50,
    "minimum_score_threshold": 25,
    "service_config": {
        "max_friends_per_session": 50,
        "friend_point_target": 1000,
        "support_card_priority": ["ssr", "sr", "r"],
        "auto_restart_on_completion": true,
        "notification_settings": {
            "notify_on_ssr_support": true,
            "notify_on_high_points": true,
            "high_points_threshold": 100
        }
    }
}
```

## Usage

### Starting the Service

1. **Start the web interface**:
   ```bash
   python main.py --web-only
   ```

2. **Access the dashboard**:
   - Main dashboard: `http://localhost:5000`
   - Friend point dashboard: `http://localhost:5000/fp`

### Creating Service Requests

Via the web interface:
1. Navigate to `/fp`
2. Fill in the request form:
   - **Buyer ID**: Customer identifier
   - **Target Points**: Number of friend points to earn
   - **Support Card Type**: Auto, SSR, SR, or R only
   - **Priority**: Normal, High, or Urgent
3. Click "Create Request"

Via API:
```bash
curl -X POST http://localhost:5000/api/fp/service/request \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "customer123",
    "target_points": 500,
    "support_card_type": "auto",
    "priority": "normal"
  }'
```

### Managing Requests

- **Start Request**: Begin processing a pending request
- **Pause Request**: Temporarily stop processing
- **Resume Request**: Continue processing a paused request
- **Monitor Progress**: Real-time tracking of points earned

## API Endpoints

### Service Management
- `GET /api/fp/service/status` - Get service status and queue info
- `GET /api/fp/service/stats` - Get service statistics
- `GET /api/fp/service/requests` - Get all requests
- `POST /api/fp/service/request` - Create new request

### Request Management
- `GET /api/fp/service/request/{request_id}` - Get specific request
- `POST /api/fp/service/request/{request_id}/start` - Start request
- `POST /api/fp/service/request/{request_id}/pause` - Pause request
- `POST /api/fp/service/request/{request_id}/resume` - Resume request

## Automation States

The service uses the following automation states:

1. **waiting_for_main_menu** - Wait for main menu to load
2. **navigating_to_friends** - Navigate to friends section
3. **waiting_for_friend_list** - Wait for friend list to load
4. **selecting_friend** - Select first friend from list
5. **waiting_for_friend_profile** - Wait for friend profile to load
6. **using_support_card** - Use support card on friend
7. **waiting_for_support_result** - Wait for support result
8. **collecting_support_points** - Collect support points
9. **returning_to_friend_list** - Return to friend list
10. **session_complete** - Session completed

## Macros

The service uses the following macros:

- `navigate_to_friends.txt` - Navigate to friends section
- `select_first_friend.txt` - Select first friend from list
- `use_support_card.txt` - Use support card on friend
- `collect_support_points.txt` - Collect support points
- `return_to_friend_list.txt` - Return to friend list

## Support Card Detection

The service can detect different types of support cards:

- **SSR Support Cards**: Highest value, 100 points
- **SR Support Cards**: Medium value, 50 points  
- **R Support Cards**: Lower value, 25 points

## Pricing Strategy

Suggested pricing model:

- **SSR Support**: $X per 100 points
- **SR Support**: $Y per 100 points
- **R Support**: $Z per 100 points
- **Auto Selection**: $W per 100 points (best available)

## Monitoring and Analytics

The service provides comprehensive monitoring:

- **Real-time Statistics**: Total requests, completion rate, points earned
- **Queue Management**: Active, pending, and completed requests
- **Progress Tracking**: Points earned vs target for each request
- **Performance Metrics**: Average points per request, success rate

## Discord Integration

Optional Discord webhook integration for notifications:

- **Request Started**: When a new request begins processing
- **High Points Alert**: When significant points are earned
- **SSR Support Alert**: When SSR support cards are used
- **Request Completed**: When target points are reached

## Troubleshooting

### Common Issues

1. **Service not starting**:
   - Check if ADB is properly configured
   - Verify device connection
   - Check template images are available

2. **Low success rate**:
   - Adjust template thresholds in config
   - Update macro coordinates for your device
   - Check support card detection regions

3. **Points not being tracked**:
   - Verify OCR regions are correct
   - Check support points region coordinates
   - Ensure proper image preprocessing

### Debug Mode

Enable verbose logging:
```bash
python main.py umamusume-fp --verbose
```

## Security Considerations

- **Request Validation**: All requests are validated before processing
- **Rate Limiting**: Implement rate limiting for API endpoints
- **Authentication**: Consider adding authentication for web interface
- **Data Privacy**: Secure storage of buyer information

## Future Enhancements

- **Multi-device Support**: Process multiple devices simultaneously
- **Advanced Analytics**: Detailed performance analytics and reporting
- **Payment Integration**: Direct payment processing
- **Mobile App**: Native mobile app for service management
- **AI Optimization**: Machine learning for optimal support card selection

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the automation logs
3. Verify configuration settings
4. Test with a small request first

## License

This service is part of the Uma Musume automation framework and follows the same license terms. 