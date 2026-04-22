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