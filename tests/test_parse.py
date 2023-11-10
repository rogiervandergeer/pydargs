from dataclasses import dataclass
from pydargs import parse


@dataclass
class Config:
    a: int
    b: str = "abc"
    c: float = 0.1
    d: bool = False


class TestParse:
    def test_minimal(self):
        c = parse(Config, ["--a", "12"])
        assert isinstance(c, Config)
        assert c.a == 12
        assert c.b == "abc"
        assert c.c == 0.1
        assert c.d is False

    def test_str(self):
        c = parse(Config, ["--a", "12", "--b", "abcd"])
        assert c.b == "abcd"

    def test_float(self):
        c = parse(Config, ["--a", "12", "--c", "1.23"])
        assert c.c == 1.23

    def test_bool(self):
        c = parse(Config, ["--a", "12", "--d", "True"])
        assert c.d is True
