"""
Stadium location and travel calculation functionality.

This module handles stadium data retrieval, coordinate lookup,
and international game tracking for NFL venues.
"""

import gzip
import shutil
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..core.scraper import get_page, parse_table


def get_intl_games() -> pd.DataFrame:
    """
    Pulls details about the games in the NFL International Series (used in annotating neutral site games).

    Returns:
        DataFrame containing dates, teams, and scores for each matchup.
    """
    response = requests.get(
        "https://en.wikipedia.org/wiki/NFL_International_Series"
    ).text
    soup = BeautifulSoup(response, "html.parser")
    tables = soup.find_all("table", attrs={"class": "wikitable sortable"})[1:-1]
    intl_games = pd.concat(pd.read_html(StringIO(str(tables))), ignore_index=True)
    intl_games = intl_games.loc[
        ~intl_games.Date.isnull() & ~intl_games.Date.isin(["TBD", "TBA"])
    ].reset_index(drop=True)
    intl_games.Year = intl_games.Year.astype(str).str.split(" ").str[0].astype(int)
    intl_games["team1"] = intl_games["Designated home team"].str.split(r"\[").str[0]
    intl_games["team2"] = intl_games["Designated visitor"].str.split(r"\[").str[0]
    intl_games.Stadium = intl_games.Stadium.str.split(r"\[").str[0]
    intl_games["game_date"] = pd.to_datetime(
        intl_games.Date + ", " + intl_games.Year.astype(str)
    )
    return intl_games[["game_date", "team1", "team2", "Stadium"]]


def get_stadiums() -> pd.DataFrame:
    """
    Pulls details about all stadiums ever used for an NFL game.

    Returns:
        DataFrame containing names, locations, and timespans of each stadium.
    """
    raw_text = get_page("stadiums")
    stadiums = parse_table(raw_text, "stadiums")
    return stadiums


def get_team_stadium(abbrev: str, season: int) -> str:
    """
    Identifies the home stadium of the specified team during the specified season.

    Args:
        abbrev: team abbreviation according to Pro Football Reference
        season: year of the NFL season of interest

    Returns:
        Stadium identifier according to Pro Football Reference
    """
    raw_text = get_page(f"teams/{abbrev.lower()}/{int(season)}.htm")
    from bs4 import Tag

    meta_div = raw_text.find(id="meta")
    if meta_div is None or not isinstance(meta_div, Tag):
        return ""
    team_info = meta_div.find_all("p")
    stadium_info = [val for val in team_info if val.text.startswith("Stadium:")]
    if len(stadium_info) == 0:
        stadiums = get_stadiums()
        stadiums.teams_abbrev = stadiums.teams_abbrev.str.split(", ")
        stadiums = stadiums.explode("teams_abbrev", ignore_index=True)
        stadium_id = stadiums.loc[
            (stadiums.teams_abbrev == abbrev)
            & (stadiums.year_min <= season)
            & (stadiums.year_max >= season),
            "stadium_abbrev",
        ]
        if stadium_id.shape[0] > 0:
            stadium_id = stadium_id.values[0]
        else:
            print(f"Can't find home stadium for {season} {abbrev}...")
            stadium_id = None
    else:
        stadium_info = stadium_info[0]
        link = stadium_info.find("a")
        if link is not None and hasattr(link, "attrs") and "href" in link.attrs:
            stadium_id = link.attrs["href"].split("/")[-1].split(".")[0]
        else:
            stadium_id = ""
    return stadium_id or ""


def get_game_stadium(game_id: str) -> str:
    """
    Identifies the stadium where the specified game was played.

    Args:
        game_id: Pro Football Reference identifier string for the game in question (e.g. 202209080ram).

    Returns:
        Stadium identifier according to Pro Football Reference.
    """
    raw_text = get_page(f"boxscores/{game_id}.htm")
    game_info = raw_text.find("div", attrs={"class": "scorebox_meta"})
    if game_info is None:
        return ""
    link = game_info.find("a")
    if link is not None and hasattr(link, "attrs") and "href" in link.attrs:
        stadium_id = link.attrs["href"].split("/")[-1].split(".")[0]
        return stadium_id
    return ""


def get_address(stadium_id: str) -> str:
    """
    Identifies the address of the specified stadium (with a few typo corrections here and there).

    Args:
        stadium_id: stadium identifier according to Pro Football Reference.

    Returns:
        Address of the specified stadium according to Pro Football Reference.
    """
    raw_text = get_page(f"stadiums/{stadium_id}.htm")
    meta_info = raw_text.find(id="meta")
    if meta_info is None:
        print(f"Can't find stadium address for stadium ID: {stadium_id}")
        return "Unknown Stadium Address"
    else:
        p_tag = meta_info.find("p")
        if p_tag is not None and hasattr(p_tag, "text"):
            address = p_tag.text
        else:
            return "Unknown Stadium Address"
    fixes = {
        "New Jersey": "NJ",
        "Park Houston": "Park, Houston",
        "Blvd Opa-Locka": "Blvd, Opa-Locka",
        "Northumberland Development Project": "782 High Rd, London N17 0BX, UK",
        "Toronto, Ontario M5V 1J3": "Toronto, ON M5V 1J3, Canada",
        "Sao Paulo - SP": "São Paulo - SP, Brazil",
    }
    for fix in fixes:
        address = address.replace(fix, fixes[fix])
    return address


def download_zip_codes(
    url: str = "https://nominatim.org/data/us_postcodes.csv.gz",
) -> pd.DataFrame:
    """
    Downloads a csv from Nominatim containing the GPS coordinates of every zip code in the US
    and returns it in the form of a pandas dataframe (used when accounting for team travel).

    Args:
        url: URL location of the zipcode csv, defaults to "https://nominatim.org/data/us_postcodes.csv.gz".

    Returns:
        DataFrame containing the GPS coordinates of every US zip code.
    """
    response = requests.get(url, stream=True)
    with open(url.split("/")[-1], "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)
    with gzip.open(url.split("/")[-1], "rb") as f_in:
        with open(url.split("/")[-1][:-3], "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    zips = pd.read_csv(url.split("/")[-1][:-3], dtype={"postcode": str})
    return zips


def get_coordinates(address: str, zips: pd.DataFrame) -> str:
    """
    Provides the coordinates of the specified address. If no exact coordinates are available,
    city, state, and zip code are used for an approximate position.

    Args:
        address: physical address of interest.
        zips: DataFrame containing zip code coordinate data.

    Returns:
        Latitudinal and longitudinal coordinates separated by a comma.
    """
    stad_zip = address.split(" ")[-1]
    stad_coords = zips.loc[zips.postcode == stad_zip, ["lat", "lon"]].astype(str)
    intl_coords = {
        "Mexico": "19.3029,-99.1505",
        "UK": "51.5072,-0.1276",
        "Bavaria": "48.2188,11.6248",
        "Hesse": "50.0686,8.6455",
        "Canada": "43.6414,-79.3892",
        "Brazil": "-23.5453,-46.4742",
        "Ireland": "53.3607,-6.2511",
        "Spain": "40.4530,-3.6883",
        "Berlin": "52.5147,13.2395",
    }
    if stad_coords.shape[0] > 0:
        coords = ",".join(stad_coords.values[0])
    elif stad_zip in intl_coords:
        coords = intl_coords[stad_zip]
    else:
        print("Can't find zip code provided: " + str(stad_zip))
        print("Using centerpoint of USA...")
        coords = "37.0902,-95.7129"
    return coords
