from dataclasses import dataclass, field
from pydargs import parse
from pytest import raises


@dataclass
class Config:
    a: int
    b: str = "abc"
    c: float = 0.1
    d: bool = False
    e: list[int] = field(default_factory=lambda: [])


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

    def test_list(self):
        c = parse(Config, ["--a", "12", "--e", "1", "2", "3"])
        assert c.e == [1, 2, 3]


class TestParseLists:
    def test_parse_list_default(self):
        @dataclass
        class TConfig:
            arg: list[str] = field(default_factory=lambda: [])

        t = parse(TConfig, [])
        assert t.arg == []

    def test_parse_list(self):
        @dataclass
        class TConfig:
            arg: list[str] = field(default_factory=lambda: [])

        t = parse(TConfig, ["--arg", "1", "2"])
        assert t.arg == ["1", "2"]

    def test_parse_list_int(self):
        @dataclass
        class TConfig:
            arg: list[int] = field(default_factory=lambda: [])

        t = parse(TConfig, ["--arg", "1", "2"])
        assert t.arg == [1, 2]

    def test_parse_list_required(self):
        @dataclass
        class TConfig:
            arg: list[int] = field()

        with raises(NotImplementedError):
            parse(TConfig, ["--arg", "1", "2"])


class TestNotImplemented:
    def test_set(self):
        @dataclass
        class TConfig:
            a: set[int]

        with raises(NotImplementedError):
            parse(TConfig, ["--a", "1", "1", "2"])

    def test_tuple(self):
        @dataclass
        class TConfig:
            a: tuple[str]

        with raises(NotImplementedError):
            parse(TConfig, ["--a", "1", "1", "2"])
