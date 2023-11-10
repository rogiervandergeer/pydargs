from dataclasses import dataclass, field
from pydargs import parse
from pytest import raises


@dataclass
class Config:
    a: int
    g: bool = field(metadata={"bool_arg_type": "flag_only"})
    b: str = "abc"
    c: float = 0.1
    d: bool = False
    f: bool = field(default=True)


class TestParse:
    def test_minimal(self):
        c = parse(Config, ["--a", "12"])
        assert isinstance(c, Config)
        assert c.a == 12
        assert c.b == "abc"
        assert c.c == 0.1
        assert c.d is False
        assert c.f is True
        assert c.g is False

    def test_str(self):
        c = parse(Config, ["--a", "12", "--b", "abcd"])
        assert c.b == "abcd"

    def test_float(self):
        c = parse(Config, ["--a", "12", "--c", "1.23"])
        assert c.c == 1.23


class TestParseBool:
    def test_bool_0(self):
        c = parse(Config, ["--a", "12", "--f", "0"])
        assert c.f is False

    def test_bool_1(self):
        c = parse(Config, ["--a", "12", "--f", "1"])
        assert c.f is True

    def test_bool_lower(self):
        with raises(SystemExit):
            parse(Config, ["--a", "12", "--f", "blabla"])

    def test_bool_upper_false(self):
        c = parse(Config, ["--a", "12", "--f", "False"])
        assert c.f is False

    def test_bool_upper_true(self):
        c = parse(Config, ["--a", "12", "--d", "TRUE"])
        assert c.d is True

    def test_bool_flag(self):
        c = parse(Config, ["--a", "12", "--g"])
        assert c.g is True

    def test_bool_no_flag(self):
        c = parse(Config, ["--a", "12", "--no-g"])
        assert c.g is False

    def test_bool_too_many_arguments(self):
        with raises(SystemExit):
            parse(Config, ["--a", "12", "--g", "help"])
