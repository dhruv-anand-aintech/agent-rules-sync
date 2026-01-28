#!/usr/bin/env python3
"""
Setup script for Agent Rules Sync.

This minimal setup.py preserves the custom install hook for daemon installation.
All other configuration is in pyproject.toml (modern standard).
"""
import subprocess
import sys
from pathlib import Path
from setuptools import setup
from setuptools.command.install import install


class InstallWithDaemon(install):
    """Custom install command that sets up daemon after installation."""

    def run(self):
        install.run(self)
        # Run daemon installer after package is installed
        try:
            subprocess.check_call([sys.executable, "install_daemon.py"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\n⚠️  Could not auto-start daemon. Run manually:")
            print("   agent-rules-sync")


# Read version from pyproject.toml (single source of truth)
def get_version():
    """Read version from pyproject.toml."""
    import tomllib if sys.version_info >= (3, 11) else tomli
    
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomli as tomllib
        except ImportError:
            # Fallback if tomli not installed
            return "1.2.1"
    
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


setup(
    cmdclass={"install": InstallWithDaemon},
)
