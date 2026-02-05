# mp_stickers - Shocking Stickers

**Due:** Feb 09, 23:59
**Week:** 2-3
**Submit:** [PrairieLearn](https://us.prairielearn.com/pl/course_instance/187789/assessment_instance/10950232)

## Overview

Solo MP exploring image processing in C++ using the HSL color space.

## Goals

- Explore image processing in C++
- Practice using the HSL Color Space
- Learn best practices for memory management and 'The Rule of Three'
- Write your own tests for individual functions

## Parts

### Part 1: Image Class

Subclass of `PNG` with the following transformations:
- `lighten()` / `darken()` - Adjust luminance
- `saturate()` / `desaturate()` - Adjust saturation
- `grayscale()` - Convert to grayscale
- `rotateColor()` - Shift hue
- `illinify()` - Change to Illini Orange (hue 11) or Illini Blue (hue 216)
- `scale()` - Resize image
- `invert()` - Invert colors (flip hue 180°, flip saturation/luminance around 0.5)

### Part 2: StickerSheet Class

Layer stickers on a base image:
- Store base Image at coordinate (0,0)
- Maintain vector of Image pointers with (x,y) positions
- Support adding, removing, repositioning stickers
- Render final composite image

### Part 3: Creative

Create `myImage.png` with at least 3 stickers.

## HSL Color Space

| Component | Description | Range |
|-----------|-------------|-------|
| **Hue (h)** | Color itself (red, blue, etc.) | 0-360° |
| **Saturation (s)** | Color intensity vs gray | 0-100% |
| **Luminance (l)** | Brightness level | 0-100% |

Special hues:
- Illini Orange: 11°
- Illini Blue: 216°

## Build & Run

```bash
cd mp_stickers
mkdir build && cd build
cmake ..
make
```

### Test Part 1 (Image)
```bash
make testimage
./testimage
```

### Test All
```bash
make test
./test
```

### Generate Creative Image
```bash
make
./sticker
```

## Submit

Upload to PrairieLearn:
- `Image.cpp`
- `Image.h`
- `StickerSheet.cpp`
- `StickerSheet.h`

## Reference Images

See this folder for HSL diagrams and example transformations.
