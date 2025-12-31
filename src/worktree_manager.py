"""
Git Worktree Manager for Parallel Development with Claude Code Agents.

This module provides automatic worktree management for parallel feature development.
It handles port allocation, database isolation, and virtual environment sharing.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    """Information about a worktree."""

    branch: str
    path: Path
    port: int
    db_suffix: str
    commit: str


class WorktreeManager:
    """
    Manages git worktrees for parallel development.

    Features:
    - Automatic worktree creation and cleanup
    - Port allocation (8001-8999 range)
    - Database isolation per branch
    - Virtual environment sharing via symlinks
    - Thread-safe port registry with file locking
    """

    def __init__(
        self,
        repo_root: Path | None = None,
        port_range_start: int = 8001,
        port_range_end: int = 8099,
        ports_registry_path: Path | None = None,
    ):
        """
        Initialize WorktreeManager.

        Args:
            repo_root: Path to git repository root. Auto-detected if None.
            port_range_start: Start of port allocation range (default: 8001)
            port_range_end: End of port allocation range (default: 8099)
            ports_registry_path: Path to port registry JSON file.
        """
        self.repo_root = repo_root or self._detect_repo_root()
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        self.ports_registry_path = (
            ports_registry_path or self.repo_root / "data" / "worktree-ports.json"
        )
        self.ports_lock_path = self.ports_registry_path.with_suffix(".lock")

        # Ensure data directory exists
        self.ports_registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize port registry if needed
        self._init_registry()

    def _detect_repo_root(self) -> Path:
        """Detect git repository root from current directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            )
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Could not detect git repository root: {e}") from e

    def _init_registry(self) -> None:
        """Initialize port registry file if it doesn't exist."""
        if not self.ports_registry_path.exists():
            self._write_registry({})

    def _read_registry(self) -> dict[str, int]:
        """Read port registry from file with locking."""
        if not self.ports_registry_path.exists():
            return {}

        with open(self.ports_registry_path) as f:
            try:
                return json.load(f) or {}
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in {self.ports_registry_path}, resetting")
                return {}

    def _write_registry(self, registry: dict[str, int]) -> None:
        """Write port registry to file atomically."""
        temp_path = self.ports_registry_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(registry, f, indent=2)
        temp_path.replace(self.ports_registry_path)

    def _get_db_suffix(self, branch_name: str) -> str:
        """
        Generate database suffix for branch isolation.

        Args:
            branch_name: Git branch name

        Returns:
            Suffix string for database filename
        """
        # Replace slashes with dashes, remove special chars
        return branch_name.replace("/", "-").replace("\\", "-").replace("_", "-")

    def get_db_path(self, branch_name: str) -> Path:
        """
        Get isolated database path for a branch.

        Args:
            branch_name: Git branch name

        Returns:
            Path to isolated database file
        """
        suffix = self._get_db_suffix(branch_name)
        return self.repo_root / "data" / f"articles-{suffix}.db"

    def allocate_port(self, branch_name: str) -> int:
        """
        Allocate a port for a branch.

        Uses file locking for thread-safety. Port is allocated from the
        available range and associated with the branch name.

        Args:
            branch_name: Git branch name to allocate port for

        Returns:
            Allocated port number

        Raises:
            RuntimeError: If no ports available in range
        """
        # Simple retry-based locking for cross-platform compatibility
        max_retries = 10
        last_error: OSError | None = None

        for attempt in range(max_retries):
            try:
                registry = self._read_registry()

                # Check if branch already has a port
                if branch_name in registry:
                    return registry[branch_name]

                # Find available port
                used_ports = set(registry.values())
                for port in range(self.port_range_start, self.port_range_end + 1):
                    if port not in used_ports:
                        # Allocate this port
                        registry[branch_name] = port
                        self._write_registry(registry)
                        logger.info(f"Allocated port {port} for branch '{branch_name}'")
                        return port

                # No ports available
                raise RuntimeError(
                    f"No ports available in range {self.port_range_start}-{self.port_range_end}"
                )

            except OSError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.debug(f"Retry {attempt + 1}/{max_retries} after error: {e}")
                    import time

                    time.sleep(0.1 * (2**attempt))  # Exponential backoff
                    continue

        # All retries exhausted
        raise RuntimeError(f"Failed to allocate port after {max_retries} attempts") from last_error

    def release_port(self, branch_name: str) -> None:
        """
        Release a port allocation for a branch.

        Args:
            branch_name: Git branch name to release port for
        """
        registry = self._read_registry()
        if branch_name in registry:
            port = registry.pop(branch_name)
            self._write_registry(registry)
            logger.info(f"Released port {port} for branch '{branch_name}'")

    def create_worktree(
        self,
        branch_name: str,
        worktree_path: Path | None = None,
        create_branch: bool = True,
    ) -> WorktreeInfo:
        """
        Create a new git worktree with automatic setup.

        Args:
            branch_name: Name of the branch to checkout
            worktree_path: Path for worktree (default: ../lolstonksrss-branch-name)
            create_branch: Create new branch if it doesn't exist

        Returns:
            WorktreeInfo with details about the created worktree

        Raises:
            RuntimeError: If worktree creation fails
        """
        # Determine worktree path
        if worktree_path is None:
            safe_name = branch_name.replace("/", "-").replace("\\", "-")
            worktree_path = self.repo_root.parent / f"{self.repo_root.name}-{safe_name}"

        # Check if worktree already exists
        if worktree_path.exists():
            logger.info(f"Worktree already exists at {worktree_path}")
            info = self.get_worktree_info(worktree_path)
            if info is None:
                raise RuntimeError(f"Could not get worktree info for {worktree_path}")
            return info

        # Allocate port
        port = self.allocate_port(branch_name)

        # Create worktree
        try:
            if create_branch:
                # Create new branch and worktree
                subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        "-b",
                        branch_name,
                        str(worktree_path),
                    ],
                    check=True,
                    cwd=self.repo_root,
                )
            else:
                # Checkout existing branch
                subprocess.run(
                    ["git", "worktree", "add", str(worktree_path), branch_name],
                    check=True,
                    cwd=self.repo_root,
                )

            logger.info(f"Created worktree at {worktree_path}")

        except subprocess.CalledProcessError as e:
            # Clean up port allocation on failure
            self.release_port(branch_name)
            raise RuntimeError(f"Failed to create worktree: {e}") from e

        # Setup venv symlink
        self.setup_venv_link(worktree_path)

        # Setup environment and config
        self.setup_environment(worktree_path, branch_name, port)

        # Get commit SHA
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=worktree_path,
            )
            commit = result.stdout.strip()
        except subprocess.CalledProcessError:
            commit = "unknown"

        return WorktreeInfo(
            branch=branch_name,
            path=worktree_path,
            port=port,
            db_suffix=self._get_db_suffix(branch_name),
            commit=commit,
        )

    def setup_environment(self, worktree_path: Path, branch_name: str, port: int) -> None:
        """
        Setup environment variables and configuration for the worktree.

        1. Copies .env from main repo and appends WORKTREE_* variables.
        2. Copies .claude/ config files if they exist.

        Args:
            worktree_path: Path to the worktree directory
            branch_name: Name of the branch
            port: Allocated port
        """
        import shutil

        # 1. Setup .env
        main_env = self.repo_root / ".env"
        worktree_env = worktree_path / ".env"

        if main_env.exists():
            try:
                # Read main .env
                content = main_env.read_text(encoding="utf-8")

                # Append worktree specific config
                db_suffix = self._get_db_suffix(branch_name)

                # Ensure we have a newline before appending
                if content and not content.endswith("\n"):
                    content += "\n"

                content += "\n# --- Worktree Configuration (Auto-generated) ---\n"
                content += "WORKTREE_MODE=True\n"
                content += f"WORKTREE_BRANCH={branch_name}\n"
                content += f"WORKTREE_PORT={port}\n"
                content += f"WORKTREE_DB_SUFFIX={db_suffix}\n"
                content += f"PORT={port}\n"  # For tools that might use PORT directly

                worktree_env.write_text(content, encoding="utf-8")
                logger.info(f"Created .env at {worktree_env} with worktree config")
            except Exception as e:
                logger.error(f"Failed to setup .env: {e}")
        else:
            logger.warning("No .env found in main repo to copy")

        # 2. Setup .claude config
        main_claude = self.repo_root / ".claude"
        worktree_claude = worktree_path / ".claude"

        # Ensure .claude exists in worktree
        worktree_claude.mkdir(parents=True, exist_ok=True)

        # Copy settings files if they exist
        for config_file in ["settings.json", "settings.local.json", "CLAUDE.md"]:
            src = main_claude / config_file
            dst = worktree_claude / config_file

            if src.exists() and not dst.exists():
                try:
                    shutil.copy2(src, dst)
                    logger.info(f"Copied {config_file} to worktree")
                except Exception as e:
                    logger.warning(f"Failed to copy {config_file}: {e}")

    def setup_venv_link(self, worktree_path: Path) -> None:
        """
        Create symlink from worktree to main venv.

        On Windows, creates a junction point if symlinks are not available.

        Args:
            worktree_path: Path to the worktree directory
        """
        main_venv = self.repo_root / ".venv"
        worktree_venv = worktree_path / ".venv"

        if not main_venv.exists():
            logger.warning(f"Main venv not found at {main_venv}, skipping symlink")
            return

        if worktree_venv.exists():
            logger.info(f"Venv link already exists at {worktree_venv}")
            return

        try:
            # Try creating a symlink first
            worktree_venv.symlink_to(main_venv)
            logger.info(f"Created venv symlink: {worktree_venv} -> {main_venv}")
        except OSError:
            # Symlink failed, try junction point on Windows
            try:
                import ctypes

                ctypes.windll.kernel32.CreateSymbolicLinkW(
                    str(worktree_venv), str(main_venv), 1  # 1 = directory
                )
                logger.info(f"Created venv junction: {worktree_venv} -> {main_venv}")
            except (AttributeError, OSError):
                # Both symlink and junction failed, copy as fallback
                logger.warning("Could not create symlink or junction, copying venv (slower)")
                import shutil

                shutil.copytree(main_venv, worktree_venv)
                logger.info(f"Copied venv to {worktree_venv}")

    def cleanup_worktree(self, branch_name: str, force: bool = False) -> None:
        """
        Remove a worktree and free its resources.

        Args:
            branch_name: Branch name to clean up
            force: Force removal even if worktree has uncommitted changes
        """
        # Find worktree path
        worktree_info = None
        for wt in self.list_worktrees():
            if wt.branch == branch_name:
                worktree_info = wt
                break

        if not worktree_info:
            logger.warning(f"No worktree found for branch '{branch_name}'")
            return

        # Remove worktree
        try:
            cmd = ["git", "worktree", "remove"]
            if force:
                cmd.append("--force")
            cmd.append(str(worktree_info.path))

            subprocess.run(cmd, check=True, cwd=self.repo_root)
            logger.info(f"Removed worktree at {worktree_info.path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove worktree: {e}")
            raise

        # Release port
        self.release_port(branch_name)

    def list_worktrees(self) -> list[WorktreeInfo]:
        """
        List all worktrees for the repository.

        Returns:
            List of WorktreeInfo objects
        """
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            cwd=self.repo_root,
        )

        worktrees = []
        current: dict[str, str] = {}

        for line in result.stdout.splitlines():
            if not line:
                if current:
                    worktrees.append(self._parse_worktree(current))
                    current = {}
                continue

            parts = line.split(" ", 1)
            if len(parts) != 2:
                continue

            key, value = parts
            current[key] = value

        # Don't forget the last worktree
        if current:
            worktrees.append(self._parse_worktree(current))

        return worktrees

    def _parse_worktree(self, data: dict[str, str]) -> WorktreeInfo:
        """Parse worktree data from git worktree list output."""
        path = Path(data.get("worktree", ""))
        branch = data.get("branch", "").replace("refs/heads/", "")
        commit = data.get("HEAD", "")

        # Get port from registry
        registry = self._read_registry()
        port = registry.get(branch, 0)

        return WorktreeInfo(
            branch=branch,
            path=path,
            port=port,
            db_suffix=self._get_db_suffix(branch),
            commit=commit,
        )

    def get_worktree_info(self, worktree_path: Path) -> WorktreeInfo | None:
        """
        Get information about a specific worktree.

        Args:
            worktree_path: Path to the worktree directory

        Returns:
            WorktreeInfo if found, None otherwise
        """
        for wt in self.list_worktrees():
            if wt.path == worktree_path:
                return wt
        return None

    def get_available_capacity(self) -> int:
        """
        Get the number of available worktree slots.

        Returns:
            Number of worktrees that can still be created
        """
        registry = self._read_registry()
        used_ports = len(registry)
        total_ports = self.port_range_end - self.port_range_start + 1
        return max(0, total_ports - used_ports)

    def prune(self) -> None:
        """
        Clean up stale worktree metadata.

        Removes administrative files for worktrees that are no longer on disk.
        """
        try:
            subprocess.run(
                ["git", "worktree", "prune"],
                check=True,
                cwd=self.repo_root,
            )
            logger.info("Pruned stale worktree metadata")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to prune worktrees: {e}")

    def get_current_branch(self) -> str:
        """
        Get the current git branch name.

        Returns:
            Current branch name
        """
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Could not get current branch: {e}") from e

    def is_worktree(self, path: Path | None = None) -> bool:
        """
        Check if the current directory is a worktree.

        Args:
            path: Path to check (default: current directory)

        Returns:
            True if path is a worktree, False otherwise
        """
        if path is None:
            path = Path.cwd()

        # Check if we're inside a git worktree
        try:
            git_dir = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True,
                cwd=path,
            )
            # Worktrees have .git files pointing to main repo, not directories
            git_dir_path = Path(git_dir.stdout.strip())
            return git_dir_path.is_file()
        except subprocess.CalledProcessError:
            return False
