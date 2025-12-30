"""
LoL Stonks RSS Feed Generator

A Python application that generates RSS feeds for League of Legends news.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lolstonksrss")
except PackageNotFoundError:
    # Development mode fallback
    __version__ = "0.0.0.dev0"
