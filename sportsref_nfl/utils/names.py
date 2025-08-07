"""
Player name and ID lookup utilities.

This module handles retrieving player names and IDs from Pro Football Reference
for player identification and matching purposes.
"""

import pandas as pd

from ..core.scraper import get_page


def get_names() -> pd.DataFrame:
    """
    Pulls the player id and name for every player on Pro Football Reference for conversion purposes.

    Returns:
        DataFrame containing name, position, player id, and timespan of every player in the database.
    """
    names = pd.DataFrame()
    for letter in range(65, 91):
        raw_text = get_page("players/" + chr(letter))
        from bs4 import Tag

        div_players = raw_text.find(id="div_players")
        if div_players is None or not isinstance(div_players, Tag):
            continue
        players = div_players.find_all("p")
        for player in players:
            entry = {
                "name": player.find("a").text,
                "position": player.text.split("(")[-1].split(")")[0],
                "player_id": player.find("a")
                .attrs["href"]
                .split("/")[-1]
                .split(".")[0],
                "years_active": player.text.split(") ")[-1],
            }
            names = pd.concat([names, pd.DataFrame(entry, index=[names.shape[0]])])
    return names
