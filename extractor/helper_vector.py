from dataclasses import dataclass

@dataclass
class Vector4:
    X:float
    Y:float
    Z:float
    W:float
    
    def __str__(self) -> str:
        return f"{self.X} {self.Y} {self.Z} {self.W}"

    def __getitem__(self, key):
        return [self.X, self.Y, self.Z, self.W][key]

@dataclass
class Vector3:
    X:float
    Y:float
    Z:float
    
    def __str__(self) -> str:
        return f"{self.X} {self.Y} {self.Z}"

    def __getitem__(self, key):
        return [self.X, self.Y, self.Z][key]

@dataclass
class Vector2:
    X:float
    Y:float

    @property
    def U(self):
        return self.X
    @U.setter
    def set_U(self, u:float):
        self.X = u

    @property
    def V(self):
        return self.Y
    @V.setter
    def set_V(self, v:float):
        self.Y = v

    def __str__(self) -> str:
        return f"{self.X} {self.Y}"
    
    def __getitem__(self, key):
        return [self.X, self.Y][key]

# need to check the Z for position/normal, might be oriented wrong direction
class PositionVector(Vector3):
    def __str__(self) -> str:
        return f"v {-self.X} {-self.Y} {self.Z}" 

class TextureVector(Vector2):
    def __str__(self) -> str:
        return f"vt {self.U} {-self.V}" 

class NormalVector(Vector3):
    def __str__(self) -> str:
        return f"vn {-self.X} {-self.Y} {self.Z}"

class ColorVector(Vector4):
    def __str__(self) -> str:
        return f'# vc {self.X} {self.Y} {self.Z} {self.W}'