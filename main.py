#!/usr/bin/env python3
"""
Generic Mobile Game Automation Framework
Main entry point for the automation system.
"""

import sys
import os
import argparse
import time
import threading
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.automation_engine import AutomationEngine
from core.device_manager import DeviceManager
from games.game_factory import GameFactory
from web_interface import create_web_interface

def parse_arguments():
    """Parse command-line arguments for the automation framework"""
    parser = argparse.ArgumentParser(
        description="Generic Mobile Game Automation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py umamusume --speed 2.0 --instances 4 --pulls 10
  python main.py umamusume --device emulator-5554 --speed 1.5
  python main.py othergame --instances 2 --speed 3.0
  python main.py umamusume --verbose --instances 1  # Debug mode
  python main.py --list-games  # Show available games
  python main.py --picker umamusume  # Launch slot picker for umamusume
  python main.py umamusume --web  # Start with web interface
  python main.py --web-only  # Start web interface only
        """
    )
    
    parser.add_argument('game', 
                       nargs='?',
                       help='Game to automate (e.g., umamusume, fgo, etc.)')
    
    parser.add_argument('--list-games', 
                       action='store_true',
                       help='List all available games')
    
    parser.add_argument('--picker',
                       type=str,
                       help='Launch slot picker for the specified game')
    
    parser.add_argument('--speed', '--multiplier', 
                       type=float, 
                       default=2.4,
                       help='Macro speed multiplier (default: 2.4). Higher = slower execution')
    
    parser.add_argument('--instances', '--parallel',
                       type=int,
                       default=8,
                       help='Number of parallel instances to run (default: 8)')
    
    parser.add_argument('--cycles', '--pulls',
                       type=int,
                       help='Number of cycles/pulls per session (game-specific default if not set)')
    
    parser.add_argument('--device',
                       type=str,
                       help='Specific device ID to use (overrides parallel instances)')
    
    parser.add_argument('--delay',
                       type=float,
                       default=1.0,
                       help='Inter-macro delay in seconds (default: 1.0)')
    
    parser.add_argument('--config',
                       type=str,
                       help='Custom config file path (optional)')
    
    parser.add_argument('--discord-webhook',
                       type=str,
                       help='Discord webhook URL for notifications')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose logging for debugging')
    
    parser.add_argument('--web',
                       action='store_true',
                       help='Start web interface alongside automation')
    
    parser.add_argument('--web-only',
                       action='store_true',
                       help='Start web interface only (no automation)')
    
    parser.add_argument('--web-port',
                       type=int,
                       default=5000,
                       help='Port for web interface (default: 5000)')
    
    parser.add_argument('--web-host',
                       type=str,
                       default='0.0.0.0',
                       help='Host for web interface (default: 0.0.0.0)')
    
    parser.add_argument('--no-ngrok',
                       action='store_true',
                       help='Disable ngrok tunnel (run locally only)')
    
    return parser.parse_args()

def list_available_games():
    """List all available games in the games directory"""
    games_dir = project_root / "games"
    if not games_dir.exists():
        print("❌ No games directory found")
        return []
    
    available_games = []
    for item in games_dir.iterdir():
        if item.is_dir() and not item.name.startswith('__'):
            game_file = item / f"{item.name}_game.py"
            if game_file.exists():
                available_games.append(item.name)
    
    return available_games

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Handle web-only mode
    if args.web_only:
        print("🌐 Starting web interface only...")
        web_interface = create_web_interface()
        return web_interface.start(host=args.web_host, port=args.web_port, debug=args.verbose)
    
    # Handle picker mode
    if args.picker:
        picker_script = project_root / "core" / "picker.py"
        if not picker_script.exists():
            print("❌ Error: Picker script not found")
            return
        
        # Validate game exists
        available_games = list_available_games()
        if args.picker not in available_games:
            print(f"❌ Error: Game '{args.picker}' not found")
            if available_games:
                print("Available games:", ", ".join(available_games))
            return
        
        print(f"🔧 Launching slot picker for game: {args.picker}")
        try:
            import subprocess
            result = subprocess.run([sys.executable, str(picker_script), args.picker])
            return
        except Exception as e:
            print(f"❌ Error launching picker: {e}")
            return
    
    # List available games
    if args.list_games:
        games = list_available_games()
        if games:
            print("📱 Available games:")
            for game in games:
                print(f"   • {game}")
            print(f"\nUsage: python main.py <game_name> [options]")
        else:
            print("❌ No games found in games/ directory")
        return
    
    # Validate game selection (unless web-only mode)
    if not args.game and not args.web_only:
        print("❌ Error: Please specify a game to automate")
        print("Use --list-games to see available games")
        print("Example: python main.py umamusume --speed 2.0")
        print("Or use --web-only to start web interface only")
        return
    
    if args.game:
        available_games = list_available_games()
        if args.game not in available_games:
            print(f"❌ Error: Game '{args.game}' not found")
            if available_games:
                print("Available games:", ", ".join(available_games))
            return
    
    # Validation
    if args.speed < 0.1:
        print("❌ Error: Macro speed multiplier must be at least 0.1")
        return
    
    if args.instances < 1:
        print("❌ Error: Number of parallel instances must be at least 1")
        return
    
    if args.delay < 0:
        print("❌ Error: Inter-macro delay cannot be negative")
        return
    
    # Initialize device manager
    device_manager = DeviceManager()
    if not device_manager.initialize():
        print("❌ Failed to initialize device manager")
        return
    
    # Override device list if specific device requested
    if args.device:
        device_manager.set_device_list([args.device])
        print(f"🔧 Using user-specified device: {args.device}")
    
    # Limit devices to requested instances
    available_devices = device_manager.get_device_list()[:args.instances]
    if len(available_devices) < args.instances:
        print(f"⚠️ Only {len(available_devices)} device(s) detected, but {args.instances} requested")
        print(f"   Will run with {len(available_devices)} instance(s)")
    
    # Initialize web interface if requested
    web_interface = None
    if args.web or args.web_only:
        web_interface = create_web_interface(verbose=args.verbose)
        print(f"🌐 Web interface will be available at http://{args.web_host}:{args.web_port}")
    
    try:
        # Create game instance if game specified
        game = None
        if args.game:
            game = GameFactory.create_game(args.game, args.config)
            if not game:
                print(f"❌ Failed to create game instance for '{args.game}'")
                return
            
            # Set cycles if specified, otherwise use game default
            if args.cycles:
                game.set_cycles_per_session(args.cycles)
            
            # Set Discord webhook if provided
            if args.discord_webhook:
                game.set_discord_webhook(args.discord_webhook)
            
            # Print configuration
            print(f"🎮 Starting automation for: {game.get_display_name()}")
            print(f"📋 Configuration:")
            print(f"   • Parallel instances: {len(available_devices)}")
            print(f"   • Cycles per session: {game.get_cycles_per_session()}")
            print(f"   • Macro speed multiplier: {args.speed}x")
            print(f"   • Inter-macro delay: {args.delay}s")
            print(f"   • Discord notifications: {'✅' if game.has_discord_webhook() else '❌'}")
            print(f"   • Web interface: {'✅' if args.web else '❌'}")
            print("")
            
            # Verbose configuration details
            if args.verbose:
                print("🔍 Verbose mode enabled - detailed logging active")
                print("📊 Detailed Configuration:")
                print(f"   • App package: {game.get_app_package()}")
                print(f"   • App activity: {game.get_app_activity()}")
                print(f"   • Device resolution: {game.get_device_resolution()}")
                print(f"   • Score threshold: {game.get_minimum_score_threshold()}")
                print(f"   • Available devices: {device_manager.get_device_list()}")
                
                # Show automation states
                states = game.get_automation_states()
                print(f"   • Automation states: {len(states)} defined")
                for state_name, state_config in states.items():
                    timeout = state_config.get('timeout', 60)
                    templates = state_config.get('templates', [])
                    macros = state_config.get('macros', [])
                    print(f"     - {state_name}: timeout={timeout}s, templates={templates}, macros={macros}")
                print("")
        
        # Create automation engine if game specified
        engine = None
        if game:
            engine = AutomationEngine(
                game=game,
                device_manager=device_manager,
                speed_multiplier=args.speed,
                inter_macro_delay=args.delay,
                max_instances=len(available_devices),
                verbose=args.verbose
            )
            
            # Update web interface with automation engine
            if web_interface:
                web_interface.automation_engine = engine
                # Start web interface in background thread
                web_thread = threading.Thread(
                    target=web_interface.start,
                    kwargs={
                        'host': args.web_host, 
                        'port': args.web_port, 
                        'debug': False,
                        'use_ngrok': not args.no_ngrok
                    },
                    daemon=True
                )
                web_thread.start()
                print("🚀 Starting automation engine...")
                engine.start()
            else:
                print("🚀 Starting automation engine...")
                engine.start()
        else:
            # Web interface only mode
            if web_interface:
                web_interface.start(
                    host=args.web_host, 
                    port=args.web_port, 
                    debug=args.verbose,
                    use_ngrok=not args.no_ngrok
                )
        
    except KeyboardInterrupt:
        print("\n🛑 Automation interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🏁 Automation session ended")

if __name__ == "__main__":
    main()
