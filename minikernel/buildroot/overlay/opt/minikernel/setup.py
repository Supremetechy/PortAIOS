"""
MiniKernel Setup Configuration
PyPI package setup for easy installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text().split('\n')
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="minikernel",
    version="0.1.0",
    author="MiniKernel Project",
    author_email="minikernel@example.com",
    description="AI-First Voice-Controlled Operating System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/minikernel",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/minikernel/issues",
        "Source": "https://github.com/yourusername/minikernel",
        "Documentation": "https://minikernel.readthedocs.io",
    },
    packages=find_packages(exclude=["tests", "tests.*", "deploy", "deploy.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Operating System Kernels",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "llm": [
            "llama-cpp-python>=0.2.0",
        ],
        "voice": [
            # Voice dependencies from PortAIOS
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "all": [
            "llama-cpp-python>=0.2.0",
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "minikernel=minikernel.boot:main",
        ],
    },
    include_package_data=True,
    package_data={
        "minikernel": [
            "security/*.json",
            "models/*.onnx",
            "models/*.json",
        ],
    },
    zip_safe=False,
    keywords="ai operating-system voice-control microkernel llm natural-language",
)
