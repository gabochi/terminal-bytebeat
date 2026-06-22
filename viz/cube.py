import numpy as np

from .shape import Shape


def _make_face(nx, ny, nz, half, sub):
    eps = 1e-6
    if abs(nx) > eps:
        u, v = np.array([0, 0, 1]), np.array([0, 1, 0])
    elif abs(ny) > eps:
        u, v = np.array([1, 0, 0]), np.array([0, 0, 1])
    else:
        u, v = np.array([1, 0, 0]), np.array([0, 1, 0])
    n = np.array([nx, ny, nz])
    verts, edges = [], []
    for j in range(sub + 1):
        for i in range(sub + 1):
            p = n * half + (i / sub - 0.5) * 2 * half * u + (j / sub - 0.5) * 2 * half * v
            verts.append(p)
            if i < sub:
                edges.append((j * (sub + 1) + i, j * (sub + 1) + i + 1))
            if j < sub:
                edges.append((j * (sub + 1) + i, (j + 1) * (sub + 1) + i))
    return np.array(verts, dtype=np.float32), edges


class Cube(Shape):
    name = "cube"

    def __init__(self, half=2.5, sub=8):
        super().__init__()
        self.cam_y = 0.5
        self.half = half
        self.sub = sub
        self.face_normals = [
            (1, 0, 0), (-1, 0, 0),
            (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1),
        ]
        all_verts = []
        offset = 0
        for n in self.face_normals:
            fv, _ = _make_face(*n, half, sub)
            all_verts.append(fv)
            offset += len(fv)
        self.base = np.vstack(all_verts)
        self.verts = self.base.copy()
        self.edges = []
        self.line_groups = []
        vpf = (sub + 1) ** 2
        for fi in range(6):
            off = fi * vpf
            rows = [[off + r * (sub + 1) + c for c in range(sub + 1)]
                    for r in range(sub + 1)]
            cols = [[off + r * (sub + 1) + c for r in range(sub + 1)]
                    for c in range(sub + 1)]
            self.line_groups.extend((r, False) for r in rows)
            self.line_groups.extend((c, False) for c in cols)
        self.radius = np.linalg.norm([half, half, half])

    def deform(self, samples):
        if not samples:
            return
        self.verts = self.base.copy()
        n_faces = len(self.face_normals)
        verts_per_face = len(self.base) // n_faces
        ns = max(1, len(samples))

        for fi in range(n_faces):
            n = np.array(self.face_normals[fi])
            sidx = fi * verts_per_face
            eidx = sidx + verts_per_face
            face_verts = self.base[sidx:eidx]

            face_center = n * self.half
            dist = np.linalg.norm(face_verts - face_center, axis=1) / self.half

            for vi in range(verts_per_face):
                s = samples[(fi * 7 + vi * 3) % ns] / 255.0
                weight = 1.0 - dist[vi] * 0.55
                self.verts[sidx + vi] += n * s * 0.9 * weight
