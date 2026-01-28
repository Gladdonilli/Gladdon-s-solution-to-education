# lab_debug - Disastrous Debugging

**Due:** Feb 08, 23:59 PM
**Week:** 2
**Submit:** [PrairieLearn](https://us.prairielearn.com/pl/course_instance/175183/assessment/2506334)

## Learning Objectives

- Practice fundamental debugging skills in C++
- Review the PNG class
- Review pointers, file IO, and reading doxygen

## Resources

| Resource | Link |
|----------|------|
| Handout | [cs225-lab_debug-handout.pdf](./cs225-lab_debug-handout.pdf) |
| Slides | [Google Drive](https://drive.google.com/file/d/1BzwGrOM2ObMf5ts9K_MBlGn-999Km526/view?usp=sharing) |
| Summer 2025 Recording | [MediaSpace (Kendall)](https://mediaspace.illinois.edu/media/t/1_8fx8utln) |
| Fall 2025 Recording | [MediaSpace (Mattox)](https://mediaspace.illinois.edu/media/t/1_ymkimhmb/177553201) |

## Build & Run

```bash
cd lab_debug
mkdir build && cd build
cmake ..
make
cp ../tests/in_01.png in.png
./sketch
```

## Testing

```bash
make test
./test
```

## Debugging Workflow (Agans' 9 Rules)

1. **Understand the System** - Know the task, code structure, control flow
2. **Make it Fail** - Reproduce the bug consistently
3. **Quit Thinking and Look** - Add print statements, instrument code
4. **Divide and Conquer** - Binary search through code to find bug location
5. **Change One Thing at a Time** - Scientific method
6. **Keep an Audit Trail** - Track what you've tried
7. **Check the Plug** - Verify assumptions (Makefile, initialization)
8. **Get a Fresh View** - Explain to someone else
9. **If you didn't fix it, it ain't fixed** - Test thoroughly

## Key Debugging Tool

```cpp
std::cout << "line " << __LINE__ << ": x = " << x << std::endl;
```

## Submit

Upload `sketchify.cpp` to PrairieLearn (remove print statements first!)
