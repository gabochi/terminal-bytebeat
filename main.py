import curses
import numpy as np
import sounddevice as sd
import time
import copy
import string
from collections import deque

# --- Configuración 2026 ---
SAMPLE_RATE = 8000
BUFFER_SIZE = 1024
HEX_CHARS = "0123456789ABCDEF"
SAVE_FILE = "bytebeat_saves.txt"

OP_MAP = {'+': '+', '-': '-', '*': '*', '/': '/', '%': '%',
          '&': '&', '|': '|', '^': '^', '<': '<<', '>': '>>', 't': 't'}
OPERATORS = list(OP_MAP.values())


class RPNEngine:

    def __init__(self):
        self.tokens = ["t"]
        self.active_tokens = ["t"]
        self.t = 0
        self.history = []
        self.last_samples = np.zeros(60)
        self.last_val = 0
        self.cascade = deque(maxlen=12)
        self.paused = False

    def save_state(self):
        self.history.append(copy.deepcopy(self.tokens))
        if len(self.history) > 50:
            self.history.pop(0)

    def undo(self):
        if self.history:
            self.tokens = self.history.pop()

    def eval_rpn(self, t_val):
        stack = []
        # Evalúa siempre los active_tokens (los últimos confirmados)
        for token in self.active_tokens:
            try:
                if token == "t":
                    stack.append(t_val)
                elif token in OPERATORS:
                    if len(stack) < 2:
                        continue
                    b = stack.pop()
                    a = stack.pop()
                    if token == "+":
                        stack.append(a + b)
                    elif token == "-":
                        stack.append(a - b)
                    elif token == "*":
                        stack.append(a * b)
                    elif token == "/":
                        stack.append(a // (b or 1))
                    elif token == "%":
                        stack.append(a % (b or 1))
                    elif token == "&":
                        stack.append(a & b)
                    elif token == "|":
                        stack.append(a | b)
                    elif token == "^":
                        stack.append(a ^ b)
                    elif token == ">>":
                        stack.append(a >> (b % 32))
                    elif token == "<<":
                        stack.append(a << (b % 32))
                else:
                    stack.append(int(token, 16))
            except:
                continue
        return int(stack[-1]) & 255 if stack else 0

    def callback(self, outdata, frames, time, status):
        t_range = np.arange(self.t, self.t + frames) & 0xFFFFFFFF
        vfunc = np.vectorize(self.eval_rpn)
        samples_uint8 = vfunc(t_range).astype(np.uint8)
        self.last_samples = samples_uint8[:60]
        # Corrección del error: indexar el primer elemento
        self.last_val = int(samples_uint8[0])
        outdata[:, 0] = (samples_uint8.astype(np.float32) / 127.5) - 1.0
        self.t = (self.t + frames) & 0xFFFFFFFF


def main(stdscr):
    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    engine = RPNEngine()
    t_idx = 0
    c_idx = 0
    sr = 8000

    with sd.OutputStream(channels=1, samplerate=sr, callback=engine.callback):
        while True:
            # Actualiza audio solo si NO está pausado
            if not engine.paused:
                engine.active_tokens = copy.deepcopy(engine.tokens)

            stdscr.erase()
            curr_x = 2
            cursor_pos_x = 2
            for i, token in enumerate(engine.tokens):
                for char_pos, char in enumerate(token):
                    if i == t_idx and char_pos == c_idx:
                        attr = curses.A_REVERSE | curses.A_BOLD
                        cursor_pos_x = curr_x
                    else:
                        attr = curses.A_NORMAL
                    stdscr.addstr(1, curr_x, char, attr)
                    curr_x += 1
                curr_x += 2
            stdscr.move(1, cursor_pos_x)

            engine.cascade.appendleft((engine.t, engine.last_val))
            for i, (ct, cv) in enumerate(engine.cascade):
                try:
                    attr = curses.A_BOLD if i == 0 else curses.A_DIM
                    stdscr.addstr(4 + i, 2, f"{ct:08X} {cv:02X}", attr)
                except:
                    pass

            scope_x_start = 15
            scope_height = 12
            for x, val_255 in enumerate(engine.last_samples):
                y_norm = val_255 / 255.0
                y_pos = scope_height - 1 - int(y_norm * (scope_height - 1))
                try:
                    stdscr.addch(4 + y_pos, scope_x_start + x, "█")
                except:
                    pass

            if engine.paused:
                stdscr.addstr(0, 2, "[!]", curses.A_BOLD)

            stdscr.refresh()
            try:
                key = stdscr.getkey()
            except:
                key = ""

            if key == 'q':
                break
            elif key == '!':
                engine.paused = not engine.paused
            elif key == 'w':
                # Guardar expresión
                with open(SAVE_FILE, "a") as f:
                    f.write(" ".join(engine.tokens) + "\n")
            elif key == 'W':
                # Ir al comienzo del siguiente término
                if t_idx < len(engine.tokens) - 1:
                    t_idx += 1
                    c_idx = 0
            elif key == 'E':
                # Ir al final del término
                if c_idx == len(engine.tokens[t_idx]) - 1:
                    if t_idx < len(engine.tokens) - 1:
                        t_idx += 1
                c_idx = len(engine.tokens[t_idx]) - 1
            elif key == 'B':
                # Como E hacia atrás
                if c_idx == 0:
                    if t_idx > 0:
                        t_idx -= 1
                c_idx = 0
            elif key == '$':
                t_idx = len(engine.tokens) - 1
                c_idx = len(engine.tokens[t_idx]) - 1
            elif key in ['KEY_LEFT', 'h']:
                if c_idx > 0:
                    c_idx -= 1
                elif t_idx > 0:
                    t_idx -= 1
                    c_idx = len(engine.tokens[t_idx]) - 1
            elif key in ['KEY_RIGHT', 'l']:
                if c_idx < len(engine.tokens[t_idx]) - 1:
                    c_idx += 1
                elif t_idx < len(engine.tokens) - 1:
                    t_idx += 1
                    c_idx = 0
            elif key in ['KEY_UP', 'k', 'KEY_DOWN', 'j']:
                engine.save_state()
                token = engine.tokens[t_idx]
                delta = 1 if key in ['KEY_UP', 'k'] else -1
                if token in OPERATORS:
                    idx = OPERATORS.index(token)
                    engine.tokens[t_idx] = OPERATORS[(idx + delta) % len(OPERATORS)]
                    c_idx = 0
                else:
                    char = token[c_idx]
                    v_h = HEX_CHARS.find(char.upper())
                    n_c = HEX_CHARS[(v_h + delta) % 16]
                    l_t = list(token)
                    l_t[c_idx] = n_c
                    engine.tokens[t_idx] = "".join(l_t)
            elif key == 'u':
                engine.undo()
                t_idx = min(t_idx, len(engine.tokens) - 1)
                c_idx = 0
            elif key == 'i':
                engine.save_state()
                engine.tokens.insert(t_idx + 1, "0000")
                t_idx += 1
                c_idx = 0
            elif key == 'x':
                if len(engine.tokens) > 1:
                    engine.save_state()
                    engine.tokens.pop(t_idx)
                    t_idx = max(0, t_idx - 1)
                    c_idx = 0
            elif key in OP_MAP:
                engine.save_state()
                engine.tokens[t_idx] = OP_MAP[key]
                c_idx = 0
            elif key != "" and all(c in string.hexdigits for c in key):
                engine.save_state()
                if engine.tokens[t_idx] in OPERATORS:
                    engine.tokens[t_idx] = key.upper().zfill(4)
                    c_idx = 0
                else:
                    l_t = list(engine.tokens[t_idx])
                    l_t[c_idx] = key.upper()
                    engine.tokens[t_idx] = "".join(l_t)

            time.sleep(0.01)


if __name__ == "__main__":
    curses.wrapper(main)
