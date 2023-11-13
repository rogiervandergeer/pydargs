"""
TODO:

add underscores in names
test nested (double, tripple)
defaults and required
underscores naam van classes en fields en in string value of list fields
"""

from dataclasses import dataclass, field

from pydargs import parse


@dataclass
class TConfigLevel3:
    d: list[str] = field(default_factory=lambda: ["hi", "under_score"])


@dataclass
class TConfigLevel2:
    level_3: TConfigLevel3
    c: int = 5
    b: int = 4


@dataclass
class TConfigLevel1:
    level_2: TConfigLevel2
    b: int


@dataclass
class TConfigLevel0:
    level1: TConfigLevel1
    a: int = 3


class TestNested:
    def test_nested(self):
        config = parse(TConfigLevel0, ["--a", "12", "--level1-b", "13", "--level1-level-2-c", "20"])
        assert config.a == 12
        assert config.level1.b == 13
        assert config.level1.level_2.b == 4
        assert config.level1.level_2.c == 20
        assert config.level1.level_2.level_3.d == ['hi', 'under_score']