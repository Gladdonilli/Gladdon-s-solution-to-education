"""CLI entry point for Canvas Sync.

Usage:
    python -m canvas_sync          # Launch web UI
    python -m canvas_sync --daemon # Run as background sync daemon
"""

import argparse
import logging
import sys


def main() -> None:
    """Main entry point for canvas_sync CLI."""
    parser = argparse.ArgumentParser(
        prog="canvas_sync",
        description="Sync Canvas LMS data to Obsidian markdown notes",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background sync daemon",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Run daily update (sync all courses + regenerate TODO)",
    )
    parser.add_argument(
        "--docs",
        action="store_true",
        help="Sync course documents only (PDFs, pages, materials)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    args = parser.parse_args()

    if args.version:
        from canvas_sync import __version__

        print(f"canvas-sync {__version__}")
        sys.exit(0)

    if args.docs:
        from canvas_sync.api.auth import ConfigError, get_api_token
        from canvas_sync.sync.documents import sync_all_documents

        try:
            get_api_token(require=True)
        except ConfigError as e:
            logging.error("Config error: %s", e)
            print("Error: Canvas API token not configured. Run the web UI first.")
            sys.exit(1)
        
        print("Syncing course documents...")
        results = sync_all_documents()
        for course, data in results['courses'].items():
            print(f"  {course}: {data['synced']} synced, {data['skipped']} skipped")
        print(f"Total: {results['total_synced']} synced, {results['total_skipped']} skipped")
        sys.exit(0 if not results['errors'] else 1)
    elif args.update:
        from canvas_sync.api.auth import ConfigError, get_api_token
        from canvas_sync.sync.daily_update import run_daily_update

        try:
            get_api_token(require=True)
        except ConfigError as e:
            logging.error("Config error: %s", e)
            print("Error: Canvas API token not configured. Run the web UI first.")
            sys.exit(1)
        
        print("Running daily update...")
        results = run_daily_update()
        print(f"Synced {results['assignments_synced']} assignments, {results['events_synced']} events")
        if results.get('todo_generated'):
            print("TODO.md regenerated")
        sys.exit(0 if not results['errors'] else 1)
    elif args.daemon:
        from canvas_sync.api.auth import ConfigError, get_api_token
        from canvas_sync.scheduler import run_daemon

        try:
            get_api_token(require=True)
        except ConfigError as e:
            logging.error("Config error: %s", e)
            print("Error: Canvas API token not configured. Run the web UI first.")
            sys.exit(1)
        run_daemon()
    else:
        import webbrowser

        from canvas_sync.web.app import create_app

        app = create_app()
        webbrowser.open("http://localhost:5000")
        app.run(port=5000)


if __name__ == "__main__":
    main()
