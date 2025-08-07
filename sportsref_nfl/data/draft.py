"""
NFL draft data retrieval functionality.

This module handles downloading draft results and calculating
initial QB ELO values based on draft position.
"""

import os
from typing import Optional

import pandas as pd

from ..core.scraper import get_page, parse_table


def get_draft(season: int) -> pd.DataFrame:
    """
    Pulls NFL draft results for the specified season from Pro Football Reference.

    Args:
        season: season of interest.

    Returns:
        DataFrame containing draft results for the season of interest.
    """
    raw_text = get_page(f"years/{season}/draft.htm")
    draft_order = parse_table(raw_text, "drafts")
    return draft_order


def get_bulk_draft_pos(
    start_season: int,
    finish_season: int,
    path: Optional[str] = None,
    best_qb_val: float = 34.313,
    qb_val_per_pick: float = -0.137,
) -> pd.DataFrame:
    """
    Pulls draft results for each season in the specified timeframe from Pro Football Reference
    and infers initial QB elo values from draft positions.

    Args:
        start_season: first season of interest.
        finish_season: last season of interest.
        path: where to save the draft results in csv form, defaults to None.
        best_qb_val: QB elo value assigned to a first overall pick, defaults to 34.313.
        qb_val_per_pick: elo point decline per pick, defaults to -0.137.

    Returns:
        DataFrame containing all draft results over the timeframe of interest.
    """
    start_season = int(start_season)
    finish_season = int(finish_season)
    if path and os.path.exists(str(path)):
        draft_pos = pd.read_csv(path)
    else:
        draft_pos = pd.DataFrame(columns=["year"])
    new_drafts = any(
        year not in draft_pos.year.unique()
        for year in range(start_season, finish_season + 1)
    )
    for year in range(start_season, finish_season + 1):
        if year not in draft_pos.year.unique():
            draft_pos = pd.concat([draft_pos, get_draft(year)], ignore_index=True)
            draft_pos.year = draft_pos.year.fillna(year)
    if path and new_drafts:
        draft_pos.to_csv(path, index=False)
    draft_pos = draft_pos.loc[
        draft_pos.year.isin(list(range(start_season, finish_season + 1)))
    ].reset_index(drop=True)
    qbs = draft_pos.pos == "QB"
    draft_pos.loc[qbs, "qb_value_init"] = (
        draft_pos.loc[qbs, "draft_pick"] * qb_val_per_pick + best_qb_val
    )
    return draft_pos
