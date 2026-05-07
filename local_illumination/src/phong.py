import json

import torch


def normalize(vector):
    norm = torch.linalg.norm(vector, dim=-1, keepdim=True)
    return torch.where(norm > 0, vector / norm, torch.zeros_like(vector))


class Sphere:
    def __init__(self, file, device):
        self.device = device
        self.load_params(file)
        self.r = self.params["r"]
        self.coords = torch.tensor(
            [self.params["x"], self.params["y"], self.params["z"]],
            dtype=torch.float32,
            device=self.device,
        )

    def lines_intersect(self, points, vectors):
        oc = points - self.coords
        # vectors = normalize(vectors)

        b = torch.sum(vectors * oc, dim=-1)
        c = torch.sum(oc * oc, dim=-1) - self.r**2

        delta = b**2 - c
        mask = delta >= 0

        intersect_points = torch.zeros_like(points)

        if mask.any():
            d = -b[mask] - torch.sqrt(delta[mask])
            intersect_points[mask] = points[mask] + d.unsqueeze(-1) * vectors[mask]

        return mask, intersect_points

    def load_params(self, file):
        with open(file) as f:
            self.params = json.load(f)
        self.color = torch.tensor(
            [self.params["red"], self.params["green"], self.params["blue"]],
            dtype=torch.float32,
            device=self.device,
        )

    def get_lum(self, vec, cos):
        cos_pow = torch.pow(cos, self.params["n"])

        ambient = self.params["Ia"] * self.params["ka"]
        diffuse = self.params["fatt"] * self.params["IP"] * self.params["kd"] * vec
        specular = self.params["fatt"] * self.params["IP"] * self.params["ks"] * cos_pow

        intensity = ambient + diffuse + specular

        intensity_multiplier = intensity / self.params["IP"]

        return intensity_multiplier.unsqueeze(-1) * self.color

    def move(self, x, y, z):
        self.coords += torch.tensor([x, y, z], dtype=torch.float32, device=self.device)


class Camera:
    def __init__(self, width, height, file, device="cpu"):
        self.width = width
        self.height = height
        self.device = torch.device(device)

        self.sphere = Sphere(file, self.device)
        self.light = torch.tensor(
            [width / 2, height / 2, 0], dtype=torch.float32, device=self.device
        )

        self.vectors = torch.zeros(
            (width, height, 3), dtype=torch.float32, device=self.device
        )
        self.vectors[:, :, 2] = 1.0

        rows = torch.arange(width, dtype=torch.float32, device=self.device)
        cols = torch.arange(height, dtype=torch.float32, device=self.device)
        ii, jj = torch.meshgrid(rows, cols, indexing="ij")

        self.points = torch.stack([ii, jj, torch.zeros_like(ii)], dim=-1)

    def draw(self):
        mask, points = self.sphere.lines_intersect(self.points, self.vectors)

        I = torch.zeros(
            (self.width, self.height, 3), dtype=torch.float32, device=self.device
        )

        if mask.any():
            valid_points = points[mask]
            valid_ray_origins = self.points[mask]

            N = valid_points - self.sphere.coords
            N_norm = N / self.sphere.r

            L = self.light - valid_points
            L_norm = normalize(L)

            V = valid_ray_origins - valid_points
            V_norm = normalize(V)

            N_dot_L = torch.sum(N_norm * L_norm, dim=1)
            N_dot_L = torch.clamp(N_dot_L, min=0)

            R = 2 * N_dot_L.unsqueeze(-1) * N_norm - L_norm
            R_norm = normalize(R)

            V_dot_R = torch.sum(V_norm * R_norm, dim=1)
            cos_alpha = torch.clamp(V_dot_R, min=0)

            I_valid = self.sphere.get_lum(N_dot_L, cos_alpha)

            I[mask] = torch.clamp(I_valid, 0, 255)

        return I.to(dtype=torch.uint8).cpu().numpy()

    def translate_x(self, step):
        self.sphere.move(step, 0, 0)

    def translate_y(self, step):
        self.sphere.move(0, step, 0)

    def translate_z(self, step):
        self.sphere.move(0, 0, step)
