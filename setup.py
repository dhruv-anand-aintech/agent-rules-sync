#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agent-rules-sync",
    version="1.0.0",
    author="Agent Rules Sync Contributors",
    description="Synchronize rules across AI coding assistants (Claude Code, Cursor, Gemini, OpenCode)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/agent-rules-sync",
    py_modules=["agent_rules_sync"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "agent-rules-sync=agent_rules_sync:main",
        ],
    },
)
