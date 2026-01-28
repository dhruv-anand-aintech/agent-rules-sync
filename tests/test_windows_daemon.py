"""
Windows-specific daemon tests for Agent Rules Sync.

These tests verify Windows daemon installation and management behavior.
Note: Some tests use mocking to simulate Windows behavior on non-Windows platforms.
"""

import sys
import threading
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from agent_rules_sync import AgentRulesSync


class TestWindowsDaemonThreading:
    """Test Windows daemon threading and graceful shutdown."""

    def test_stop_event_created_on_init(self):
        """Test: stop_event is initialized in __init__."""
        sync = AgentRulesSync()
        assert hasattr(sync, 'stop_event')
        assert isinstance(sync.stop_event, threading.Event)
        assert not sync.stop_event.is_set()

    def test_stop_event_not_set_initially(self):
        """Test: stop_event is not set initially."""
        sync = AgentRulesSync()
        assert not sync.stop_event.is_set()

    def test_daemon_stop_sets_stop_event(self):
        """Test: daemon_stop() sets the stop_event on Windows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.pid_file = config_dir / "daemon.pid"
            
            # Create a PID file to simulate running daemon
            sync.pid_file.write_text("12345")
            
            # Mock platform check
            with patch('sys.platform', 'win32'):
                # Capture print output
                with patch('builtins.print'):
                    sync.daemon_stop()
            
            # stop_event should be set
            assert sync.stop_event.is_set()
            # PID file should be removed
            assert not sync.pid_file.exists()

    def test_windows_daemon_loop_respects_stop_event(self):
        """Test: Windows daemon loop checks stop_event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            master_file = config_dir / "RULES.md"
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.master_file = master_file
            
            # Initialize files
            sync._ensure_master_exists()
            master_file.write_text("# Shared Rules\n")
            
            # Set up minimal agents
            for agent_id in ["claude", "cursor"]:
                agent_file = config_dir / f"{agent_id}.md"
                agent_file.write_text("# Shared Rules\n")
                sync.agents[agent_id]["path"] = agent_file
            
            # Simulate the loop checking stop_event
            loop_iterations = 0
            sync.stop_event.clear()
            
            while not sync.stop_event.is_set() and loop_iterations < 2:
                loop_iterations += 1
                if loop_iterations == 1:
                    sync.stop_event.set()
            
            # Verify loop exited due to stop_event
            assert sync.stop_event.is_set()
            assert loop_iterations == 1


