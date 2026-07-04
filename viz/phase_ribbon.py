import math

import numpy as np
import pygame

from .shape import Shape


class PhaseRibbon(Shape):
    name = "phase_ribbon"

    def __init__(self, trail=256):
        super().__init__()
        self.trail_len = trail
        self.buf = np.zeros((trail * 2, 3), dtype=np.float32)
        self.verts = self.buf.copy()
        self.base = self.buf.copy()
        self.edges = [(i * 2, i * 2 + 1) for i in range(trail)]
        self.line_groups = [
            ([i * 2 for i in range(trail)], False),
            ([i * 2 + 1 for i in range(trail)], False),
        ]
        self.radius = 3.0
        self.cam_y = 0.0

    def deform(self, samples):
        if len(samples) < 4:
            return
        samples_f = [float(x) for x in samples]
        ns = len(samples_f)
        n = min(ns - 3, 4)
        self.buf = np.roll(self.buf, -n * 2, axis=0)
        tail = (self.trail_len - n) * 2
        for i in range(n):
            li, ri = tail + i * 2, tail + i * 2 + 1
            self.buf[li] = [
                (samples_f[i] - 128) / 42.0,
                (samples_f[i + 1] - 128) / 42.0,
                (samples_f[i + 2] - 128) / 42.0,
            ]
            self.buf[ri] = [
                (samples_f[i + 1] - 128) / 42.0,
                (samples_f[i + 2] - 128) / 42.0,
                (samples_f[i + 3] - 128) / 42.0,
            ]
        self.verts = self.buf.copy()

    def render(self, surf, fov, sw, sh, angle_y, angle_x, cam_pos):
        cy, sy = math.cos(angle_y), math.sin(angle_y)
        cx, sx = math.cos(angle_x), math.sin(angle_x)
        cx_pos, cy_pos, cz_pos = cam_pos
        x1 = self.verts[:, 0] * cy - self.verts[:, 2] * sy
        z1 = self.verts[:, 0] * sy + self.verts[:, 2] * cy
        y1 = self.verts[:, 1]
        y = y1 * cx - z1 * sx - cy_pos
        z = y1 * sx + z1 * cx - cz_pos
        x = x1 - cx_pos
        near, far = 0.5, 60.0
        mask = (z > near) & (z < far)
        f_arr = fov / np.maximum(z, near)
        sx = (sw // 2 + (x * f_arr)).astype(int)
        sy = (sh // 2 - (y * f_arr)).astype(int)

        # left/right trails — age-brightened
        for g_indices, closed in self.line_groups:
            pts = []
            for k in range(len(g_indices) - 1):
                i, j = g_indices[k], g_indices[k + 1]
                if mask[i] and mask[j]:
                    pi, pj = i // 2, j // 2
                    age = (pi + pj) * 0.5 / self.trail_len
                    b = max(20, int(age * 235))
                    if not pts:
                        pts.append((sx[i], sy[i], b))
                    pts.append((sx[j], sy[j], b))
            if len(pts) >= 2:
                bs = [p[2] for p in pts]
                avg_b = int(sum(bs) / len(bs))
                xy = [(p[0], p[1]) for p in pts]
                pygame.draw.lines(surf, (avg_b, avg_b, avg_b),
                                  False, xy, 1)

        # cross edges — individual
        for i, j in self.edges:
            if mask[i] and mask[j]:
                pi, pj = i // 2, j // 2
                age = (pi + pj) * 0.5 / self.trail_len
                b = max(20, int(age * 235))
                pygame.draw.line(surf, (b, b, b),
                                 (sx[i], sy[i]), (sx[j], sy[j]), 1)
