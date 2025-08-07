"""
NFL game boxscore data retrieval and processing.

This module contains the Boxscore class for downloading and parsing
individual game statistics from Pro Football Reference.
"""

import pandas as pd

from .scraper import get_page, parse_table


class Boxscore:
    """
    Boxscore class that gathers all relevant statistics for the game in question
    and parses them into a pandas dataframe.

    Attributes:
        game_id: unique SportsRef identifier for the game in question.
        raw_text: raw html for the Pro Football Reference page of the game in question.
        season: season of the game in question.
        week: week of the season for the game in question.
        team1_abbrev: abbreviation for the home team.
        team1_score: points scored by the home team.
        team2_abbrev: abbreviation for the away team.
        team2_score: points scored by the away team.
        game_stats: dataframe containing relevant statistics for the game in question.
        starters: dataframe containing the list of starting players for both teams.
        snaps: dataframe containing the number of snaps played by every player on both teams.
    """

    # Type annotations for dynamic attributes
    game_id: str
    season: int
    week: int
    team1_abbrev: str
    team1_score: int
    team2_abbrev: str
    team2_score: int

    def __init__(self, game_id: str):
        """
        Initializes a Boxscore object using the parameters provided and class functions defined below.

        Args:
            game_id: unique SportsRef identifier for the game in question.
        """
        self.game_id = game_id
        self.get_raw_text()
        self.get_details()
        self.get_stats()
        self.get_advanced_stats()
        self.get_starters()
        self.get_snap_counts()
        self.add_depth_chart()
        self.add_qb_value()
        self.normalize_team_names()

    def get_raw_text(self) -> None:
        """
        Pulls down the raw html from Pro Football Reference containing the statistics for the game in question.
        """
        self.raw_text = get_page(f"boxscores/{self.game_id}.htm")

    def get_details(self) -> None:
        """
        Extracts the overarching details for the game in question, specifically the season, week, score, and teams involved.
        """
        season_week_div = self.raw_text.find(
            "div", attrs={"class": "game_summaries compressed"}
        )
        if season_week_div is None:
            raise ValueError("Could not find season/week information in game data")

        link = season_week_div.find("a")
        if link is None or not hasattr(link, "attrs") or "href" not in link.attrs:
            raise ValueError("Could not extract season/week from game data")

        season_week = link.attrs["href"]
        self.season = int(season_week.split("/")[-2])
        self.week = int(season_week.split("/")[-1].split("_")[-1].split(".")[0])
        home_scores = self.raw_text.find_all(
            ["th", "td"], attrs={"data-stat": "home_team_score"}
        )
        self.team1_abbrev = home_scores[0].text
        self.team1_score = int(home_scores[-1].text)
        away_scores = self.raw_text.find_all(
            ["th", "td"], attrs={"data-stat": "vis_team_score"}
        )
        self.team2_abbrev = away_scores[0].text
        self.team2_score = int(away_scores[-1].text)

    def get_stats(self) -> None:
        """
        Extracts the basic offensive, defensive, and special teams stats
        from the raw html for the game in question.
        """
        self.game_stats = pd.concat(
            [
                parse_table(self.raw_text, "player_offense"),
                parse_table(self.raw_text, "player_defense"),
                parse_table(self.raw_text, "kicking"),
            ]
        )
        if self.raw_text.find(id="returns"):
            self.game_stats = pd.concat(
                [self.game_stats, parse_table(self.raw_text, "returns")]
            )
        self.game_stats = (
            self.game_stats.fillna(0.0)
            .groupby(["player", "player_id", "team"])
            .sum()
            .reset_index()
        )
        self.game_stats.loc[self.game_stats.team == self.team1_abbrev, "opponent"] = (
            self.team2_abbrev
        )
        self.game_stats.loc[self.game_stats.team == self.team2_abbrev, "opponent"] = (
            self.team1_abbrev
        )

    def get_advanced_stats(self) -> None:
        """
        Extracts the advanced offensive, defensive, and special teams stats
        from the raw html for the game in question (e.g. first downs).
        """
        if self.raw_text.find(id="passing_advanced"):
            advanced = pd.concat(
                [
                    parse_table(self.raw_text, "passing_advanced"),
                    parse_table(self.raw_text, "rushing_advanced"),
                    parse_table(self.raw_text, "receiving_advanced"),
                ]
            )
            advanced = (
                advanced.fillna(0.0)
                .groupby(["player", "player_id", "team"])
                .sum()
                .reset_index()
            )
        else:
            advanced = pd.DataFrame(
                columns=[
                    "player_id",
                    "pass_first_down",
                    "rush_first_down",
                    "rec_first_down",
                ]
            )
        self.game_stats = pd.merge(
            left=self.game_stats,
            right=advanced[
                ["player_id", "pass_first_down", "rush_first_down", "rec_first_down"]
            ],
            how="left",
            on="player_id",
        )
        for col in ["pass_first_down", "rush_first_down", "rec_first_down"]:
            self.game_stats[col] = self.game_stats[col].astype(float).fillna(0.0)

    def get_starters(self) -> None:
        """
        Extracts the intended starters for each team in the game in question.
        """
        self.starters = pd.concat(
            [
                parse_table(self.raw_text, "home_starters"),
                parse_table(self.raw_text, "vis_starters"),
            ]
        )

    def get_snap_counts(self) -> None:
        """
        Extracts the actual snap counts for all players on each team in the game in question.
        """
        # Games before 2012 don't have snapcounts and therefore no positions for non-starters...
        # Could merge position in via the get_names function...
        if (
            self.raw_text.find(id="home_snap_counts") is not None
            and self.raw_text.find(id="vis_snap_counts") is not None
        ):
            self.snaps = pd.concat(
                [
                    parse_table(self.raw_text, "home_snap_counts"),
                    parse_table(self.raw_text, "vis_snap_counts"),
                ]
            )
        else:
            self.snaps = self.game_stats[["player", "player_id"]].copy()
            self.snaps[["off_pct", "def_pct", "st_pct"]] = 0.0

    def add_depth_chart(self) -> None:
        """
        Infers actual depth chart based on available depth charts/snap counts
        and merges it into the game_stats dataframe.
        """
        nonstarters = self.snaps.loc[
            ~self.snaps.player_id.isin(self.starters.player_id.tolist())
        ].sort_values(by=["off_pct", "def_pct", "st_pct"], ascending=False)
        depth_chart = pd.merge(
            left=pd.concat([self.starters.iloc[::-1], nonstarters]),
            right=self.game_stats[["player", "player_id", "team"]],
            how="inner",
            on=["player", "player_id"],
        )
        depth_chart["dummy"] = 1
        depth_chart["string"] = depth_chart.groupby(["team", "pos"]).dummy.rank(
            method="first"
        )
        self.game_stats = pd.merge(
            left=self.game_stats,
            right=depth_chart[["player", "player_id", "team", "pos", "string"]],
            how="inner",
            on=["player", "player_id", "team"],
        )

    def add_qb_value(
        self,
        pass_att: float = -2.2,
        pass_cmp: float = 3.7,
        pass_yds: float = 0.2,
        pass_td: float = 11.3,
        pass_int: float = -14.1,
        pass_sacked: float = -8.0,
        rush_att: float = -1.1,
        rush_yds: float = 0.6,
        rush_td: float = 15.9,
    ) -> None:
        """
        Calculates individual QB elo value based on 538's model (#RIP).

        Args:
            pass_att: weighting factor for pass attempts, defaults to -2.2.
            pass_cmp: weighting factor for pass completions, defaults to 3.7.
            pass_yds: weighting factor for passing yards, defaults to 0.2.
            pass_td: weighting factor for passing touchdowns, defaults to 11.3.
            pass_sacked: weighting factor for sacks, defaults to -8.0.
            rush_att: weighting factor for rush attempts, defaults to -1.1.
            rush_yds: weighting factor for rush yards, defaults to 0.6.
            rush_td: weighting factor for rushing touchdowns, defaults to 15.9.
        """
        qbs = self.game_stats.pos == "QB"
        self.game_stats.loc[qbs, "VALUE"] = (
            pass_att * self.game_stats.loc[qbs, "pass_att"]
            + pass_cmp * self.game_stats.loc[qbs, "pass_cmp"]
            + pass_yds * self.game_stats.loc[qbs, "pass_yds"]
            + pass_td * self.game_stats.loc[qbs, "pass_td"]
            + pass_int * self.game_stats.loc[qbs, "pass_int"]
            + pass_sacked * self.game_stats.loc[qbs, "pass_sacked"]
            + rush_att * self.game_stats.loc[qbs, "rush_att"]
            + rush_yds * self.game_stats.loc[qbs, "rush_yds"]
            + rush_td * self.game_stats.loc[qbs, "rush_td"]
        )

    def normalize_team_names(self) -> None:
        """
        Normalizes team names between Pro Football Reference's boxscores and schedules.
        """
        abbrevs = {
            "OAK": "RAI",
            "LVR": "RAI",
            "LAC": "SDG",
            "STL": "RAM",
            "LAR": "RAM",
            "ARI": "CRD",
            "IND": "CLT",
            "BAL": "RAV",
            "HOU": "HTX",
            "TEN": "OTI",
        }
        for team in abbrevs:
            for val in ["team", "opponent"]:
                self.game_stats.loc[self.game_stats[val] == team, val] = abbrevs[team]
        if self.team1_abbrev in abbrevs:
            self.team1_abbrev = abbrevs[self.team1_abbrev]
        if self.team2_abbrev in abbrevs:
            self.team2_abbrev = abbrevs[self.team2_abbrev]


# Keep this as an alias for backward compatibility
Game = Boxscore
