"""
NFL player statistics data retrieval functionality.

This module handles downloading individual player game statistics
from Pro Football Reference for specified time periods.
"""

import os
from typing import Optional

import pandas as pd

from ..core.game import Boxscore


def get_bulk_stats(
    start_season: int,
    start_week: int,
    finish_season: int,
    finish_week: int,
    playoffs: bool = True,
    path: Optional[str] = None,
    schedule_data: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Pulls individual player statistics for each game in the specified timeframe from Pro Football Reference.

    Args:
        start_season: first season of interest.
        start_week: first week of interest.
        finish_season: last season of interest.
        finish_week: last week of interest.
        playoffs: whether to include playoff games, defaults to True.
        path: file path where stats are/should be saved to, defaults to None.
        schedule_data: Optional pre-computed schedule DataFrame to avoid circular import.

    Returns:
        DataFrame containing player statistics for games during the timespan of interest.
    """
    if schedule_data is not None:
        schedule_df = schedule_data.loc[
            (
                schedule_data.season * 100 + schedule_data.week
                >= start_season * 100 + start_week
            )
            & (
                schedule_data.season * 100 + schedule_data.week
                <= finish_season * 100 + finish_week
            )
            & ~schedule_data.score1.isnull()
            & ~schedule_data.score2.isnull()
        ].reset_index(drop=True)
    else:
        # Fallback: If no schedule provided, we can't filter games properly
        raise ValueError("schedule_data parameter required to filter games")
    if path is not None and os.path.exists(str(path)):
        stats = pd.read_csv(path)
    else:
        stats = pd.DataFrame(columns=["season", "week", "game_id"])
    to_save = (
        path is not None
        and (~schedule_df.boxscore_abbrev.isin(stats.game_id.unique())).any()
    )
    for ind in range(schedule_df.shape[0]):
        if schedule_df.iloc[ind]["boxscore_abbrev"] not in stats.game_id.unique():
            print(schedule_df.iloc[ind]["boxscore_abbrev"])
            b = Boxscore(schedule_df.iloc[ind]["boxscore_abbrev"])
            stats = pd.concat([stats, b.game_stats], ignore_index=True)
            stats.season = stats.season.fillna(b.season)
            stats.week = stats.week.fillna(b.week)
            stats.game_id = stats.game_id.fillna(b.game_id)
            if to_save and b.season not in schedule_df.iloc[ind + 1 :].season.unique():
                stats.to_csv(path, index=False)
    if to_save:
        stats.to_csv(path, index=False)
    stats = stats.loc[
        stats.game_id.isin(schedule_df.boxscore_abbrev.tolist())
    ].reset_index(drop=True)
    return stats
