"""
Caching system for sportsref-nfl package.

This module provides file-based caching for web requests to Pro Football Reference,
with intelligent expiration based on data type and recency.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from bs4 import BeautifulSoup


class NFLCache:
    """
    File-based cache system for NFL data with smart expiration rules.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the cache system.

        Args:
            cache_dir: Custom cache directory path. Defaults to ~/.sportsref_nfl_cache
        """
        if cache_dir is None:
            self.cache_dir = Path.home() / ".sportsref_nfl_cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def _get_cache_key(self, endpoint: str) -> str:
        """Generate a cache key for the given endpoint."""
        return hashlib.md5(endpoint.encode()).hexdigest()

    def _get_cache_type(self, endpoint: str) -> str:
        """Determine cache type based on endpoint pattern."""
        current_year = datetime.now().year
        
        if "boxscores/" in endpoint:
            # Extract year from boxscore ID (e.g., 202409050kan -> 2024)
            game_id = endpoint.split("/")[-1].split(".")[0]
            if len(game_id) >= 4:
                try:
                    game_year = int(game_id[:4])
                    if game_year < current_year:
                        return "historical"
                    else:
                        return "current_season"
                except ValueError:
                    pass
            return "current_season"
        
        elif "years/" in endpoint and "games.htm" in endpoint:
            # Schedule pages
            year_match = endpoint.split("/")[-2]
            try:
                schedule_year = int(year_match)
                if schedule_year < current_year:
                    return "historical"
                else:
                    return "live_season"
            except ValueError:
                pass
            return "live_season"
        
        elif "draft" in endpoint:
            return "draft"
        elif "stadiums" in endpoint:
            return "stadiums"
        else:
            return "current_season"  # Default

    def _get_expiration_time(self, cache_type: str) -> Optional[float]:
        """Get expiration timestamp for cache type."""
        durations = {
            "historical": None,  # Never expires
            "current_season": 24*60*60,  # 24 hours
            "live_season": 4*60*60,  # 4 hours
            "draft": None,  # Never expires
            "stadiums": 30*24*60*60,  # 30 days
        }
        
        duration = durations.get(cache_type)
        if duration is None:
            return None  # Never expires
        return time.time() + duration

    def _is_expired(self, cache_key: str) -> bool:
        """Check if cached item is expired."""
        if cache_key not in self.metadata:
            return True
        
        expires_at = self.metadata[cache_key].get("expires_at")
        if expires_at is None:
            return False  # Never expires
        
        return time.time() > expires_at

    def get_cached_page(self, endpoint: str) -> Optional[BeautifulSoup]:
        """
        Retrieve cached page if available and not expired.

        Args:
            endpoint: The endpoint path (e.g., "boxscores/202409050kan.htm")

        Returns:
            BeautifulSoup object if cached and valid, None otherwise
        """
        cache_key = self._get_cache_key(endpoint)
        cache_file = self.cache_dir / f"{cache_key}.html"

        if not cache_file.exists() or self._is_expired(cache_key):
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return BeautifulSoup(content, 'html.parser')
        except (IOError, UnicodeDecodeError):
            # Remove corrupted cache file
            cache_file.unlink(missing_ok=True)
            if cache_key in self.metadata:
                del self.metadata[cache_key]
                self._save_metadata()
            return None

    def cache_page(self, endpoint: str, soup: BeautifulSoup) -> None:
        """
        Cache a page to disk.

        Args:
            endpoint: The endpoint path
            soup: BeautifulSoup object to cache
        """
        cache_key = self._get_cache_key(endpoint)
        cache_file = self.cache_dir / f"{cache_key}.html"
        cache_type = self._get_cache_type(endpoint)

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))

            self.metadata[cache_key] = {
                "endpoint": endpoint,
                "cache_type": cache_type,
                "cached_at": time.time(),
                "expires_at": self._get_expiration_time(cache_type)
            }
            self._save_metadata()
            
            print(f"📁 Cached: {endpoint} ({cache_type})")
            
        except IOError as e:
            print(f"⚠️  Failed to cache {endpoint}: {e}")

    def clear_cache(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cache files.

        Args:
            cache_type: Specific cache type to clear, or None for all

        Returns:
            Number of files cleared
        """
        cleared = 0
        
        for cache_key, metadata in list(self.metadata.items()):
            if cache_type is None or metadata.get("cache_type") == cache_type:
                cache_file = self.cache_dir / f"{cache_key}.html"
                cache_file.unlink(missing_ok=True)
                del self.metadata[cache_key]
                cleared += 1

        if cleared > 0:
            self._save_metadata()
            print(f"🗑️  Cleared {cleared} cache files")
        
        return cleared

    def cache_info(self) -> Dict[str, Any]:
        """Get cache information and statistics."""
        now = time.time()
        stats = {
            "total_files": len(self.metadata),
            "cache_dir": str(self.cache_dir),
            "size_mb": 0,
            "by_type": {},
            "expired": 0
        }

        # Calculate cache directory size
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            stats["size_mb"] = round(total_size / (1024 * 1024), 2)
        except OSError:
            pass

        # Count by type and expired files
        for cache_key, metadata in self.metadata.items():
            cache_type = metadata.get("cache_type", "unknown")
            stats["by_type"][cache_type] = stats["by_type"].get(cache_type, 0) + 1
            
            expires_at = metadata.get("expires_at")
            if expires_at is not None and now > expires_at:
                stats["expired"] += 1

        return stats


# Global cache instance
_cache_instance: Optional[NFLCache] = None


def get_cache() -> NFLCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = NFLCache()
    return _cache_instance


def clear_cache(cache_type: Optional[str] = None) -> int:
    """Clear cache files."""
    return get_cache().clear_cache(cache_type)


def cache_info() -> Dict[str, Any]:
    """Get cache information."""
    return get_cache().cache_info()