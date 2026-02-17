#!/usr/bin/env python
"""
Sports Reference NFL Data CLI

Command-line interface for the sportsref_nfl package.
"""

import argparse
import sys

import pandas as pd

from . import Boxscore, Schedule
from .cache import cache_info, clear_cache
from .data import depth_charts, draft, rosters, stadiums, stats


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the CLI interface.

    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="NFL Data Scraper and Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sportsref-nfl schedule --start-year 2020 --end-year 2024 --elo
  sportsref-nfl boxscore --game-id "202401070buf"
  sportsref-nfl stats --year 2024 --position QB
  sportsref-nfl draft --year 2024
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Schedule command
    schedule_parser = subparsers.add_parser(
        "schedule", help="Download NFL schedule data"
    )
    schedule_parser.add_argument(
        "--start-year", type=int, required=True, help="Start year for schedule"
    )
    schedule_parser.add_argument(
        "--end-year", type=int, required=True, help="End year for schedule"
    )
    schedule_parser.add_argument(
        "--elo", action="store_true", help="Include ELO calculations"
    )
    schedule_parser.add_argument(
        "--playoffs", action="store_true", help="Include playoff games"
    )
    schedule_parser.add_argument("--output", type=str, help="Output CSV file path")

    # Boxscore command
    boxscore_parser = subparsers.add_parser(
        "boxscore", help="Get boxscore data for a specific game"
    )
    boxscore_parser.add_argument(
        "--game-id", type=str, required=True, help="Game ID (e.g., 202401070buf)"
    )
    boxscore_parser.add_argument("--output", type=str, help="Output CSV file path")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Download player statistics")
    stats_parser.add_argument("--year", type=int, required=True, help="Season year")
    stats_parser.add_argument(
        "--position",
        type=str,
        choices=["QB", "RB", "WR", "TE", "K", "DST"],
        help="Position to filter by",
    )
    stats_parser.add_argument("--output", type=str, help="Output CSV file path")

    # Draft command
    draft_parser = subparsers.add_parser("draft", help="Download NFL draft data")
    draft_parser.add_argument("--year", type=int, required=True, help="Draft year")
    draft_parser.add_argument("--output", type=str, help="Output CSV file path")

    # Rosters command
    roster_parser = subparsers.add_parser("rosters", help="Download team rosters")
    roster_parser.add_argument("--year", type=int, required=True, help="Season year")
    roster_parser.add_argument("--team", type=str, help="Specific team abbreviation")
    roster_parser.add_argument("--output", type=str, help="Output CSV file path")

    # Depth charts command
    depth_parser = subparsers.add_parser(
        "depth-charts", help="Download team depth charts"
    )
    depth_parser.add_argument("--year", type=int, required=True, help="Season year")
    depth_parser.add_argument("--team", type=str, help="Specific team abbreviation")
    depth_parser.add_argument("--output", type=str, help="Output CSV file path")

    # Stadiums command
    stadium_parser = subparsers.add_parser(
        "stadiums", help="Download stadium information"
    )
    stadium_parser.add_argument("--output", type=str, help="Output CSV file path")

    # Name utilities command
    names_parser = subparsers.add_parser("names", help="Player name utilities")
    names_parser.add_argument("--normalize", type=str, help="Normalize a player name")
    names_parser.add_argument(
        "--match",
        type=str,
        nargs=2,
        metavar=("NAME1", "NAME2"),
        help="Check if two names match",
    )

    # FlareSolverr management command
    flaresolverr_parser = subparsers.add_parser(
        "flaresolverr", help="Manage FlareSolverr (Cloudflare bypass)"
    )
    flaresolverr_parser.add_argument(
        "action",
        choices=["start", "stop", "status"],
        help="Action to perform",
    )

    # Cache management commands
    cache_parser = subparsers.add_parser("cache", help="Cache management")
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_command", help="Cache commands"
    )

    # Cache info
    cache_subparsers.add_parser("info", help="Show cache information")

    # Cache clear
    cache_clear_parser = cache_subparsers.add_parser("clear", help="Clear cache")
    cache_clear_parser.add_argument(
        "--type",
        choices=["historical", "current_season", "live_season", "draft", "stadiums"],
        help="Cache type to clear (default: all)",
    )

    # Global options
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--version", action="version", version=f"sportsref-nfl {get_version()}"
    )

    return parser


def get_version() -> str:
    """Get the package version."""
    try:
        from . import __version__

        return __version__
    except ImportError:
        return "unknown"


