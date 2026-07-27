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
from minikernel.services.package_service import PackageService
from minikernel.intent.intent_parser import IntentParser
from minikernel.intent.command_validator import CommandValidator
from minikernel.intent.execution_engine import ExecutionEngine
from minikernel.security.sandbox import Sandbox
from minikernel.security.capability_manager import CapabilityManager
from minikernel.security.confirmation_loop import ConfirmationLoop, ConfirmationMode

# Configure logging
def _get_log_handler():
    """Get appropriate log file handler based on permissions."""
    # Try user-writable locations first
    log_locations = [
        Path.home() / '.portaios' / 'minikernel.log',
        Path('/tmp/minikernel.log'),
        Path('/var/log/minikernel.log') if os.path.exists('/var/log') and os.access('/var/log', os.W_OK) else None
    ]
    
    for log_path in log_locations:
        if log_path is None:
            continue
        try:
            # Create parent directory if needed
            log_path.parent.mkdir(parents=True, exist_ok=True)
            # Test write access
            handler = logging.FileHandler(str(log_path))
            return handler
        except (PermissionError, OSError):
            continue
    
    # Fallback to NullHandler if no writable location found
    return logging.NullHandler()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        _get_log_handler()
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

    # Package service
    package_service = PackageService()
    kernel.register_service("package", package_service, priority=ServicePriority.NORMAL)

    # Security services
    sandbox = Sandbox()
    kernel.register_service("sandbox", sandbox, priority=ServicePriority.HIGH)

    capability_mgr = CapabilityManager()
    kernel.register_service("capabilities", capability_mgr, priority=ServicePriority.HIGH)

    validator = CommandValidator()
    kernel.register_service("validator", validator, priority=ServicePriority.HIGH)

    confirmation_loop = ConfirmationLoop(mode=ConfirmationMode.TEXT)
    kernel.register_service("confirmation", confirmation_loop, priority=ServicePriority.HIGH)

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
    logger.info(f"Uptime: {stats['uptime_seconds']:.2f}s")
    logger.info(f"Services running: {stats['services']}/{len(kernel.services)}")
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

        intent_parser = kernel.get_service("intent_parser")
        validator = kernel.get_service("validator")
        execution_engine = kernel.get_service("execution_engine")
        confirmation_loop = kernel.get_service("confirmation")
        if confirmation_loop:
            confirmation_loop.set_mode(ConfirmationMode.VOICE)
            confirmation_loop.set_voice_pipeline(voice)

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

                    # Parse and validate intent
                    intent = intent_parser.parse(text)
                    validation = validator.validate(intent)

                    if not validation.is_valid:
                        response = "; ".join(validation.errors) or "I can't do that."
                        logger.warning(f"Blocked: {response}")
                        voice.speak(response)
                        continue

                    confirmed = True
                    if validation.requires_confirmation:
                        confirmed = confirmation_loop.request_confirmation(
                            prompt=validation.confirmation_prompt or text,
                            command=text,
                            risk_level=validation.risk_level.value,
                        )
                        if not confirmed:
                            voice.speak("Cancelled.")
                            continue

                    # Execute
                    result = execution_engine.execute(intent, validation, confirmed=confirmed)

                    # Respond
                    if result.success:
                        response = (
                            result.output.get("message")
                            if isinstance(result.output, dict)
                            else "Done"
                        ) or "Done"
                    else:
                        response = result.error or "That failed."
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
    print("Prefix with 'agent:' for multi-step goals, e.g. 'agent: install numpy and then show memory usage'")
    print("Type 'help' for assistance, 'exit' to quit")
    print("=" * 60 + "\n")

    intent_parser = kernel.get_service("intent_parser")
    validator = kernel.get_service("validator")
    execution_engine = kernel.get_service("execution_engine")
    confirmation_loop = kernel.get_service("confirmation")

    def cli_confirm(prompt: str, command: str, risk_level: str) -> bool:
        return confirmation_loop.request_confirmation(prompt, command, risk_level)

    from minikernel.ai.agent_loop import AgentLoop
    agent_loop = AgentLoop(
        kernel,
        confirm_fn=lambda prompt, risk_level: cli_confirm(prompt, prompt, risk_level),
    )

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

            if user_input.lower().startswith("agent:"):
                goal = user_input.split(":", 1)[1].strip()
                run_result = agent_loop.run(goal)
                print(run_result.summary())
                continue

            # Parse and validate
            intent = intent_parser.parse(user_input)
            validation = validator.validate(intent)

            if not validation.is_valid:
                print(f"✗ {'; '.join(validation.errors) or 'Invalid command'}")
                continue

            confirmed = True
            if validation.requires_confirmation:
                confirmed = cli_confirm(
                    validation.confirmation_prompt or user_input, user_input, validation.risk_level.value
                )
                if not confirmed:
                    print("Cancelled.")
                    continue

            # Execute
            result = execution_engine.execute(intent, validation, confirmed=confirmed)

            # Display result
            if result.success:
                message = result.output.get("message") if isinstance(result.output, dict) else None
                print(f"✓ {message or 'Done'}")
            else:
                print(f"✗ {result.error or 'Failed'}")

            if result.output:
                print(result.output)

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

Multi-step goals:
  Prefix a goal with 'agent:' to have it split into steps and run
  autonomously. Failed steps are diagnosed and, where possible,
  self-corrected (e.g. a missing package is installed) before retrying.

Examples:
  minikernel> find all python files
  minikernel> list processes using more than 100MB
  minikernel> show files modified today
  minikernel> what is the system uptime
  minikernel> agent: install numpy and then show memory usage
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
