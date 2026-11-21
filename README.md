# The World in One Day — Saturday 21 November 2026

[![make.fun](https://img.shields.io/badge/make.fun-news--image--20261121-blue)](https://make.fun/bounty/news-image-20261121)

An editorial news infographic summing up the world's news for Saturday,
21 November 2026: 40 stories across 8 regions, with a world map, a numbered
index and a date check. `main.py` (Python 3.13, standard library only) draws
the whole image and writes it to `/output/entry.png` (1024x1024 PNG).

## Run it

```sh
python3 main.py
```

Deterministic: two runs write byte-identical PNGs. No network access.

## How it works

- Glyph bitmaps for the Liberation fonts are packed in `fontdata.bin`
  (generated at build-prep time from the system fonts); `main.py` reads the
  binary at runtime and rebuilds the font tables in memory.
- All stories, figures and dates were verified against news sources on
  21 November 2026. Stories that belong to Friday 20 November are listed in
  the image's DATE CHECK section, not shown as Saturday's news.

## License

MIT — see [LICENSE](LICENSE).
