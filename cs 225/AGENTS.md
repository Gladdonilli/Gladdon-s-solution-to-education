# CS 225 - Data Structures

**Semester:** Spring 2026
**Course Site:** https://courses.grainger.illinois.edu/cs225/sp2026/
**PrairieLearn:** For assignments/tests (separate from Canvas)
**Last Updated:** Jan 29, 2026

## Code Style Rules

**comments vibe:** no caps unless absolutely necessary, discord style casual talking. no overly formal explanations. keep it chill but correct.

```cpp
// good examples:
// the workhorse constructor - does the heavy lifting
// nothing to do here lol
// member initializer list did all the work

// bad examples:
// FIX 1: Changed -1 to valid hue (280 = purple)
// This constructor initializes all member variables.
```

**general rules:**
- make solutions fun/creative when possible
- no ai-style comments like "// FIX 1:" or "// TODO:"
- keep original doxygen from starter code
- code should look like natural student work

## Structure

```
cs 225/
├── lectures/
│   ├── week01/     # Intro, C++ Review
│   └── week02/     # List ADT, Linked Lists
├── labs/
│   └── lab_debug/  # debugging lab
├── mps/
│   └── mp_stickers/  # sticker sheet mp
└── AGENTS.md       # this file
```

## Coursework Repository

**Location:** `C:\Users\li859\Documents\Personal-projects\cs225_coursework`

| Remote  | URL                                                            |
|---------|----------------------------------------------------------------|
| origin  | https://github.com/illinois-cs-coursework/sp26_cs225_tianyi35  |
| release | https://github.com/illinois-cs-coursework/sp26_cs225_.release  |

### Pull New Assignments

```bash
cd "C:\Users\li859\Documents\Personal-projects\cs225_coursework"
jj git fetch --remote release
jj new main@release -m "Merge new assignments"
```

## Current Assignments

| Type | Assignment   | Due Date       | Status      |
|------|--------------|----------------|-------------|
| Lab  | lab_debug    | Feb 08, 23:59  | ✅ Done     |
| MP   | mp_stickers  | Feb 09, 23:59  | 🟡 Active   |
| POTD | POTD0-9      | Feb 03, 23:59  | 🟡 In Progress |

## Docker Dev Environment

```bash
# in cs225_coursework folder
docker build -t cs225 .
docker run -it -v "$(pwd):/workspaces/cs225_coursework" cs225
```

## Build Commands

```bash
mkdir build && cd build
cmake ..
make
./main  # or ./test or ./sketch depending on assignment
```

## Important Links

| Resource            | URL                                                                 |
|---------------------|---------------------------------------------------------------------|
| Course Site         | https://courses.grainger.illinois.edu/cs225/sp2026/                 |
| PrairieLearn        | https://us.prairielearn.com/pl/course_instance/202144               |
| CBTF Registration   | https://us.prairietest.com/                                         |
