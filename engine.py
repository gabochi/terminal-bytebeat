import numpy as np
import re
import math
import threading
from collections import deque

import editor


class RPNEngine:
    def __init__(self, sample_rate=8000, t_step=1, t_den=1):
        self.SAMPLE_RATE = sample_rate
        self.BUFFER_SIZE = 1024
        self.T_STEP = t_step
        self.T_DEN = t_den

        self.global_t = 0
        self.t_frac = 0
        self.signed_mode = False

        self.hist = np.zeros(256, dtype=np.uint8)
        self.log_t = []
        self.log_o = []
        self.last_out = 0
        self.samples = deque(maxlen=256)
        self.telemetry_lock = threading.Lock()

    def eval_rpn(self, str_expr, t_val):
        clean_str = str_expr.replace(',', ' ')
        tokens = [tok for tok in re.split(r'(<<|>>|[\s\&\|\^\+\-\/\*\%t\,])', clean_str)
                  if tok.strip()]

        stack = []
        for token in tokens:
            if token == 't':
                stack.append(t_val & 0xFFFFFFFF)
            elif token in editor.OPERATORS:
                if len(stack) < 2:
                    return 0
                b = stack.pop()
                a = stack.pop()
                try:
                    if token == '&':
                        res = a & b
                    elif token == '|':
                        res = a | b
                    elif token == '^':
                        res = a ^ b
                    elif token == '+':
                        res = (a + b) & 0xFFFFFFFF
                    elif token == '-':
                        res = (a - b) & 0xFFFFFFFF
                    elif token == '*':
                        res = (a * b) & 0xFFFFFFFF
                        if self.signed_mode and res >= 0x80000000:
                            res -= 0x100000000
                    elif token == '/':
                        res = (a // b) & 0xFFFFFFFF if b != 0 else 0
                    elif token == '%':
                        if self.signed_mode:
                            res = int(math.fmod(a, b)) & 0xFFFFFFFF if b != 0 else 0
                        else:
                            res = (a % b) & 0xFFFFFFFF if b != 0 else 0
                    elif token == '<<':
                        res = (a << (b % 32)) & 0xFFFFFFFF
                    elif token == '>>':
                        res = (a >> (b % 32)) & 0xFFFFFFFF
                    stack.append(res)
                except Exception:
                    stack.append(0)
            else:
                try:
                    val = int(token, 16) & 0xFFFFFFFF
                    stack.append(val)
                except ValueError:
                    pass

        return (stack[-1] & 0xFF) if stack else 0

    def callback(self, outdata, frames, time_info, status):
        with editor.buffer_lock:
            local_buffer = editor.buf

        out_samples = np.zeros(frames, dtype=np.uint8)
        ct = self.global_t
        lt = self.t_frac

        for i in range(frames):
            out_samples[i] = self.eval_rpn(local_buffer, ct)
            self.hist[ct % 256] = out_samples[i]
            lt += self.T_STEP
            if lt >= self.T_DEN:
                lt -= self.T_DEN
                ct += 1

        self.global_t = ct
        self.t_frac = lt

        with self.telemetry_lock:
            self.last_out = out_samples[-1] if frames > 0 else 0
            self.log_t.insert(0, f"t:0x{self.global_t:08X}")
            if len(self.log_t) > 10:
                self.log_t.pop()
            self.log_o.insert(0, f"OUT:0x{self.last_out:02X}")
            if len(self.log_o) > 10:
                self.log_o.pop()

        for s in out_samples:
            self.samples.append(s)

        outdata[:, 0] = (out_samples / 127.5) - 1.0

    def reset(self):
        self.global_t = 0
        self.t_frac = 0
