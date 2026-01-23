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
        self.t = 0
        self.history = []
        self.last_samples = np.zeros(60) 
        self.last_val = 0
        self.cascade = deque(maxlen=12)

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
                else: stack.append(int(token, 16))
            except: continue
        return int(stack[-1]) & 255 if stack else 0

    def callback(self, outdata, frames, time, status):
        t_range = np.arange(self.t, self.t + frames) & 0xFFFFFFFF
        vfunc = np.vectorize(self.eval_rpn)
        samples_uint8 = vfunc(t_range).astype(np.uint8)
        self.last_samples = samples_uint8[:60]
        self.last_val = int(samples_uint8[0])
        outdata[:, 0] = (samples_uint8.astype(np.float32) / 127.5) - 1.0
        self.t = (self.t + frames) & 0xFFFFFFFF

def main(stdscr):
    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    
    engine = RPNEngine()
    t_idx, c_idx = 0, 0
    
    #try:
    #    sr = int(sd.query_devices(kind='output')['default_samplerate'])
    #except:
    #    sr = 44100
    sr = 8000

    with sd.OutputStream(channels=1, samplerate=sr, callback=engine.callback):
        while True:
            stdscr.erase()
            
            # 1. Expresión (Línea 1)
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
            
            # 2. Cascada Hexadecimal (Izquierda)
            engine.cascade.appendleft((engine.t, engine.last_val))
            for i, (ct, cv) in enumerate(engine.cascade):
                try:
                    attr = curses.A_BOLD if i == 0 else curses.A_DIM
                    stdscr.addstr(4 + i, 2, f"{ct:08X} {cv:02X}", attr)
                except: pass

            # 3. Osciloscopio Manual Monocromo (Derecha)
            # Dibujamos directamente en la rejilla de la terminal
            scope_x_start = 15
            scope_height = 12
            for x, val_255 in enumerate(engine.last_samples):
                # Invertimos el eje Y para que 255 sea arriba y 0 abajo
                # Escalamos de 0-255 a 0-11
                y_pos = scope_height - 1 - int((val_255 / 255.0) * (scope_height - 1))
                try:
                    # Usamos un caracter de bloque denso para la onda
                    stdscr.addch(4 + y_pos, scope_x_start + x, "█")
                except curses.error:
                    pass

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
                    engine.save_state() 
                    engine.tokens.pop(t_idx)
                    c_idx = 0
            elif key == 's':
                with open(SAVE_FILE, "a") as f: f.write(" ".join(engine.tokens) + "\n")
            elif key in OP_MAP and key != "":
                engine.save_state(); engine.tokens[t_idx] = OP_MAP[key]; c_idx = 0
            elif key != "" and all(c in string.hexdigits for c in key):
                engine.save_state()
                if engine.tokens[t_idx] in OPERATORS:
                    engine.tokens[t_idx] = key.upper().zfill(4); c_idx = 0
                else:
                    l_t = list(engine.tokens[t_idx]); l_t[c_idx] = key.upper()
                    engine.tokens[t_idx] = "".join(l_t)
            elif key in ['KEY_UP', 'KEY_DOWN']:
                engine.save_state(); token = engine.tokens[t_idx]; delta = 1 if key == 'KEY_UP' else -1
                if token in OPERATORS:
                    idx = OPERATORS.index(token); engine.tokens[t_idx] = OPERATORS[(idx+delta)%len(OPERATORS)]; c_idx = 0
                else:
                    char = token[c_idx]; v_h = HEX_CHARS.find(char.upper()); n_c = HEX_CHARS[(v_h+delta)%16]
                    l_t = list(token); l_t[c_idx] = n_c; engine.tokens[t_idx] = "".join(l_t)
            
            time.sleep(0.01)

if __name__ == "__main__":
    curses.wrapper(main)

