import math

import numpy as np

from .shape import Shape


class Pyramid(Shape):
    name = "pyramid"

    def __init__(self, base_r=2.8, height=4.0, n_sides=4, n_steps=20):
        super().__init__()
        self.cam_y = 0.5
        self.n_sides = n_sides
        self.n_steps = n_steps
        nv = 1 + n_steps * n_sides

        self.base = np.zeros((nv, 3), dtype=np.float32)
        self.base[0] = [0, height / 2, 0]
        for l in range(1, n_steps + 1):
            t = l / n_steps
            r = t * base_r
            y = (1 - t) * height / 2 + t * (-height / 2)
            for s in range(n_sides):
                theta = s * 2 * math.pi / n_sides
                idx = 1 + (l - 1) * n_sides + s
                self.base[idx] = [r * math.cos(theta), y, r * math.sin(theta)]
        self.verts = self.base.copy()

        self.edges = []
        self.line_groups = []
        for l in range(n_steps):
            ring = [1 + l * n_sides + s for s in range(n_sides)]
            self.line_groups.append((ring, True))
        for s in range(n_sides):
            spine = [0]
            for l in range(n_steps):
                spine.append(1 + l * n_sides + s)
            self.line_groups.append((spine, False))

        self.radius = math.sqrt(base_r ** 2 + (height / 2) ** 2) + 0.5

    def deform(self, samples):
        if not samples:
            return
        self.verts = self.base.copy()
        ns = len(samples)
        for idx in range(len(self.base)):
            s = samples[idx % ns]
            val = (s - 128) / 128.0 * 1.2
            v = self.base[idx]
            r = np.linalg.norm([v[0], v[2]])
            if r > 1e-6:
                self.verts[idx, 0] += v[0] / r * val
                self.verts[idx, 2] += v[2] / r * val
            self.verts[idx, 1] += val * 0.6
