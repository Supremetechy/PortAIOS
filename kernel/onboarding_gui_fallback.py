#!/usr/bin/env python3
"""
AI-OS Onboarding GUI - Fallback Version (No Video Dependencies)
Works without PyQt6-Multimedia, uses basic PyQt6 only
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QStackedWidget, QProgressBar, QCheckBox,
        QLineEdit, QTextEdit, QComboBox, QGroupBox, QScrollArea,
        QMessageBox, QFileDialog, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
    from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor
except ImportError:
    print("PyQt6 not installed. Install with: pip install PyQt6")
    sys.exit(1)


class OnboardingConfig:
    """Manages onboarding configuration and state"""
    
    CONFIG_FILE = Path.home() / ".aios" / "onboarding_config.json"
    
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load existing configuration or create default"""
        if self.CONFIG_FILE.exists():
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {
            "onboarding_complete": False,
            "current_step": 0,
            "user_name": "",
            "system_name": "",
            "install_path": str(Path.cwd()),
            "gpu_enabled": False,
            "auto_start": False,
            "telemetry_enabled": True,
            "completed_steps": []
        }
    
    def save_config(self):
        """Save configuration to disk"""
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def mark_step_complete(self, step: int):
        """Mark a step as completed"""
        if step not in self.config["completed_steps"]:
            self.config["completed_steps"].append(step)
        self.save_config()
    
    def is_step_complete(self, step: int) -> bool:
        """Check if step is completed"""
        return step in self.config.get("completed_steps", [])


class VideoPlaceholder(QWidget):
    """Placeholder widget when videos are not available"""
    
    def __init__(self, video_title: str = "", parent=None):
        super().__init__(parent)
        self.video_title = video_title
        self.setup_ui()
        
    def setup_ui(self):
        """Setup placeholder UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Placeholder frame
        frame = QFrame()
        frame.setMinimumSize(QSize(640, 360))
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3498db, stop:1 #2c3e50);
                border: 2px solid #2c3e50;
                border-radius: 10px;
            }
        """)
        
        frame_layout = QVBoxLayout(frame)
        
        # Video icon placeholder
        icon_label = QLabel("🎥")
        icon_label.setFont(QFont("Arial", 72))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("color: white;")
        frame_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel(self.video_title or "AI Assistant Video")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white;")
        frame_layout.addWidget(title_label)
        
        # Info text
        info_label = QLabel("Video guide will play here\n(Add videos to assets/onboarding_videos/)")
        info_label.setFont(QFont("Arial", 11))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        frame_layout.addWidget(info_label)
        
        layout.addWidget(frame)


