import curses
import numpy as np
import sounddevice as sd
import time
import copy
import string
import plotille

# --- Configuración ---
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
        self.t = 0
        self.history = []
        self.last_samples = np.zeros(80)

    def save_state(self):
        self.history.append(copy.deepcopy(self.tokens))
        if len(self.history) > 50: self.history.pop(0)

    def undo(self):
        if self.history: self.tokens = self.history.pop()

    def eval_rpn(self, t_val):
        stack = []
        for token in self.tokens:
            try:
                if token == "t": stack.append(t_val)
                elif token in OPERATORS:
                    if len(stack) < 2: continue
                    b, a = stack.pop(), stack.pop()
                    if token == "+": stack.append(a + b)
                    elif token == "-": stack.append(a - b)
                    elif token == "*": stack.append(a * b)
                    elif token == "/": stack.append(a // (b or 1))
                    elif token == "%": stack.append(a % (b or 1))
                    elif token == "&": stack.append(a & b)
                    elif token == "|": stack.append(a | b)
                    elif token == "^": stack.append(a ^ b)
                    elif token == ">>": stack.append(a >> (b % 32))
                    elif token == "<<": stack.append(a << (b % 32))
                else:
                    stack.append(int(token, 16))
            except: continue
        return int(stack[-1]) & 255 if stack else 0

    def callback(self, outdata, frames, time, status):
        chunk = np.arange(self.t, self.t + frames)
        vfunc = np.vectorize(self.eval_rpn)
        samples_uint8 = vfunc(chunk).astype(np.uint8)
        self.last_samples = samples_uint8[:80] 
        outdata[:, 0] = (samples_uint8.astype(np.float32) / 127.5) - 1.0
        self.t += frames & 0xFFFFFFFF

def save_expression(tokens):
    with open(SAVE_FILE, "a") as f:
        f.write(" ".join(tokens) + "\n")

def main(stdscr):
    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    
    engine = RPNEngine()
    t_idx, c_idx = 0, 0

    with sd.OutputStream(channels=1, 
                         samplerate=SAMPLE_RATE, 
                         callback=engine.callback):
        while True:
            stdscr.erase()
            
            # --- 1. Expresión (Línea 1) ---
            curr_x = 2
            cursor_pos_x = 2
            for i, token in enumerate(engine.tokens):
                for char_pos, char in enumerate(token):
                    if i == t_idx and char_pos == c_idx:
                        attr = curses.A_REVERSE | curses.A_BOLD
                        cursor_pos_x = curr_x
                    else: attr = curses.A_NORMAL
                    stdscr.addstr(1, curr_x, char, attr)
                    curr_x += 1
                curr_x += 2
            stdscr.move(1, cursor_pos_x)
            
            # --- 2. Osciloscopio Limpio con plotille.scatter ---
            # Scatter es más confiable para Braille puro en 2026
            res = plotille.scatter(
                range(len(engine.last_samples)), 
                engine.last_samples,
                width=75,
                height=12,
                y_min=0,
                y_max=255,
                origin=False # Quita las líneas de los ejes 0,0
            )
            
            # Limpieza manual de cualquier número que plotille intente meter
            for i, line in enumerate(res.splitlines()):
                # Ignoramos líneas que contengan caracteres de ejes como '|' o '-'
                # para mantener el gráfico 100% puro
                clean_line = "".join([c for c in line if ord(c) > 127 or c == ' '])
                if clean_line.strip():
                    try:
                        stdscr.addstr(4 + i, 0, clean_line, curses.color_pair(1))
                    except: pass

            stdscr.refresh()
            try: key = stdscr.getkey()
            except: key = ""

            if key == 'q': break
            elif key == 'KEY_LEFT':
                if c_idx > 0: c_idx -= 1
                elif t_idx > 0: t_idx -= 1; c_idx = len(engine.tokens[t_idx]) - 1
            elif key == 'KEY_RIGHT':
                if c_idx < len(engine.tokens[t_idx]) - 1: c_idx += 1
                elif t_idx < len(engine.tokens) - 1: t_idx += 1; c_idx = 0
            elif key == 'u':
                engine.undo()
                t_idx = min(t_idx, len(engine.tokens)-1); c_idx = 0
            elif key == 'i':
                engine.save_state(); engine.tokens.insert(t_idx + 1, "0000"); t_idx += 1; c_idx = 0
            elif key == 'x':
                if len(engine.tokens) > 1:
                    engine.save_state(); engine.tokens.pop(t_idx)
                    c_idx = 0
            elif key == 's': save_expression(engine.tokens)
            elif key in OP_MAP and key != "":
                engine.save_state(); engine.tokens[t_idx] = OP_MAP[key]; c_idx = 0
            elif key != "" and all(c in string.hexdigits for c in key):
                engine.save_state()
                if engine.tokens[t_idx] in OPERATORS:
                    engine.tokens[t_idx] = key.upper().zfill(4); c_idx = 0
                else:
                    l_token = list(engine.tokens[t_idx]); l_token[c_idx] = key.upper()
                    engine.tokens[t_idx] = "".join(l_token)
            elif key in ['KEY_UP', 'KEY_DOWN']:
                engine.save_state(); token = engine.tokens[t_idx]; delta = 1 if key == 'KEY_UP' else -1
                if token in OPERATORS:
                    op_idx = OPERATORS.index(token); engine.tokens[t_idx] = OPERATORS[(op_idx + delta) % len(OPERATORS)]; c_idx = 0
                else:
                    char = token[c_idx]; hex_val = HEX_CHARS.find(char.upper()); new_char = HEX_CHARS[(hex_val + delta) % 16]
                    l_token = list(token); l_token[c_idx] = new_char; engine.tokens[t_idx] = "".join(l_token)
            time.sleep(0.01)

if __name__ == "__main__":
    curses.wrapper(main)

