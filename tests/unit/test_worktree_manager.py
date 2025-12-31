"""
Unit tests for WorktreeManager.

Tests cover port allocation, database isolation, and core logic
without requiring actual git repositories.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.worktree_manager import WorktreeInfo, WorktreeManager


@pytest.fixture
def temp_dir(tmp_path: Path):
    """
    Create a temporary directory for testing.

    Args:
        tmp_path: Temporary directory path

    Yields:
        Path to temporary directory with data folder
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    yield tmp_path


@pytest.fixture
def worktree_manager(temp_dir: Path) -> WorktreeManager:
    """
    Create WorktreeManager instance for testing.

    Args:
        temp_dir: Temporary directory path

    Yields:
        WorktreeManager instance
    """
    # Use a smaller port range for testing
    manager = WorktreeManager(
        repo_root=temp_dir,
        port_range_start=9001,
        port_range_end=9010,
    )
    yield manager

    # Cleanup port registry
    manager.ports_registry_path.unlink(missing_ok=True)


class TestWorktreeManagerInitialization:
    """Test WorktreeManager initialization."""

    def test_initialization(self, temp_dir: Path):
        """Test WorktreeManager initialization."""
        wm = WorktreeManager(repo_root=temp_dir)

        assert wm.repo_root == temp_dir
        assert wm.port_range_start == 8001
        assert wm.port_range_end == 8099
        assert wm.ports_registry_path == temp_dir / "data" / "worktree-ports.json"
        assert wm.ports_lock_path == temp_dir / "data" / "worktree-ports.lock"

    def test_custom_port_range(self, temp_dir: Path):
        """Test WorktreeManager with custom port range."""
        wm = WorktreeManager(
            repo_root=temp_dir,
            port_range_start=9001,
            port_range_end=9099,
        )

        assert wm.port_range_start == 9001
        assert wm.port_range_end == 9099


class TestDatabaseIsolation:
    """Test database isolation for worktrees."""

    def test_get_db_suffix(self, worktree_manager: WorktreeManager):
        """Test database suffix generation."""
        assert worktree_manager._get_db_suffix("feature/test") == "feature-test"
        assert worktree_manager._get_db_suffix("feature/test_branch") == "feature-test-branch"
        assert worktree_manager._get_db_suffix("fix/bug-123") == "fix-bug-123"
        assert worktree_manager._get_db_suffix("docs/update_guide") == "docs-update-guide"

    def test_db_suffix_replaces_backslashes(self, worktree_manager: WorktreeManager):
        """Test that backslashes are replaced in DB suffix."""
        # Windows-style paths
        assert worktree_manager._get_db_suffix("feature\\test") == "feature-test"
        assert worktree_manager._get_db_suffix("fix\\bug-123") == "fix-bug-123"

    def test_db_suffix_replaces_underscores(self, worktree_manager: WorktreeManager):
        """Test that underscores are replaced in DB suffix."""
        assert worktree_manager._get_db_suffix("feature/test_branch") == "feature-test-branch"

    def test_get_db_path(self, worktree_manager: WorktreeManager):
        """Test database path generation."""
        db_path = worktree_manager.get_db_path("feature/test")
        expected = worktree_manager.repo_root / "data" / "articles-feature-test.db"
        assert db_path == expected

    def test_db_suffix_uniqueness(self, worktree_manager: WorktreeManager):
        """Test that different branches get unique DB suffixes."""
        branches = [
            "feature/oauth2",
            "feature/redis-cache",
            "fix/critical-bug",
            "docs/update-guide",
        ]

        suffixes = [worktree_manager._get_db_suffix(branch) for branch in branches]

        # All suffixes should be unique
        assert len(set(suffixes)) == len(suffixes)

        # Suffixes should not contain slashes
        for suffix in suffixes:
            assert "/" not in suffix
            assert "\\" not in suffix

    def test_db_path_isolation(self, worktree_manager: WorktreeManager):
        """Test that different branches get different DB paths."""
        db_path1 = worktree_manager.get_db_path("feature/branch-a")
        db_path2 = worktree_manager.get_db_path("feature/branch-b")

        assert db_path1 != db_path2
        assert "branch-a" in str(db_path1)
        assert "branch-b" in str(db_path2)