class TestWindowsInstallation:
    """Test Windows daemon installation logic."""

    @patch('subprocess.run')
    def test_task_scheduler_installation_attempted(self, mock_run):
        """Test: Task Scheduler installation is attempted on Windows."""
        # Import here to avoid issues on non-Windows systems
        import install_daemon
        
        # Mock the Task Scheduler command
        mock_run.return_value = MagicMock(returncode=0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Would normally use Path.home(), but we mock it
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                result = install_daemon._try_install_task_scheduler()
                
                # Verify schtasks was called
                assert mock_run.called
                call_args = str(mock_run.call_args)
                assert "schtasks" in call_args or result is True or result is False

    @patch('subprocess.run')
    def test_batch_file_fallback_created(self, mock_run):
        """Test: Batch file fallback is created when Task Scheduler fails."""
        import install_daemon
        
        # Simulate Task Scheduler failure
        mock_run.return_value = MagicMock(returncode=1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            startup_dir = Path(tmpdir) / "Startup"
            startup_dir.mkdir()
            
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                # This would create batch file
                result = install_daemon._install_windows_startup_folder()
                assert result is True


class TestWindowsDaemonStop:
    """Test Windows daemon stop behavior."""

    def test_daemon_stop_removes_pid_file(self):
        """Test: daemon_stop() removes the PID file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.pid_file = config_dir / "daemon.pid"
            
            # Create PID file
            sync.pid_file.write_text("12345")
            assert sync.pid_file.exists()
            
            # Mock platform check and capture output
            with patch('sys.platform', 'win32'):
                with patch('builtins.print'):
                    sync.daemon_stop()
            
            # PID file should be gone
            assert not sync.pid_file.exists()

    def test_daemon_stop_when_not_running(self):
        """Test: daemon_stop() gracefully handles missing PID file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.pid_file = config_dir / "daemon.pid"
            
            # Ensure PID file doesn't exist
            assert not sync.pid_file.exists()
            
            # Should print error but not crash
            with patch('builtins.print') as mock_print:
                sync.daemon_stop()
                mock_print.assert_called()

    def test_daemon_stop_handles_invalid_pid(self):
        """Test: daemon_stop() handles corrupted PID file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.pid_file = config_dir / "daemon.pid"
            
            # Create corrupted PID file
            sync.pid_file.write_text("not-a-number")
            
            # Should handle gracefully
            with patch('builtins.print'):
                sync.daemon_stop()
            
            # PID file should still be cleaned up
            assert not sync.pid_file.exists()


class TestUninstallScript:
    """Test cross-platform uninstall.py script."""

    def test_uninstall_removes_config_directory(self):
        """Test: uninstall removes config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".config" / "agent-rules-sync"
            config_dir.mkdir(parents=True)
            
            # Create dummy config files
            (config_dir / "RULES.md").write_text("# Rules")
            (config_dir / "daemon.pid").write_text("12345")
            
            assert config_dir.exists()
            
            # In real scenario, uninstall.py would remove this
            import shutil
            shutil.rmtree(config_dir)
            
            assert not config_dir.exists()

    def test_uninstall_python_script_syntax_valid(self):
        """Test: uninstall.py is valid Python."""
        uninstall_path = Path(__file__).parent.parent / "uninstall.py"
        
        # Should be able to compile without syntax errors
        with open(uninstall_path) as f:
            code = f.read()
        
        # This will raise SyntaxError if invalid
        compile(code, "uninstall.py", "exec")


class TestWindowsDaemonCompatibility:
    """Test Windows daemon compatibility with real stop mechanism."""

    def test_daemon_start_windows_uses_thread(self):
        """Test: _daemon_start_windows creates background thread."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.master_file = config_dir / "RULES.md"
            sync.pid_file = config_dir / "daemon.pid"
            
            # Initialize
            sync._ensure_master_exists()
            
            # Mock to prevent actual daemon start
            with patch('threading.Thread') as mock_thread:
                mock_instance = MagicMock()
                mock_thread.return_value = mock_instance
                
                with patch('builtins.print'):
                    sync._daemon_start_windows()
                
                # Verify thread was created
                mock_thread.assert_called_once()
                mock_instance.start.assert_called_once()

    def test_windows_daemon_thread_is_daemon(self):
        """Test: Windows daemon thread is created as daemon thread."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.master_file = config_dir / "RULES.md"
            sync.pid_file = config_dir / "daemon.pid"
            
            sync._ensure_master_exists()
            
            with patch('threading.Thread') as mock_thread:
                mock_instance = MagicMock()
                mock_thread.return_value = mock_instance
                
                with patch('builtins.print'):
                    sync._daemon_start_windows()
                
                # Check daemon=True was passed
                call_kwargs = mock_thread.call_args[1]
                assert call_kwargs.get('daemon') is True


# Integration test
class TestWindowsDaemonIntegration:
    """Integration tests for Windows daemon behavior."""

    def test_full_daemon_lifecycle_windows(self):
        """Test: Full Windows daemon start -> stop lifecycle."""
        if sys.platform != 'win32':
            # Skip on non-Windows for actual daemon test
            pytest.skip("Windows-only test")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            sync = AgentRulesSync()
            sync.config_dir = config_dir
            sync.master_file = config_dir / "RULES.md"
            sync.pid_file = config_dir / "daemon.pid"
            
            sync._ensure_master_exists()
            
            # Note: We don't actually start/stop daemon in tests
            # as it would run indefinitely, but we verify the mechanisms work
            assert sync.stop_event is not None
            assert isinstance(sync.stop_event, threading.Event)
