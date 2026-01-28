@echo off
REM Canvas Sync Startup Script
REM Runs daily update and opens TODO.md in Obsidian

cd /d "C:\Users\li859\Documents\Personal-projects\canvas-obsidian-sync"

REM Run daily update (sync all courses + regenerate TODO)
python -m canvas_sync --update

REM Open TODO.md in Obsidian
REM Uses obsidian:// URI protocol to open the file in the vault
start "" "obsidian://open?vault=Project-obsidian-vault&file=UIUC%%20education%%2FTODO"

exit
