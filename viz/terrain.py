import math

import numpy as np
import pygame

from .shape import Shape


class Terrain(Shape):
    name = "terrain"

    def __init__(self, tw=80, td=28):
        super().__init__()
        self.tw, self.td = tw, td
        self.cam_y = 3.0
        self.fixed_cam_dist = 13.0
        self.samples_buf = np.zeros((td, tw), dtype=np.uint8)
        cols = np.arange(tw, dtype=np.float32)
        rows = np.arange(td, dtype=np.float32)
        spacing = 0.30
        self.base_x, self.base_z = np.meshgrid(
            (cols - tw / 2) * spacing, (rows - td / 2) * spacing
        )
        self.height_scale = 3.5
        self.radius = np.sqrt(
            (tw * spacing / 2) ** 2 + (td * spacing / 2) ** 2 +
            (self.height_scale / 2) ** 2
        )

    def deform(self, samples):
        if not samples:
            return
        self.samples_buf = np.roll(self.samples_buf, 1, axis=0)
        n = min(len(samples), self.tw)
        self.samples_buf[0, :n] = np.array(samples[:n], dtype=np.uint8)
        y = self.samples_buf.astype(np.float32) / 255.0 * self.height_scale
        self.verts = np.stack([self.base_x, y, self.base_z], axis=-1)

    def render(self, surf, fov, sw, sh, angle_y, angle_x, cam_pos):
        cy, sy = math.cos(angle_y), math.sin(angle_y)
        cx, sx = math.cos(angle_x), math.sin(angle_x)
        cx_pos, cy_pos, cz_pos = cam_pos
        td, tw, _ = self.verts.shape
        x1 = self.verts[:, :, 0] * cy - self.verts[:, :, 2] * sy
        z1 = self.verts[:, :, 0] * sy + self.verts[:, :, 2] * cy
        y1 = self.verts[:, :, 1]
        y = y1 * cx - z1 * sx - cy_pos
        z = y1 * sx + z1 * cx - cz_pos
        x = x1 - cx_pos
        near, far = 0.5, 60.0
        f = fov / np.maximum(z, near)
        sx = (sw // 2 + (x * f)).astype(int)
        sy = (sh // 2 - (y * f)).astype(int)

        visible_z = z[(z > near) & (z < far)]
        if visible_z.size > 0:
            z_lo, z_hi = visible_z.min(), visible_z.max()
            z_rng = max(z_hi - z_lo, 0.1)
        else:
            z_lo, z_rng = near, 1.0

        for row in range(td - 1, -1, -1):
            avg_z = float(np.mean(z[row]))
            d = (avg_z - z_lo) / z_rng
            b = max(25, int(255 - d * 230))
            pts = list(zip(sx[row], sy[row]))
            if len(pts) >= 2:
                pygame.draw.lines(surf, (b, b, b), False, pts, 1)

        for col in range(tw):
            avg_z = float(np.mean(z[:, col]))
            d = (avg_z - z_lo) / z_rng
            b = max(15, int(220 - d * 205))
            pts = [(sx[r, col], sy[r, col]) for r in range(td - 1, -1, -1)]
            pygame.draw.lines(surf, (b, b, b), False, pts, 1)
