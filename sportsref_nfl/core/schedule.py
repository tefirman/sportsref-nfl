"""
NFL Schedule management and ELO calculation functionality.

This module contains the Schedule class for downloading NFL schedules,
calculating ELO ratings, and managing team travel/rest data.
"""

import datetime

import numpy as np
import pandas as pd
from geopy.distance import geodesic

from ..data.qb_elos import get_qb_elos
from ..data.stadiums import (
    download_zip_codes,
    get_address,
    get_coordinates,
    get_game_stadium,
    get_intl_games,
    get_team_stadium,
)
from .scraper import get_page, parse_table


class Schedule:
    """
    Schedule class that gathers all matchups and outcomes for the seasons in question and
    assess the evolution of each team's elo ranking according to 538's methodology.

    Attributes:
        schedule: dataframe containing matchup details for the seasons of interest.
    """

    schedule: pd.DataFrame

    def __init__(
        self,
        start: int,
        finish: int,
        playoffs: bool = True,
        elo: bool = False,
        qbelo: bool = False,
    ):
        """
        Initializes a Schedule object using the parameters provided and class functions defined below.

        Args:
            start: first NFL season of interest
            finish: last NFL season of interest
            playoffs: whether to include playoff games, defaults to True.
            elo: whether to include elo rating considerations, defaults to False.
            qbelo: whether to include QB elo rating considerations, defaults to False.
        """
        self.get_schedules(start, finish)
        self.add_weeks()
        self.convert_to_home_away()
        self.mark_intl_games()
        self.add_rest()
        if elo:
            self.add_team_coords()
            self.add_game_coords()
            self.add_travel()
            self.add_elo_columns(qbelo)
            while self.schedule.elo1_pre.isnull().any():
                self.next_init_elo()
                self.next_elo_prob()
                self.next_elo_delta()
        if not playoffs:
            self.schedule = self.schedule.loc[
                self.schedule.week_num.str.isnumeric()
            ].reset_index(drop=True)

    def get_schedules(self, start: int, finish: int) -> None:
        """
        Pulls the full NFL schedules for the seasons provided.

        Args:
            start: first season of interest
            finish: last season of interest
        """
        self.schedule = pd.DataFrame(columns=["season"])
        for season in range(int(start), int(finish) + 1):
            raw_text = get_page(f"years/{season}/games.htm")
            season_sched = parse_table(raw_text, "games")
            season_sched.week_num = (
                season_sched.week_num.astype(str).str.split(".").str[0]
            )
            season_sched = season_sched.loc[
                ~season_sched.week_num.astype(str).str.startswith("Pre")
            ].reset_index(drop=True)
            season_sched["season"] = season
            if "game_date" not in season_sched.columns:  # Current season
                season_sched["game_date"] = (
                    season_sched.boxscore_word
                    + ", "
                    + (
                        datetime.datetime.now().year
                        + season_sched.boxscore_word.str.startswith("January").astype(
                            int
                        )
                    ).astype(str)
                )
                season_sched = season_sched.rename(
                    columns={
                        "visitor_team": "winner",
                        "visitor_team_abbrev": "winner_abbrev",
                        "home_team": "loser",
                        "home_team_abbrev": "loser_abbrev",
                    }
                )
                season_sched[["yards_win", "to_win", "yards_lose", "to_lose"]] = None
            self.schedule = pd.concat([self.schedule, season_sched], ignore_index=True)

    def add_weeks(self) -> None:
        """
        Infers season week based on game dates for each season.
        """
        self.schedule.game_date = pd.to_datetime(
            self.schedule.game_date, format="mixed"
        )
        min_date = self.schedule.groupby("season").game_date.min().reset_index()
        self.schedule = pd.merge(
            left=self.schedule,
            right=min_date,
            how="inner",
            on="season",
            suffixes=("", "_min"),
        )
        self.schedule["days_into_season"] = (
            self.schedule.game_date - self.schedule.game_date_min
        ).dt.days
        self.schedule["week"] = self.schedule.days_into_season // 7 + 1
        # NFL scheduled 2024 Christmas games on a Wednesday... Why...
        mismatch = (
            self.schedule.week_num != self.schedule.week.astype(str)
        ) & self.schedule.week_num.str.isnumeric()
        self.schedule.loc[mismatch, "week"] = self.schedule.loc[
            mismatch, "week_num"
        ].astype(int)

    def convert_to_home_away(self) -> None:
        """
        Converts winner/loser syntax of Pro Football Reference schedules into home/away.
        """
        list1 = ["team1", "team1_abbrev", "score1", "yards1", "timeouts1"]
        list2 = ["team2", "team2_abbrev", "score2", "yards2", "timeouts2"]
        winner_list = ["winner", "winner_abbrev", "pts_win", "yards_win", "to_win"]
        loser_list = ["loser", "loser_abbrev", "pts_lose", "yards_lose", "to_lose"]
        home_loser = self.schedule.game_location == "@"
        self.schedule.loc[home_loser, list1] = self.schedule.loc[
            home_loser, loser_list
        ].values
        self.schedule.loc[home_loser, list2] = self.schedule.loc[
            home_loser, winner_list
        ].values
        away_loser = (
            self.schedule.game_location.isnull()
            | self.schedule.game_location.isin(["N"])
        )
        self.schedule.loc[away_loser, list1] = self.schedule.loc[
            away_loser, winner_list
        ].values
        self.schedule.loc[away_loser, list2] = self.schedule.loc[
            away_loser, loser_list
        ].values

    def mark_intl_games(self) -> None:
        """
        Identifies international games in the provided schedule (used when accounting for team travel).
        """
        intl = get_intl_games()
        intl = intl.loc[
            (intl.game_date.dt.year >= self.schedule.season.min())
            & (intl.game_date.dt.year <= self.schedule.season.max())
        ]
        intl["international"] = True
        self.schedule = pd.merge(
            left=self.schedule,
            right=intl,
            how="left",
            on=["game_date", "team1", "team2"],
        )
        self.schedule.international = self.schedule.international.notna()
        self.schedule.loc[self.schedule.international, "game_location"] = "N"
        if self.schedule.international.sum() < intl.shape[0]:
            print("Missing some international games!!!")
            bad = pd.merge(
                left=intl,
                right=self.schedule[["boxscore_abbrev", "game_date", "team1", "team2"]],
                how="left",
                on=["game_date", "team1", "team2"],
            )
            bad = bad.loc[bad.boxscore_abbrev.isnull()]
            print(bad)

    def add_team_coords(self) -> None:
        """
        Adds the home coordinates for each team in each matchup of the schedule.
        """
        teams = pd.concat(
            [
                self.schedule[["season", "team1_abbrev"]].rename(
                    columns={"team1_abbrev": "abbrev"}
                ),
                self.schedule[["season", "team2_abbrev"]].rename(
                    columns={"team2_abbrev": "abbrev"}
                ),
            ]
        ).drop_duplicates(ignore_index=True)
        zips = download_zip_codes()
        for ind in range(teams.shape[0]):
            team = teams.iloc[ind]
            print(team["abbrev"])
            stadium_id = get_team_stadium(team["abbrev"], team["season"])
            address = get_address(stadium_id)
            coords = get_coordinates(address, zips)
            self.schedule.loc[
                self.schedule.team1_abbrev == team["abbrev"], "coords1"
            ] = coords
            self.schedule.loc[
                self.schedule.team2_abbrev == team["abbrev"], "coords2"
            ] = coords

    def add_game_coords(self) -> None:
        """
        Adds game coordinates for each of the matchups in the schedule.
        If the game is international, the location is pulled directly from Pro Football Reference.
        """
        neutral = self.schedule.game_location == "N"
        self.schedule.loc[~neutral, "game_coords"] = self.schedule.loc[
            ~neutral, "coords1"
        ]
        zips = download_zip_codes()
        for box in self.schedule.loc[neutral, "boxscore_abbrev"]:
            stadium_id = get_game_stadium(box)
            if stadium_id in ["", "attendance"]:
                stad_name = self.schedule.loc[
                    self.schedule.boxscore_abbrev == box, "Stadium"
                ].values[0]
                intl_stads = {
                    "Wembley Stadium": "LON00",
                    "Tottenham Hotspur Stadium": "LON02",
                    "Deutsche Bank Park": "FRA00",
                    "Arena Corinthians": "SAO00",
                    "Allianz Arena": "MUN01",
                    "Croke Park": "DUB00",
                    "Santiago Bernabéu Stadium": "MAD01",
                    "Olympiastadion": "BER00",
                }
                if stad_name in intl_stads:
                    stadium_id = intl_stads[stad_name]
            address = get_address(stadium_id)
            coords = get_coordinates(address, zips)
            self.schedule.loc[self.schedule.boxscore_abbrev == box, "game_coords"] = (
                coords
            )
        del self.schedule["Stadium"]
        self.schedule.game_coords = self.schedule.game_coords.str.split(",")

    def add_travel(self) -> None:
        """
        Adds the distance traveled for each team in each matchup of the schedule.
        """
        for team in [1, 2]:
            self.schedule["coords" + str(team)] = self.schedule[
                "coords" + str(team)
            ].str.split(",")
            self.schedule["travel" + str(team)] = self.schedule.apply(
                lambda x, t=team: geodesic(x["coords" + str(t)], x["game_coords"]).mi,
                axis=1,
            )

    def add_rest(self) -> None:
        """
        Identifies teams that had a bye week before the matchup in question.
        """
        for week in range(2, self.schedule.week.max() + 1):
            prev = (
                self.schedule.loc[self.schedule.week == week - 1, ["team1", "team2"]]
                .values.flatten()
                .tolist()
            )
            now = (
                self.schedule.loc[self.schedule.week == week, ["team1", "team2"]]
                .values.flatten()
                .tolist()
            )
            rested = [team for team in now if team not in prev]
            self.schedule.loc[
                (self.schedule.week == week) & self.schedule.team1.isin(rested),
                "rested1",
            ] = True
            self.schedule.loc[
                (self.schedule.week == week) & self.schedule.team2.isin(rested),
                "rested2",
            ] = True
        self.schedule.rested1 = self.schedule.rested1.astype(bool).fillna(False)
        self.schedule.rested2 = self.schedule.rested2.astype(bool).fillna(False)

    def add_elo_columns(self, qbelo: bool = False) -> None:
        """
        Adds the necessary columns for elo projections throughout the schedule.

        Args:
            qbelo: whether to infer QB elo values, defaults to False.
        """
        self.schedule[
            [
                "elo1_pre",
                "elo2_pre",
                "elo1_post",
                "elo2_post",
                "elo_diff",
                "point_spread",
                "elo_prob1",
                "elo_prob2",
                "score_diff",
                "forecast_delta",
                "mov_multiplier",
                "elo_delta",
            ]
        ] = None
        if qbelo:
            qb_elos = get_qb_elos(
                self.schedule.season.min(),
                self.schedule.season.max(),
                schedule_data=self.schedule,
            )
            for team_num in ["1", "2"]:
                self.schedule = pd.merge(
                    left=self.schedule,
                    right=qb_elos.rename(
                        columns={
                            "game_id": "boxscore_abbrev",
                            "team": f"team{team_num}_abbrev",
                            "player": "qb" + team_num,
                            "team_qbvalue_avg": f"team{team_num}_qbvalue_avg",
                            "opp_qbvalue_avg": f"opp{team_num}_qbvalue_avg",
                            "qb_value_pre": f"qb{team_num}_value_pre",
                            "qb_adj": f"qb{team_num}_adj",
                            "qb_value_post": f"qb{team_num}_value_post",
                            "VALUE": f"VALUE{team_num}",
                        }
                    ),
                    how="inner",
                    on=["boxscore_abbrev", f"team{team_num}_abbrev"],
                )

    def next_init_elo(
        self, init_elo: float = 1300.0, regress_pct: float = 0.333
    ) -> None:
        """
        Identifies the next matchup that does not have complete elo projections
        and calculates each team's starting elo rating based on 538's model (#RIP).

        Args:
            init_elo: initial elo rating to provide new teams with, defaults to 1300.
            regress_pct: percentage to regress teams back to the mean between each season, defaults to 0.333.
        """
        ind = self.schedule.loc[self.schedule.elo1_pre.isnull()].index[0]
        for team_num in ["1", "2"]:
            team = self.schedule.loc[ind, f"team{team_num}_abbrev"]
            prev = self.schedule.iloc[:ind].copy()
            prev = prev.loc[(prev.team1_abbrev == team) | (prev.team2_abbrev == team)]
            if prev.shape[0] > 0:
                # Team already exists
                prev = prev.iloc[-1]
                prev_num = 1 if prev["team1_abbrev"] == team else 2
                if not pd.isnull(prev[f"elo{prev_num}_post"]):
                    self.schedule.loc[ind, f"elo{team_num}_pre"] = prev[
                        f"elo{prev_num}_post"
                    ]
                    if prev["season"] == self.schedule.loc[ind, "season"] - 1:
                        # Start of a new season
                        self.schedule.loc[ind, f"elo{team_num}_pre"] += (
                            1505 - prev[f"elo{prev_num}_post"]
                        ) * regress_pct
                    elif prev["season"] < self.schedule.loc[ind, "season"] - 1:
                        # Resurrected teams (e.g. 1999 Cleveland Browns)
                        self.schedule.loc[ind, f"elo{team_num}_pre"] = init_elo
                else:
                    # Game hasn't been played yet...
                    self.schedule.loc[ind, f"elo{team_num}_pre"] = prev[
                        f"elo{prev_num}_pre"
                    ]
            else:
                # New Team
                self.schedule.loc[ind, f"elo{team_num}_pre"] = init_elo
            if f"qb{team_num}_adj" in self.schedule.columns:
                self.schedule.loc[ind, f"qbelo{team_num}_pre"] = (
                    self.schedule.loc[ind, f"elo{team_num}_pre"]
                    + self.schedule.loc[ind, f"qb{team_num}_adj"]
                )

    def next_elo_prob(
        self,
        homefield: float = 48.0,
        travel: float = 0.004,
        rested: float = 25.0,
        playoffs: float = 1.2,
        elo2points: float = 0.04,
    ) -> None:
        """
        Identifies the next matchup that does not have complete elo projections
        and calculates each team's win probability based on 538's model (#RIP).

        Args:
            homefield: elo rating boost for home-field advantage, defaults to 48.
            travel: elo rating penalty for travel, defaults to 0.004 per mile traveled.
            rested: elo rating boost for rested teams, defaults to 25.
            playoffs: elo rating expansion in the playoffs, defaults to 1.2.
            elo2points: conversion rate between elo and points, defaults to 0.04.
        """
        ind = self.schedule.loc[self.schedule.elo_prob1.isnull()].index[0]
        self.schedule.loc[ind, "elo_diff"] = (
            self.schedule.loc[ind, "elo1_pre"] - self.schedule.loc[ind, "elo2_pre"]
        )
        self.schedule.loc[ind, "elo_diff"] += homefield  # Homefield advantage
        self.schedule.loc[ind, "elo_diff"] += travel * (
            self.schedule.loc[ind, "travel2"] - self.schedule.loc[ind, "travel1"]
        )  # Travel
        if self.schedule.loc[ind, "rested1"]:
            self.schedule.loc[ind, "elo_diff"] += rested  # Bye week
        if self.schedule.loc[ind, "rested2"]:
            self.schedule.loc[ind, "elo_diff"] -= rested  # Bye week
        if not self.schedule.loc[ind, "week_num"].isnumeric():
            self.schedule.loc[ind, "elo_diff"] *= playoffs  # Playoffs
        self.schedule.loc[ind, "point_spread"] = (
            self.schedule.loc[ind, "elo_diff"] * elo2points
        )
        self.schedule.loc[ind, "elo_prob1"] = 1 / (
            10 ** (self.schedule.loc[ind, "elo_diff"] / -400) + 1
        )
        self.schedule.loc[ind, "elo_prob2"] = 1 - self.schedule.loc[ind, "elo_prob1"]
        if "qb1_adj" in self.schedule.columns and "qb2_adj" in self.schedule.columns:
            self.schedule.loc[ind, "qbelo_diff"] = (
                self.schedule.loc[ind, "elo_diff"]
                + self.schedule.loc[ind, "qb1_adj"]
                - self.schedule.loc[ind, "qb2_adj"]
            )
            self.schedule.loc[ind, "qbpoint_spread"] = (
                self.schedule.loc[ind, "qbelo_diff"] * elo2points
            )
            self.schedule.loc[ind, "qbelo_prob1"] = 1 / (
                10 ** (self.schedule.loc[ind, "qbelo_diff"] / -400) + 1
            )
            self.schedule.loc[ind, "qbelo_prob2"] = (
                1 - self.schedule.loc[ind, "qbelo_prob1"]
            )

    def next_elo_delta(self, k_factor: float = 20.0) -> None:
        """
        Identifies the next matchup that does not have complete elo projections
        and calculates each team's new elo rating based on the results of that game.

        Args:
            k_factor: scaling factor that dictates how much ratings should shift based on recent results, defaults to 20.
        """
        ind = self.schedule.loc[
            ~self.schedule.elo_prob1.isnull() & self.schedule.elo_delta.isnull()
        ].index[-1]
        if not pd.isnull(self.schedule.loc[ind, "score1"]):
            self.schedule.loc[ind, "score_diff"] = (
                self.schedule.loc[ind, "score1"] - self.schedule.loc[ind, "score2"]
            )
            self.schedule.loc[ind, "forecast_delta"] = (
                float(self.schedule.loc[ind, "score_diff"] > 0)
                + 0.5 * float(self.schedule.loc[ind, "score_diff"] == 0)
                - self.schedule.loc[ind, "elo_prob1"]
            )
            self.schedule.loc[ind, "mov_multiplier"] = (
                np.log(abs(self.schedule.loc[ind, "score_diff"]) + 1)
                * 2.2
                / (self.schedule.loc[ind, "elo_diff"] * 0.001 + 2.2)
            )
            if pd.isnull(self.schedule.loc[ind, "mov_multiplier"]):
                self.schedule.loc[ind, "mov_multiplier"] = 0.0
            self.schedule.loc[ind, "elo_delta"] = (
                self.schedule.loc[ind, "forecast_delta"]
                * self.schedule.loc[ind, "mov_multiplier"]
                * k_factor
            )
            self.schedule.loc[ind, "elo1_post"] = (
                self.schedule.loc[ind, "elo1_pre"] + self.schedule.loc[ind, "elo_delta"]
            )
            self.schedule.loc[ind, "elo2_post"] = (
                self.schedule.loc[ind, "elo2_pre"] - self.schedule.loc[ind, "elo_delta"]
            )
