# SportsRef NFL - NFL Data Scraping Library

A comprehensive Python library for scraping NFL data from Pro Football Reference, including schedules, player statistics, draft information, and advanced metrics like ELO ratings.

## Features

- **NFL Schedule Data**: Complete schedules with ELO ratings and playoff information
- **Player Statistics**: Comprehensive stats for all positions (QB, RB, WR, TE, K, DST)
- **Draft Information**: Historical NFL draft data with player details
- **Team Rosters**: Complete team rosters by season
- **Depth Charts**: Team depth chart information
- **Stadium Data**: Stadium information including locations and capacities
- **Advanced Metrics**: ELO ratings for team strength analysis
- **Name Utilities**: Player name normalization and matching
- **Robust Scraping**: Built-in retry logic and error handling
- **Command Line Interface**: Easy-to-use CLI for data extraction

## Installation

```bash
pip install sportsref-nfl
```

## Quick Start

### Command Line Interface

```bash
# Download NFL schedule with ELO ratings
sportsref-nfl schedule --start-year 2020 --end-year 2024 --elo

# Get specific game boxscore
sportsref-nfl boxscore --game-id "202401070buf"

# Download player statistics
sportsref-nfl stats --year 2024 --position QB

# Get draft data
sportsref-nfl draft --year 2024

# Download team rosters
sportsref-nfl rosters --year 2024 --team BUF
```

### Python API

```python
import sportsref_nfl as sr

# Load NFL schedule with ELO ratings
schedule = sr.Schedule(
    start_year=2020, 
    end_year=2024, 
    elo=True
)
print(schedule.schedule.head())

# Get boxscore data
game = sr.Boxscore("202401070buf")
print(f"{game.away_team} {game.away_score} - {game.home_score} {game.home_team}")

# Load player statistics
from sportsref_nfl.data import StatsLoader
stats_loader = StatsLoader()
qb_stats = stats_loader.load_position_stats(2024, "QB")

# Load draft data
from sportsref_nfl.data import DraftLoader
draft_loader = DraftLoader()
draft_2024 = draft_loader.load_draft_data(2024)
```

## Core Classes

### Schedule

```python
import sportsref_nfl as sr

# Basic schedule
schedule = sr.Schedule(2020, 2024)

# With ELO ratings and playoffs
schedule = sr.Schedule(
    start_year=2020,
    end_year=2024,
    playoffs=True,
    elo=True,
    verbose=True
)

# Access the data
df = schedule.schedule
print(df.columns)
# ['season', 'week', 'date', 'away_team', 'home_team', 
#  'away_score', 'home_score', 'elo_diff', ...]
```

### Boxscore

```python
import sportsref_nfl as sr

# Load specific game
game = sr.Boxscore("202401070buf")  # Bills playoff game

# Access game data
print(game.date)
print(game.away_team, game.home_team)
print(game.away_score, game.home_score)
print(game.weather)
```

### Data Loaders

```python
from sportsref_nfl.data import (
    StatsLoader, DraftLoader, RosterLoader, 
    DepthChartLoader, StadiumLoader
)

# Player statistics
stats_loader = StatsLoader()
all_stats = stats_loader.load_all_stats(2024)
qb_stats = stats_loader.load_position_stats(2024, "QB")

# Draft data
draft_loader = DraftLoader()
draft_2024 = draft_loader.load_draft_data(2024)

# Team rosters
roster_loader = RosterLoader()
bills_roster = roster_loader.load_team_roster(2024, "BUF")
all_rosters = roster_loader.load_all_rosters(2024)

# Depth charts
depth_loader = DepthChartLoader()
team_depth = depth_loader.load_team_depth_chart(2024, "BUF")

# Stadium information
stadium_loader = StadiumLoader()
stadiums = stadium_loader.load_stadiums()
```

### Name Utilities

```python
from sportsref_nfl.utils import NameUtils

name_utils = NameUtils()

# Normalize player names
normalized = name_utils.normalize_name("Josh Allen")
print(normalized)  # "josh allen"

# Check if names match
is_match = name_utils.names_match("Josh Allen", "J. Allen")
print(is_match)  # True

# Handle common name variations
is_match = name_utils.names_match("Robert Griffin III", "RG3")
print(is_match)  # True
```

## Command Line Reference

### Schedule Command
```bash
sportsref-nfl schedule --start-year 2020 --end-year 2024 [OPTIONS]

Options:
  --elo               Include ELO calculations
  --playoffs          Include playoff games
  --output PATH       Output CSV file path
  --verbose           Enable verbose output
```

### Boxscore Command
```bash
sportsref-nfl boxscore --game-id GAME_ID [OPTIONS]

Options:
  --output PATH       Output CSV file path
  --verbose           Enable verbose output
```

### Stats Command
```bash
sportsref-nfl stats --year YEAR [OPTIONS]

Options:
  --position POS      Filter by position (QB/RB/WR/TE/K/DST)
  --output PATH       Output CSV file path
  --verbose           Enable verbose output
```

### Other Commands
```bash
# Draft data
sportsref-nfl draft --year 2024

# Team rosters
sportsref-nfl rosters --year 2024 --team BUF

# Depth charts
sportsref-nfl depth-charts --year 2024 --team BUF

# Stadium information
sportsref-nfl stadiums

# Name utilities
sportsref-nfl names --normalize "Josh Allen"
sportsref-nfl names --match "Josh Allen" "J. Allen"
```

## ELO Rating System

The library includes an advanced ELO rating system for team strength analysis:

```python
schedule = sr.Schedule(2020, 2024, elo=True)

# ELO data includes:
# - elo_home: Home team ELO rating
# - elo_away: Away team ELO rating  
# - elo_diff: ELO difference (positive favors home team)
# - elo_prob_home: Probability home team wins
# - elo_prob_away: Probability away team wins

elo_data = schedule.schedule[['home_team', 'away_team', 'elo_diff', 'elo_prob_home']]
```

## Error Handling and Retries

The library includes robust error handling:

```python
from sportsref_nfl.core import ScrapingError

try:
    schedule = sr.Schedule(2024, 2024)
except ScrapingError as e:
    print(f"Scraping failed: {e}")
```

## Caching

Data is automatically cached to improve performance:

```python
# First call scrapes from web
schedule1 = sr.Schedule(2024, 2024)

# Second call uses cached data
schedule2 = sr.Schedule(2024, 2024)  # Much faster

# Force refresh
schedule3 = sr.Schedule(2024, 2024, force_refresh=True)
```

## Development

```bash
git clone https://github.com/tefirman/sportsref-nfl.git
cd sportsref-nfl
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pre-commit install

# Run tests
pytest

# Run linting and formatting
ruff check .
ruff format .

# Run type checking
mypy sportsref_nfl --ignore-missing-imports
```

## Dependencies

- `cloudscraper>=1.2.0` - Bypass Cloudflare protection
- `requests>=2.25.0` - HTTP requests
- `beautifulsoup4>=4.9.0` - HTML parsing
- `pandas>=1.3.0` - Data manipulation
- `numpy>=1.20.0` - Numerical computations
- `geopy>=2.1.0` - Geographic calculations

## Rate Limiting

Please be respectful of Pro Football Reference's servers:
- Built-in delays between requests
- Automatic retry with exponential backoff
- Caching to reduce redundant requests

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## Support

- GitHub Issues: https://github.com/tefirman/sportsref-nfl/issues
- Documentation: https://sportsref-nfl.readthedocs.io/
- Email: tefirman@gmail.com