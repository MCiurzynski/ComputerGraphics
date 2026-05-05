import numpy as np
import copy
from pathlib import Path


class Point:
    def __init__(self, x, y, z):
        self.coords = np.array([x, y, z, 1], dtype="float").T

    def normalize(self):
        if self.coords[3] != 0:
            self.coords = self.coords / self.coords[3]

    def transform(self, matrix):
        self.coords = matrix @ self.coords
        return self

    def __str__(self):
        return str(self.coords)
    
    def copy(self):
        return Point(self.coords[0], self.coords[1], self.coords[2])


class Polygon:
    def __init__(self, points, hex):
        self.points = points
        self.color = self._get_rgb(hex)

    def _get_rgb(self, hex) -> tuple[int, int, int]:
        if len(hex) == 3:
            return hex
        if len(hex) != 6:
            return (100, 150, 200)
        return tuple(int(hex[i : i + 2], 16) for i in range(0, 6, 2))

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

    def get_depth(self):
        if not self.points:
            return 0
        return sum(p.coords[2] for p in self.points) / len(self.points)

    def get_normal_vector(self):
        v1 = self.points[1].coords[:3] - self.points[0].coords[:3]
        v2 = self.points[2].coords[:3] - self.points[0].coords[:3]
        norm = np.cross(v1, v2)
        return norm / np.linalg.norm(norm)

    def front(self, other):
        normal = self.get_normal_vector()
        first_point = self.points[0]
        for point in other.points:
            v = point.coords[:3] - first_point.coords[:3]
            if normal @ v < 0:
                return False
        return True

    def back(self, other):
        normal = self.get_normal_vector()
        first_point = self.points[0]
        for point in other.points:
            v = point.coords[:3] - first_point.coords[:3]
            if normal @ v > 0:
                return False
        return True

    def cut(self, other):
        normal = self.get_normal_vector()
        P0 = self.points[0].coords[:3]

        front_points = []
        back_points = []

        for i in range(len(other.points)):
            A = other.points[i]
            B = other.points[(i + 1) % len(other.points)]

            dA = normal @ (A.coords[:3] - P0)
            dB = normal @ (B.coords[:3] - P0)

            sideA = 1 if dA > 0 else (-1 if dA < -0 else 0)
            sideB = 1 if dB > 0 else (-1 if dB < -0 else 0)

            if sideA >= 0:
                front_points.append(A)
            if sideA <= 0:
                back_points.append(A)

            if (sideA == 1 and sideB == -1) or (sideA == -1 and sideB == 1):
                t = dA / (dA - dB)

                I_coords = A.coords + t * (B.coords - A.coords)

                I = Point(I_coords[0], I_coords[1], I_coords[2])
                front_points.append(I)
                back_points.append(I)

        return Polygon(front_points), Polygon(back_points)
    
    def copy(self):
        points = [point.copy() for point in self.points]
        return Polygon(points, self.color)

    def clip_against_plane(self, plane_point, plane_normal):
        if not self.points:
            return None

        plane_point = np.array(plane_point)
        plane_normal = np.array(plane_normal)
        
        clipped_points = []
        
        for i in range(len(self.points)):
            A = self.points[i]
            dA = plane_normal @ (A.coords[:3] - plane_point)
            if dA >= 0:
                clipped_points.append(A)
                
        if len(clipped_points) >= 3:
            return Polygon(clipped_points, self.color)
        return None
    

class BSPNode:
    def __init__(self, polygon, left=None, right=None):
        self.polygon = polygon
        self.left = left
        self.right = right


class BSP:
    def __init__(self, polygons_list):
        self.head = self._create_tree(polygons_list)

    def _create_tree(self, polygon_list):
        if len(polygon_list) == 0:
            return None
        if len(polygon_list) == 1:
            return BSPNode(polygon_list[0])
        root = polygon_list.pop()
        front_list = []
        back_list = []
        for polygon in polygon_list:
            if root.front(polygon):
                front_list.append(polygon)
            elif root.back(polygon):
                back_list.append(polygon)
            else:
                front, back = root.cut(polygon)
                if len(front.points) >= 3:
                    front_list.append(front)
                if len(back.points) >= 3:
                    back_list.append(back)
        left = self._create_tree(front_list)
        right = self._create_tree(back_list)
        return BSPNode(root, left, right)


