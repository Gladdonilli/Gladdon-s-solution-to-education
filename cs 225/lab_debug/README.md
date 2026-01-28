# CS225 Debug Lab

## Overview
**Due**: Feb 08, 23:59 PM
**Assignment**: Disastrous Debugging
**Location**: https://courses.grainger.illinois.edu/cs225/sp2026/labs/debug/
**Repo**: `C:\Users\li859\Documents\Personal-projects\cs225_coursework\mp_debug`

## Learning Objectives
- Practice fundamental debugging skills in C++
- Review (or introduce depending on your MP progress) the PNG class
- Review the fundamentals of pointers, file IO, and reading doxygen

## Setup Instructions

### Git Workflow
```bash
cd "C:\Users\li859\Documents\Personal-projects\cs225_coursework"
git pull --no-edit --no-rebase release main --allow-unrelated-histories
git push
```

### Build Commands
```bash
cd mp_debug
mkdir build
cd build
cmake ..
make
cp ../tests/in_01.png in.png
./sketch
```

## Debugging Workflow (9 Rules)

From: DEBUGGING: The 9 Indispensable Rules for Finding Even the Most Elusive Software and Hardware Problems by David J. Agans

1. **Understand the System** - What the task is, code structure, control flow, library usage
2. **Make it Fail** - Reproduce the bug reliably with a test case
3. **Quit Thinking and Look** - Add print statements, instrument code, check assumptions
4. **Divide and Conquer** - Binary search approach to narrow down bug location
5. **Change One Thing at a Time** - Scientific method: single variable changes
6. **Keep an Audit Trail** - Track what you've tried
7. **Check the Plug** - Verify assumptions (Makefile, initialization, etc.)
8. **Get a Fresh View** - Different perspective, explain to someone
9. **If You Didn't Fix It, It Ain't Fixed** - Test it!

## Bugs to Fix

### Bug 1: Segmentation Fault
- **Symptom**: Program crashes with segfault
- **Cause**: NULL or uninitialized pointer access
- **Debug Approach**: Add `std::cout` statements before and after calls to identify crash location
- **Location**: Between lines 40 and 44 (around `original->readFromFile()`, `width()`, `height()`)

### Bug 2: Second Segfault
- **Symptom**: After fixing first bug, another segfault occurs
- **Debug Approach**: Add print statements at beginning and end of inner for loop
- **Location**: Inner loop processing

### Additional Bugs
- Multiple bugs may be present; use divide and conquer to find each

## Print Statement Template
```cpp
#include <iostream>
std::cout << "Reached line " << __LINE__ << std::endl;
std::cout << "line " << __LINE__ << ": x = " << x << std::endl;
```

**Important**: Remove all print statements before final submission!

## Testing Commands

### Build and Run
```bash
make
cp ../tests/in_01.png in.png
./sketch
```

### Compare Output
```bash
diff out.png ../tests/out_01.png
```

### Visual Comparison (set hue to 280 first)
```bash
compare out.png ../tests/out_01.png comparison.png
```

### Run Autograder Tests
```bash
make test
./test
```

## Submission
- **Files**: `sketchify.cpp`
- **Platform**: PrairieLearn (lab_debug question)

## Additional Resources
- Stack and heap memory note
- Pointers refresher
- Doxygen: https://courses.grainger.illinois.edu/cs225/sp2026/doxygen/

## Personal Notes
- [ ] Bug 1 fixed: Line ___ was causing segfault because ___
- [ ] Bug 2 fixed: Line ___ was causing segfault because ___
- [ ] Testing completed: __/__ test cases passed
- [ ] Final output verified against expected output