def handle_schedule_command(args: argparse.Namespace) -> None:
    """Handle the schedule command."""
    if args.verbose:
        print(f"Loading NFL schedule from {args.start_year} to {args.end_year}...")

    schedule = Schedule(
        start=args.start_year,
        finish=args.end_year,
        playoffs=args.playoffs,
        elo=args.elo,
    )

    output_path = args.output or f"nfl_schedule_{args.start_year}_{args.end_year}.csv"
    schedule.schedule.to_csv(output_path, index=False)

    print(f"Schedule data saved to: {output_path}")
    print(f"Total games: {len(schedule.schedule)}")

    if args.elo:
        print("ELO calculations included")


def handle_boxscore_command(args: argparse.Namespace) -> None:
    """Handle the boxscore command."""
    if args.verbose:
        print(f"Loading boxscore for game: {args.game_id}")

    try:
        boxscore = Boxscore(args.game_id)

        # Create a summary DataFrame
        summary_data = {
            "game_id": [args.game_id],
            "season": [boxscore.season],
            "week": [boxscore.week],
            "away_team": [boxscore.team2_abbrev],
            "home_team": [boxscore.team1_abbrev],
            "away_score": [boxscore.team2_score],
            "home_score": [boxscore.team1_score],
        }
        summary_df = pd.DataFrame(summary_data)

        output_path = args.output or f"boxscore_{args.game_id}.csv"
        summary_df.to_csv(output_path, index=False)

        print(f"Boxscore data saved to: {output_path}")
        print(f"Game: {boxscore.team2_abbrev} @ {boxscore.team1_abbrev}")
        print(f"Score: {boxscore.team2_score} - {boxscore.team1_score}")

    except Exception as e:
        print(f"Error loading boxscore: {e}")
        sys.exit(1)


def handle_stats_command(args: argparse.Namespace) -> None:
    """Handle the stats command."""
    if args.verbose:
        print(f"Loading {args.year} player statistics...")

    try:
        # First create a schedule to get game data
        if args.verbose:
            print("Creating schedule to identify games...")
        schedule = Schedule(start=args.year, finish=args.year, playoffs=True, elo=False)

        # Use the actual get_bulk_stats function with schedule data
        stats_df = stats.get_bulk_stats(
            start_season=args.year,
            start_week=1,
            finish_season=args.year,
            finish_week=18,
            playoffs=True,
            schedule_data=schedule.schedule,
        )

        # Filter by position if specified
        if args.position and "position" in stats_df.columns:
            stats_df = stats_df[stats_df["position"] == args.position]
            output_suffix = f"_{args.position.lower()}"
        else:
            output_suffix = "_all"

        output_path = args.output or f"nfl_stats_{args.year}{output_suffix}.csv"
        stats_df.to_csv(output_path, index=False)

        print(f"Stats data saved to: {output_path}")
        print(f"Total players: {len(stats_df)}")

    except Exception as e:
        print(f"Error loading stats: {e}")
        sys.exit(1)


def handle_draft_command(args: argparse.Namespace) -> None:
    """Handle the draft command."""
    if args.verbose:
        print(f"Loading {args.year} NFL draft data...")

    try:
        draft_df = draft.get_draft(args.year)

        output_path = args.output or f"nfl_draft_{args.year}.csv"
        draft_df.to_csv(output_path, index=False)

        print(f"Draft data saved to: {output_path}")
        print(f"Total picks: {len(draft_df)}")

    except Exception as e:
        print(f"Error loading draft data: {e}")
        sys.exit(1)


def handle_rosters_command(args: argparse.Namespace) -> None:
    """Handle the rosters command."""
    if args.verbose:
        print(f"Loading {args.year} team rosters...")

    try:
        if args.team:
            roster_df = rosters.get_roster(args.team, args.year)
            output_suffix = f"_{args.team.lower()}"
        else:
            roster_df = rosters.get_bulk_rosters(args.year, args.year)
            output_suffix = "_all"

        output_path = args.output or f"nfl_rosters_{args.year}{output_suffix}.csv"
        roster_df.to_csv(output_path, index=False)

        print(f"Roster data saved to: {output_path}")
        print(f"Total players: {len(roster_df)}")

    except Exception as e:
        print(f"Error loading roster data: {e}")
        sys.exit(1)


def handle_depth_charts_command(args: argparse.Namespace) -> None:
    """Handle the depth charts command."""
    if args.verbose:
        print(f"Loading {args.year} depth charts...")

    try:
        if args.team:
            depth_df = depth_charts.get_depth_chart(args.team)
            output_suffix = f"_{args.team.lower()}"
        else:
            depth_df = depth_charts.get_all_depth_charts()
            output_suffix = "_all"

        output_path = args.output or f"nfl_depth_charts_{args.year}{output_suffix}.csv"
        depth_df.to_csv(output_path, index=False)

        print(f"Depth chart data saved to: {output_path}")
        print(f"Total entries: {len(depth_df)}")

    except Exception as e:
        print(f"Error loading depth chart data: {e}")
        sys.exit(1)


