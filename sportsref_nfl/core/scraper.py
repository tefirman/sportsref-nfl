"""
Core scraping functionality for Pro Football Reference.

This module contains the base functions for making requests to Pro Football Reference
and parsing HTML tables into pandas DataFrames.
"""

import sys
import time

import cloudscraper
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "https://www.pro-football-reference.com/"


def get_page_selenium(endpoint: str) -> BeautifulSoup:
    """
    Pulls down the raw html for the specified endpoint of Pro Football Reference using Selenium.
    This helps bypass Cloudflare protection by using a real browser.

    Args:
        endpoint: relative location of the page to pull down.

    Returns:
        Parsed html of the specified endpoint.
    """
    print(f"🌐 Using Selenium to fetch: {BASE_URL + endpoint}")

    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Add a realistic User-Agent
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None
    try:
        # Create WebDriver
        driver = webdriver.Chrome(options=chrome_options)

        # Execute script to hide WebDriver presence
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Navigate to the page
        full_url = BASE_URL + endpoint
        driver.get(full_url)

        # Wait for page to load and check for Cloudflare challenge
        try:
            # Wait up to 30 seconds for either the content to load or Cloudflare to resolve
            WebDriverWait(driver, 30).until(
                lambda d: d.find_element(By.TAG_NAME, "table")
                or "Just a moment" not in d.title
            )
        except TimeoutException:
            print("⏰ Timeout waiting for page to load, proceeding anyway...")

        # Additional wait to ensure Cloudflare challenge is resolved
        time.sleep(5)

        # Get the page source
        html = driver.page_source

        # Check if we still have Cloudflare challenge
        if "Just a moment" in driver.title or "challenge" in html.lower():
            raise Exception("Cloudflare challenge not resolved after waiting")

        print(f"✅ Successfully loaded page: {driver.title}")

    except WebDriverException as e:
        raise Exception(f"Selenium WebDriver error: {e}") from e
    except Exception as e:
        raise Exception(f"Failed to load page with Selenium: {e}") from e
    finally:
        if driver:
            driver.quit()

    # Process the HTML same way as before
    uncommented = html.replace("<!--", "").replace("-->", "")
    soup = BeautifulSoup(uncommented, "html.parser")
    return soup


def get_page(endpoint: str) -> BeautifulSoup:
    """
    Pulls down the raw html for the specified endpoint of Pro Football Reference.
    First tries Selenium to bypass Cloudflare, falls back to cloudscraper if needed.

    Args:
        endpoint: relative location of the page to pull down.

    Returns:
        Parsed html of the specified endpoint.
    """
    # Add delay to respect rate limits
    time.sleep(4)

    # Try Selenium first (better for Cloudflare)
    try:
        return get_page_selenium(endpoint)
    except Exception as selenium_error:
        print(f"⚠️  Selenium failed: {selenium_error}")
        print("🔄 Falling back to cloudscraper...")

        # Fall back to original cloudscraper method
        try:
            scraper = cloudscraper.create_scraper()
            response = scraper.get(BASE_URL + endpoint).text
            uncommented = response.replace("<!--", "").replace("-->", "")
            soup = BeautifulSoup(uncommented, "html.parser")
            return soup
        except requests.exceptions.ConnectionError:
            print("GETTING CONNECTION ERROR AGAIN!!!")
            print(endpoint)
            sys.exit(1)
        except Exception as cloudscraper_error:
            raise Exception(
                f"Both Selenium and cloudscraper failed. Selenium: {selenium_error}. Cloudscraper: {cloudscraper_error}"
            ) from cloudscraper_error


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
