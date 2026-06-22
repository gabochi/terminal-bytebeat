import math

import numpy as np

from .shape import Shape


class Cylinder(Shape):
    name = "cylinder"

    def __init__(self, radius=2.2, height=4.0, ns=32, nh=20):
        super().__init__()
        self.cam_y = 0.5
        self.ns, self.nh = ns, nh
        thetas = np.linspace(0, 2 * math.pi, ns, endpoint=False)
        heights = np.linspace(-height / 2, height / 2, nh)
        tt, hh = np.meshgrid(thetas, heights)
        self.base = np.zeros((ns * nh, 3), dtype=np.float32)
        self.base[:, 0] = (radius * np.cos(tt)).ravel()
        self.base[:, 1] = hh.ravel()
        self.base[:, 2] = (radius * np.sin(tt)).ravel()
        self.verts = self.base.copy()

        self.edges = []
        self.line_groups = []
        for j in range(nh):
            ring = [j * ns + i for i in range(ns)]
            self.line_groups.append((ring, True))
        for i in range(ns):
            col = [j * ns + i for j in range(nh)]
            self.line_groups.append((col, False))
        self.radius = math.sqrt(radius ** 2 + (height / 2) ** 2) + 0.5

    def deform(self, samples):
        if not samples:
            return
        self.verts = self.base.copy()
        ns = len(samples)
        for j in range(self.nh):
            for i in range(self.ns):
                idx = j * self.ns + i
                s = samples[(i + j * 3) % ns] / 255.0 * 0.5
                v = self.base[idx]
                r = np.linalg.norm([v[0], v[2]])
                if r > 1e-6:
                    self.verts[idx, 0] += v[0] / r * s
                    self.verts[idx, 2] += v[2] / r * s
