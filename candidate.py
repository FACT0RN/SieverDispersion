from dataclasses import dataclass

@dataclass
class Candidate:
    id: int
    height: int
    N: int

    active: bool = True