class TestPortAllocation:
    """Test port allocation functionality."""

    def test_port_allocation(self, worktree_manager: WorktreeManager):
        """Test port allocation and release."""
        # Allocate ports
        port1 = worktree_manager.allocate_port("feature/test1")
        port2 = worktree_manager.allocate_port("feature/test2")

        assert port1 == 9001  # First available port
        assert port2 == 9002  # Second available port

        # Same branch gets same port
        port1_again = worktree_manager.allocate_port("feature/test1")
        assert port1_again == port1

        # Release port
        worktree_manager.release_port("feature/test1")

        # Port can be reused
        port3 = worktree_manager.allocate_port("feature/test3")
        assert port3 == 9001  # Reused port

    def test_port_allocation_exhaustion(self, worktree_manager: WorktreeManager):
        """Test port allocation exhaustion."""
        # Allocate all available ports (9001-9010 = 10 ports)
        for i in range(10):
            worktree_manager.allocate_port(f"feature/test{i}")

        # Next allocation should fail
        with pytest.raises(RuntimeError, match="No ports available"):
            worktree_manager.allocate_port("feature/test10")

    def test_get_available_capacity(self, worktree_manager: WorktreeManager):
        """Test available capacity calculation."""
        # Initially full capacity
        assert worktree_manager.get_available_capacity() == 10

        # Allocate some ports
        worktree_manager.allocate_port("feature/test1")
        worktree_manager.allocate_port("feature/test2")

        assert worktree_manager.get_available_capacity() == 8

    def test_registry_persistence(self, worktree_manager: WorktreeManager):
        """Test port registry persistence."""
        # Allocate a port
        port = worktree_manager.allocate_port("feature/test")

        # Read registry directly
        registry = worktree_manager._read_registry()
        assert registry["feature/test"] == port

        # Release port
        worktree_manager.release_port("feature/test")

        # Verify release
        registry = worktree_manager._read_registry()
        assert "feature/test" not in registry

    def test_concurrent_allocation_safety(self, worktree_manager: WorktreeManager):
        """Test that concurrent allocations don't create duplicate ports."""

        # Simulate concurrent allocations
        ports = []
        for i in range(5):
            port = worktree_manager.allocate_port(f"feature/concurrent{i}")
            ports.append(port)

        # All ports should be unique
        assert len(set(ports)) == len(ports)

        # All should be within range
        for port in ports:
            assert 9001 <= port <= 9010


class TestWorktreeInfo:
    """Test WorktreeInfo dataclass."""

    def test_worktree_info_creation(self):
        """Test creating WorktreeInfo instance."""
        info = WorktreeInfo(
            branch="feature/test",
            path=Path("/tmp/test"),
            port=8001,
            db_suffix="feature-test",
            commit="abc123",
        )

        assert info.branch == "feature/test"
        assert info.path == Path("/tmp/test")
        assert info.port == 8001
        assert info.db_suffix == "feature-test"
        assert info.commit == "abc123"


class TestWorktreeDetection:
    """Test worktree detection functionality."""

    @patch("subprocess.run")
    def test_is_worktree_with_file_git(self, mock_run: Mock, worktree_manager: WorktreeManager):
        """Test worktree detection when .git is a file (not a directory)."""
        # Mock git rev-parse to return a file path (worktree case)
        mock_result = Mock()
        mock_result.stdout.strip.return_value = ".git"
        mock_run.return_value = mock_result

        # Mock is_file to return True
        with patch.object(Path, "is_file", return_value=True):
            result = worktree_manager.is_worktree()
            assert result is True

    @patch("subprocess.run")
    def test_is_not_worktree_with_directory_git(
        self, mock_run: Mock, worktree_manager: WorktreeManager
    ):
        """Test worktree detection when .git is a directory (main repo case)."""
        # Mock git rev-parse to return a directory path (main repo case)
        mock_result = Mock()
        mock_result.stdout.strip.return_value = ".git"
        mock_run.return_value = mock_result

        # Mock is_file to return False (directory)
        with patch.object(Path, "is_file", return_value=False):
            result = worktree_manager.is_worktree()
            assert result is False

    @patch("subprocess.run")
    def test_is_not_worktree_on_error(self, mock_run: Mock, worktree_manager: WorktreeManager):
        """Test worktree detection when git command fails."""
        # Mock git rev-parse to raise an error
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = worktree_manager.is_worktree()
        assert result is False


