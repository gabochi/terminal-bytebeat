import math
import numpy as np
import pygame


def render_wireframe(surf, verts, edges, fov, sw, sh, angle, cam_pos,
                     line_groups=None):
    c, s = math.cos(angle), math.sin(angle)
    cx, cy, cz = cam_pos

    x = verts[:, 0] * c - verts[:, 2] * s - cx
    z = verts[:, 0] * s + verts[:, 2] * c - cz
    y = verts[:, 1] - cy

    near, far = 0.5, 60.0
    mask = (z > near) & (z < far)
    f = fov / np.maximum(z, near)
    sx = (sw // 2 + (x * f)).astype(int)
    sy = (sh // 2 - (y * f)).astype(int)

    visible_z = z[mask]
    if visible_z.size > 0:
        z_lo, z_hi = visible_z.min(), visible_z.max()
        z_rng = max(z_hi - z_lo, 0.1)
    else:
        z_lo, z_rng = near, 1.0

    if line_groups:
        for g_indices, closed in line_groups:
            pts = []
            for k in range(len(g_indices) - 1):
                i, j = g_indices[k], g_indices[k + 1]
                if mask[i] and mask[j]:
                    avg_z2 = (z[i] + z[j]) * 0.5
                    d = (avg_z2 - z_lo) / z_rng
                    b = max(30, int(255 - d * 225))
                    if not pts:
                        pts.append((sx[i], sy[i], b))
                    pts.append((sx[j], sy[j], b))
            if closed and mask[g_indices[-1]] and mask[g_indices[0]]:
                i, j = g_indices[-1], g_indices[0]
                avg_z2 = (z[i] + z[j]) * 0.5
                d = (avg_z2 - z_lo) / z_rng
                b = max(30, int(255 - d * 225))
                if pts:
                    pts.append((sx[j], sy[j], b))
                else:
                    pts = [(sx[i], sy[i], b), (sx[j], sy[j], b)]
            if len(pts) >= 2:
                bs = [p[2] for p in pts]
                avg_b = int(sum(bs) / len(bs))
                xy = [(p[0], p[1]) for p in pts]
                pygame.draw.lines(surf, (avg_b, avg_b, avg_b), False, xy, 1)
    else:
        for i, j in edges:
            if mask[i] and mask[j]:
                avg_z2 = (z[i] + z[j]) * 0.5
                d = (avg_z2 - z_lo) / z_rng
                b = max(30, int(255 - d * 225))
                pygame.draw.line(surf, (b, b, b),
                                 (sx[i], sy[i]), (sx[j], sy[j]), 1)


class Shape:
    name = "shape"
    def __init__(self):
        self.verts = np.zeros((0, 3), dtype=np.float32)
        self.base = np.zeros((0, 3), dtype=np.float32)
        self.edges = []
        self.line_groups = None
        self.radius = 1.0
        self.cam_y = 0.0
        self.fixed_cam_dist = None

    def deform(self, samples):
        """Update self.verts from self.base using audio samples."""

    def render(self, surf, fov, sw, sh, angle, cam_pos):
        render_wireframe(surf, self.verts, self.edges, fov, sw, sh,
                         angle, cam_pos, self.line_groups)
