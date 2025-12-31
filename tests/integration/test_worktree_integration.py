"""
Integration tests for WorktreeManager.

These tests require actual git repositories and worktrees.
They are skipped on Windows due to git compatibility issues in temporary directories.
"""

from pathlib import Path

import pytest

from src.worktree_manager import WorktreeManager


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    """
    Create a temporary git repository for testing.

    Args:
        tmp_path: Temporary directory path

    Yields:
        Path to temporary git repository
    """
    import subprocess

    original_dir = Path.cwd()

    try:
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        (tmp_path / "README.md").write_text("# Test Repository")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create data directory
        (tmp_path / "data").mkdir(exist_ok=True)

        yield tmp_path

    finally:
        # Cleanup
        subprocess.run(["git", "clean", "-fd"], cwd=tmp_path, capture_output=True)
        Path.chdir(original_dir)


@pytest.fixture
def worktree_manager(temp_git_repo: Path) -> WorktreeManager:
    """
    Create WorktreeManager instance for testing.

    Args:
        temp_git_repo: Temporary git repository path

    Yields:
        WorktreeManager instance
    """
    import subprocess

    # Use a smaller port range for testing
    manager = WorktreeManager(
        repo_root=temp_git_repo,
        port_range_start=9001,
        port_range_end=9010,
    )
    yield manager

    # Cleanup
    for wt in manager.list_worktrees():
        if wt.path != temp_git_repo:
            try:
                subprocess.run(
                    ["git", "worktree", "remove", str(wt.path)],
                    cwd=temp_git_repo,
                    capture_output=True,
                )
            except Exception:
                pass
    manager.prune()


@pytest.mark.skip(reason="Integration tests skipped on Windows - git worktree issues in temp dirs")
@pytest.mark.integration
class TestWorktreeIntegration:
    """Integration tests for worktree functionality requiring real git."""

    def test_full_worktree_lifecycle(self, worktree_manager: WorktreeManager):
        """Test complete worktree lifecycle: create -> use -> cleanup."""

        # Create worktree
        info = worktree_manager.create_worktree("feature/full-lifecycle")

        # Verify creation
        assert info.path.exists()
        assert (info.path / ".git").exists()

        # Verify venv link (may not exist if main venv doesn't exist)
        _ = info.path / ".venv"

        # Cleanup
        worktree_manager.cleanup_worktree("feature/full-lifecycle")

        # Verify cleanup
        assert not info.path.exists()

    def test_multiple_worktrees_parallel(self, worktree_manager: WorktreeManager):
        """Test creating multiple worktrees in parallel."""

        features = [f"feature/parallel{i}" for i in range(3)]

        infos = []
        for feature in features:
            info = worktree_manager.create_worktree(feature)
            infos.append(info)

        # Verify all created
        assert len(infos) == 3
        for i, info in enumerate(infos):
            assert info.branch == features[i]
            assert info.path.exists()
            assert info.port == 9001 + i

        # Cleanup all
        for feature in features:
            worktree_manager.cleanup_worktree(feature)

        # Verify all cleaned up
        worktrees = worktree_manager.list_worktrees()
        assert len(worktrees) == 1  # Only main remains

    def test_setup_environment_creates_env_file(
        self, worktree_manager: WorktreeManager, temp_git_repo: Path
    ):
        """Test that setup_environment creates .env file in worktree."""
        import shutil

        # Create main .env file
        main_env = temp_git_repo / ".env"
        main_env.write_text("TEST_VAR=value\n")

        # Create worktree
        info = worktree_manager.create_worktree("feature/env-test")

        # Verify .env was created in worktree
        worktree_env = info.path / ".env"
        assert worktree_env.exists()

        # Verify it contains WORKTREE variables
        content = worktree_env.read_text()
        assert "WORKTREE_MODE=True" in content
        assert "WORKTREE_BRANCH=feature/env-test" in content
        assert "WORKTREE_PORT=" in content
        assert "WORKTREE_DB_SUFFIX=feature-env-test" in content

        # Cleanup
        shutil.rmtree(info.path)

    def test_setup_environment_copies_claude_config(
        self, worktree_manager: WorktreeManager, temp_git_repo: Path
    ):
        """Test that setup_environment copies .claude config files."""
        import shutil

        # Create .claude directory with config files
        main_claude = temp_git_repo / ".claude"
        main_claude.mkdir(exist_ok=True)
        (main_claude / "settings.json").write_text('{"test": true}')
        (main_claude / "CLAUDE.md").write_text("# Test")

        # Create worktree
        info = worktree_manager.create_worktree("feature/claude-test")

        # Verify .claude was created in worktree
        worktree_claude = info.path / ".claude"
        assert worktree_claude.exists()

        # Verify config files were copied
        assert (worktree_claude / "settings.json").exists()
        assert (worktree_claude / "CLAUDE.md").exists()

        # Cleanup
        shutil.rmtree(info.path)

    def test_setup_venv_link(self, worktree_manager: WorktreeManager, temp_git_repo: Path):
        """Test venv symlink creation."""

        # Create main venv
        main_venv = temp_git_repo / ".venv"
        main_venv.mkdir()

        # Create worktree
        info = worktree_manager.create_worktree("feature/venv-test")

        # Verify venv link exists
        worktree_venv = info.path / ".venv"
        assert worktree_venv.exists()

        # Cleanup
        worktree_manager.cleanup_worktree("feature/venv-test")
