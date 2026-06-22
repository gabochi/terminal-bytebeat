import math

import numpy as np

from .shape import Shape


class Torus(Shape):
    name = "torus"

    def __init__(self, R=2.5, r=0.9, nu=40, nv=16):
        super().__init__()
        self.cam_y = 0.5
        self.R, self.r0 = R, r
        self.nu, self.nv = nu, nv
        us = np.linspace(0, 2 * math.pi, nu, endpoint=False)
        vs = np.linspace(0, 2 * math.pi, nv, endpoint=False)
        uu, vv = np.meshgrid(us, vs)
        self.base = np.zeros((nu * nv, 3), dtype=np.float32)
        self.base[:, 0] = ((R + r * np.cos(vv)) * np.cos(uu)).ravel()
        self.base[:, 1] = (r * np.sin(vv)).ravel()
        self.base[:, 2] = ((R + r * np.cos(vv)) * np.sin(uu)).ravel()
        self.verts = self.base.copy()
        self.edges = []
        self.line_groups = []
        for j in range(nv):
            ring = [j * nu + i for i in range(nu)]
            self.line_groups.append((ring, True))
        for i in range(nu):
            slice = [j * nu + i for j in range(nv)]
            self.line_groups.append((slice, False))
        self.radius = R + r + 0.5

    def deform(self, samples):
        if not samples:
            return
        self.verts = self.base.copy()
        ns = len(samples)
        for j in range(self.nv):
            for i in range(self.nu):
                idx = j * self.nu + i
                s = samples[(i + j * 3) % ns] / 255.0 * 0.5
                d = np.linalg.norm(self.base[idx])
                if d > 1e-6:
                    self.verts[idx] += self.base[idx] / d * s
