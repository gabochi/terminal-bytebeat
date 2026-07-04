import math
import numpy as np
from .shape import Shape


class Blob(Shape):
    name = "blob"

    def __init__(self, n_lat=16, n_lon=32, radius=2.8):
        super().__init__()
        self.cam_y = 0.5
        self.radius = radius + 0.5
        self.n_lat, self.n_lon = n_lat, n_lon

        thetas = np.linspace(0, math.pi, n_lat)
        phis = np.linspace(0, 2 * math.pi, n_lon, endpoint=False)
        tt, pp = np.meshgrid(thetas, phis)
        self.base = np.zeros((n_lat * n_lon, 3), dtype=np.float32)
        self.base[:, 0] = (radius * np.sin(tt) * np.cos(pp)).ravel()
        self.base[:, 1] = (radius * np.cos(tt)).ravel()
        self.base[:, 2] = (radius * np.sin(tt) * np.sin(pp)).ravel()
        self.verts = self.base.copy()

        self.edges = []
        self.line_groups = []
        for i in range(n_lat):
            ring = [j * n_lat + i for j in range(n_lon)]
            self.line_groups.append((ring, True))
        for j in range(n_lon):
            lon = [j * n_lat + i for i in range(n_lat)]
            self.line_groups.append((lon, True))

        norms = np.linalg.norm(self.base, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-6)
        verts_norm = self.base / norms

        rng = np.random.RandomState(0)
        nf = 8
        features = rng.randn(nf, 3)
        features /= np.linalg.norm(features, axis=1, keepdims=True)
        self.features = features
        self.angle_cos = verts_norm @ features.T

    def deform(self, samples):
        if len(samples) < 2:
            return
        ns = len(samples)
        nf = self.features.shape[0]
        vals = np.array([samples[f % ns] / 255.0 for f in range(nf)])
        influence = np.maximum(0, self.angle_cos) ** 4
        total = influence.sum(axis=1, keepdims=True)
        total = np.maximum(total, 1e-6)
        weights = influence / total
        blend = weights @ vals
        deform = blend * 0.5 - 0.1
        self.verts = self.base * (1.0 + deform.reshape(-1, 1))
