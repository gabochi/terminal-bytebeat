import numpy as np
import copy
from collections import deque
from constants import OPERATORS

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
        if len(self.history) > 50: self.history.pop(0)

    def undo(self):
        if self.history: self.tokens = self.history.pop()

    def eval_rpn(self, t_val):
        stack = []
        for token in self.active_tokens:
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
