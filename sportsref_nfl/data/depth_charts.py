"""
NFL team depth chart data retrieval from ESPN.

This module handles downloading and parsing depth charts
for all NFL teams from ESPN's website.
"""

import os

import pandas as pd
from bs4 import BeautifulSoup


def get_depth_chart(team_abbrev: str) -> pd.DataFrame:
    """
    Pulls the team depth chart directly from ESPN based on the team abbreviation provided.

    Args:
        team_abbrev: ESPN abbreviation for the team of interest.

    Returns:
        DataFrame containing the depth chart ranking for each player on the team of interest.
    """
    os.system(
        f"wget https://www.espn.com/nfl/team/depth/_/name/{team_abbrev} -q -O {team_abbrev}.html"
    )
    tempData = open(team_abbrev + ".html")
    response = tempData.read()
    tempData.close()
    os.remove(team_abbrev + ".html")

    soup = BeautifulSoup(response, "html.parser")
    tables = soup.find_all("table")
    depth = pd.DataFrame()
    for table_ind in range(len(tables) // 2):
        positions = [pos.text.strip() for pos in tables[table_ind * 2].find_all("td")]
        players = [
            player.text.strip() for player in tables[table_ind * 2 + 1].find_all("td")
        ]
        num_strings = len(players) // len(positions)
        for pos in range(len(positions)):
            for string in range(num_strings):
                depth = pd.concat(
                    [
                        depth,
                        pd.DataFrame(
                            {
                                "player": [players[pos * num_strings + string]],
                                "pos": [positions[pos]],
                                "string": [string + 1],
                            }
                        ),
                    ],
                    ignore_index=True,
                )
    depth.loc[depth.pos.isin(["PK"]), "pos"] = "K"
    depth = depth.loc[depth.player != "-"].reset_index(drop=True)
    for status in ["P", "Q", "O", "PUP", "SUSP", "IR"]:
        injured = depth.player.str.endswith(" " + status)
        depth.loc[injured, "status"] = status
        depth.loc[injured, "player"] = (
            depth.loc[injured, "player"].str.split(" ").str[:-1].apply(" ".join)
        )
    injured = depth.loc[depth.status.isin(["O", "PUP", "SUSP", "IR"])].reset_index(
        drop=True
    )
    injured.string = float("inf")
    depth = pd.concat(
        [depth.loc[~depth.status.isin(["O", "PUP", "SUSP", "IR"])], injured],
        ignore_index=True,
    )
    depth["string"] = depth.groupby("pos").string.rank(method="first")
    wrs = depth.pos == "WR"
    depth.loc[wrs, "string"] = 1 + (depth.loc[wrs, "string"] - 1) / 3
    corrections = pd.read_csv(
        "https://raw.githubusercontent.com/tefirman/fantasy-data/main/fantasyfb/name_corrections.csv"
    )
    depth = pd.merge(
        left=depth,
        right=corrections.rename(columns={"name": "player"}),
        how="left",
        on="player",
    )
    to_fix = ~depth.new_name.isnull()
    depth.loc[to_fix, "player"] = depth.loc[to_fix, "new_name"]
    del depth["new_name"], depth["status"]
    depth = depth.sort_values(by=["pos", "string"], ignore_index=True)
    return depth


def get_all_depth_charts() -> pd.DataFrame:
    """
    Pulls all ESPN depth charts across the NFL.

    Returns:
        DataFrame containing the depth chart ranking for each player in the NFL.
    """
    teams = pd.read_csv(
        "https://raw.githubusercontent.com/tefirman/fantasy-data/main/fantasyfb/team_abbrevs.csv"
    )
    teams["espn"] = teams.fivethirtyeight.str.replace("OAK", "LV")
    depths = pd.DataFrame(columns=["team"])
    for ind in range(teams.shape[0]):
        depths = pd.concat(
            [depths, get_depth_chart(teams.loc[ind, "espn"])], ignore_index=True
        )
        depths.team = depths.team.fillna(teams.loc[ind, "real_abbrev"])
    return depths