class WelcomeStep(QWidget):
    """Welcome screen"""
    
    def __init__(self, config: OnboardingConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        """Setup welcome step UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Welcome to AI-OS")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Your AI-Powered Operating System")
        subtitle.setFont(QFont("Arial", 14))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Video placeholder
        video_placeholder = VideoPlaceholder("Welcome to AI-OS")
        layout.addWidget(video_placeholder)
        
        # Welcome message
        message = QLabel(
            "AI-OS is designed specifically for AI workloads, providing:\n\n"
            "• Automatic hardware detection and optimization\n"
            "• GPU acceleration support (CUDA, ROCm, Metal)\n"
            "• Seamless integration with AI frameworks\n"
            "• Resource management for training and inference\n\n"
            "Let's get your system configured!"
        )
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignLeft)
        message.setStyleSheet("margin: 20px; font-size: 11pt; line-height: 1.6;")
        layout.addWidget(message)


class HardwareDetectionStep(QWidget):
    """Hardware detection and configuration step"""
    
    detection_complete = pyqtSignal(dict)
    
    def __init__(self, config: OnboardingConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.hardware_info = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup hardware detection UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Hardware Detection")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Video placeholder
        video_placeholder = VideoPlaceholder("Hardware Detection Guide")
        layout.addWidget(video_placeholder)
        
        # Detection status
        self.status_label = QLabel("Click 'Detect Hardware' to scan your system")
        self.status_label.setStyleSheet("font-size: 11pt; margin: 10px;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Hardware info display
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(200)
        layout.addWidget(self.info_text)
        
        # Detect button
        self.detect_button = QPushButton("🔍 Detect Hardware")
        self.detect_button.setMinimumHeight(40)
        self.detect_button.clicked.connect(self.start_detection)
        layout.addWidget(self.detect_button)
            
    def start_detection(self):
        """Start hardware detection"""
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        self.detect_button.setEnabled(False)
        self.status_label.setText("Detecting hardware...")
        
        # Run detection in background
        QTimer.singleShot(100, self.run_detection)
        
    def run_detection(self):
        """Run actual hardware detection"""
        try:
            # Import hardware detection module
            from kernel.hardware_detection import HardwareDetector
            
            detector = HardwareDetector()
            specs = detector.detect_all()
            
            # Convert to expected format
            self.hardware_info = {
                "cpu": {
                    "model": specs.processors[0].model if specs.processors else "Unknown",
                    "cores": specs.processors[0].cores if specs.processors else 0,
                    "architecture": specs.processors[0].architecture if specs.processors else "Unknown"
                },
                "gpu": [
                    {
                        "name": gpu.model,
                        "memory": f"{gpu.memory_gb}GB" if gpu.memory_gb else "N/A",
                        "vendor": gpu.vendor.value if gpu.vendor else "Unknown"
                    }
                    for gpu in specs.processors if gpu.processor_type.value in ["GPU", "APPLE_GPU"]
                ],
                "memory": {
                    "total": f"{specs.memory.total_gb:.1f}GB" if specs.memory else "Unknown",
                    "available": f"{specs.memory.available_gb:.1f}GB" if specs.memory else "Unknown"
                },
                "storage": [
                    {
                        "device": disk.device,
                        "size": f"{disk.total_gb:.1f}GB",
                        "type": "SSD" if disk.is_ssd else "HDD"
                    }
                    for disk in specs.storage
                ]
            }
            
            # Display results
            self.display_hardware_info()
            self.status_label.setText("✓ Hardware detection complete!")
            self.detection_complete.emit(self.hardware_info)
            
        except Exception as e:
            self.status_label.setText(f"❌ Detection failed: {str(e)}")
            self.info_text.setPlainText(f"Error: {str(e)}\n\nTip: Hardware detection is optional. You can continue setup.")
        
        finally:
            self.progress.setVisible(False)
            self.detect_button.setEnabled(True)
            
    def display_hardware_info(self):
        """Display detected hardware information"""
        info_lines = ["=== Detected Hardware ===\n"]
        
        if "cpu" in self.hardware_info:
            cpu = self.hardware_info["cpu"]
            info_lines.append(f"CPU: {cpu.get('model', 'Unknown')}")
            info_lines.append(f"Cores: {cpu.get('cores', 'N/A')}")
            info_lines.append("")
        
        if "gpu" in self.hardware_info:
            gpus = self.hardware_info["gpu"]
            if gpus:
                info_lines.append("GPUs:")
                for i, gpu in enumerate(gpus, 1):
                    info_lines.append(f"  {i}. {gpu.get('name', 'Unknown')}")
                    info_lines.append(f"     Memory: {gpu.get('memory', 'N/A')}")
                info_lines.append("")
        
        if "memory" in self.hardware_info:
            mem = self.hardware_info["memory"]
            info_lines.append(f"Memory: {mem.get('total', 'Unknown')}")
            info_lines.append("")
            
        if "storage" in self.hardware_info:
            storage = self.hardware_info["storage"]
            info_lines.append("Storage:")
            for disk in storage:
                info_lines.append(f"  • {disk.get('device', 'N/A')}: {disk.get('size', 'N/A')}")
        
        self.info_text.setPlainText("\n".join(info_lines))


class GPUConfigurationStep(QWidget):
    """GPU configuration step"""
    
    def __init__(self, config: OnboardingConfig, hardware_info: Dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.hardware_info = hardware_info
        self.setup_ui()
        
    def setup_ui(self):
        """Setup GPU configuration UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("GPU Configuration")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Video placeholder
        video_placeholder = VideoPlaceholder("GPU Configuration Guide")
        layout.addWidget(video_placeholder)
        
        # GPU options
        options_group = QGroupBox("GPU Settings")
        options_layout = QVBoxLayout()
        
        self.enable_gpu = QCheckBox("Enable GPU Acceleration")
        self.enable_gpu.setChecked(True)
        options_layout.addWidget(self.enable_gpu)
        
        self.cuda_checkbox = QCheckBox("Enable CUDA (NVIDIA)")
        options_layout.addWidget(self.cuda_checkbox)
        
        self.rocm_checkbox = QCheckBox("Enable ROCm (AMD)")
        options_layout.addWidget(self.rocm_checkbox)
        
        self.metal_checkbox = QCheckBox("Enable Metal (Apple)")
        options_layout.addWidget(self.metal_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Auto-detect GPUs
        self.auto_detect_gpus()
            
    def auto_detect_gpus(self):
        """Auto-detect and enable appropriate GPU options"""
        gpus = self.hardware_info.get("gpu", [])
        
        for gpu in gpus:
            name = gpu.get("name", "").lower()
            if "nvidia" in name or "cuda" in name:
                self.cuda_checkbox.setChecked(True)
            elif "amd" in name or "radeon" in name:
                self.rocm_checkbox.setChecked(True)
            elif "apple" in name or "metal" in name:
                self.metal_checkbox.setChecked(True)


class SystemConfigurationStep(QWidget):
    """System configuration step"""
    
    def __init__(self, config: OnboardingConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        """Setup system configuration UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("System Configuration")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Form
        form_group = QGroupBox("Basic Settings")
        form_layout = QVBoxLayout()
        
        # User name
        form_layout.addWidget(QLabel("Your Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name")
        self.name_input.setText(self.config.config.get("user_name", ""))
        form_layout.addWidget(self.name_input)
        
        # System name
        form_layout.addWidget(QLabel("System Name:"))
        self.system_name_input = QLineEdit()
        self.system_name_input.setPlaceholderText("e.g., my-ai-workstation")
        self.system_name_input.setText(self.config.config.get("system_name", ""))
        form_layout.addWidget(self.system_name_input)
        
        # Install path
        form_layout.addWidget(QLabel("Installation Path:"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(self.config.config.get("install_path", str(Path.cwd())))
        path_layout.addWidget(self.path_input)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_path)
        path_layout.addWidget(browse_button)
        form_layout.addLayout(path_layout)
        
        # Auto-start option
        self.auto_start = QCheckBox("Start AI-OS automatically on boot")
        self.auto_start.setChecked(self.config.config.get("auto_start", False))
        form_layout.addWidget(self.auto_start)
        
        # Telemetry option
        self.telemetry = QCheckBox("Send anonymous usage statistics (helps improve AI-OS)")
        self.telemetry.setChecked(self.config.config.get("telemetry_enabled", True))
        form_layout.addWidget(self.telemetry)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
    def browse_path(self):
        """Browse for installation path"""
        path = QFileDialog.getExistingDirectory(self, "Select Installation Directory")
        if path:
            self.path_input.setText(path)
            
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            "user_name": self.name_input.text(),
            "system_name": self.system_name_input.text(),
            "install_path": self.path_input.text(),
            "auto_start": self.auto_start.isChecked(),
            "telemetry_enabled": self.telemetry.isChecked()
        }


class CompletionStep(QWidget):
    """Setup completion step"""
    
    def __init__(self, config: OnboardingConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        """Setup completion UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🎉 Setup Complete!")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Video placeholder
        video_placeholder = VideoPlaceholder("Setup Complete")
        layout.addWidget(video_placeholder)
        
        # Completion message
        message = QLabel(
            "Congratulations! AI-OS is now configured and ready to use.\n\n"
            "You can now start running AI workloads, training models, and "
            "leveraging the full power of your hardware."
        )
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("font-size: 12pt; margin: 20px;")
        layout.addWidget(message)
        
        # Next steps
        next_steps = QGroupBox("Next Steps")
        steps_layout = QVBoxLayout()
        
        steps_text = QTextEdit()
        steps_text.setReadOnly(True)
        steps_text.setMaximumHeight(150)
        steps_text.setHtml("""
            <ul>
                <li><b>Run Demo:</b> Try the demo script to see AI-OS in action</li>
                <li><b>Check Documentation:</b> Read GETTING_STARTED.md for tutorials</li>
                <li><b>Configure Models:</b> Set up your AI models and datasets</li>
                <li><b>Join Community:</b> Connect with other AI-OS users</li>
            </ul>
        """)
        steps_layout.addWidget(steps_text)
        
        next_steps.setLayout(steps_layout)
        layout.addWidget(next_steps)


class OnboardingWizard(QMainWindow):
    """Main onboarding wizard window"""
    
    def __init__(self):
        super().__init__()
        self.config = OnboardingConfig()
        self.hardware_info = {}
        self.current_step = 0
        
        self.setup_ui()
        self.setup_steps()
        
    def setup_ui(self):
        """Setup main window UI"""
        self.setWindowTitle("AI-OS Setup Wizard")
        self.setMinimumSize(900, 700)
        
        # Center window on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        layout = QVBoxLayout(main_widget)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Stacked widget for steps
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.back_button = QPushButton("← Back")
        self.back_button.clicked.connect(self.previous_step)
        self.back_button.setMinimumHeight(40)
        self.back_button.setEnabled(False)
        
        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        
        self.next_button = QPushButton("Next →")
        self.next_button.clicked.connect(self.next_step)
        self.next_button.setMinimumHeight(40)
        self.next_button.setMinimumWidth(120)
        
        self.finish_button = QPushButton("🚀 Launch AI-OS")
        self.finish_button.clicked.connect(self.finish_setup)
        self.finish_button.setMinimumHeight(40)
        self.finish_button.setMinimumWidth(120)
        self.finish_button.setVisible(False)
        
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.finish_button)
        
        layout.addLayout(nav_layout)
        
        # Apply styling
        self.apply_styling()
        
    def create_header(self) -> QWidget:
        """Create header with progress indicator"""
        header = QWidget()
        header.setFixedHeight(80)
        header.setStyleSheet("background-color: #2c3e50; border-radius: 5px;")
        
        layout = QVBoxLayout(header)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                background-color: white;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        
        # Step indicator
        self.step_label = QLabel("Step 1 of 5: Welcome")
        self.step_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;")
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.step_label)
        layout.addWidget(self.progress_bar)
        
        return header
        
    def setup_steps(self):
        """Setup wizard steps"""
        # Step 1: Welcome
        self.welcome_step = WelcomeStep(self.config)
        self.stack.addWidget(self.welcome_step)
        
        # Step 2: Hardware Detection
        self.hardware_step = HardwareDetectionStep(self.config)
        self.hardware_step.detection_complete.connect(self.on_hardware_detected)
        self.stack.addWidget(self.hardware_step)
        
        # Step 3: GPU Configuration (placeholder, will be created after hardware detection)
        self.gpu_step = None
        
        # Step 4: System Configuration
        self.system_step = SystemConfigurationStep(self.config)
        self.stack.addWidget(self.system_step)
        
        # Step 5: Completion
        self.completion_step = CompletionStep(self.config)
        self.stack.addWidget(self.completion_step)
        
        self.update_navigation()
        
    def on_hardware_detected(self, hardware_info: Dict):
        """Handle hardware detection completion"""
        self.hardware_info = hardware_info
        
        # Create GPU configuration step if not exists
        if self.gpu_step is None and self.stack.count() < 5:
            self.gpu_step = GPUConfigurationStep(self.config, hardware_info)
            self.stack.insertWidget(2, self.gpu_step)
            
    def next_step(self):
        """Move to next step"""
        # Validate current step
        if not self.validate_current_step():
            return
            
        # Save current step configuration
        self.save_current_step()
        
        # Move to next step
        if self.current_step < self.stack.count() - 1:
            self.current_step += 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_navigation()
            self.config.mark_step_complete(self.current_step - 1)
            
    def previous_step(self):
        """Move to previous step"""
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_navigation()
            
    def validate_current_step(self) -> bool:
        """Validate current step before proceeding"""
        current_widget = self.stack.currentWidget()
        
        # Step 2: Ensure hardware detection is run (optional)
        if isinstance(current_widget, HardwareDetectionStep):
            if not current_widget.hardware_info:
                reply = QMessageBox.question(
                    self,
                    "Skip Hardware Detection?",
                    "Hardware detection hasn't been run. You can skip this step, but we recommend running it for optimal configuration.\n\nContinue without detection?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                return reply == QMessageBox.StandardButton.Yes
                
        # Step 4: Ensure required fields are filled
        if isinstance(current_widget, SystemConfigurationStep):
            config = current_widget.get_configuration()
            if not config["user_name"] or not config["system_name"]:
                QMessageBox.warning(
                    self,
                    "Required Fields",
                    "Please fill in your name and system name."
                )
                return False
                
        return True
        
    def save_current_step(self):
        """Save current step configuration"""
        current_widget = self.stack.currentWidget()
        
        if isinstance(current_widget, SystemConfigurationStep):
            config = current_widget.get_configuration()
            self.config.config.update(config)
            self.config.save_config()
            
    def update_navigation(self):
        """Update navigation buttons and progress"""
        total_steps = self.stack.count()
        
        # Update progress bar
        progress = int((self.current_step / (total_steps - 1)) * 100)
        self.progress_bar.setValue(progress)
        
        # Update step label
        step_names = [
            "Welcome",
            "Hardware Detection",
            "GPU Configuration",
            "System Settings",
            "Complete"
        ]
        
        if self.current_step < len(step_names):
            step_name = step_names[self.current_step]
            self.step_label.setText(f"Step {self.current_step + 1} of {total_steps}: {step_name}")
        
        # Update buttons
        self.back_button.setEnabled(self.current_step > 0)
        
        if self.current_step == total_steps - 1:
            self.next_button.setVisible(False)
            self.finish_button.setVisible(True)
        else:
            self.next_button.setVisible(True)
            self.finish_button.setVisible(False)
            
    def finish_setup(self):
        """Finish setup and launch AI-OS"""
        # Mark onboarding as complete
        self.config.config["onboarding_complete"] = True
        self.config.save_config()
        
        # Show success message
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Setup Complete")
        msg.setText("AI-OS setup is complete!")
        msg.setInformativeText(
            "Would you like to launch AI-OS now or exit to configure manually?"
        )
        
        launch_button = msg.addButton("Launch Now", QMessageBox.ButtonRole.AcceptRole)
        exit_button = msg.addButton("Exit", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == launch_button:
            self.launch_aios()
        
        self.close()
        
    def launch_aios(self):
        """Launch AI-OS kernel"""
        try:
            import subprocess
            subprocess.Popen([sys.executable, "aios_kernel.py"])
        except Exception as e:
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Failed to launch AI-OS: {str(e)}"
            )
            
    def apply_styling(self):
        """Apply application-wide styling"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 5px;
                font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #3498db;
            }
            QCheckBox {
                font-size: 10pt;
                spacing: 5px;
            }
        """)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("AI-OS Setup")
    app.setOrganizationName("AI-OS")
    
    # Create and show wizard
    wizard = OnboardingWizard()
    wizard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
