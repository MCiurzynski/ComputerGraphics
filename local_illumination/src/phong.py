import json

import numpy as np


def normalize(vector):
    norm = np.linalg.norm(vector, axis=-1, keepdims=True)
    return np.divide(vector, norm, out=np.zeros_like(vector), where=norm != 0)


class Sphere:
    def __init__(self, file):
        self.load_params(file)
        self.r = self.params["r"]
        self.coords = np.array(
            [self.params["x"], self.params["y"], self.params["z"]], dtype="float"
        )

    def lines_intersect(self, points, vectors):
        oc = points - self.coords
        # vectors = normalize(vectors)

        b = np.einsum("...i,...i->...", vectors, oc)
        c = np.einsum("...i,...i->...", oc, oc) - self.r**2

        delta = b**2 - c
        mask = delta >= 0

        intersect_points = np.zeros_like(points)

        if np.any(mask):
            d = -b[mask] - np.sqrt(delta[mask])
            intersect_points[mask] = points[mask] + d[:, np.newaxis] * vectors[mask]

        return mask, intersect_points

    def load_params(self, file):
        with open(file) as f:
            self.params = json.load(f)
        self.color = np.array(
            [self.params["red"], self.params["green"], self.params["blue"]]
        )

    def get_lum(self, vec, cos):
        cos_pow = np.power(cos, self.params["n"])

        ambient = self.params["Ia"] * self.params["ka"]
        diffuse = self.params["fatt"] * self.params["IP"] * self.params["kd"] * vec
        specular = self.params["fatt"] * self.params["IP"] * self.params["ks"] * cos_pow

        intensity = ambient + diffuse + specular

        intensity_multiplier = intensity / self.params["IP"]

        return intensity_multiplier[:, np.newaxis] * self.color

    def move(self, x, y, z):
        self.coords[0] += x
        self.coords[1] += y
        self.coords[2] += z


class Camera:
    def __init__(self, width, height, file):
        self.width = width
        self.height = height

        self.sphere = Sphere(file)
        self.light = np.array([width / 2, height / 2, 0], dtype="float")

        self.vectors = np.zeros((width, height, 3), dtype="float")
        self.vectors[:, :, 2] = 1.0

        rows = np.arange(width)
        cols = np.arange(height)
        ii, jj = np.meshgrid(rows, cols, indexing="ij")

        self.points = np.stack([ii, jj, np.zeros_like(ii)], axis=-1).astype("float")

    def draw(self):
        mask, points = self.sphere.lines_intersect(self.points, self.vectors)

        I = np.zeros((self.width, self.height, 3))

        if np.any(mask):
            valid_points = points[mask]
            valid_ray_origins = self.points[mask]

            N = valid_points - self.sphere.coords
            N_norm = N / self.sphere.r

            L = self.light - valid_points
            L_norm = normalize(L)

            V = valid_ray_origins - valid_points
            V_norm = normalize(V)

            N_dot_L = np.einsum("ij,ij->i", N_norm, L_norm)
            N_dot_L = np.maximum(0, N_dot_L)

            R = 2 * N_dot_L[:, np.newaxis] * N_norm - L_norm
            R_norm = normalize(R)

            V_dot_R = np.einsum("ij,ij->i", V_norm, R_norm)
            cos_alpha = np.maximum(0, V_dot_R)

            I_valid = self.sphere.get_lum(N_dot_L, cos_alpha)

            I[mask] = np.clip(I_valid, 0, 255)

        I_uint8 = I.astype(np.uint8)
        return I_uint8

    def translate_x(self, step):
        self.sphere.move(step, 0, 0)

    def translate_y(self, step):
        self.sphere.move(0, step, 0)

    def translate_z(self, step):
        self.sphere.move(0, 0, step)

