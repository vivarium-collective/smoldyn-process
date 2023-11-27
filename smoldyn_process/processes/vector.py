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

