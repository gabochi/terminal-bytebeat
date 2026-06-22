import curses
import re

import editor


def draw_expression(stdscr, buf, cursor, signed_mode, y=0, x_offset=2):
    if signed_mode:
        stdscr.addstr(y, 0, "SIGNED", curses.A_BOLD)

    tokens = re.split(r'(<<|>>|[\s\&\|\^\+\-\/\*\%t\,])', buf)
    curr_x = x_offset
    char_count = 0

    for token in tokens:
        if not token:
            continue
        for ch in token:
            is_cursor = (char_count == cursor)
            style = curses.A_BOLD if (token in editor.OPERATORS or token == 't') else curses.A_NORMAL
            if is_cursor:
                stdscr.addstr(y, curr_x, ch, style | curses.A_REVERSE)
            else:
                stdscr.addstr(y, curr_x, ch, style)
            curr_x += 1
            char_count += 1

    if cursor >= len(buf):
        stdscr.addstr(y, curr_x, " ", curses.A_REVERSE)


def draw_cascade(stdscr, log_t, log_o, y=1):
    if not log_t or not log_o:
        return
    parts = []
    for t, o in zip(log_t[:3], log_o[:3]):
        t_hex = t[4:12]
        o_hex = o[5:7]
        parts.append(f"{t_hex}:{o_hex}")
    stdscr.addstr(y, 2, "  ".join(parts), curses.A_DIM)


class PhasePortrait:
    CHARS = " .-:=+*#%@"

    def __init__(self, width=40, decay=0.92):
        self.width = width
        self.decay = decay
        self.grid = None
        self.height = 0

    def _resize(self, height):
        if self.grid is None or len(self.grid) != height:
            self.grid = [[0.0] * self.width for _ in range(height)]
            self.height = height

    def render(self, stdscr, x_start, y_start, samples, height=10):
        self._resize(height)

        for y in range(self.height):
            for x in range(self.width):
                self.grid[y][x] *= self.decay

        for i in range(len(samples) - 1):
            gx = int(samples[i]) * self.width // 256
            gy = int(samples[i + 1]) * self.height // 256
            gy = self.height - 1 - gy
            if gx >= self.width:
                gx = self.width - 1
            if gy >= self.height:
                gy = self.height - 1
            self.grid[gy][gx] += 1.0

        max_val = max(max(row) for row in self.grid) or 1.0
        n_chars = len(self.CHARS) - 1

        for y in range(self.height):
            for x in range(self.width):
                d = int(self.grid[y][x] * n_chars / max_val)
                if d > n_chars:
                    d = n_chars
                try:
                    stdscr.addch(y_start + y, x_start + x, self.CHARS[d])
                except Exception:
                    pass


class BitPlanes:
    def __init__(self, width=48):
        self.width = width

    def render(self, stdscr, x_start, y_start, samples, height=8):
        recent = list(samples)[-self.width:]
        for i in range(height):
            bit = 7 - i
            y = y_start + i
            try:
                stdscr.addstr(y, x_start, f"{bit}")
            except Exception:
                pass
            for col, val in enumerate(recent):
                try:
                    ch = chr(0x2588) if (int(val) >> bit) & 1 else ' '
                    stdscr.addch(y, x_start + 2 + col, ch)
                except Exception:
                    pass


class Waveform:
    BLOCKS = [' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

    def __init__(self, width=64):
        self.width = width

    def render(self, stdscr, x_start, y_start, samples, height=4):
        if not samples:
            return 0, 0

        step = max(1, len(samples) // self.width)
        display = list(samples)[::step][:self.width]

        LEVELS = height * 8

        for col, v in enumerate(display):
            level = int(v) * (LEVELS - 1) // 255
            for row in range(height):
                threshold_min = (height - 1 - row) * 8
                local = level - threshold_min
                if local < 0:
                    ch = ' '
                elif local >= 8:
                    ch = chr(0x2588)
                else:
                    ch = self.BLOCKS[local]
                try:
                    stdscr.addch(y_start + row, x_start + col, ch)
                except Exception:
                    pass

        return min(int(v) for v in display), max(int(v) for v in display)
