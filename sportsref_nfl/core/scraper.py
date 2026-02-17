"""
Core scraping functionality for Pro Football Reference.

This module contains the base functions for making requests to Pro Football Reference
and parsing HTML tables into pandas DataFrames.
"""

import shutil
import subprocess
import sys
import time

import cloudscraper
import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..cache import get_cache

BASE_URL = "https://www.pro-football-reference.com/"
FLARESOLVERR_URL = "http://localhost:8191/v1"
FLARESOLVERR_IMAGE = "flaresolverr/flaresolverr:latest"
FLARESOLVERR_CONTAINER = "flaresolverr"


def ensure_flaresolverr() -> bool:
    """
    Checks if FlareSolverr is running and attempts to start it via Docker if not.

    Returns:
        True if FlareSolverr is available, False otherwise.
    """
    # Check if already running
    try:
        resp = requests.get("http://localhost:8191/", timeout=3)
        if resp.ok:
            return True
    except requests.exceptions.ConnectionError:
        pass

    # Try to start via Docker
    if shutil.which("docker") is None:
        return False

    print("🐳 Starting FlareSolverr via Docker...")
    try:
        # Check if container exists but is stopped
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Running}}",
                FLARESOLVERR_CONTAINER,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            if result.stdout.strip() == "true":
                return True  # Already running
            # Container exists but stopped — restart it
            subprocess.run(
                ["docker", "start", FLARESOLVERR_CONTAINER],
                capture_output=True,
                check=True,
            )
        else:
            # Container doesn't exist — create it
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    FLARESOLVERR_CONTAINER,
                    "-p",
                    "8191:8191",
                    FLARESOLVERR_IMAGE,
                ],
                capture_output=True,
                check=True,
            )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

    # Wait for it to become ready
    for _ in range(12):
        time.sleep(5)
        try:
            resp = requests.get("http://localhost:8191/", timeout=3)
            if resp.ok:
                print("✅ FlareSolverr is ready!")
                return True
        except requests.exceptions.ConnectionError:
            continue

    print("⚠️  FlareSolverr started but not responding")
    return False


def get_page_flaresolverr(endpoint: str) -> BeautifulSoup:
    """
    Fetches a page using a local FlareSolverr instance to bypass Cloudflare protection.

    Requires FlareSolverr running locally (e.g. via Docker):
        docker run -d --name flaresolverr -p 8191:8191 flaresolverr/flaresolverr:latest

    Args:
        endpoint: relative location of the page to pull down.

    Returns:
        Parsed html of the specified endpoint.
    """
    full_url = BASE_URL + endpoint
    print(f"🌐 Using FlareSolverr to fetch: {full_url}")

    response = requests.post(
        FLARESOLVERR_URL,
        json={
            "cmd": "request.get",
            "url": full_url,
            "maxTimeout": 60000,
        },
        timeout=90,
    )
    data = response.json()

    if data["status"] != "ok":
        raise Exception(f"FlareSolverr error: {data.get('message', data)}")

    html = data["solution"]["response"]

    # Check if we still got a Cloudflare challenge page
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.text if soup.title else ""
    if "just a moment" in title.lower() or "challenge" in title.lower():
        raise Exception(f"FlareSolverr did not solve Cloudflare challenge: {title}")

    print(f"✅ Successfully loaded page: {title}")

    # Remove HTML comments to expose hidden tables (PFR convention)
    uncommented = html.replace("<!--", "").replace("-->", "")
    return BeautifulSoup(uncommented, "html.parser")


