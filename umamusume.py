import cv2
import numpy as np
import subprocess
import os
import time
import configparser
import pyperclip
import sys
import re
import threading
import msvcrt  # For Windows keyboard input
import tempfile
import json
import requests  # For Discord webhook
import pytesseract
import argparse  # Add argparse for command-line arguments

# Configuration for card reading
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
SLOT_FOLDER = os.path.join(BASE_DIR, "slotcard")
MATCH_DISTANCE_THRESHOLD = 60
MIN_GOOD_MATCHES = 45

# Global variables for accumulating results
all_detected_cards = []
pull_count = 0
last_support_points = None
running = True
device_width = 540
device_height = 960

# Coordinates for support points region (x1, y1, x2, y2)
SUPPORT_POINTS_REGION = (400, 805, 435, 830)

# Discord webhook configuration
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1397533050698600478/VIchivVH-XAXUYh0iecVhavRKpNsQFsN8GUvWlZb9_D2JJu2G3Iqj9so3HgrjA-te5GT"  # Add your Discord webhook URL here
    # Example: DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# Card scoring configuration
CARD_SCORES = {
    "kitasan": 15,
    "supercreek": 10, 
    "finemotion": 10
}
DEFAULT_CARD_SCORE = 5
MINIMUM_SCORE_THRESHOLD = 45

# App management configuration
APP_PACKAGE_NAME = "com.cygames.umamusume"  # Add your app package name here
APP_ACTIVITY_NAME = "com.cygames.umamusume/jp.co.cygames.umamusume_activity.UmamusumeActivity"

# These will be set by command-line arguments
MACRO_SPEED_MULTIPLIER = 2.4  # Default value, will be overridden by args
PARALLEL_INSTANCES = 8        # Default value, will be overridden by args
MAX_GACHA_PULLS = 9          # Default value, will be overridden by args
INTER_MACRO_DELAY = 1        # Default value

# State-specific timeout configuration (in seconds)
STATE_TIMEOUTS = {
    "waiting_for_until_gacha": 30,      # 1.5 minutes - waiting for initial detection
    "executing_until_gacha": 110,        # 1 minute - executing until gacha macro
    "waiting_for_first_gacha": 15,      # 15 seconds - waiting for first gacha screen
    "pulling_gacha": 180,               # 2 minutes - pulling gacha (can take time)
    "executing_bind_id": 80,            # 55 seconds - executing bind ID macro
    "completed": 30                     # 30 seconds - completed state (should be quick)
}
DEFAULT_STATE_TIMEOUT = 240  # Default timeout for any undefined states

# Global variables for the new gacha automation workflow
gacha_pull_count = 0
automation_state = "waiting_for_until_gacha"  # States: waiting_for_until_gacha, waiting_for_first_gacha, pulling_gacha, executing_bind_id, completed
current_account_id = None
session_count = 0  # Track how many complete automation cycles we've done

# Parallel execution settings
DEVICE_IDS = []  # Will be populated with connected device IDs

