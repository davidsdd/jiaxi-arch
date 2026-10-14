# Changelog

## 26.10.13.1 — 2026-10-13

- Resize and redraw the WebGL buffer in the same animation frame, coalescing notifications and preserving scale and framing without blank resize flashes.
- Allow rotation down to an exact horizontal view, with bounded screen-aligned pan, pointer-anchored zoom and a grounded orbit pivot at low angles.
- Export the current viewport dimensions and keep local Finder metadata ignored without deleting files.
