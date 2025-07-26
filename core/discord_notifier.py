"""
Discord Notifier for sending webhook notifications
"""

import requests
import time
from typing import Dict, Any, Optional


class DiscordNotifier:
    """Handles Discord webhook notifications"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
    
    def set_webhook_url(self, webhook_url: str):
        """Set the Discord webhook URL"""
        self.webhook_url = webhook_url
    
    def has_webhook(self) -> bool:
        """Check if webhook is configured"""
        return self.webhook_url is not None and self.webhook_url.strip() != ""
    
    def send_notification(self, title: str, description: str = "", 
                         fields: list = None, color: int = 0x00ff00) -> bool:
        """Send a basic notification to Discord"""
        if not self.has_webhook():
            print("⚠️ Discord webhook not configured")
            return False
        
        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            }
            
            if fields:
                embed["fields"] = fields
            
            payload = {"embeds": [embed]}
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                return True
            else:
                print(f"❌ Failed to send Discord notification (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Error sending Discord notification: {e}")
            return False
    
    def send_game_result(self, game_name: str, instance_id: str, device_id: str, 
                        account_id: Optional[str], results: Dict[str, Any]) -> bool:
        """Send game automation results to Discord"""
        if not self.has_webhook():
            return False
        
        try:
            # Extract basic info from results
            total_score = results.get('total_score', 0)
            score_breakdown = results.get('score_breakdown', {})
            detected_items = results.get('detected_items', [])
            cycles_completed = results.get('cycles_completed', 0)
            
            # Build embed
            embed = {
                "title": f"🎯 {game_name.title()} High Score! (Instance: {instance_id})",
                "color": 0x00ff00,
                "description": f"**Device: {device_id}**" + 
                             (f" | **Account ID: `{account_id}`**" if account_id else " | ⚠️ **Account ID: Not Available**"),
                "fields": [
                    {
                        "name": "📊 Total Score",
                        "value": f"**{total_score}** points",
                        "inline": True
                    },
                    {
                        "name": "🤖 Instance",
                        "value": f"{instance_id} (Device: {device_id})",
                        "inline": True
                    },
                    {
                        "name": "🔄 Cycles",
                        "value": f"{cycles_completed} completed",
                        "inline": True
                    }
                ]
            }
            
            # Add item details if available
            if detected_items:
                # Count item occurrences
                item_counts = {}
                for item in detected_items:
                    item_counts[item] = item_counts.get(item, 0) + 1
                
                item_list = []
                for item, count in sorted(item_counts.items()):
                    score = score_breakdown.get(item, 0)
                    item_list.append(f"• **{item}**: {count}x ({score} pts)")
                
                if item_list:
                    embed["fields"].append({
                        "name": "🎁 Items Obtained",
                        "value": "\n".join(item_list[:10]),
                        "inline": False
                    })
                    
                    if len(item_list) > 10:
                        embed["fields"].append({
                            "name": "...",
                            "value": f"And {len(item_list) - 10} more items",
                            "inline": False
                        })
                
                embed["fields"].append({
                    "name": "📈 Total Items",
                    "value": f"{len(detected_items)} items obtained",
                    "inline": True
                })
            
            # Add timestamp
            embed["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            
            payload = {"embeds": [embed]}
            
            print(f"📤 Sending Discord notification: Score {total_score}, Account: {account_id or 'None'}")
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"✅ Discord notification sent successfully!")
                return True
            else:
                print(f"❌ Failed to send Discord notification (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Error sending game result to Discord: {e}")
            return False
    
    def send_error_notification(self, title: str, error_message: str, 
                              instance_id: str = "", device_id: str = "") -> bool:
        """Send error notification to Discord"""
        if not self.has_webhook():
            return False
        
        fields = [
            {
                "name": "❌ Error Details",
                "value": error_message,
                "inline": False
            }
        ]
        
        if instance_id:
            fields.append({
                "name": "🤖 Instance",
                "value": instance_id,
                "inline": True
            })
        
        if device_id:
            fields.append({
                "name": "📱 Device",
                "value": device_id,
                "inline": True
            })
        
        return self.send_notification(
            title=f"⚠️ {title}",
            description="An error occurred during automation",
            fields=fields,
            color=0xff0000  # Red color for errors
        )
    
    def send_status_update(self, title: str, message: str, 
                          stats: Dict[str, Any] = None) -> bool:
        """Send status update to Discord"""
        if not self.has_webhook():
            return False
        
        fields = []
        
        if stats:
            for key, value in stats.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
        
        return self.send_notification(
            title=f"📊 {title}",
            description=message,
            fields=fields,
            color=0x0099ff  # Blue color for status updates
        ) 