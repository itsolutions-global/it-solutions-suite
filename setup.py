"""
IT Solutions Enterprise Suite - Setup Script
Enables installation via `pip install .` or `pip install -e .`
"""

from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
readme_text = (this_directory / "README.md").read_text(encoding="utf-8") if (this_directory / "README.md").exists() else ""

setup(
    name="it-solutions-suite",
    version="1.0.0",
    description="Autonomous Corporate Enterprise Suite: CorePulse + NexusShield + EchoStream",
    long_description=readme_text,
    long_description_content_type="text/markdown",
    author="IT Solutions Global Corporation",
    author_email="engineering@itsolutions.corp",
    license="MIT",
    url="https://github.com/itsolutions-corp/it-solutions-suite",
    packages=find_packages(include=["products*"]),
    include_package_data=True,
    package_data={
        "": [
            "*.html",
            "*.css",
            "*.js",
            "*.json",
            "*.md",
            "*.svg",
            "*.ico",
            "*.txt"
        ],
    },
    entry_points={
        "console_scripts": [
            "it-solutions=products.cli:main",
        ],
    },
    python_requires=">=3.8",
    install_requires=[],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Security",
        "Topic :: Office/Business",
        "Operating System :: OS Independent",
    ],
)
