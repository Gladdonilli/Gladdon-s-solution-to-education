# mp_stickers Repository Location

The actual CS 225 coursework repository is located at:

```
C:\Users\li859\Documents\Personal-projects\cs225_coursework
```

## Remote Configuration

| Remote | URL |
|--------|-----|
| origin | https://github.com/illinois-cs-coursework/sp26_cs225_tianyi35.git |
| release | https://github.com/illinois-cs-coursework/sp26_cs225_.release.git |

## Commands

```bash
# Navigate to repo
cd "C:\Users\li859\Documents\Personal-projects\cs225_coursework"

# Pull new assignments
jj git fetch --remote release
jj new main@release -m "Merge new assignments"

# Build mp_stickers
cd mp_stickers
mkdir build && cd build
cmake ..
make
```
