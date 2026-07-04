import math

import numpy as np

from .shape import Shape


class BitBars(Shape):
    name = "bit_bars"

    def __init__(self, n_columns=8, n_rings=12, n_sides=8, r0=0.35, H=5.0, orbit=3.0):
        super().__init__()
        self.cam_y = 0.0
        self.nc = n_columns
        self.nr = n_rings
        self.ns = n_sides
        self.orbit = orbit

        nv = n_columns * n_rings * n_sides
        self.base = np.zeros((nv, 3), dtype=np.float32)
        idx = 0
        for c in range(n_columns):
            theta = c * 2 * math.pi / n_columns
            for ri in range(n_rings):
                y = -H / 2 + ri * H / (n_rings - 1) if n_rings > 1 else 0
                for si in range(n_sides):
                    phi = si * 2 * math.pi / n_sides
                    self.base[idx] = [
                        orbit * math.cos(theta) + r0 * math.cos(phi),
                        y,
                        orbit * math.sin(theta) + r0 * math.sin(phi),
                    ]
                    idx += 1

        self.verts = self.base.copy()
        self.edges = []
        self.line_groups = []

        for c in range(n_columns):
            for ri in range(n_rings):
                ring = [c * n_rings * n_sides + ri * n_sides + si
                        for si in range(n_sides)]
                self.line_groups.append((ring, True))
            for si in range(n_sides):
                spine = [c * n_rings * n_sides + ri * n_sides + si
                         for ri in range(n_rings)]
                self.line_groups.append((spine, False))

        self.radius = orbit + r0 + 1.0

    def deform(self, samples):
        if not samples:
            return
        self.verts = self.base.copy()
        ns = len(samples)
        nc, nr, nsides = self.nc, self.nr, self.ns

        for c in range(nc):
            theta = c * 2 * math.pi / nc
            cx = self.orbit * math.cos(theta)
            cz = self.orbit * math.sin(theta)
            for ri in range(nr):
                si = (c + ri * nc) % ns
                s = samples[si]
                amp = 1.0 if (s >> c) & 1 else 0.0
                scale = 1 + amp * 0.6
                for v in range(nsides):
                    idx = c * nr * nsides + ri * nsides + v
                    dx = self.base[idx, 0] - cx
                    dz = self.base[idx, 2] - cz
                    self.verts[idx, 0] = cx + dx * scale
                    self.verts[idx, 2] = cz + dz * scale
