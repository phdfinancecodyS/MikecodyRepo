#!/usr/bin/env python3
"""Download brand fonts for video generation."""
import os
import urllib.request
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

FONTS = {
    "Montserrat-Black.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Black.ttf",
    "Montserrat-Bold.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
    "Montserrat-Regular.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf",
    "Raleway-Regular.ttf": "https://github.com/impallari/Raleway/raw/master/fonts/TTF/Raleway-Regular.ttf",
    "Raleway-Medium.ttf": "https://github.com/impallari/Raleway/raw/master/fonts/TTF/Raleway-Medium.ttf",
}

for name, url in FONTS.items():
    dest = FONTS_DIR / name
    if dest.exists():
        print(f"  Already exists: {name}")
        continue
    print(f"  Downloading {name}...")
    urllib.request.urlretrieve(url, str(dest))

print(f"Fonts ready in {FONTS_DIR}")
print("Files:", [f.name for f in FONTS_DIR.iterdir()])
