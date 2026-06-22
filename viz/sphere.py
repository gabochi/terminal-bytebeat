import math

import numpy as np

from .shape import Shape


class Sphere(Shape):
    name = "sphere"

    def __init__(self, radius=2.8, nlat=16, nlon=32):
        super().__init__()
        self.cam_y = 0.5
        self.radius = radius
        self.nlat, self.nlon = nlat, nlon
        thetas = np.linspace(0, math.pi, nlat)
        phis = np.linspace(0, 2 * math.pi, nlon, endpoint=False)
        tt, pp = np.meshgrid(thetas, phis)
        self.base = np.zeros((nlat * nlon, 3), dtype=np.float32)
        self.base[:, 0] = (radius * np.sin(tt) * np.cos(pp)).ravel()
        self.base[:, 1] = (radius * np.cos(tt)).ravel()
        self.base[:, 2] = (radius * np.sin(tt) * np.sin(pp)).ravel()
        self.verts = self.base.copy()
        self.edges = []
        self.line_groups = []
        for j in range(nlon):
            lat = [j * nlat + i for i in range(nlat)]
            self.line_groups.append((lat, True))
        for i in range(nlat):
            lon = [j * nlat + i for j in range(nlon)]
            self.line_groups.append((lon, False))
        self.radius = radius + 0.5

    def deform(self, samples):
        if not samples:
            return
        self.verts = self.base.copy()
        ns = len(samples)
        for j in range(self.nlon):
            for i in range(self.nlat):
                idx = j * self.nlat + i
                s = samples[(i + j * 2) % ns] / 255.0 * 0.4
                d = np.linalg.norm(self.base[idx])
                if d > 1e-6:
                    self.verts[idx] += self.base[idx] / d * s
