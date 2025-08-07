"""
Basic import and smoke tests for sportsref_nfl package.
"""

import pytest


def test_main_imports():
    """Test that main package imports work."""
    import sportsref_nfl as sr

    # Check version exists
    assert hasattr(sr, "__version__")
    assert isinstance(sr.__version__, str)

    # Check main classes can be imported
    assert hasattr(sr, "Schedule")
    assert hasattr(sr, "Boxscore")
    assert hasattr(sr, "Game")


def test_core_module_imports():
    """Test that core modules can be imported."""
    from sportsref_nfl.core import game, schedule, scraper

    # Check classes exist
    assert hasattr(schedule, "Schedule")
    assert hasattr(game, "Boxscore")
    assert hasattr(game, "Game")
    assert hasattr(scraper, "get_page")
    assert hasattr(scraper, "parse_table")


def test_data_module_imports():
    """Test that data modules can be imported."""
    from sportsref_nfl.data import (
        depth_charts,
        draft,
        qb_elos,
        rosters,
        stadiums,
        stats,
    )

    # Check functions exist
    assert hasattr(stats, "get_bulk_stats")
    assert hasattr(draft, "get_draft")
    assert hasattr(rosters, "get_roster")
    assert hasattr(depth_charts, "get_depth_chart")
    assert hasattr(stadiums, "get_stadiums")
    assert hasattr(qb_elos, "get_qb_elos")


def test_utils_module_imports():
    """Test that utils modules can be imported."""
    from sportsref_nfl.utils import names

    assert hasattr(names, "get_names")


def test_schedule_instantiation():
    """Test that Schedule class can be instantiated (without network calls)."""
    import sportsref_nfl as sr

    # This should not fail to instantiate the class
    schedule_cls = sr.Schedule
    assert callable(schedule_cls)


def test_boxscore_instantiation():
    """Test that Boxscore class can be instantiated (without network calls)."""
    import sportsref_nfl as sr

    # This should not fail to instantiate the class
    boxscore_cls = sr.Boxscore
    assert callable(boxscore_cls)


def test_all_exports_exist():
    """Test that all items in __all__ actually exist."""
    import sportsref_nfl as sr

    for item in sr.__all__:
        assert hasattr(sr, item), f"Exported item '{item}' does not exist in module"


if __name__ == "__main__":
    pytest.main([__file__])
