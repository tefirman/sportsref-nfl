"""
sportsref_nfl - NFL data scraping library for Pro Football Reference

A Python library for scraping NFL statistics, schedules, and other data
from Pro Football Reference (pro-football-reference.com).
"""

__version__ = "1.0.0"
__author__ = "Taylor Firman"
__email__ = "tefirman@gmail.com"

from .core.game import Boxscore, Game
from .core.schedule import Schedule
from .core.scraper import get_page, parse_table
from .data.depth_charts import get_all_depth_charts, get_depth_chart
from .data.draft import get_bulk_draft_pos, get_draft
from .data.qb_elos import get_qb_elos
from .data.rosters import get_bulk_rosters, get_roster
from .data.stadiums import (
    download_zip_codes,
    get_address,
    get_coordinates,
    get_game_stadium,
    get_intl_games,
    get_stadiums,
    get_team_stadium,
)
from .data.stats import get_bulk_stats
from .utils.names import get_names

__all__ = [
    "Schedule",
    "Boxscore",
    "Game",
    "get_page",
    "parse_table",
    "get_bulk_stats",
    "get_draft",
    "get_bulk_draft_pos",
    "get_roster",
    "get_bulk_rosters",
    "get_depth_chart",
    "get_all_depth_charts",
    "get_stadiums",
    "get_team_stadium",
    "get_intl_games",
    "get_game_stadium",
    "get_address",
    "download_zip_codes",
    "get_coordinates",
    "get_qb_elos",
    "get_names",
]
