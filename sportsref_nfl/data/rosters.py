"""
NFL team roster data retrieval functionality.

This module handles downloading team rosters from Pro Football Reference
for specified seasons and teams.
"""

import datetime
import os
from typing import Optional

import pandas as pd

from ..core.schedule import Schedule
from ..core.scraper import get_page, parse_table


def get_roster(team: str, season: int) -> pd.DataFrame:
    """
    Pulls the full team roster for the team and season of interest from Pro Football Reference.

    Args:
        team: abbreviation for the team of interest.
        season: season of interest.

    Returns:
        DataFrame containing identifying information for each player on the roster of interest.
    """
    raw_text = get_page(f"teams/{team.lower()}/{season}_roster.htm")
    roster = parse_table(raw_text, "roster")
    return roster


def get_bulk_rosters(
    start_season: int, finish_season: int, path: Optional[str] = None
) -> pd.DataFrame:
    """
    Pulls all NFL rosters during the specified timeframe from Pro Football Reference.

    Args:
        start_season: first season of interest.
        finish_season: last season of interest.
        path: where to save the rosters in csv form, defaults to None.

    Returns:
        DataFrame containing all rosters for the specified timeframe.
    """
    s = Schedule(start_season, finish_season)
    # Need to delete and repull after every new week to account for trades, etc.
    if path and os.path.exists(str(path)):
        teams = pd.read_csv(path)
    else:
        teams = pd.DataFrame(columns=["season"])
    new_games = any(
        season not in teams.season.unique()
        for season in range(start_season, finish_season + 1)
    )
    for season in range(start_season, finish_season + 1):
        if season not in teams.season.unique():
            for team in s.schedule.loc[
                s.schedule.season == season, "team1_abbrev"
            ].unique():
                roster = get_roster(team, season)
                roster["team"] = team
                roster["season"] = season
                teams = pd.concat([teams, roster], ignore_index=True)
    if path and (new_games or finish_season == datetime.datetime.now().year):
        teams.to_csv(path, index=False)
    teams.player = teams.player.str.split(" (", regex=False).str[0]
    return teams
