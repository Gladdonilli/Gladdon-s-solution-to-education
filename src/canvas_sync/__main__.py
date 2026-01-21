"""CLI entry point for Canvas Sync.

Usage:
    python -m canvas_sync          # Launch web UI
    python -m canvas_sync --daemon # Run as background sync daemon
"""

import argparse
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
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    args = parser.parse_args()

    if args.version:
        from canvas_sync import __version__

        print(f"canvas-sync {__version__}")
        sys.exit(0)

    if args.daemon:
        from canvas_sync.api.auth import ConfigError, get_api_token
        from canvas_sync.scheduler import run_daemon

        try:
            get_api_token(require=True)
        except ConfigError as e:
            print(f"Error: {e}")
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
