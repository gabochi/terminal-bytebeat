import math

import numpy as np
import pygame

from .shape import Shape

_SEG = 32


class Phase3D(Shape):
    name = "phase_3d"

    def __init__(self, trail=512):
        super().__init__()
        self.trail_len = trail
        self.buf = np.zeros((trail, 3), dtype=np.float32)
        self.head = 0
        self.verts = self.buf.copy()
        self.base = self.buf.copy()
        self.edges = []
        self.line_groups = []
        for k in range(0, trail - 1, _SEG):
            end = min(k + _SEG + 1, trail)
            if end - k >= 2:
                self.line_groups.append((list(range(k, end)), False))
        self.radius = 3.0
        self.cam_y = 0.0

    def deform(self, samples):
        if len(samples) < 3:
            return
        samples_f = [float(x) for x in samples]
        ns = len(samples_f)
        n = min(ns - 2, 4)
        for i in range(n):
            self.head = (self.head + 1) % self.trail_len
            self.buf[self.head] = [
                (samples_f[i] - 128) / 42.0,
                (samples_f[i + 1] - 128) / 42.0,
                (samples_f[i + 2] - 128) / 42.0,
            ]
        self.verts = self.buf.copy()

    def render(self, surf, fov, sw, sh, angle, cam_pos):
        c, s = math.cos(angle), math.sin(angle)
        cx, cy, cz = cam_pos
        x = self.verts[:, 0] * c - self.verts[:, 2] * s - cx
        z = self.verts[:, 0] * s + self.verts[:, 2] * c - cz
        y = self.verts[:, 1] - cy
        near, far = 0.5, 60.0
        mask = (z > near) & (z < far)
        f_arr = fov / np.maximum(z, near)
        sx = (sw // 2 + (x * f_arr)).astype(int)
        sy = (sh // 2 - (y * f_arr)).astype(int)

        ages = (np.arange(self.trail_len) - self.head) % self.trail_len
        ages = ages.astype(float) / self.trail_len

        for g_indices, closed in self.line_groups:
            pts = []
            for k in range(len(g_indices) - 1):
                i, j = g_indices[k], g_indices[k + 1]
                if mask[i] and mask[j]:
                    age = (ages[i] + ages[j]) * 0.5
                    b = max(20, int(255 - age * 235))
                    if not pts:
                        pts.append((sx[i], sy[i], b))
                    pts.append((sx[j], sy[j], b))
            if len(pts) >= 2:
                bs = [p[2] for p in pts]
                avg_b = int(sum(bs) / len(bs))
                xy = [(p[0], p[1]) for p in pts]
                pygame.draw.lines(surf, (avg_b, avg_b, avg_b),
                                  False, xy, 1)