# Parse command-line arguments
def parse_arguments():
    """Parse command-line arguments for script configuration"""
    parser = argparse.ArgumentParser(
        description="Uma Musume Gacha Automation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python umamusume.py --speed 2.0 --instances 4 --pulls 10
  python umamusume.py --device emulator-5554 --speed 1.5
  python umamusume.py --instances 2 --pulls 5 --speed 3.0
        """
    )
    
    parser.add_argument('--speed', '--multiplier', 
                       type=float, 
                       default=2.4,
                       help='Macro speed multiplier (default: 2.4). Higher = slower execution for stability')
    
    parser.add_argument('--instances', '--parallel',
                       type=int,
                       default=8,
                       help='Number of parallel instances to run (default: 8)')
    
    parser.add_argument('--pulls', '--gacha',
                       type=int,
                       default=9,
                       help='Number of gacha pulls per cycle (default: 9)')
    
    parser.add_argument('--device',
                       type=str,
                       help='Specific device ID to use (overrides parallel instances)')
    
    parser.add_argument('--delay',
                       type=float,
                       default=1.0,
                       help='Inter-macro delay in seconds (default: 1.0)')
    
    return parser.parse_args()

# Parse arguments and set global variables
args = parse_arguments()
MACRO_SPEED_MULTIPLIER = args.speed
PARALLEL_INSTANCES = args.instances
MAX_GACHA_PULLS = args.pulls
INTER_MACRO_DELAY = args.delay
device_override = args.device

# Show help information if running with default values (likely first time user)
if (args.speed == 2.4 and args.instances == 8 and args.pulls == 9 and 
    args.delay == 1.0 and args.device is None and len(sys.argv) == 1):
    print("💡 Running with default settings. Use --help to see all configuration options:")
    print("   python umamusume.py --help")
    print("")

# Validation
if MACRO_SPEED_MULTIPLIER < 0.1:
    print("❌ Error: Macro speed multiplier must be at least 0.1")
    sys.exit(1)

if PARALLEL_INSTANCES < 1:
    print("❌ Error: Number of parallel instances must be at least 1")
    sys.exit(1)

if MAX_GACHA_PULLS < 1:
    print("❌ Error: Number of gacha pulls must be at least 1")
    sys.exit(1)

if INTER_MACRO_DELAY < 0:
    print("❌ Error: Inter-macro delay cannot be negative")
    sys.exit(1)

# ----------------- Utility: Execute macro -----------------

def execute_macro(record_file, device_id, width=540, height=960):
    """Run macro.py on the given device. Returns True on success."""
    try:
        cmd = [
            'python', 'macro.py', record_file,
            '--width', str(width), '--height', str(height),
            '--device', device_id,
            '--speed', str(MACRO_SPEED_MULTIPLIER)
        ]
        env = os.environ.copy()
        env['ADB_DEVICE_ID'] = device_id
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
        if result.returncode == 0:
            return True
        else:
            print(f"❌ execute_macro failed ({record_file}): {result.stderr.strip() if result.stderr else 'no stderr'})")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ execute_macro timed out: {record_file}")
        return False
    except Exception as e:
        print(f"❌ execute_macro error: {e}")
        return False

# ----------------- Utility: Get account ID -----------------

def get_account_id(device_id):
    """Retrieve account ID from the device via clipper broadcast."""
    try:
        result = subprocess.run(
            ['adb', '-s', device_id, 'shell', 'am', 'broadcast', '-a', 'clipper.get'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print(f"❌ get_account_id failed (device {device_id})")
            return None
        m = re.search(r'data="([^"]+)"', result.stdout)
        if m:
            return m.group(1)
        return None
    except Exception as e:
        print(f"❌ get_account_id error: {e}")
        return None

# ----------------- Utility: Calculate card score -----------------

def calculate_card_score(cards):
    """Return total score and breakdown dict for a list of card names."""
    total = 0
    breakdown = {}
    for card in cards:
        score = CARD_SCORES.get(card.lower(), DEFAULT_CARD_SCORE)
        total += score
        breakdown[card] = breakdown.get(card, 0) + score
    return total, breakdown

# ----------------- Utility: Crop slot from screenshot -----------------

def crop_slot_from_screenshot(rel_pos, screenshot):
    """Crop a slot region from screenshot using relative positions"""
    try:
        x1, y1, x2, y2 = rel_pos
        
        # Ensure coordinates are within screenshot bounds
        height, width = screenshot.shape[:2]
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))
        
        # Crop the region
        if x2 > x1 and y2 > y1:
            slot_img = screenshot[y1:y2, x1:x2]
            return slot_img
        else:
            return None
    except Exception as e:
        print(f"❌ Error cropping slot: {e}")
        return None

# ----------------- Utility: Match slot image with reference cards -----------------

def match_with_all_refs(slot_img, slot_name, ref_dir):
    """Return best matching reference name (or None) and match count."""
    try:
        # Check if reference directory exists
        if not os.path.exists(ref_dir):
            return None, 0
        
        # Get list of reference files
        ref_files = [f for f in os.listdir(ref_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not ref_files:
            return None, 0
        
        orb = cv2.ORB_create(nfeatures=500)
        kp1, des1 = orb.detectAndCompute(slot_img, None)
        
        if des1 is None:
            return None, 0
        
        best_name, best_count = None, 0
        
        for ref_file in ref_files:
            ref_path = os.path.join(ref_dir, ref_file)
            ref_img = cv2.imread(ref_path)
            
            if ref_img is None:
                continue
            
            # Resize reference to match slot size
            ref_resized = cv2.resize(ref_img, (slot_img.shape[1], slot_img.shape[0]))
            kp2, des2 = orb.detectAndCompute(ref_resized, None)
            
            if des2 is None:
                continue
            
            # Match features
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            good = [m for m in matches if m.distance < MATCH_DISTANCE_THRESHOLD]
            
            match_count = len(good)
            
            # Track best match
            if match_count > best_count:
                best_count = match_count
                best_name = os.path.splitext(ref_file)[0]
        
        # Return result
        if best_count >= MIN_GOOD_MATCHES:
            return best_name, best_count
        else:
            return None, best_count
            
    except Exception:
        return None, 0

class GachaAutomationInstance:
    """Individual automation instance for a specific device"""
    
    def __init__(self, device_id, instance_number):
        self.device_id = device_id
        self.instance_number = instance_number
        self.gacha_pull_count = 0
        self.automation_state = "waiting_for_until_gacha"
        self.current_account_id = None
        self.session_count = 0
        self.all_detected_cards = []
        self.pull_count = 0
        self.last_support_points = None
        self.running = True
        
        # State timeout tracking
        self.last_state_change_time = time.time()
        self.current_state_start_time = time.time()
        
        # Background timeout checker
        self.timeout_thread = None
        self.timeout_detected = False
        
        print(f"🤖 Instance #{instance_number} initialized for device: {device_id}")
        print(f"📸 Instance #{instance_number}: Using ADB exec-out for screenshots")
    
    def start_background_timeout_checker(self):
        """Start background thread to check for timeouts"""
        self.timeout_thread = threading.Thread(target=self._timeout_checker_loop, daemon=True)
        self.timeout_thread.start()
        print(f"⏰ Instance #{self.instance_number}: Background timeout checker started")
    
    def stop_background_timeout_checker(self):
        """Stop background timeout checker"""
        if self.timeout_thread and self.timeout_thread.is_alive():
            self.timeout_thread.join(timeout=1)
        print(f"⏰ Instance #{self.instance_number}: Background timeout checker stopped")
    
    def _timeout_checker_loop(self):
        """Background loop to check for timeouts"""
        while self.running:
            try:
                if self.check_state_timeout():
                    print(f"🚨 Instance #{self.instance_number}: TIMEOUT detected! Restarting app...")
                    
                    # Execute immediate timeout recovery
                    if self.immediate_timeout_recovery():
                        # Reset timeout detection flag
                        self.timeout_detected = False
                    else:
                        print(f"❌ Instance #{self.instance_number}: Timeout recovery failed")
                        self.running = False
                        break
                    
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"❌ Instance #{self.instance_number}: Error in timeout checker: {e}")
                break
    
    def change_state(self, new_state):
        """Change automation state and update timing"""
        if new_state != self.automation_state:
            self.automation_state = new_state
            self.last_state_change_time = time.time()
            self.current_state_start_time = time.time()
    
    def check_state_timeout(self):
        """Check if current state has been running too long (adjusted for macro speed)"""
        current_time = time.time()
        time_in_state = current_time - self.current_state_start_time
        
        # Get timeout for current state, fallback to default if not defined
        base_timeout = STATE_TIMEOUTS.get(self.automation_state, DEFAULT_STATE_TIMEOUT)
        
        # Adjust timeout based on macro speed multiplier
        # If macros are running slower (higher multiplier), we need longer timeouts
        adjusted_timeout = base_timeout * MACRO_SPEED_MULTIPLIER
        
        if time_in_state > adjusted_timeout:
            print(f"⏰ Instance #{self.instance_number}: TIMEOUT! State '{self.automation_state}' stuck for {time_in_state:.1f}s")
            return True
        return False
    
    def kill_and_restart_app(self):
        """Kill and restart the app for this device"""
        try:
            # Kill the app
            kill_cmd = ['adb', '-s', self.device_id, 'shell', 'am', 'force-stop', APP_PACKAGE_NAME]
            result = subprocess.run(kill_cmd, capture_output=True, timeout=10)
            
            # Wait a moment before restarting
            time.sleep(2)
            
            # Restart the app
            start_cmd = ['adb', '-s', self.device_id, 'shell', 'am', 'start', '-W', '-n', APP_ACTIVITY_NAME]
            result = subprocess.run(start_cmd, capture_output=True, timeout=15)
            
            if result.returncode == 0:
                # Wait for app to load
                time.sleep(5)
                # Reset timeout tracking after successful app restart
                self.current_state_start_time = time.time()
                self.last_state_change_time = time.time()
                self.timeout_detected = False
                return True
            else:
                print(f"❌ Instance #{self.instance_number}: Failed to restart app")
                return False
                
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error during app restart: {e}")
            return False
    
    def reset_automation_after_timeout(self):
        """Reset automation state after timeout"""
        try:
            # Kill and restart app
            if self.kill_and_restart_app():
                # Reset state to initial
                self.change_state("waiting_for_until_gacha")
                self.gacha_pull_count = 0
                self.all_detected_cards = []
                self.pull_count = 0
                self.current_account_id = None
                self.last_support_points = None
                return True
            else:
                return False
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error during automation reset: {e}")
            return False
    
    def check_app_running(self):
        """Check if the app is actually running and accessible"""
        try:
            # Check if app is in foreground
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'dumpsys', 'activity', 'activities', '|', 'grep', 'mResumedActivity'],
                capture_output=True, timeout=5, text=True
            )
            
            if result.returncode == 0 and APP_PACKAGE_NAME in result.stdout:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error checking app status: {e}")
            return False
    
    def force_app_restart_with_retry(self):
        """Force restart app with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Kill app
                kill_cmd = ['adb', '-s', self.device_id, 'shell', 'am', 'force-stop', APP_PACKAGE_NAME]
                subprocess.run(kill_cmd, capture_output=True, timeout=10)
                
                time.sleep(2)
                
                # Start app
                start_cmd = ['adb', '-s', self.device_id, 'shell', 'monkey', '-p', APP_PACKAGE_NAME, '-c', 'android.intent.category.LAUNCHER', '1']
                result = subprocess.run(start_cmd, capture_output=True, timeout=15)
                
                if result.returncode == 0:
                    time.sleep(5)
                    # Reset timeout tracking after successful app restart
                    self.current_state_start_time = time.time()
                    self.last_state_change_time = time.time()
                    self.timeout_detected = False
                    return True
                else:
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    print(f"❌ Instance #{self.instance_number}: App restart failed after {max_retries} attempts")
                    return False
        
        return False
    
    def immediate_timeout_recovery(self):
        """Execute immediate timeout recovery"""
        try:
            # Check for running macros and kill them
            if self.check_running_macros_for_device():
                self.kill_running_macros()
            else:
                # No running macros found, proceed with app restart
                pass
            
            # Force restart app
            if self.force_app_restart_with_retry():
                # Reset automation state
                self.reset_automation_after_timeout()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error in immediate timeout recovery: {e}")
            return False
    
    def get_device_adb_prefix(self):
        """Get ADB command prefix with device specification"""
        return ['adb', '-s', self.device_id]
    
    def get_screenshot(self):
        """Get screenshot for this specific device using adb exec-out"""
        try:
            # Use adb exec-out to get screenshot directly
            result = subprocess.run([
                'adb', '-s', self.device_id, 'exec-out', 'screencap', '-p'
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                # Convert binary data to numpy array
                image_array = np.frombuffer(result.stdout, dtype=np.uint8)
                # Decode as image
                screenshot = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                return screenshot
            else:
                print(f"❌ Instance #{self.instance_number}: Failed to get screenshot via exec-out")
                return None
                
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error getting screenshot: {e}")
            return None
    
    def execute_macro(self, record_file, width=540, height=960):
        """Execute macro for this specific device"""
        return execute_macro(record_file, self.device_id, width, height)
    
    def get_account_id(self):
        """Get account ID for this specific device"""
        return get_account_id(self.device_id)
    
    def reset_for_next_cycle(self):
        """Reset this instance for the next cycle"""
        self.session_count += 1
        self.gacha_pull_count = 0
        self.last_support_points = None
        self.current_account_id = None
        self.all_detected_cards = []
        self.pull_count = 0
        
        print(f"\n🔄 Instance #{self.instance_number} starting cycle #{self.session_count}")
        print(f"   Device {self.device_id}: Waiting for next 'until gacha.png' detection...")
        
        # Reset to initial state with fresh timing
        self.change_state("waiting_for_until_gacha")
        
        # Brief pause between cycles for stability
        time.sleep(3)
    
    def calculate_score(self):
        """Calculate score for this instance's cards"""
        return calculate_card_score(self.all_detected_cards)
    
    def send_results_to_discord(self):
        """Send this instance's results to Discord if score meets threshold"""
        if not self.all_detected_cards:
            return False
            
        total_score, score_breakdown = self.calculate_score()
        
        if total_score >= MINIMUM_SCORE_THRESHOLD:
            print(f"🎯 Instance #{self.instance_number}: HIGH SCORE! ({total_score} >= {MINIMUM_SCORE_THRESHOLD})")
            if DISCORD_WEBHOOK_URL:
                return self.send_to_discord_webhook(total_score, score_breakdown)
            else:
                print("⚠️ Discord webhook URL not configured!")
                return False
        else:
            print(f"📊 Instance #{self.instance_number}: Score {total_score} < {MINIMUM_SCORE_THRESHOLD} - Not sending")
            return False
    
    def send_to_discord_webhook(self, total_score, score_breakdown):
        """Send results to Discord with instance information"""
        try:
            # Count card occurrences
            card_counts = {}
            for card in self.all_detected_cards:
                card_counts[card] = card_counts.get(card, 0) + 1
            
            # Build embed with instance information
            embed = {
                "title": f"🎯 Instance #{self.instance_number} High Score! (Account: {self.current_account_id or 'Unknown'})",
                "color": 0x00ff00,
                "description": f"**Device: {self.device_id}** | **Account ID: `{self.current_account_id}`**" if self.current_account_id else f"**Device: {self.device_id}** | ⚠️ **Account ID: Not Available**",
                "fields": [
                    {
                        "name": "📊 Total Score",
                        "value": f"**{total_score}** points",
                        "inline": True
                    },
                    {
                        "name": "🤖 Instance",
                        "value": f"#{self.instance_number} (Device: {self.device_id})",
                        "inline": True
                    },
                    {
                        "name": "📈 Cards Obtained",
                        "value": f"{len(self.all_detected_cards)} total cards",
                        "inline": True
                    }
                ]
            }
            
            # Add card breakdown
            card_list = []
            for card, count in sorted(card_counts.items()):
                score = score_breakdown.get(card, 0)
                card_list.append(f"• **{card}**: {count}x ({score} pts)")
            
            if card_list:
                embed["fields"].append({
                    "name": "🃏 Card Details",
                    "value": "\n".join(card_list[:10]),
                    "inline": False
                })
                
                if len(card_list) > 10:
                    embed["fields"].append({
                        "name": "...",
                        "value": f"And {len(card_list) - 10} more cards",
                        "inline": False
                    })
            
            # Add timestamp
            embed["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            
            payload = {"embeds": [embed]}
            
            print(f"📤 Instance #{self.instance_number}: Sending to Discord (Score: {total_score}, Account: {self.current_account_id or 'None'})")
            
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"✅ Instance #{self.instance_number}: Results sent to Discord!")
                return True
            else:
                print(f"❌ Instance #{self.instance_number}: Failed to send to Discord (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error sending to Discord: {e}")
            return False
    
    def run_automation(self):
        """Main automation logic for this instance"""
        # Start background timeout checker
        self.start_background_timeout_checker()
        
        # Kill and restart app at instance start for clean state
        if not self.kill_and_restart_app():
            self.stop_background_timeout_checker()
            return False
        
        # Reset timeout tracking after app restart
        self.change_state("waiting_for_until_gacha")
        
        # Load template images
        until_gacha_template = cv2.imread("step/until gacha.png", cv2.IMREAD_COLOR)
        first_gacha_template = cv2.imread("step/first_gacha.png", cv2.IMREAD_COLOR)
        
        if until_gacha_template is None or first_gacha_template is None:
            return False
        
        # Track last detection time to avoid repeated processing
        last_detection_time = 0
        detection_cooldown = 2  # 2 second cooldown between detections
        
        try:
            while self.running:
                current_time = time.time()
                
                frame = self.get_screenshot()
                if frame is None:
                    time.sleep(0.5)
                    continue
                
                # State machine for gacha automation
                if self.automation_state == "waiting_for_until_gacha":
                    if detect_image(frame, until_gacha_template, threshold=0.8):
                        if current_time - last_detection_time > detection_cooldown:
                            # Change to executing state first
                            self.change_state("executing_until_gacha")
                            last_detection_time = current_time
                            
                elif self.automation_state == "executing_until_gacha":
                    # Execute the until gacha macro
                    if current_time - last_detection_time > detection_cooldown:
                        if self.execute_macro("./macro/until gacha.record"):
                            self.change_state("waiting_for_first_gacha")
                        else:
                            # Fall back to waiting state if macro fails
                            self.change_state("waiting_for_until_gacha")
                        
                        last_detection_time = current_time
                            
                elif self.automation_state == "waiting_for_first_gacha":
                    if detect_image(frame, first_gacha_template, threshold=0.8):
                        if current_time - last_detection_time > detection_cooldown:
                            
                            if self.execute_macro("./macro/first_gacha.record"):
                                self.change_state("pulling_gacha")
                                self.gacha_pull_count = 1
                                time.sleep(2)
                                try:
                                    self.read_cards_for_instance()
                                except Exception as e:
                                    print(f"❌ Instance #{self.instance_number}: Error reading cards from first pull: {e}")
                                
                            else:
                                print(f"❌ Instance #{self.instance_number}: Failed to execute first gacha macro")
                            
                            last_detection_time = current_time
                            
                elif self.automation_state == "pulling_gacha":
                    if self.gacha_pull_count < MAX_GACHA_PULLS:
                        if current_time - last_detection_time > detection_cooldown:
                            if self.execute_macro("./macro/gacha.record"):
                                self.gacha_pull_count += 1
                                time.sleep(2)
                                try:
                                    self.read_cards_for_instance()
                                except Exception as e:
                                    print(f"❌ Instance #{self.instance_number}: Error reading cards from pull {self.gacha_pull_count}: {e}")
                                
                                if self.gacha_pull_count >= MAX_GACHA_PULLS:
                                    print(f"🏁 Instance #{self.instance_number}: All {MAX_GACHA_PULLS} pulls completed! Going back home...")
                                    if self.execute_macro("./macro/back_home.record"):
                                        self.change_state("executing_bind_id")
                                    else:
                                        print(f"❌ Instance #{self.instance_number}: Failed to execute back home macro")
                            else:
                                print(f"❌ Instance #{self.instance_number}: Failed to execute gacha pull {self.gacha_pull_count + 1}")
                            
                            last_detection_time = current_time
                            
                elif self.automation_state == "executing_bind_id":
                    if current_time - last_detection_time > detection_cooldown:
                        
                        if self.execute_macro("./macro/bind_id.record"):
                            
                            # Get account ID
                            self.current_account_id = self.get_account_id()
                            
                            if self.current_account_id:
                                print(f"✅ Instance #{self.instance_number}: Account ID captured: {self.current_account_id}")
                            else:
                                print(f"⚠️ Instance #{self.instance_number}: Could not retrieve account ID")
                            
                            self.change_state("completed")
                            print(f"🎉 Instance #{self.instance_number}: Automation cycle completed!")
                            
                            # Show results and send to Discord if score is high enough
                            self.show_final_results()
                            self.send_results_to_discord()
                            
                        else:
                            print(f"❌ Instance #{self.instance_number}: Failed to execute bind ID macro")
                            self.change_state("completed")
                            self.show_final_results()
                        
                        last_detection_time = current_time
                        
                elif self.automation_state == "completed":
                    # Reset for next cycle
                    self.reset_for_next_cycle()
                    last_detection_time = current_time
                
                # Sleep between iterations
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Instance #{self.instance_number}: Interrupted by user")
            self.running = False
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Unexpected error: {e}")
            self.running = False
        
        # Cleanup background timeout checker
        self.stop_background_timeout_checker()
        
        return True
    
    def show_final_results(self):
        """Show final results for this instance"""
        if self.all_detected_cards:
            total_score, score_breakdown = self.calculate_score()
            
            # Count occurrences of each card
            card_counts = {}
            for card in self.all_detected_cards:
                card_counts[card] = card_counts.get(card, 0) + 1
            
            # Sort by card name
            sorted_cards = sorted(card_counts.items())
            
            print(f"\n=== Instance #{self.instance_number} FINAL RESULTS ===")
            print(f"Device: {self.device_id}")
            print(f"Account ID: {self.current_account_id or 'Not available'}")
            print(f"Pulls completed: {self.pull_count}")
            print(f"Total cards: {len(self.all_detected_cards)}")
            print(f"Total Score: {total_score} points")
            print("Card Details:")
            for card, count in sorted_cards:
                score = score_breakdown.get(card, 0)
                print(f"  {card}: {count}x ({score} pts)")
            print("=" * 50)
        else:
            print(f"\n📊 Instance #{self.instance_number}: No cards detected this cycle")
            print(f"Device: {self.device_id}")
            print(f"Account ID: {self.current_account_id or 'Not available'}")
            print("=" * 50)

    def read_cards_for_instance(self):
        """Read and identify cards from screenshot for this specific instance"""
        try:
            # Load slot positions
            slot_positions = load_slot_positions()
            
            # Check slot folder exists
            if not os.path.exists(SLOT_FOLDER):
                return
            
            # Get screenshot for this instance
            screenshot = self.get_screenshot()
            if screenshot is None:
                return
            
            # Check if this is a new pull by examining support points
            if not self.is_new_pull(screenshot):
                return
            
            # Process the screenshot
            best_matches = {}
            
            for slot, rel_pos in slot_positions.items():
                try:
                    slot_img = crop_slot_from_screenshot(rel_pos, screenshot)
                    if slot_img is None:
                        continue
                    
                    ref_name, match_count = match_with_all_refs(slot_img, slot, SLOT_FOLDER)
                    
                    if ref_name:
                        best_matches[slot] = (ref_name, match_count)
                        
                except Exception as e:
                    continue

            # Extract card names from this pull
            detected_cards = [match[0] for match in best_matches.values()]
            
            if detected_cards:
                # Add to this instance's collection
                self.all_detected_cards.extend(detected_cards)
                self.pull_count += 1
                
                # Calculate current score for progress tracking
                total_score, _ = self.calculate_score()
                
                # Only show results for high scores or completion
                if total_score >= MINIMUM_SCORE_THRESHOLD or self.pull_count >= MAX_GACHA_PULLS:
                    print(f"🃏 Instance #{self.instance_number}: Pull {self.pull_count}: {len(detected_cards)} cards (Score: {total_score})")
                
            else:
                self.pull_count += 1
            
        except Exception as e:
            pass  # Silently handle card reading errors
    
    def is_new_pull(self, screenshot):
        """
        Check if this is a new pull by comparing Support Exchange Points for this instance
        Returns True if it's a new pull, False if same pull
        """
        current_points = self.extract_support_points(screenshot)
        
        if current_points is None:
            return False  # Don't process if we can't read valid points
        
        # Compare with last known points
        if self.last_support_points is not None and current_points == self.last_support_points:
            return False  # Same pull detected
        
        # Update last known points
        self.last_support_points = current_points
        return True  # New pull detected
    
    def extract_support_points(self, screenshot):
        """Extract support points from the screenshot for this instance"""
        try:
            # Crop the support points region
            x1, y1, x2, y2 = SUPPORT_POINTS_REGION
            support_region = screenshot[y1:y2, x1:x2]
            
            if support_region.size == 0:
                print(f"❌ Instance #{self.instance_number}: Support region crop failed")
                return None
            
            # Scale up the image for better OCR (3x scale)
            scale_factor = 3
            height, width = support_region.shape[:2]
            scaled_region = cv2.resize(support_region, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_CUBIC)
            
            # Convert to grayscale
            gray_region = cv2.cvtColor(scaled_region, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray_region, (3, 3), 0)
            
            # Try multiple preprocessing approaches
            processed_images = []
            
            # Method 1: OTSU thresholding with contrast enhancement
            enhanced = cv2.convertScaleAbs(blurred, alpha=2.0, beta=10)
            _, thresh1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_images.append(("OTSU_enhanced", thresh1))
            
            # Method 2: Adaptive thresholding
            adaptive_thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            processed_images.append(("adaptive", adaptive_thresh))
            
            # Method 3: Simple binary threshold with optimal value
            _, thresh2 = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
            processed_images.append(("binary_127", thresh2))
            
            # Method 4: Inverted threshold for white text on dark background
            _, thresh3 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            processed_images.append(("inverted_OTSU", thresh3))
            
            # Method 5: Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            morph_cleaned = cv2.morphologyEx(thresh1, cv2.MORPH_CLOSE, kernel)
            morph_cleaned = cv2.morphologyEx(morph_cleaned, cv2.MORPH_OPEN, kernel)
            processed_images.append(("morphological", morph_cleaned))
            
            # Try OCR on each processed image
            ocr_configs = [
                '--psm 7 -c tessedit_char_whitelist=0123456789',
                '--psm 8 -c tessedit_char_whitelist=0123456789',
                '--psm 13 -c tessedit_char_whitelist=0123456789',
                '--psm 6 -c tessedit_char_whitelist=0123456789',
                '--psm 7 -c tessedit_char_whitelist=0123456789 -c page_separator=""'
            ]
            
            results = []
            
            for method_name, processed_img in processed_images:
                for config_idx, config in enumerate(ocr_configs):
                    try:
                        text = pytesseract.image_to_string(processed_img, config=config).strip()
                        # Clean the text (remove any non-digit characters)
                        clean_text = ''.join(filter(str.isdigit, text))
                        
                        if clean_text and clean_text.isdigit():
                            points = int(clean_text)
                            # Reasonable range check (support points should be 0-99999)
                            if 0 <= points <= 99999:
                                results.append((points, method_name, config_idx, text))
                    except Exception:
                        continue
            
            # If we got results, pick the most common one or the first valid one
            if results:
                # Sort by frequency if we have multiple results
                if len(results) > 1:
                    from collections import Counter
                    point_counts = Counter([r[0] for r in results])
                    most_common_points = point_counts.most_common(1)[0][0]
                    
                    # Find the first result with the most common value
                    for points, method, config_idx, raw_text in results:
                        if points == most_common_points:
                            return points
                else:
                    points, method, config_idx, raw_text = results[0]
                    return points
            
            # If no valid results, try one more aggressive approach
            # Try to find numbers using template matching or contour detection
            try:
                # Find contours and filter for number-like shapes
                contours, _ = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    # Sort contours by area and try OCR on the largest ones
                    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:3]
                    
                    for contour in contours:
                        x, y, w, h = cv2.boundingRect(contour)
                        if w > 10 and h > 10:  # Minimum size filter
                            contour_region = thresh1[y:y+h, x:x+w]
                            # Add padding
                            padded = cv2.copyMakeBorder(contour_region, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=255)
                            
                            text = pytesseract.image_to_string(padded, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
                            clean_text = ''.join(filter(str.isdigit, text))
                            
                            if clean_text and clean_text.isdigit():
                                points = int(clean_text)
                                if 0 <= points <= 99999:
                                    return points
            except Exception:
                pass
            
            print(f"❌ Instance #{self.instance_number}: Could not extract valid support points from image")
            return None
            
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error extracting support points: {e}")
            import traceback
            print(f"❌ Instance #{self.instance_number}: Full traceback:")
            traceback.print_exc()
            return None

    def check_running_macros_for_device(self):
        """Check if there are any running macro processes for this device"""
        try:
            # Check for running macro.py processes that might be stuck
            result = subprocess.run([
                'tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'
            ], capture_output=True, timeout=5, text=True)
            
            if result.returncode == 0:
                # Look for macro.py processes
                if 'macro.py' in result.stdout:
                    print(f"⚠️ Instance #{self.instance_number}: Found running macro processes")
                    return True
                else:
                    return False
            else:
                return False
                
        except Exception as e:
            print(f"❌ Instance #{self.instance_number}: Error checking for running macros: {e}")
            return False

def detect_image(frame, template, threshold=0.8):
    """Detect template image in frame"""
    try:
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        return max_val >= threshold
    except Exception as e:
        print(f"❌ Error in image detection: {e}")
        return False

def load_slot_positions():
    """Load slot positions from configuration"""
    config = configparser.ConfigParser()
    config_path = os.path.join(BASE_DIR, "config.ini")
    
    if not os.path.exists(config_path):
        print("⚠️ config.ini not found, using default slot positions")
        return {
            "slot1": (50, 200, 150, 300),
            "slot2": (160, 200, 260, 300),
            "slot3": (270, 200, 370, 300),
            "slot4": (380, 200, 480, 300),
            "slot5": (50, 320, 150, 420),
            "slot6": (160, 320, 260, 420),
            "slot7": (270, 320, 370, 420),
            "slot8": (380, 320, 480, 420),
            "slot9": (50, 440, 150, 540),
            "slot10": (160, 440, 260, 540)
        }
    
    try:
        config.read(config_path)
        slot_positions = {}
        
        if "Slots" in config:
            for slot_name, slot_value in config["Slots"].items():
                # Parse relative coordinates (x, y, width, height)
                coords = [float(x) for x in slot_value.split(',')]
                if len(coords) == 4:
                    rel_x, rel_y, rel_w, rel_h = coords
                    # Convert to absolute coordinates based on device resolution
                    x1 = int(rel_x * device_width)
                    y1 = int(rel_y * device_height)
                    x2 = int((rel_x + rel_w) * device_width)
                    y2 = int((rel_y + rel_h) * device_height)
                    slot_positions[slot_name] = (x1, y1, x2, y2)
        
        if slot_positions:
            return slot_positions
        else:
            print("⚠️ No valid slot positions found in config.ini, using defaults")
            return {
                "slot1": (50, 200, 150, 300),
                "slot2": (160, 200, 260, 300),
                "slot3": (270, 200, 370, 300),
                "slot4": (380, 200, 480, 300),
                "slot5": (50, 320, 150, 420),
                "slot6": (160, 320, 260, 420),
                "slot7": (270, 320, 370, 420),
                "slot8": (380, 320, 480, 420),
                "slot9": (50, 440, 150, 540),
                "slot10": (160, 440, 260, 540)
            }
            
    except Exception as e:
        print(f"❌ Error loading config.ini: {e}")
        print("Using default slot positions")
        return {
            "slot1": (50, 200, 150, 300),
            "slot2": (160, 200, 260, 300),
            "slot3": (270, 200, 370, 300),
            "slot4": (380, 200, 480, 300),
            "slot5": (50, 320, 150, 420),
            "slot6": (160, 320, 260, 420),
            "slot7": (270, 320, 370, 420),
            "slot8": (380, 320, 480, 420),
            "slot9": (50, 440, 150, 540),
            "slot10": (160, 440, 260, 540)
        }

def is_new_pull(screenshot):
    """Check if this is a new pull by examining support points"""
    # This is a placeholder - implement actual logic if needed
    return True

def reset_automation_state():
    """Reset automation state"""
    # This is a placeholder for compatibility
    pass

def show_automation_status():
    """Show automation status"""
    # This is a placeholder for compatibility
    pass

def start_adb():
    """Check if ADB is available and detect connected devices."""
    try:
        # Check if ADB is available
        result = subprocess.run(['adb', 'version'], capture_output=True, timeout=5)
        if result.returncode != 0:
            print("❌ ADB not available")
            return False
        
        # Get connected devices
        result = subprocess.run(['adb', 'devices'], capture_output=True, timeout=5)
        if result.returncode != 0:
            print("❌ Failed to get device list")
            return False
        
        # Parse device list
        lines = result.stdout.decode().strip().split('\n')[1:]  # Skip header
        connected_devices = [line.split('\t')[0] for line in lines if line.strip() and not line.endswith('offline')]
        
        global DEVICE_IDS
        if connected_devices:
            # Limit to PARALLEL_INSTANCES and update global list
            DEVICE_IDS = connected_devices[:PARALLEL_INSTANCES]
            print(f"✅ Connected devices: {DEVICE_IDS}")
            if len(DEVICE_IDS) < PARALLEL_INSTANCES:
                print(f"⚠️ Only {len(DEVICE_IDS)} device(s) detected, but {PARALLEL_INSTANCES} requested")
            return True
        else:
            print("❌ No devices connected")
            return False
    except Exception as e:
        print(f"❌ Error initializing ADB: {e}")
        return False

# ------------- Simple CLI args -------------
# device_override = None # This line is now handled by args.device

# Allow: --device <id>   and   --test-support handled earlier
# if '--device' in sys.argv:
#     idx = sys.argv.index('--device')
#     if idx + 1 < len(sys.argv):
#         device_override = sys.argv[idx + 1]
#     else:
#         print("Usage: python umamusume.py --device <adb_device_id>")
#         sys.exit(1)

# Remove processed args to avoid interfering later
# clean_args = []
# i = 0
# while i < len(sys.argv):
#     if sys.argv[i] == '--device':
#         i += 2
#     else:
#         clean_args.append(sys.argv[i])
#         i += 1
# sys.argv = clean_args

print("Starting parallel gacha automation system...")
print(f"📋 Configuration:")
print(f"   • Parallel instances: {PARALLEL_INSTANCES}")
print(f"   • Gacha pulls per cycle: {MAX_GACHA_PULLS}")
print(f"   • Macro speed multiplier: {MACRO_SPEED_MULTIPLIER}x")
print(f"   • Inter-macro delay: {INTER_MACRO_DELAY}s")
if device_override:
    print(f"   • Using specific device: {device_override}")
print("")
print(f"This will run {PARALLEL_INSTANCES} instances in PARALLEL and REPEAT AUTOMATICALLY:")
print("1. Wait for 'until gacha.png' detection")
print("2. Execute until gacha macro")
print("3. Wait for 'first_gacha.png' detection") 
print("4. Execute first gacha macro + read cards")
print(f"5. Execute gacha macro {MAX_GACHA_PULLS - 1} more times ({MAX_GACHA_PULLS} total pulls) + read cards after each")
print("6. Execute back home macro")
print("7. Execute bind ID macro")
print("8. Get account ID via clipper")
print("9. Calculate card scores and send to Discord if score >= 45")
print("10. 🔄 AUTOMATICALLY RESET AND REPEAT FROM STEP 1")
print("")
print("⚠️ This will run CONTINUOUSLY on ALL instances until you press 'q' to quit!")
print(f"🚀 Target: {PARALLEL_INSTANCES} parallel instances for maximum efficiency!")
print("⏰ State-specific timeouts (base → adjusted for macro speed):")
for state, timeout in STATE_TIMEOUTS.items():
    adjusted_timeout = timeout * MACRO_SPEED_MULTIPLIER
    print(f"   • {state}: {timeout//60}m {timeout%60}s → {int(adjusted_timeout//60)}m {int(adjusted_timeout%60)}s")
print("💡 Tip: Use 't' to view detailed timeout configuration, or modify STATE_TIMEOUTS in code")
print(f"📱 App package: {APP_PACKAGE_NAME}")
print("🃏 Card reading: Enabled for all instances with real-time detection")
print(f"🐌 Macro speed: {MACRO_SPEED_MULTIPLIER}x (slower = more stable for parallel execution)")
print(f"⏳ Inter-macro delay: {INTER_MACRO_DELAY}s (prevents resource conflicts)")
print("")
print("Card Scoring:")
print("  • kitasan: 15 points")
print("  • supercreek: 10 points") 
print("  • finemotion: 10 points")
print("  • other cards: 5 points each")
print(f"  • Minimum score for Discord: {MINIMUM_SCORE_THRESHOLD} points")
print("")
if not DISCORD_WEBHOOK_URL:
    print("⚠️ WARNING: Discord webhook URL not configured!")
    print("   Add your webhook URL to DISCORD_WEBHOOK_URL variable in the code")
    print("   Results will only be displayed locally until configured.")
else:
    print("✅ Discord webhook configured - high scores will be sent automatically!")

# Initialise ADB / populate DEVICE_IDS
adb_success = start_adb()

# If user supplied a specific device, override
if device_override:
    DEVICE_IDS = [device_override]
    print(f"🔧 Using user-specified device: {device_override}")

if len(DEVICE_IDS) < PARALLEL_INSTANCES:
    print(f"⚠️ Only {len(DEVICE_IDS)} device(s) detected, but {PARALLEL_INSTANCES} requested")
    print(f"   Will run with {len(DEVICE_IDS)} instance(s)")

def adjust_speed_for_parallel_execution():
    """Automatically adjust macro speed settings based on number of instances"""
    actual_instances = len(DEVICE_IDS)
    
    if actual_instances <= 1:
        suggested_speed = 1.0
        suggested_delay = 0.5
    elif actual_instances <= 2:
        suggested_speed = 1.5
        suggested_delay = 1.0
    elif actual_instances <= 3:
        suggested_speed = 2.0
        suggested_delay = 1.5
    else:
        suggested_speed = 2.5 + (actual_instances - 4) * 0.3
        suggested_delay = 2.0 + (actual_instances - 4) * 0.2
    
    print(f"📊 Auto-adjusting speed for {actual_instances} parallel instance(s):")
    print(f"   Current speed: {MACRO_SPEED_MULTIPLIER}x, delay: {INTER_MACRO_DELAY}s")
    print(f"   Suggested speed: {suggested_speed}x, delay: {suggested_delay}s")
    
    if abs(MACRO_SPEED_MULTIPLIER - suggested_speed) > 0.1 or abs(INTER_MACRO_DELAY - suggested_delay) > 0.1:
        print(f"💡 Consider updating parameters for better stability:")
        print(f"   --speed {suggested_speed} --delay {suggested_delay}")
    else:
        print(f"✅ Current speed settings are optimal for {actual_instances} instance(s)")
    print("")

# Auto-adjust speed settings based on number of instances
adjust_speed_for_parallel_execution()

print("Keyboard commands:")
print("  'q' - Quit (ONLY way to stop all parallel automation)")
print("  's' - Show detailed status of all instances (includes card progress)")
print("  't' - Show current timeout configuration")
print("")
print("Command-line usage examples:")
print("  python umamusume.py --speed 2.0 --instances 4 --pulls 10")
print("  python umamusume.py --device emulator-5554 --speed 1.5")
print("  python umamusume.py --instances 2 --pulls 5 --speed 3.0 --delay 1.5")
print("  python umamusume.py --help  # Show all available options")

def run_instance_thread(instance):
    """Run a single automation instance in a thread"""
    try:
        print(f"🚀 Starting Instance #{instance.instance_number} thread for device {instance.device_id}")
        instance.run_automation()
    except Exception as e:
        print(f"❌ Instance #{instance.instance_number} thread error: {e}")
    finally:
        print(f"🏁 Instance #{instance.instance_number} thread ended")

def start_parallel_automation():
    """Start parallel automation with multiple instances"""
    if len(DEVICE_IDS) == 0:
        print("❌ No devices available for parallel automation")
        return False
    
    # Create automation instances
    instances = []
    threads = []
    
    for i, device_id in enumerate(DEVICE_IDS, 1):
        instance = GachaAutomationInstance(device_id, i)
        instances.append(instance)
    
    print(f"🚀 Starting parallel automation with {len(instances)} instances...")
    
    # Start threads for each instance
    for instance in instances:
        thread = threading.Thread(target=run_instance_thread, args=(instance,), daemon=True)
        threads.append(thread)
        thread.start()
    
    print("✅ All instances started! Press 'q' to stop, 's' for status\n")
    
    # Track start time for speed calculation
    start_time = time.time()
    
    # Global keyboard listener for stopping all instances
    global running
    try:
        while running:
            # Check if any instance is still running
            any_running = any(instance.running for instance in instances)
            if not any_running:
                break
            
            # Check for keyboard input
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'q':
                    print("\n🛑 Stopping all instances...")
                    running = False
                    for instance in instances:
                        instance.running = False
                    break
                elif key == 's':
                    # Calculate speed statistics
                    elapsed_time = time.time() - start_time
                    total_sessions = sum(instance.session_count for instance in instances)
                    sessions_per_hour = (total_sessions / elapsed_time) * 3600 if elapsed_time > 0 else 0
                    
                    print(f"\n📊 PARALLEL STATUS ({len(instances)} instances):")
                    print(f"📋 Config: {MAX_GACHA_PULLS} pulls/cycle, {MACRO_SPEED_MULTIPLIER}x speed, {INTER_MACRO_DELAY}s delay")
                    print(f"⏱️  Runtime: {elapsed_time/3600:.1f} hours")
                    print(f"🔄 Total cycles: {total_sessions}")
                    print(f"⚡ Speed: {sessions_per_hour:.1f} accounts/hour")
                    
                    for instance in instances:
                        total_score = 0
                        if instance.all_detected_cards:
                            total_score, _ = instance.calculate_score()
                        
                        print(f"   Instance #{instance.instance_number}: {instance.session_count} cycles, Score: {total_score}, State: {instance.automation_state}")
                elif key == 't':
                    print("\nShowing current timeout configuration...")
                    show_timeout_configuration()
        
        time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt - stopping all instances...")
        running = False
        for instance in instances:
            instance.running = False
    
    # Wait for all threads to finish
    print("⏳ Waiting for all instances to stop...")
    for thread in threads:
        thread.join(timeout=5)
    
    # Show final summary with speed statistics
    elapsed_time = time.time() - start_time
    total_sessions = sum(instance.session_count for instance in instances)
    sessions_per_hour = (total_sessions / elapsed_time) * 3600 if elapsed_time > 0 else 0
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"📋 Configuration: {MAX_GACHA_PULLS} pulls/cycle, {MACRO_SPEED_MULTIPLIER}x speed, {INTER_MACRO_DELAY}s delay")
    print(f"🤖 Instances: {len(instances)} parallel")
    print(f"⏱️  Total runtime: {elapsed_time/3600:.1f} hours")
    print(f"🔄 Total cycles: {total_sessions}")
    print(f"⚡ Average speed: {sessions_per_hour:.1f} accounts/hour")
    
    return True

# Start the parallel automation system
try:
    print("🚀 Starting parallel gacha automation...")
    print("This will run indefinitely on all instances until you press 'q' to quit")
    start_parallel_automation()
        
except KeyboardInterrupt:
    print("\nParallel automation interrupted by user")
    running = False
except Exception as e:
    print(f"\nUnexpected error during parallel automation: {e}")
    
finally:
    # Cleanup
    print("\nParallel automation session ended")

def update_global_timeout(state, timeout_seconds):
    """Update timeout for a specific state globally"""
    if state in STATE_TIMEOUTS:
        old_timeout = STATE_TIMEOUTS[state]
        STATE_TIMEOUTS[state] = timeout_seconds
        print(f"⏰ Updated global timeout for '{state}': {old_timeout}s → {timeout_seconds}s")
    else:
        STATE_TIMEOUTS[state] = timeout_seconds
        print(f"⏰ Added new global timeout for '{state}': {timeout_seconds}s")

def show_timeout_configuration():
    """Display current timeout configuration"""
    print("\n⏰ Current State Timeout Configuration:")
    print("=" * 60)
    print(f"Macro Speed Multiplier: {MACRO_SPEED_MULTIPLIER}x")
    print("=" * 60)
    for state, timeout in STATE_TIMEOUTS.items():
        minutes = timeout // 60
        seconds = timeout % 60
        adjusted_timeout = timeout * MACRO_SPEED_MULTIPLIER
        adjusted_minutes = int(adjusted_timeout // 60)
        adjusted_seconds = int(adjusted_timeout % 60)
        print(f"   {state:25} : {minutes}m {seconds}s → {adjusted_minutes}m {adjusted_seconds}s ({timeout}s → {adjusted_timeout:.1f}s)")
    
    default_adjusted = DEFAULT_STATE_TIMEOUT * MACRO_SPEED_MULTIPLIER
    default_minutes = DEFAULT_STATE_TIMEOUT // 60
    default_seconds = DEFAULT_STATE_TIMEOUT % 60
    default_adj_minutes = int(default_adjusted // 60)
    default_adj_seconds = int(default_adjusted % 60)
    print(f"   {'default':25} : {default_minutes}m {default_seconds}s → {default_adj_minutes}m {default_adj_seconds}s ({DEFAULT_STATE_TIMEOUT}s → {default_adjusted:.1f}s)")
    print("=" * 60)

def keyboard_listener():
    """Listen for keyboard input in a separate thread"""
    global running
    
    while running:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8').lower()
            
            if key == 'q':
                print("\nQuitting...")
                running = False
                break
            elif key == 'r':
                print("\nResetting automation state...")
                reset_automation_state()
            elif key == 'f':
                print("\nShowing automation status...")
                show_automation_status()
            elif key == 't':
                print("\nShowing current timeout configuration...")
                show_timeout_configuration()
        
        time.sleep(0.1)

# ----------------- Utility: Extract support points from raw image -----------------

def preprocess_image(img):
    """Preprocess image for better OCR recognition"""
    try:
        # Scale up the image for better OCR (3x scale)
        scale_factor = 3
        height, width = img.shape[:2]
        scaled = cv2.resize(img, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_CUBIC)
        
        # Convert to grayscale if needed
        if len(scaled.shape) == 3:
            gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        else:
            gray = scaled
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply contrast enhancement and OTSU thresholding
        enhanced = cv2.convertScaleAbs(blurred, alpha=2.0, beta=10)
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return thresh
    except Exception as e:
        print(f"❌ Error in preprocess_image: {e}")
        return img

def extract_support_points_from_image(img):
    """Standalone extractor using enhanced OCR logic."""
    try:
        x1, y1, x2, y2 = SUPPORT_POINTS_REGION
        region = img[y1:y2, x1:x2]
        if region.size == 0:
            print("❌ Region crop failed (check SUPPORT_POINTS_REGION)")
            return None
        
        # Scale up the image for better OCR (3x scale)
        scale_factor = 3
        height, width = region.shape[:2]
        scaled_region = cv2.resize(region, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_CUBIC)
        
        # Convert to grayscale
        gray_region = cv2.cvtColor(scaled_region, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray_region, (3, 3), 0)
        
        # Try multiple preprocessing approaches
        processed_images = []
        
        # Method 1: OTSU thresholding with contrast enhancement
        enhanced = cv2.convertScaleAbs(blurred, alpha=2.0, beta=10)
        _, thresh1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(("OTSU_enhanced", thresh1))
        
        # Method 2: Adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        processed_images.append(("adaptive", adaptive_thresh))
        
        # Method 3: Simple binary threshold
        _, thresh2 = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY)
        processed_images.append(("binary_127", thresh2))
        
        # Try OCR on each processed image
        ocr_configs = [
            '--psm 7 -c tessedit_char_whitelist=0123456789',
            '--psm 8 -c tessedit_char_whitelist=0123456789',
            '--psm 13 -c tessedit_char_whitelist=0123456789'
        ]
        
        results = []
        
        for method_name, processed_img in processed_images:
            for config in ocr_configs:
                try:
                    text = pytesseract.image_to_string(processed_img, config=config).strip()
                    # Clean the text (remove any non-digit characters)
                    clean_text = ''.join(filter(str.isdigit, text))
                    
                    if clean_text and clean_text.isdigit():
                        points = int(clean_text)
                        # Reasonable range check (support points should be 0-99999)
                        if 0 <= points <= 99999:
                            results.append(points)
                except Exception:
                    continue
        
        # Return the most common result or the first valid one
        if results:
            if len(results) > 1:
                from collections import Counter
                point_counts = Counter(results)
                most_common_points = point_counts.most_common(1)[0][0]
                print(f"✅ Standalone: Support points detected: {most_common_points}")
                return most_common_points
            else:
                print(f"✅ Standalone: Support points detected: {results[0]}")
                return results[0]
        
        print("❌ Standalone: Could not extract valid support points")
        return None
    except Exception as e:
        print(f"❌ Error in standalone extraction: {e}")
        return None