class VirtualCamera:
    def __init__(self):
        self.bsp_tree = None
        self.d = 1000

    def _apply_transform(self, node, matrix):
        if node is None:
            return
        node.polygon.transform(matrix)
        self._apply_transform(node.left, matrix)
        self._apply_transform(node.right, matrix)

    def translateX(self, step):
        matrix = np.eye(4)
        matrix[0, 3] = -step
        if self.bsp_tree:
            self._apply_transform(self.bsp_tree.head, matrix)

    def translateY(self, step):
        matrix = np.eye(4)
        matrix[1, 3] = -step
        if self.bsp_tree:
            self._apply_transform(self.bsp_tree.head, matrix)

    def translateZ(self, step):
        matrix = np.eye(4)
        matrix[2, 3] = -step
        if self.bsp_tree:
            self._apply_transform(self.bsp_tree.head, matrix)

    def rotateX(self, deg):
        matrix = np.eye(4, dtype="float")
        matrix[1, 1] = matrix[2, 2] = np.cos(deg)
        matrix[2, 1] = np.sin(deg)
        matrix[1, 2] = -matrix[2, 1]
        if self.bsp_tree:
            self._apply_transform(self.bsp_tree.head, matrix)

    def rotateY(self, deg):
        matrix = np.eye(4, dtype="float")
        matrix[0, 0] = matrix[2, 2] = np.cos(deg)
        matrix[2, 0] = -np.sin(deg)
        matrix[0, 2] = -matrix[2, 0]
        if self.bsp_tree:
            self._apply_transform(self.bsp_tree.head, matrix)

    def rotateZ(self, deg):
        matrix = np.eye(4, dtype="float")
        matrix[0, 0] = matrix[1, 1] = np.cos(deg)
        matrix[1, 0] = np.sin(deg)
        matrix[0, 1] = -matrix[1, 0]
        if self.bsp_tree:
            self._apply_transform(self.bsp_tree.head, matrix)

    def change_focal_length(self, step):
        if self.d + step != 0:
            self.d = self.d + step

    def _get_sorted_polygons(self, node):
        if node is None:
            return []

        camera_pos = np.array([0.0, 0.0, 0.0])
        normal = node.polygon.get_normal_vector()
        p0 = node.polygon.points[0].coords[:3]

        val = normal @ (camera_pos - p0)

        polys = []
        if val > 0:
            polys.extend(self._get_sorted_polygons(node.right))
            polys.append(node.polygon)
            polys.extend(self._get_sorted_polygons(node.left))
        else:
            polys.extend(self._get_sorted_polygons(node.left))
            polys.append(node.polygon)
            polys.extend(self._get_sorted_polygons(node.right))

        return polys

    def cast(self):
        matrix = np.diag([1.0, 1.0, 1.0, 0.0])
        matrix[3, 2] = 1.0 / self.d
        matrix2 = np.eye(4, dtype='float')
        matrix2[0, 3] = 500
        matrix2[1, 3] = 500
        matrix = matrix2 @ matrix
        
        if not self.bsp_tree:
            return []
            
        sorted_polygons = self._get_sorted_polygons(self.bsp_tree.head)
        
        near_plane_point = [0.0, 0.0, 1.0] 
        near_plane_normal = [0.0, 0.0, 1.0]
        
        casted = []
        for pol in sorted_polygons:
            pol_copy = pol.copy()
            
            clipped_obj = pol_copy.clip_against_plane(near_plane_point, near_plane_normal)
            
            if clipped_obj is not None:
                casted.append(clipped_obj.transform(matrix))
                
        return casted

    def load_objects(self, path):
        file = Path(path)
        if not file.is_file():
            raise FileNotFoundError()
        objects = []
        palette = []
        vertices = []

        with open(file, "r") as f:
            lines = f.read().replace(";", "\n").splitlines()

            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue

                if parts[0] == "v":
                    x = float(parts[1]) if len(parts) > 1 else 0.0
                    y = float(parts[2]) if len(parts) > 2 else 0.0
                    z = float(parts[3]) if len(parts) > 3 else 0.0
                    vertices.append(Point(x, y, z))

                elif parts[0] == "c":
                    value = parts[1].lstrip("#")
                    palette.append(value)

                elif parts[0] == "f":
                    points = []
                    hex = "6699CC"
                    for token in parts[1:-1]:
                        v_index_str = token.split("/")[0]
                        try:
                            v_index = int(v_index_str)
                            if 0 < v_index <= len(vertices):
                                orig_point = vertices[v_index - 1]
                                points.append(copy.deepcopy(orig_point))
                        except ValueError:
                            pass

                    color_id_str = parts[-1]
                    try:
                        color_id = int(color_id_str)
                        hex = palette[color_id - 1]
                    except ValueError:
                        pass

                    if len(points) >= 3:
                        objects.append(Polygon(points, hex))

        self.bsp_tree = BSP(objects)

