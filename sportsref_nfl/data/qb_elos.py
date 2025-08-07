"""
NFL quarterback ELO rating calculation functionality.

This module handles calculating QB ELO ratings based on
performance statistics and draft position.
"""

import datetime

import pandas as pd

from .depth_charts import get_all_depth_charts
from .draft import get_bulk_draft_pos
from .stats import get_bulk_stats


def get_qb_elos(
    start: int,
    finish: int,
    regress_pct: float = 0.25,
    qb_games: int = 10,
    team_games: int = 20,
    elo_adj: float = 3.3,
    schedule_data: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Pulls QB-related statistics and calculates QB elo ratings as they progress over time.

    Args:
        start: first season of interest.
        finish: last season of interest.
        regress_pct: percentage to regress QBs back to the mean between each season, defaults to 0.25.
        qb_games: number of games to use in the rolling average for individual QB elos, defaults to 10.
        team_games: number of games to use in the rolling average for team QB elos, defaults to 20.
        elo_adj: conversion factor between QB rating and team elos, defaults to 3.3.
        schedule_data: Optional pre-computed schedule DataFrame to avoid circular import.

    Returns:
        DataFrame containing QB statistics and elo ratings throughout the timeframe of interest.
    """
    stats = get_bulk_stats(
        start - 3,
        1,
        finish,
        50,
        True,
        "GameByGameFantasyFootballStats.csv",
        schedule_data,
    )
    if finish == datetime.datetime.now().year and datetime.datetime.now().month > 5:
        # Accounting for current season
        if schedule_data is not None:
            sched = schedule_data.copy()
        else:
            # Fallback: If no schedule provided, we can't do current season processing
            # This should be handled by the caller providing schedule_data
            raise ValueError(
                "schedule_data parameter required for current season processing"
            )
        missing = pd.concat(
            [
                sched.loc[
                    sched.score1.isnull() & sched.score2.isnull(),
                    [
                        "season",
                        "week_num",
                        "boxscore_abbrev",
                        "team1_abbrev",
                        "team2_abbrev",
                    ],
                ].rename(
                    columns={
                        "week_num": "week",
                        "boxscore_abbrev": "game_id",
                        "team1_abbrev": "team",
                        "team2_abbrev": "opponent",
                    }
                ),
                sched.loc[
                    sched.score1.isnull() & sched.score2.isnull(),
                    [
                        "season",
                        "week_num",
                        "boxscore_abbrev",
                        "team2_abbrev",
                        "team1_abbrev",
                    ],
                ].rename(
                    columns={
                        "week_num": "week",
                        "boxscore_abbrev": "game_id",
                        "team2_abbrev": "team",
                        "team1_abbrev": "opponent",
                    }
                ),
            ],
            ignore_index=True,
        )
        current = get_all_depth_charts()
        current = current.loc[(current.pos == "QB") & (current.string == 1.0)]
        missing = pd.merge(left=missing, right=current, how="inner", on="team")
        stats = pd.concat([stats, missing], ignore_index=True)
    draft_pos = get_bulk_draft_pos(start - 10, finish, "NFLDraftPositions.csv")
    prev_all = stats.loc[
        (stats.season < stats.season.min() + 2)
        & (stats.pos == "QB")
        & (stats.string == 1)
    ].reset_index(drop=True)
    by_opponent = (
        prev_all.groupby(["season", "week", "game_id", "opponent"])
        .VALUE.sum()
        .reset_index()
    )
    by_opponent = by_opponent.sort_values(
        by=["season", "week"], ascending=False
    ).reset_index(drop=True)
    by_opponent = (
        by_opponent.groupby("opponent")
        .head(team_games)
        .groupby("opponent")
        .VALUE.mean()
        .reset_index()
    )
    by_team = (
        prev_all.groupby(["season", "week", "game_id", "team"])
        .VALUE.sum()
        .reset_index()
    )
    by_team = by_team.sort_values(by=["season", "week"], ascending=False).reset_index(
        drop=True
    )
    by_team = (
        by_team.groupby("team")
        .head(team_games)
        .groupby("team")
        .VALUE.mean()
        .reset_index()
    )
    new = stats.loc[
        (stats.season >= stats.season.min() + 2)
        & (stats.pos == "QB")
        & (stats.string == 1)
    ].reset_index(drop=True)
    new["qb_value_pre"] = None
    for ind in range(new.shape[0]):
        avg_value = by_opponent.VALUE.mean()
        prev_qb = new.loc[(new.player == new.loc[ind, "player"]) & (new.index < ind)]
        if prev_qb.shape[0] == 0:
            drafted = draft_pos.loc[draft_pos.player == new.loc[ind, "player"]]
            if drafted.shape[0] > 0:
                new.loc[ind, "qb_value_pre"] = drafted.iloc[0].qb_value_init
            else:
                new.loc[ind, "qb_value_pre"] = 0.0
            new.loc[ind, "num_games"] = 0.0
        else:
            new.loc[ind, "qb_value_pre"] = prev_qb.iloc[-1]["qb_value_post"]
            if (
                new.loc[ind, "season"] > prev_qb.iloc[-1]["season"]
                and prev_qb.shape[0] >= 10
                and prev_qb.shape[0] <= 100
            ):
                new.loc[ind, "qb_value_pre"] = (1 - regress_pct) * new.loc[
                    ind, "qb_value_pre"
                ] + regress_pct * avg_value
            new.loc[ind, "num_games"] = prev_qb.shape[0]
        if pd.isnull(new.loc[ind, "VALUE"]):
            # Game hasn't been played yet
            new.loc[ind, "qb_value_post"] = new.loc[ind, "qb_value_pre"]
            new.loc[ind, "team_qbvalue_avg"] = by_team.loc[
                by_team.team == new.loc[ind, "team"], "VALUE"
            ].values[0]
        else:
            new.loc[ind, "team_qbvalue_avg"] = by_team.loc[
                by_team.team == new.loc[ind, "team"], "VALUE"
            ].values[0]
            new.loc[ind, "opp_qbvalue_avg"] = (
                by_opponent.loc[
                    by_opponent.opponent == new.loc[ind, "opponent"], "VALUE"
                ].values[0]
                - avg_value
            )
            new.loc[ind, "VALUE"] -= new.loc[ind, "opp_qbvalue_avg"]
            new.loc[ind, "qb_value_post"] = (
                new.loc[ind, "qb_value_pre"] * (1 - 1 / qb_games)
                + new.loc[ind, "VALUE"] / qb_games
            )
            by_opponent.loc[
                by_opponent.opponent == new.loc[ind, "opponent"], "VALUE"
            ] *= 1 - 1 / team_games
            by_opponent.loc[
                by_opponent.opponent == new.loc[ind, "opponent"], "VALUE"
            ] += new.loc[ind, "VALUE"] / team_games
            by_team.loc[by_team.team == new.loc[ind, "team"], "VALUE"] *= (
                1 - 1 / team_games
            )
            by_team.loc[by_team.team == new.loc[ind, "team"], "VALUE"] += (
                new.loc[ind, "VALUE"] / team_games
            )
    new["qb_adj"] = elo_adj * (new.qb_value_pre - new.team_qbvalue_avg)
    return new[
        [
            "game_id",
            "player",
            "team",
            "team_qbvalue_avg",
            "opp_qbvalue_avg",
            "qb_value_pre",
            "qb_adj",
            "qb_value_post",
            "VALUE",
        ]
    ]
