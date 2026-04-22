import numpy as np
import copy
from pathlib import Path

class Point:
    def __init__(self, x, y, z):
        self.coords = np.array([x, y, z, 1], dtype='float').T

    def normalize(self):
        self.coords = self.coords / self.coords[3]

    def transform(self, matrix):
        self.coords = matrix @ self.coords
        return self

    def __str__(self):
        return str(self.coords)

class Polygon:
    def __init__(self, points):
        self.points = points 

    def normalize(self):
        for p in self.points:
            p.normalize()

    def transform(self, matrix):
        for p in self.points:
            p.transform(matrix)
        self.normalize()
        return self

    def __str__(self):
        return f"Polygon({', '.join(str(p) for p in self.points)})"
    
    def _get_2d_bbox(self):
        xs = [p.coords[0] for p in self.points]
        ys = [p.coords[1] for p in self.points]
        return min(xs), max(xs), min(ys), max(ys)
    
    def _get_plane(self):
        if len(self.points) < 3:
            return np.array([0.0, 0.0, 1.0]), 0.0
        
        p0 = self.points[0].coords[:3]
        p1 = self.points[1].coords[:3]
        p2 = self.points[2].coords[:3]
        
        normal = np.cross(p1 - p0, p2 - p0)
        norm_len = np.linalg.norm(normal)
        if norm_len > 1e-6:
            normal = normal / norm_len
            
        D = -np.dot(normal, p0)
        return normal, D

    def _test2_projections_sat(self, other):
        def get_normals_2d(poly):
            normals = []
            pts = poly.points
            for i in range(len(pts)):
                p1 = pts[i].coords[:2]
                p2 = pts[(i+1) % len(pts)].coords[:2]
                edge = p2 - p1
                normals.append(np.array([-edge[1], edge[0]]))
            return normals

        def project(poly, axis):
            dots = [np.dot(pt.coords[:2], axis) for pt in poly.points]
            return min(dots), max(dots)

        normals = get_normals_2d(self) + get_normals_2d(other)
        for n in normals:
            norm_len = np.linalg.norm(n)
            if norm_len < 1e-6:
                continue
            n = n / norm_len
            min_p, max_p = project(self, n)
            min_q, max_q = project(other, n)
            if max_p < min_q or max_q < min_p:
                return True
        return False

    def _test3_opposite_side(self, other, obs_pos=np.array([0.0, 0.0, 0.0])):
        normal_q, D_q = other._get_plane()
        obs_side = np.dot(normal_q, obs_pos) + D_q
        for p in self.points:
            p_side = np.dot(normal_q, p.coords[:3]) + D_q
            if (obs_side > 0 and p_side > -1e-5) or (obs_side < 0 and p_side < 1e-5):
                return False
        return True

    def _test4_same_side(self, other, obs_pos=np.array([0.0, 0.0, 0.0])):
        normal_p, D_p = self._get_plane()
        obs_side = np.dot(normal_p, obs_pos) + D_p
        for q in other.points:
            q_side = np.dot(normal_p, q.coords[:3]) + D_p
            if (obs_side > 0 and q_side < 1e-5) or (obs_side < 0 and q_side > -1e-5):
                return False
        return True

    def __lt__(self, other):
        min_xs, max_xs, min_ys, max_ys = self._get_2d_bbox()
        min_xo, max_xo, min_yo, max_yo = other._get_2d_bbox()
        if (max_xs < min_xo or min_xs > max_xo or max_ys < min_yo or min_ys > max_yo):
            return False 
            
        if self._test2_projections_sat(other):
            return False
            
        if self._test3_opposite_side(other):
            return True 
            
        if self._test4_same_side(other):
            return True 
            
        if other._test3_opposite_side(self):
            return False 
        if other._test4_same_side(self):
            return False
            
        return False

class VirtualCamera:
    def __init__(self):
        self.objects = []
        self.d = 1000

    def translateX(self, step):
        matrix = np.eye(4)
        matrix[0, 3] = -step
        for object in self.objects:
            object.transform(matrix)

    def translateY(self, step):
        matrix = np.eye(4)
        matrix[1, 3] = -step
        for object in self.objects:
            object.transform(matrix)

    def translateZ(self, step):
        matrix = np.eye(4)
        matrix[2, 3] = -step
        for object in self.objects:
            object.transform(matrix)

    def rotateX(self, deg):
        matrix = np.eye(4, dtype='float')
        matrix[1,1] = matrix[2,2] = np.cos(deg)
        matrix[2, 1] = np.sin(deg)
        matrix[1, 2] = -matrix[2, 1]

        for object in self.objects:
            object.transform(matrix)

    def rotateY(self, deg):
        matrix = np.eye(4, dtype='float')
        matrix[0,0] = matrix[2,2] = np.cos(deg)
        matrix[2, 0] = -np.sin(deg)
        matrix[0, 2] = -matrix[2, 0]

        for object in self.objects:
            object.transform(matrix)

    def rotateZ(self, deg):
        matrix = np.eye(4, dtype='float')
        matrix[0,0] = matrix[1,1] = np.cos(deg)
        matrix[1, 0] = np.sin(deg)
        matrix[0, 1] = -matrix[1, 0]

        for object in self.objects:
            object.transform(matrix)
    
    def change_focal_length(self, step):
        if self.d + step != 0:
            self.d = self.d + step

    def cast(self):
        matrix = np.diag([1.0, 1.0, 1.0, 0.0])
        matrix[3, 2] = 1.0 / self.d
        matrix2 = np.eye(4, dtype='float')
        matrix2[0, 3] = 500
        matrix2[1, 3] = 500
        matrix = matrix2 @ matrix
        self.objects.sort()
        casted = []
        for obj in self.objects:
            obj_copy = copy.deepcopy(obj)
            casted.append(obj_copy.transform(matrix))
        return casted

    def load_objects(self, path):
        file = Path(path)
        if not file.is_file():
            raise FileNotFoundError()
        
        vertices = []
        
        with open(file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue

                if parts[0] == 'v':
                    x = float(parts[1]) if len(parts) > 1 else 0.0
                    y = float(parts[2]) if len(parts) > 2 else 0.0
                    z = float(parts[3]) if len(parts) > 3 else 0.0
                    vertices.append(Point(x, y, z))

                elif parts[0] == 'f':
                    points = []
                    for token in parts[1:]:
                        v_index_str = token.split('/')[0]
                        try:
                            v_index = int(v_index_str)
                            if 0 < v_index <= len(vertices):
                                orig_point = vertices[v_index - 1]
                                points.append(copy.deepcopy(orig_point))
                        except ValueError:
                            pass
                    
                    if points:
                        self.objects.append(Polygon(points))