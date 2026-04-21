"""
compatibility_checker.py

A module to check software compatibility with the AIOS system.
"""
import json
import platform
import subprocess
import sys
from typing import Dict, Any, List, Optional

class CompatibilityReport:
    def __init__(self, compatible: bool, issues: Optional[List[str]] = None, suggestions: Optional[List[str]] = None):
        self.compatible = compatible
        self.issues = issues or []
        self.suggestions = suggestions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compatible": self.compatible,
            "issues": self.issues,
            "suggestions": self.suggestions
        }

class CompatibilityChecker:
        def check_binary(self, binary_path: str) -> CompatibilityReport:
            """
            Checks if a binary is compatible with the current OS and architecture.
            Uses 'file' command to inspect binary type.
            """
            import shutil
            issues = []
            suggestions = []
            if not shutil.which("file"):
                issues.append("'file' command not available to check binary type.")
                suggestions.append("Install 'file' utility to enable binary compatibility checks.")
                return CompatibilityReport(False, issues, suggestions)
            try:
                output = subprocess.check_output(["file", binary_path], text=True)
                # Example output: 'ELF 64-bit LSB executable, x86-64, ...'
                current_arch = platform.machine()
                current_os = platform.system()
                if current_os == "Linux" and "ELF" not in output:
                    issues.append(f"Binary is not ELF format (Linux expected): {output.strip()}")
                elif current_os == "Darwin" and "Mach-O" not in output:
                    issues.append(f"Binary is not Mach-O format (macOS expected): {output.strip()}")
                elif current_os == "Windows" and "PE32" not in output and "PE32+" not in output:
                    issues.append(f"Binary is not PE format (Windows expected): {output.strip()}")
                if current_arch in ["x86_64", "amd64"] and "64-bit" not in output:
                    issues.append(f"Binary is not 64-bit as required: {output.strip()}")
                if current_arch in ["arm64", "aarch64"] and "ARM" not in output:
                    issues.append(f"Binary is not ARM as required: {output.strip()}")
            except Exception as e:
                issues.append(f"Failed to analyze binary: {e}")
            compatible = len(issues) == 0
            return CompatibilityReport(compatible, issues, suggestions)

        def check_container_image(self, image_name: str) -> CompatibilityReport:
            """
            Checks if a container image can run on the current system (basic check: architecture).
            Requires 'docker' or 'podman' CLI.
            """
            import shutil
            issues = []
            suggestions = []
            docker_cmd = shutil.which("docker") or shutil.which("podman")
            if not docker_cmd:
                issues.append("Neither 'docker' nor 'podman' is available to inspect container images.")
                suggestions.append("Install Docker or Podman to enable container image checks.")
                return CompatibilityReport(False, issues, suggestions)
            try:
                inspect_cmd = [docker_cmd, "image", "inspect", image_name, "--format", "{{json .Architecture}}"]
                arch = subprocess.check_output(inspect_cmd, text=True).strip().strip('"')
                current_arch = platform.machine()
                # Normalize arch names
                arch_map = {"x86_64": ["amd64", "x86_64"], "arm64": ["arm64", "aarch64"]}
                match = False
                for k, v in arch_map.items():
                    if current_arch in v and arch in v:
                        match = True
                if not match:
                    issues.append(f"Container image architecture '{arch}' does not match system '{current_arch}'")
            except Exception as e:
                issues.append(f"Failed to inspect container image: {e}")
            compatible = len(issues) == 0
            return CompatibilityReport(compatible, issues, suggestions)

        def check_shell_script(self, script_path: str) -> CompatibilityReport:
            """
            Checks if a shell script has a valid shebang and is executable.
            """
            import os
            issues = []
            suggestions = []
            try:
                with open(script_path, "r") as f:
                    first_line = f.readline()
                    if not first_line.startswith("#!"):
                        issues.append("Script does not have a shebang (#!) line.")
                        suggestions.append("Add a shebang line, e.g., #!/bin/bash")
                if not os.access(script_path, os.X_OK):
                    issues.append("Script is not executable.")
                    suggestions.append(f"Run: chmod +x {script_path}")
            except Exception as e:
                issues.append(f"Failed to check shell script: {e}")
            compatible = len(issues) == 0
            return CompatibilityReport(compatible, issues, suggestions)
        
        def __init__(self, system_specs_path: str = "system_specs.json"):
            self.system_specs = self._load_system_specs(system_specs_path)

        def _load_system_specs(self, path: str) -> Dict[str, Any]:
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                return {}

        def check_python_requirements(self, requirements_path: str) -> CompatibilityReport:
            issues = []
            suggestions = []
            try:
                with open(requirements_path, "r") as f:
                    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            except Exception as e:
                return CompatibilityReport(False, [f"Failed to read requirements: {e}"], [])

            for req in requirements:
                try:
                    subprocess.check_output([sys.executable, "-m", "pip", "show", req.split("==")[0]])
                except subprocess.CalledProcessError:
                    issues.append(f"Missing Python package: {req}")
                    suggestions.append(f"Install with: pip install {req}")

            compatible = len(issues) == 0
            return CompatibilityReport(compatible, issues, suggestions)

        def check_os(self, required_os: Optional[str] = None, required_arch: Optional[str] = None) -> CompatibilityReport:
            issues = []
            suggestions = []
            current_os = platform.system()
            current_arch = platform.machine()
            if required_os and required_os.lower() != current_os.lower():
                issues.append(f"OS mismatch: required {required_os}, found {current_os}")
            if required_arch and required_arch.lower() != current_arch.lower():
                issues.append(f"Architecture mismatch: required {required_arch}, found {current_arch}")
            compatible = len(issues) == 0
            return CompatibilityReport(compatible, issues, suggestions)

        def check(self, metadata: Dict[str, Any]) -> CompatibilityReport:
            """
            metadata: {
                "requirements_path": str (optional),
                "required_os": str (optional),
                "required_arch": str (optional),
                "binary_path": str (optional),
                "container_image": str (optional),
                "shell_script_path": str (optional)
            }
            """
            reports = []
            if "requirements_path" in metadata:
                reports.append(self.check_python_requirements(metadata["requirements_path"]))
            if "required_os" in metadata or "required_arch" in metadata:
                reports.append(self.check_os(metadata.get("required_os"), metadata.get("required_arch")))
            if "binary_path" in metadata:
                reports.append(self.check_binary(metadata["binary_path"]))
            if "container_image" in metadata:
                reports.append(self.check_container_image(metadata["container_image"]))
            if "shell_script_path" in metadata:
                reports.append(self.check_shell_script(metadata["shell_script_path"]))
            compatible = all(r.compatible for r in reports)
            issues = sum([r.issues for r in reports], [])
            suggestions = sum([r.suggestions for r in reports], [])
            return CompatibilityReport(compatible, issues, suggestions)

        def check_all(self, metadata: List[Dict[str, Any]]) -> CompatibilityReport:
            reports = [self.check(m) for m in metadata]
            compatible = all(r.compatible for r in reports)
            issues = sum([r.issues for r in reports], [])
            suggestions = sum([r.suggestions for r in reports], [])
            return CompatibilityReport(compatible, issues, suggestions)

if __name__ == "__main__":
    checker = CompatibilityChecker()
    metadata = [
        {
            "requirements_path": "requirements.txt",
            "required_os": "Linux",
            "required_arch": "x86_64",
            "binary_path": "my_binary",
            "container_image": "my_image:latest",
            "shell_script_path": "setup.sh"
        }
    ]
    report = checker.check_all(metadata)
    print(json.dumps(report.to_dict(), indent=2))