def handle_stadiums_command(args: argparse.Namespace) -> None:
    """Handle the stadiums command."""
    if args.verbose:
        print("Loading stadium information...")

    try:
        stadium_df = stadiums.get_stadiums()

        output_path = args.output or "nfl_stadiums.csv"
        stadium_df.to_csv(output_path, index=False)

        print(f"Stadium data saved to: {output_path}")
        print(f"Total stadiums: {len(stadium_df)}")

    except Exception as e:
        print(f"Error loading stadium data: {e}")
        sys.exit(1)


def handle_names_command(args: argparse.Namespace) -> None:
    """Handle the names command."""
    if args.normalize:
        # Simple normalization - just lowercase and strip
        normalized = args.normalize.lower().strip()
        print(f"Original: {args.normalize}")
        print(f"Normalized: {normalized}")

    elif args.match:
        name1, name2 = args.match
        # Simple comparison for now
        is_match = name1.lower().strip() == name2.lower().strip()
        print(f"Name 1: {name1}")
        print(f"Name 2: {name2}")
        print(f"Match: {'Yes' if is_match else 'No'}")

    else:
        print("Please specify --normalize or --match option")


def handle_flaresolverr_command(args: argparse.Namespace) -> None:
    """Handle the flaresolverr command."""
    import shutil
    import subprocess

    import requests as req

    container_name = "flaresolverr"
    image = "flaresolverr/flaresolverr:latest"

    if args.action == "status":
        try:
            resp = req.get("http://localhost:8191/", timeout=3)
            if resp.ok:
                data = resp.json()
                print(f"✅ FlareSolverr is running (v{data.get('version', '?')})")
            else:
                print("⚠️  FlareSolverr responded but may not be healthy")
        except req.exceptions.ConnectionError:
            print("❌ FlareSolverr is not running")
            if shutil.which("docker"):
                print("   Start it with: sportsref-nfl flaresolverr start")
            else:
                print("   Docker is not installed. Install Docker first.")

    elif args.action == "start":
        if shutil.which("docker") is None:
            print("❌ Docker is not installed. Install Docker from https://docker.com")
            sys.exit(1)

        from .core.scraper import ensure_flaresolverr

        if ensure_flaresolverr():
            print("✅ FlareSolverr is running and ready")
        else:
            print("❌ Failed to start FlareSolverr")
            print(
                f"   Try manually: docker run -d --name {container_name} -p 8191:8191 {image}"
            )
            sys.exit(1)

    elif args.action == "stop":
        if shutil.which("docker") is None:
            print("❌ Docker is not installed")
            sys.exit(1)
        try:
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                check=True,
            )
            print("✅ FlareSolverr stopped")
        except subprocess.CalledProcessError:
            print("⚠️  FlareSolverr container not found or already stopped")


def handle_cache_command(args: argparse.Namespace) -> None:
    """Handle the cache command."""
    if args.cache_command == "info":
        info = cache_info()
        print("📁 Cache Information")
        print("=" * 20)
        print(f"Cache directory: {info['cache_dir']}")
        print(f"Total files: {info['total_files']}")
        print(f"Total size: {info['size_mb']} MB")
        print(f"Expired files: {info['expired']}")
        print()
        print("Files by type:")
        for cache_type, count in info["by_type"].items():
            print(f"  {cache_type}: {count}")

    elif args.cache_command == "clear":
        cache_type = getattr(args, "type", None)
        cleared = clear_cache(cache_type)
        if cache_type:
            print(f"Cleared {cleared} {cache_type} cache files")
        else:
            print(f"Cleared {cleared} cache files")

    else:
        print("Please specify a cache subcommand: info or clear")


def main() -> None:
    """
    Main entry point for the sportsref-nfl CLI.
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        print("NFL Data Scraper and Analysis Tool")
        print("=" * 35)

    try:
        # Route to appropriate command handler
        if args.command == "schedule":
            handle_schedule_command(args)
        elif args.command == "boxscore":
            handle_boxscore_command(args)
        elif args.command == "stats":
            handle_stats_command(args)
        elif args.command == "draft":
            handle_draft_command(args)
        elif args.command == "rosters":
            handle_rosters_command(args)
        elif args.command == "depth-charts":
            handle_depth_charts_command(args)
        elif args.command == "stadiums":
            handle_stadiums_command(args)
        elif args.command == "names":
            handle_names_command(args)
        elif args.command == "flaresolverr":
            handle_flaresolverr_command(args)
        elif args.command == "cache":
            handle_cache_command(args)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
