from math import sqrt
from abc import ABC, abstractmethod


class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.coordinates = self.set_coords(x, y)

    def position(self):
        return (self.x, self.y)

    @staticmethod
    def _set(param, val):
        param = val
        return param

    def set_x(self, val):
        return self._set(self.x, val)

    def set_y(self, val):
        return self._set(self.y, val)

    def set_coords(self, xVal, yVal):
        self.set_x(xVal)
        self.set_y(yVal)
        return [xVal, yVal]



class Agent:
    def __init__(self, *starting_coords):
        self.position = Position(*starting_coords)

    def change_position(self, *new_coords: tuple):
        return self.position.set_coords(*new_coords)



class Vector(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def length(self):
        pass

    @abstractmethod
    def represent(self):
        pass


class Vector1d(Vector):
    def __init__(self, val):
        super().__init__()
        self.val = val

    def length(self):
        return abs(self.val)

    def represent(self):
        return [self.val]
    

class Vector2d(Vector):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y

    def length(self):
        return sqrt(self.x**2 + self.y**2)


class Vector3d(Vector):
    def __init__(self, x, y, z):
        super().__init__()
        self.x = x
        self.y = y
        self.z = z

    def length(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)

    def represent(self):
        return [self.x, self.y, self.z]




v0 = Vector3d(3, 4, 7)
print(v0.length())












