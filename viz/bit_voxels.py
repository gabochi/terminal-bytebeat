import numpy as np

from .shape import Shape


class BitVoxels(Shape):
    name = "bit_voxels"

    def __init__(self, grid=8, spacing=0.7, cross_size=0.22):
        super().__init__()
        self.grid = grid
        self.cross_size = cross_size
        self.cam_y = 0.0
        self.fixed_cam_dist = 12.0

        verts, edges = [], []
        centers = []
        for zi in range(grid):
            for yi in range(grid):
                for xi in range(grid):
                    cx = (xi - grid / 2) * spacing
                    cy = (yi - grid / 2) * spacing
                    cz = (zi - grid / 2) * spacing
                    centers.append((cx, cy, cz))
                    s = cross_size
                    verts.append([cx - s, cy, cz])
                    verts.append([cx + s, cy, cz])
                    verts.append([cx, cy - s, cz])
                    verts.append([cx, cy + s, cz])
                    verts.append([cx, cy, cz - s])
                    verts.append([cx, cy, cz + s])
                    off = len(verts) - 6
                    edges.extend([(off, off + 1), (off + 2, off + 3),
                                  (off + 4, off + 5)])

        self.base = np.array(verts, dtype=np.float32)
        self.verts = self.base.copy()
        self.edges = edges
        self.centers = np.array(centers, dtype=np.float32)
        hw = grid * spacing / 2
        self.radius = np.linalg.norm([hw, hw, hw]) + cross_size + 0.5

        # bit_buf[z][y][x] — z scrolls (time), y scrolls (samples), x = bit
        self.bit_buf = np.zeros((grid, grid, grid), dtype=bool)

    def deform(self, samples):
        if not samples:
            return
        g = self.grid
        self.bit_buf = np.roll(self.bit_buf, 1, axis=0)
        self.bit_buf[0] = np.roll(self.bit_buf[0], 1, axis=0)
        s = samples[0]
        for xi in range(g):
            self.bit_buf[0, 0, xi] = bool((s >> xi) & 1)

        self.verts = self.base.copy()
        for vi in range(g ** 3):
            if not self.bit_buf.flat[vi]:
                off = vi * 6
                c = self.centers[vi]
                for j in range(6):
                    self.verts[off + j] = c