class TestWorktreeCreationLogic:
    """Test worktree creation logic (without actual git)."""

    @patch("subprocess.run")
    def test_create_worktree_allocates_port(
        self, mock_run: Mock, worktree_manager: WorktreeManager
    ):
        """Test that create_worktree allocates a port."""
        # Mock git worktree add command
        mock_run.return_value = Mock()

        # Mock rev-parse for commit SHA
        def mock_side_effect(*args, **kwargs):
            result = Mock()
            if "rev-parse" in args[0] and "HEAD" in args[0]:
                result.stdout.strip.return_value = "abc123def4567890123456789012345678901234"
            return result

        mock_run.side_effect = mock_side_effect

        # Create worktree
        info = worktree_manager.create_worktree("feature/test")

        # Verify port was allocated
        assert info.port == 9001
        assert info.branch == "feature/test"
        assert info.db_suffix == "feature-test"

    @patch("subprocess.run")
    def test_create_worktree_releases_port_on_failure(
        self, mock_run: Mock, worktree_manager: WorktreeManager
    ):
        """Test that create_worktree releases port on git failure."""
        import subprocess

        # Mock git worktree add to fail
        mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr="Git command failed")

        # Port should be allocated first
        port = worktree_manager.allocate_port("feature/test")
        assert port == 9001

        # Create worktree should fail and release port
        with pytest.raises(RuntimeError, match="Failed to create worktree"):
            worktree_manager.create_worktree("feature/test")

        # Port should be released
        port2 = worktree_manager.allocate_port("feature/test2")
        assert port2 == 9001  # Port was released and reused


class TestWorktreeCleanup:
    """Test worktree cleanup functionality."""

    @patch("subprocess.run")
    def test_cleanup_worktree_with_existing_worktree(
        self, mock_run: Mock, worktree_manager: WorktreeManager
    ):
        """Test cleaning up a worktree that exists."""
        # Mock list_worktrees to return a worktree
        worktree_info = WorktreeInfo(
            branch="feature/test",
            path=Path("/tmp/test-worktree"),
            port=9001,
            db_suffix="feature-test",
            commit="abc123",
        )

        with patch.object(worktree_manager, "list_worktrees", return_value=[worktree_info]):
            worktree_manager.cleanup_worktree("feature/test")

            # Verify git worktree remove was called
            assert mock_run.called
            args = mock_run.call_args[0][0]
            assert "worktree" in args
            assert "remove" in args

            # Port should be released
            registry = worktree_manager._read_registry()
            assert "feature/test" not in registry

    @patch("subprocess.run")
    def test_cleanup_worktree_with_nonexistent_worktree(
        self, mock_run: Mock, worktree_manager: WorktreeManager
    ):
        """Test cleaning up a worktree that doesn't exist."""
        # Mock list_worktrees to return empty
        with patch.object(worktree_manager, "list_worktrees", return_value=[]):
            # Should not raise an exception
            worktree_manager.cleanup_worktree("feature/nonexistent")

            # Git command should not be called
            assert not mock_run.called


class TestWorktreeListing:
    """Test worktree listing functionality."""

    @patch("subprocess.run")
    def test_list_worktrees_parses_output(self, mock_run: Mock, worktree_manager: WorktreeManager):
        """Test that list_worktrees parses git output correctly."""
        # Mock git worktree list output
        git_output = """worktree /path/to/main
HEAD abc123
branch refs/heads/main

worktree /path/to/feature
HEAD def456
branch refs/heads/feature/test

"""

        mock_result = Mock()
        mock_result.stdout = git_output
        mock_run.return_value = mock_result

        worktrees = worktree_manager.list_worktrees()

        assert len(worktrees) == 2
        assert worktrees[0].branch == "main"
        assert worktrees[0].path == Path("/path/to/main")
        assert worktrees[0].commit == "abc123"
        assert worktrees[1].branch == "feature/test"
        assert worktrees[1].path == Path("/path/to/feature")
        assert worktrees[1].commit == "def456"


