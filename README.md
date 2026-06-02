# minimal terminal and html bytebeat editors

Two standalone bytebeat editors: one for the terminal (curses) and one for the browser (single HTML file). Both evaluate RPN expressions with hexadecimal values in real time.

---

## Files

| File | Description |
|------|-------------|
| `eb.py` | Terminal editor (main entry point, run with `bash run`) |
| `eb-44k.py` | Terminal editor variant at 44100 Hz sample rate (t advances at 8000 Hz rate) |
| `eb.html` | Self-contained browser version — open directly, no server needed |
| `help.txt` | Help text displayed by pressing `?` inside the editor |
| `minimal.md` | Bytebeat composition guide (not a developer doc) |
| `bytebeat_presets.txt` | Saved expressions (written by `w` key) |
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

## Tips

- Press `:` to browse and load saved expressions.
- Use `r` to restart the time counter when experimenting.
- See `minimal.md` for bytebeat composition techniques.
