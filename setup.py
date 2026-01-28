#!/usr/bin/env python3
"""
Setup script for Agent Rules Sync.

This file is REQUIRED because it defines a custom install hook.

WHY THIS FILE EXISTS:
- The InstallWithDaemon class runs install_daemon.py after pip installation
- This auto-installs the daemon service (launchd/systemd/Task Scheduler)
- Without this hook, users would need to manually run: agent-rules-sync

STAY IN SYNC WITH PYPROJECT.TOML:
- All package metadata (name, version, description) is in pyproject.toml
- setup.py only defines the custom class, not configuration
- When setup() is called with just cmdclass={...}, setuptools reads the rest from pyproject.toml
- No duplication = no sync issues!
"""
import subprocess
import sys
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


setup(
    cmdclass={"install": InstallWithDaemon},
)