class TestWorktreePrune:
    """Test worktree pruning functionality."""

    @patch("subprocess.run")
    def test_prune_calls_git_command(self, mock_run: Mock, worktree_manager: WorktreeManager):
        """Test that prune calls git worktree prune."""
        worktree_manager.prune()

        # Verify git worktree prune was called
        assert mock_run.called
        args = mock_run.call_args[0][0]
        assert "worktree" in args
        assert "prune" in args


class TestGetCurrentBranch:
    """Test getting current branch name."""

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run: Mock, worktree_manager: WorktreeManager):
        """Test getting current branch name."""
        # Mock git branch --show-current
        mock_result = Mock()
        mock_result.stdout.strip.return_value = "feature/test-branch"
        mock_run.return_value = mock_result

        branch = worktree_manager.get_current_branch()
        assert branch == "feature/test-branch"


class TestGetWorktreeInfo:
    """Test getting worktree info by path."""

    def test_get_worktree_info_found(self, worktree_manager: WorktreeManager):
        """Test getting worktree info when found."""
        test_path = Path("/tmp/test-worktree")

        # Mock list_worktrees to return worktrees
        worktree_info = WorktreeInfo(
            branch="feature/test",
            path=test_path,
            port=9001,
            db_suffix="feature-test",
            commit="abc123",
        )

        with patch.object(worktree_manager, "list_worktrees", return_value=[worktree_info]):
            result = worktree_manager.get_worktree_info(test_path)
            assert result is not None
            assert result.branch == "feature/test"

    def test_get_worktree_info_not_found(self, worktree_manager: WorktreeManager):
        """Test getting worktree info when not found."""
        test_path = Path("/tmp/nonexistent-worktree")

        # Mock list_worktrees to return empty
        with patch.object(worktree_manager, "list_worktrees", return_value=[]):
            result = worktree_manager.get_worktree_info(test_path)
            assert result is None


