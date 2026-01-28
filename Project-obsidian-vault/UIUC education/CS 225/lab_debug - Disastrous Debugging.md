---
type: assignment
course: CS 225
course_id: cs225-sp2026
assignment_type: lab
name: lab_debug
title: Disastrous Debugging
due: 2026-02-08T23:59:00
status: pending
priority: high
url: https://courses.grainger.illinois.edu/cs225/sp2026/labs/debug/
synced_at: 2026-02-02T13:55:00
---

# lab_debug - Disastrous Debugging

## Details

- **Due**: February 08, 2026 at 11:59 PM
- **Type**: Lab
- **Priority**: HIGH

## Description

Lab covers C++ debugging skills, PNG class, pointers, file IO, and doxygen.

### Learning Objectives
- Debugging workflow (9 rules from Agans)
- Print statement debugging
- Understanding system, making it fail
- Quit thinking and look
- Divide and conquer
- Change one thing at a time
- Keep audit trail
- Check the plug
- Get fresh view
- If you didn't fix it, it ain't fixed

### Known Bugs to Fix
- `sketchify.cpp`: Segfault from NULL/uninitialized pointer
- `sketchify.cpp` line 33: Color hue placeholder

### Build & Test
```bash
git pull
mkdir build && cd build
cmake ..
make
./sketch
diff/compare for output verification
```

### Submission
PrairieLearn submission required.

[Open Assignment](https://courses.grainger.illinois.edu/cs225/sp2026/labs/debug/)
