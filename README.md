# minimal terminal, html, and GUI bytebeat editors

Three bytebeat editors: terminal (curses), browser (single HTML file), and GUI (Pygame). All evaluate RPN expressions with hexadecimal values in real time.

---

## Files

| File | Description |
|------|-------------|
| `eb.py` | Terminal editor (main entry point, run with `bash run`) |
| `eb-44k.py` | Terminal editor variant at 44100 Hz sample rate (t advances at 8000 Hz rate) |
| `eb.html` | Self-contained browser version — open directly, no server needed |
| `eb_gui.py` | Pygame GUI with waveform, phase portrait, bit planes, spectrogram |
| `run-gui` | Shell script to run the GUI (activates venv + installs deps) |
| `help.txt` | Help text displayed by pressing `?` inside the editor |
| `minimal.md` | Bytebeat composition guide (not a developer doc) |
| `bytebeat_presets.txt` | Saved expressions (written by `w` key) |
| `AGENTS.md` | Architecture notes for AI coding assistants |
| `Dockerfile` | Docker image definition |
| `requirements.txt` | Python dependencies |

---

## Install

```sh
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Run

```sh
bash run
```

Or directly:

```sh
python3 eb.py
```

### Docker

```sh
docker build -t bytebeat-app .
docker run -it --rm \
    --device /dev/snd \
    -e TERM=$TERM \
    bytebeat-app
```

*Mount a volume (`-v`) if you want to keep `bytebeat_presets.txt`.*

---

## Keybindings (terminal editors)

| Key | Action |
|-----|--------|
| `h` / `l` | Move cursor left / right |
| `j` / `k` | Decrement / increment hex digit or operator at cursor |
| `<` / `>` | Insert `<<` / `>>` at cursor |
| `x` | Delete character or operator at cursor |
| `Backspace` | Delete character to the left of cursor |
| `u` | Undo last edit |
| `w` | Save expression to `bytebeat_presets.txt` |
| `$` | Toggle cursor to start / end of expression |
| `r` | Reset time variable `t` to 0 |
| `s` | Toggle signed/unsigned arithmetic mode |
| `:` | Open preset browser (type to filter, ↑/↓ to navigate, Enter to load) |
| `?` | Open help screen |
| `q` | Quit |

### Arithmetic mode

Press `s` to toggle between unsigned (default) and signed 32-bit arithmetic:

| Mode | `*` behavior | `%` behavior |
|------|-------------|-------------|
| Unsigned | masks to 0..2³²-1 | always 0..divisor-1 (Python-style) |
| Signed | wraps at 2³¹ (like JS `Math.imul`) | preserves sign of dividend (JS-style) |

Signed mode creates percussive accents on overflow, useful for rhythmic effects.
The indicator **SIGNED** appears at the top of the terminal when active.

Characters `0-9 a-f`, `t`, operators, and space are inserted at cursor position.

---

## Expression format

Expressions are written in **Reverse Polish Notation (RPN)** with hexadecimal values.

- **Values**: hex digits `0`–`f` pushed onto the stack
- **`t`**: time variable, auto-incremented each sample
- **Operators**: pop two values from the stack and push the result

The final value on the stack (`& 0xFF`) is output as a sample (0–255).

### Operators

| Op | Action |
|----|--------|
| `&` | Bitwise AND |
| `\|` | Bitwise OR |
| `^` | Bitwise XOR |
| `+` | Addition |
| `-` | Subtraction |
| `*` | Multiplication |
| `/` | Integer division |
| `%` | Modulo |
| `<<` | Left shift |
| `>>` | Right shift |

### Examples

```
t 1 &           → t & 1
t 2 * 1 &       → low bit of (t * 2)
t t * 8 &       → t² & 8
t 1 + t 3 + *   → (t+1) × (t+3)
t 9C | B3 %     → OR-shape truncated by modulo
```

---

## Browser version

Open `eb.html` in any browser. No server or build step required. It has a virtual keyboard for mobile use.

---

## Pygame GUI

Requires `pygame`, `numpy`, and `sounddevice` (install with `pip install -r requirements.txt`).

```sh
bash run-gui                    # all panels at 8000 Hz
python3 eb_gui.py               # same
python3 eb_gui.py --rate 44100  # 44.1 kHz output
python3 eb_gui.py --no-spectrogram   # hide spectrogram
python3 eb_gui.py --no-waveform --no-bits  # phase + spectrogram only
```

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--rate N` | 8000 | Sample rate in Hz |
| `--no-waveform` | off | Hide waveform panel |
| `--no-phase` | off | Hide phase portrait |
| `--no-bits` | off | Hide bit planes |
| `--no-spectrogram` | off | Hide spectrogram |

### Layout

2×2 grid of visualization panels with a large expression bar (36 px font, 80 px tall) in the middle:

- **Waveform** (top-left) — polyline with guide lines at 0x00 / 0x80 / 0xFF.
- **Bit planes** (top-right) — 8 horizontal strips showing bits 0–7 of recent samples.
- **Phase portrait** (bottom-left) — 80×24 density grid with sqrt scaling and 0.95 decay, upscaled to panel size.
- **Spectrogram** (bottom-right) — scrolling 256-point FFT (Hann window, per-column normalization, sqrt enhancement) as grayscale.

Expression bar shows the current RPN buffer in a large monospace font with cursor highlighting. The **SIGNED** indicator appears to the left when signed mode is active.

### Keybindings

Same vim-like keys as the terminal version (`h`/`l`/`j`/`k`/`x`/`u`/`w`/`r`/`s`/`q`/`<`/`>` / `:` / `?` / `$`). Arrow keys also move the cursor. `F1` opens help. `Esc` opens the preset browser.

- `:` — fuzzy-find presets from `bytebeat_presets.txt` (type to filter, ↑/↓ to select, Enter to load, Esc to cancel)
- `?` / `F1` — help overlay

---

## Tips

- Press `:` to browse and load saved expressions.
- Use `r` to restart the time counter when experimenting.
- See `minimal.md` for bytebeat composition techniques.
