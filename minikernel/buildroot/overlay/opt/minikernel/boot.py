#!/usr/bin/env python3
"""
MiniKernel Boot Loader
Initializes the microkernel and all services for bootable environment
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add minikernel to path
MINIKERNEL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MINIKERNEL_ROOT))

from minikernel.core.microkernel import MicroKernel, ServicePriority
from minikernel.services.filesystem_service import FileSystemService
from minikernel.services.process_service import ProcessService
from minikernel.intent.intent_parser import IntentParser
from minikernel.intent.execution_engine import ExecutionEngine
from minikernel.security.sandbox import Sandbox
from minikernel.security.capability_manager import CapabilityManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/minikernel.log') if os.path.exists('/var/log') else logging.NullHandler()
    ]
)

logger = logging.getLogger("MiniKernel.Boot")


def check_environment():
    """Check if running in bootable environment vs development"""
    # Check for common bootable environment indicators
    if os.path.exists('/mnt/persistent'):
        logger.info("Detected bootable environment (VirtualBox)")
        return 'bootable'
    elif os.path.exists('/.dockerenv'):
        logger.info("Detected Docker container")
        return 'container'
    else:
        logger.info("Detected development environment")
        return 'development'


def setup_persistent_storage(kernel):
    """Set up persistent storage for bootable environment"""
    persist_path = os.environ.get('MINIKERNEL_PERSIST', '/mnt/persistent')
    
    if os.path.exists(persist_path):
        logger.info(f"Using persistent storage: {persist_path}")
        
        # Create necessary directories
        for subdir in ['data', 'logs', 'config', 'models']:
            os.makedirs(os.path.join(persist_path, subdir), exist_ok=True)
        
        return persist_path
    else:
        logger.warning(f"Persistent storage not found at {persist_path}")
        return None


def boot_kernel(mode='voice', environment='development'):
    """
    Boot the MiniKernel
    
    Args:
        mode: 'voice', 'cli', or 'headless'
        environment: 'bootable', 'container', or 'development'
    """
    logger.info("=" * 60)
    logger.info("MiniKernel Boot Sequence Starting")
    logger.info("=" * 60)
    logger.info(f"Mode: {mode}")
    logger.info(f"Environment: {environment}")
    
    # Initialize kernel
    kernel = MicroKernel()
    logger.info("Microkernel initialized")
    
    # Set up persistent storage if in bootable environment
    persist_path = None
    if environment == 'bootable':
        persist_path = setup_persistent_storage(kernel)
    
    # Register core services
    logger.info("Registering core services...")
    
    # Filesystem service
    fs_db_path = os.path.join(persist_path, 'data', 'filesystem.db') if persist_path else '/tmp/minikernel_fs.db'
    fs_service = FileSystemService(index_db_path=fs_db_path)
    kernel.register_service("filesystem", fs_service, priority=ServicePriority.CRITICAL)
    
    # Process service
    proc_service = ProcessService()
    kernel.register_service("process", proc_service, priority=ServicePriority.CRITICAL)
    
    # Security services
    sandbox = Sandbox()
    kernel.register_service("sandbox", sandbox, priority=ServicePriority.HIGH)
    
    capability_mgr = CapabilityManager()
    kernel.register_service("capabilities", capability_mgr, priority=ServicePriority.HIGH)
    
    # Intent parsing and execution
    intent_parser = IntentParser()
    kernel.register_service("intent_parser", intent_parser, priority=ServicePriority.NORMAL)
    
    execution_engine = ExecutionEngine(kernel)
    kernel.register_service("execution_engine", execution_engine, priority=ServicePriority.NORMAL)
    
    # Boot the kernel
    logger.info("Booting kernel...")
    if not kernel.boot():
        logger.error("Kernel boot failed!")
        return 1
    
    logger.info("=" * 60)
    logger.info("MiniKernel Boot Complete!")
    logger.info("=" * 60)
    
    # Print status
    stats = kernel.get_stats()
    logger.info(f"Uptime: {stats['uptime']:.2f}s")
    logger.info(f"Services: {stats['services_running']}/{stats['services_total']}")
    logger.info(f"State: {stats['state']}")
    
    # Start appropriate interface
    if mode == 'voice':
        start_voice_interface(kernel, environment)
    elif mode == 'cli':
        start_cli_interface(kernel, environment)
    else:
        start_headless(kernel, environment)
    
    return 0


def start_voice_interface(kernel, environment):
    """Start voice-controlled interface"""
    logger.info("Starting voice interface...")
    
    try:
        from minikernel.ai.voice_pipeline import VoicePipeline
        
        voice = VoicePipeline()
        logger.info("Voice pipeline initialized")
        
        print("\n" + "=" * 60)
        print("MiniKernel Voice Interface Ready")
        print("=" * 60)
        print("Speak commands to control the system")
        print("Press Ctrl+C to exit")
        print("=" * 60 + "\n")
        
        # Voice loop
        while True:
            try:
                # Listen for voice input
                audio = voice.listen()
                if audio:
                    # Transcribe
                    text = voice.transcribe(audio)
                    logger.info(f"User said: {text}")
                    
                    # Parse intent
                    intent_parser = kernel.get_service("intent_parser")
                    intent = intent_parser.parse(text)
                    
                    # Execute
                    execution_engine = kernel.get_service("execution_engine")
                    result = execution_engine.execute(intent)
                    
                    # Respond
                    response = result.get('message', 'Command executed')
                    logger.info(f"Response: {response}")
                    voice.speak(response)
                    
            except KeyboardInterrupt:
                logger.info("Voice interface interrupted")
                break
            except Exception as e:
                logger.error(f"Voice interface error: {e}", exc_info=True)
                
    except ImportError:
        logger.warning("Voice pipeline not available, falling back to CLI")
        start_cli_interface(kernel, environment)


def start_cli_interface(kernel, environment):
    """Start command-line interface"""
    logger.info("Starting CLI interface...")
    
    print("\n" + "=" * 60)
    print("MiniKernel Command-Line Interface")
    print("=" * 60)
    print("Type commands in natural language")
    print("Type 'help' for assistance, 'exit' to quit")
    print("=" * 60 + "\n")
    
    intent_parser = kernel.get_service("intent_parser")
    execution_engine = kernel.get_service("execution_engine")
    
    while True:
        try:
            # Get input
            user_input = input("minikernel> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ('exit', 'quit'):
                logger.info("CLI exit requested")
                break
            
            if user_input.lower() == 'help':
                print_help()
                continue
            
            # Parse and execute
            intent = intent_parser.parse(user_input)
            result = execution_engine.execute(intent)
            
            # Display result
            if result.get('success'):
                print(f"✓ {result.get('message', 'Done')}")
            else:
                print(f"✗ {result.get('error', 'Failed')}")
            
            if result.get('output'):
                print(result['output'])
                
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit")
        except EOFError:
            break
        except Exception as e:
            logger.error(f"CLI error: {e}", exc_info=True)
            print(f"Error: {e}")
    
    # Shutdown kernel
    logger.info("Shutting down kernel...")
    kernel.shutdown()


def start_headless(kernel, environment):
    """Start in headless mode (no user interface)"""
    logger.info("Running in headless mode")
    
    print("\n" + "=" * 60)
    print("MiniKernel Headless Mode")
    print("=" * 60)
    print("Kernel running in background")
    print("Press Ctrl+C to shutdown")
    print("=" * 60 + "\n")
    
    try:
        # Just keep kernel running
        import signal
        import time
        
        def signal_handler(sig, frame):
            logger.info("Shutdown signal received")
            kernel.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Headless mode interrupted")
        kernel.shutdown()


def print_help():
    """Print help information"""
    help_text = """
MiniKernel Help
===============

Natural Language Commands:
  - "list files in /home"
  - "find files containing 'test'"
  - "show running processes"
  - "search for python files"
  - "what's the system status"

System Commands:
  - help              Show this help
  - exit, quit        Exit MiniKernel
  - status            Show kernel status
  - services          List all services

Examples:
  minikernel> find all python files
  minikernel> list processes using more than 100MB
  minikernel> show files modified today
  minikernel> what is the system uptime
"""
    print(help_text)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='MiniKernel - AI-First Voice OS')
    parser.add_argument('--mode', choices=['voice', 'cli', 'headless'], 
                       default='cli', help='Interface mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Detect environment
    environment = check_environment()
    
    # Boot kernel
    try:
        return boot_kernel(mode=args.mode, environment=environment)
    except Exception as e:
        logger.critical(f"Boot failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