def get_page(
    endpoint: str, max_retries: int = 3, use_cache: bool = True
) -> BeautifulSoup:
    """
    Pulls down the raw html for the specified endpoint of Pro Football Reference.
    First checks cache, then tries FlareSolverr to bypass Cloudflare,
    falls back to cloudscraper if FlareSolverr is not available.

    Args:
        endpoint: relative location of the page to pull down.
        max_retries: maximum number of retry attempts.
        use_cache: whether to use caching system.

    Returns:
        Parsed html of the specified endpoint.
    """
    cache = get_cache()

    # Check cache first
    if use_cache:
        cached_page = cache.get_cached_page(endpoint)
        if cached_page is not None:
            print(f"📁 Using cached: {endpoint}")
            return cached_page

    # Add delay to respect rate limits
    time.sleep(4)

    # Ensure FlareSolverr is running (auto-starts via Docker if possible)
    flaresolverr_available = ensure_flaresolverr()

    for attempt in range(max_retries):
        if attempt > 0:
            wait_time = (2**attempt) * 3  # Exponential backoff: 6s, 12s, 24s
            print(
                f"🔄 Retry attempt {attempt + 1}/{max_retries} after {wait_time}s delay..."
            )
            time.sleep(wait_time)

        # Try FlareSolverr first (best for Cloudflare)
        if flaresolverr_available:
            try:
                soup = get_page_flaresolverr(endpoint)
                # Cache successful result
                if use_cache:
                    cache.cache_page(endpoint, soup)
                return soup
            except requests.exceptions.ConnectionError:
                print("⚠️  FlareSolverr connection lost")
                flaresolverr_available = False
                print("🔄 Falling back to cloudscraper...")
            except Exception as flaresolverr_error:
                print(f"⚠️  FlareSolverr failed: {flaresolverr_error}")
                print("🔄 Falling back to cloudscraper...")

        # Fall back to cloudscraper method
        try:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(BASE_URL + endpoint).text
            uncommented = response.replace("<!--", "").replace("-->", "")
            soup = BeautifulSoup(uncommented, "html.parser")

            # Check if we got a Cloudflare challenge page
            title = soup.title.text if soup.title else ""
            if "just a moment" in title.lower() or "challenge" in title.lower():
                print(f"⚠️  Cloudscraper got Cloudflare challenge: {title}")
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    raise Exception(f"Cloudflare blocking after {max_retries} attempts")

            # Cache successful result
            if use_cache:
                cache.cache_page(endpoint, soup)
            return soup
        except requests.exceptions.ConnectionError:
            print("GETTING CONNECTION ERROR AGAIN!!!")
            print(endpoint)
            if attempt < max_retries - 1:
                continue  # Retry
            else:
                sys.exit(1)
        except Exception as cloudscraper_error:
            if attempt < max_retries - 1:
                print(f"⚠️  Attempt {attempt + 1} failed: {cloudscraper_error}")
                continue  # Retry
            else:
                raise Exception(
                    f"Both FlareSolverr and cloudscraper failed after {max_retries} attempts. "
                    f"Cloudscraper: {cloudscraper_error}. "
                    f"To bypass Cloudflare, install Docker and run: "
                    f"docker pull {FLARESOLVERR_IMAGE}"
                ) from cloudscraper_error

    raise Exception(f"Failed to fetch page after {max_retries} attempts")


def parse_table(raw_text: BeautifulSoup, table_name: str) -> pd.DataFrame:
    """
    Parses out the desired table from the raw html text into a pandas dataframe.

    Args:
        raw_text: raw html from the page of interest.
        table_name: title of the table to extract.

    Returns:
        DataFrame containing the data from the specified table.
    """
    from bs4 import Tag

    table = raw_text.find(id=table_name)
    if table is None or not isinstance(table, Tag):
        return pd.DataFrame()
    players = table.find_all("tr", attrs={"class": None})
    columns = [col.attrs["data-stat"] for col in players.pop(0).find_all("th")]
    stats = pd.DataFrame()

    for player in players:
        if player.text == "Playoffs":
            continue
        entry = {}
        for col in columns:
            entry[col] = player.find(["th", "td"], attrs={"data-stat": col})
            if col in ["boxscore_word", "stadium_name"]:
                abbrev = entry[col].find("a")
                if abbrev is not None:
                    new_col = col.split("_")[0] + "_abbrev"
                    entry[new_col] = abbrev.attrs["href"]
                    entry[new_col] = entry[new_col].split("/")[-1].split(".")[0]
            elif col == "player" and "data-append-csv" in entry[col].attrs:
                entry["player_id"] = entry[col].attrs["data-append-csv"]
            elif (
                col in ["winner", "loser", "home_team", "visitor_team", "teams", "team"]
                and entry[col].find("a") is not None
            ):
                entry[col + "_abbrev"] = ", ".join(
                    [
                        team.attrs["href"].split("/")[-2].upper()
                        for team in entry[col].find_all("a")
                    ]
                )
            entry[col] = entry[col].text
        stats = pd.concat([stats, pd.DataFrame(entry, index=[stats.shape[0]])])

    stats = stats.replace("", None).reset_index(drop=True)
    for col in stats.columns:
        if col.endswith("_pct"):
            stats[col] = stats[col].str.replace("%", "")
        stats[col] = stats[col].astype(float, errors="ignore")
    return stats
