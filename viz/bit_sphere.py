import math

import numpy as np

from .shape import Shape


class BitSphere(Shape):
    name = "bit_sphere"

    def __init__(self, radius=2.5, nlat=16, nlon=32):
        super().__init__()
        self.cam_y = 0.5
        self.base_r = radius
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
        self.radius = radius + 1.0

        nv = nlat * nlon
        self.v_map = []
        for vi in range(nv):
            self.v_map.append((vi % 8, (vi // 8) % 8))

    def deform(self, samples):
        if not samples:
            return
        self.verts = self.base.copy()
        ns = len(samples)
        for vi, (bit_pos, sample_off) in enumerate(self.v_map):
            s = samples[sample_off % ns]
            if (s >> bit_pos) & 1:
                n = self.verts[vi] / (np.linalg.norm(self.verts[vi]) + 1e-10)
                self.verts[vi] += n * 0.8