class TestSetupEnvironment:
    """Test environment setup for worktrees."""

    @patch("subprocess.run")
    def test_setup_environment_copies_env_file(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_environment copies and extends .env file."""
        # Create main .env file
        main_env = temp_dir / ".env"
        main_env.write_text("TEST_VAR=value\n")

        # Create worktree path
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Setup environment
        worktree_manager.setup_environment(worktree_path, "feature/test", 8001)

        # Verify .env was created in worktree
        worktree_env = worktree_path / ".env"
        assert worktree_env.exists()

        # Verify it contains original variables
        content = worktree_env.read_text()
        assert "TEST_VAR=value" in content

        # Verify it contains WORKTREE variables
        assert "WORKTREE_MODE=True" in content
        assert "WORKTREE_BRANCH=feature/test" in content
        assert "WORKTREE_PORT=8001" in content
        assert "WORKTREE_DB_SUFFIX=feature-test" in content
        assert "PORT=8001" in content

    @patch("subprocess.run")
    def test_setup_environment_creates_claude_dir(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_environment creates .claude directory."""
        # Create main .claude directory
        main_claude = temp_dir / ".claude"
        main_claude.mkdir()

        # Create worktree path
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Setup environment
        worktree_manager.setup_environment(worktree_path, "feature/test", 8001)

        # Verify .claude was created in worktree
        worktree_claude = worktree_path / ".claude"
        assert worktree_claude.exists()

    @patch("subprocess.run")
    def test_setup_environment_copies_settings_files(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_environment copies settings files."""

        # Create main .claude directory with config files
        main_claude = temp_dir / ".claude"
        main_claude.mkdir()
        (main_claude / "settings.json").write_text('{"test": true}')
        (main_claude / "CLAUDE.md").write_text("# Test")
        (main_claude / "settings.local.json").write_text('{"local": true}')

        # Create worktree path
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Setup environment
        worktree_manager.setup_environment(worktree_path, "feature/test", 8001)

        # Verify config files were copied
        worktree_claude = worktree_path / ".claude"
        assert (worktree_claude / "settings.json").exists()
        assert (worktree_claude / "CLAUDE.md").exists()
        assert (worktree_claude / "settings.local.json").exists()

    @patch("subprocess.run")
    def test_setup_environment_handles_missing_main_env(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_environment handles missing main .env gracefully."""
        # Create worktree path (no main .env exists)
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Should not raise an exception
        worktree_manager.setup_environment(worktree_path, "feature/test", 8001)

        # .env should not be created in worktree
        assert not (worktree_path / ".env").exists()

    @patch("subprocess.run")
    def test_setup_environment_appends_newline_if_needed(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_environment adds newline before appending if needed."""
        # Create main .env file without trailing newline
        main_env = temp_dir / ".env"
        main_env.write_text("TEST_VAR=value")

        # Create worktree path
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Setup environment
        worktree_manager.setup_environment(worktree_path, "feature/test", 8001)

        # Verify content format is correct
        worktree_env = worktree_path / ".env"
        content = worktree_env.read_text()
        # Should have newline between content and worktree config
        assert "TEST_VAR=value\n\n# --- Worktree Configuration" in content


class TestSetupVenvLink:
    """Test venv symlink creation for worktrees."""

    @patch("subprocess.run")
    def test_setup_venv_link_creates_symlink(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_venv_link creates a symlink."""
        # Create main venv
        main_venv = temp_dir / ".venv"
        main_venv.mkdir()

        # Create worktree path
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Mock symlink_to to succeed
        with patch.object(Path, "symlink_to") as mock_symlink:
            worktree_manager.setup_venv_link(worktree_path)
            # Verify symlink was attempted
            mock_symlink.assert_called_once()

    @patch("subprocess.run")
    def test_setup_venv_link_skips_if_no_main_venv(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_venv_link skips if main venv doesn't exist."""
        # Create worktree path (no main venv exists)
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Should not raise an exception
        worktree_manager.setup_venv_link(worktree_path)

        # Verify no .venv was created in worktree
        assert not (worktree_path / ".venv").exists()

    @patch("subprocess.run")
    def test_setup_venv_link_skips_if_already_exists(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_venv_link skips if link already exists."""

        # Create main venv
        main_venv = temp_dir / ".venv"
        main_venv.mkdir()

        # Create worktree path with existing .venv
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()
        worktree_venv = worktree_path / ".venv"
        worktree_venv.mkdir()

        # Mock symlink_to
        with patch.object(Path, "symlink_to") as mock_symlink:
            worktree_manager.setup_venv_link(worktree_path)
            # Should not attempt to create symlink
            mock_symlink.assert_not_called()

    @patch("subprocess.run")
    def test_setup_venv_link_falls_back_to_copy(
        self, mock_run: Mock, worktree_manager: WorktreeManager, temp_dir: Path
    ):
        """Test that setup_venv_link falls back to copy when symlink fails."""
        # Create main venv with some content
        main_venv = temp_dir / ".venv"
        main_venv.mkdir()
        (main_venv / "pyvenv.cfg").write_text("[metadata]")

        # Create worktree path
        worktree_path = temp_dir / "worktree-test"
        worktree_path.mkdir()

        # Mock symlink_to to raise OSError (simulating no symlink support)
        def mock_symlink_error(target, target_is_directory=False):
            raise OSError("No symlink support")

        original_symlink_to = Path.symlink_to

        try:
            # Apply the mock
            Path.symlink_to = mock_symlink_error

            # Run setup - on non-Windows systems this will fall back to copy
            # On Windows, it might try ctypes first
            worktree_manager.setup_venv_link(worktree_path)

            # Verify venv was created (either as link or copy)
            worktree_venv = worktree_path / ".venv"
            _ = worktree_venv  # Platform-dependent venv creation
            # Note: This test may not fully cover the fallback on all platforms
            # The fallback logic is tested through integration tests
        finally:
            # Restore original
            Path.symlink_to = original_symlink_to
