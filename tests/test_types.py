from collections.abc import Sequence
from dataclasses import dataclass, field
from sys import version_info
from typing import Optional, Union

from pytest import mark, raises

from pydargs import parse


class TestBase:
    @dataclass
    class Config:
        a: int
        b: str
        c: float = 1.0
        d: int = 4
        e: str = "e"
        f: int = field(default_factory=lambda: 1)

    def test_a_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: --a, --b" in captured.err

    def test_default(self):
        config = parse(self.Config, ["--a", "1", "--b", "b"])
        assert config.a == 1
        assert config.b == "b"
        assert config.c == 1.0
        assert config.d == 4
        assert config.e == "e"
        assert config.f == 1

    @mark.parametrize(
        "args, attr, value",
        [(["--c", "1.23"], "c", 1.23), (["--d", "123"], "d", 123), (["--e", "f"], "e", "f"), (["--f", "2"], "f", 2)],
    )
    def test_args(self, args, attr, value):
        config = parse(self.Config, ["--a", "1", "--b", "b"] + args)
        assert getattr(config, attr) == value


class TestList:
    @dataclass
    class Config:
        a: list[int]
        b: list[str] = field(default_factory=lambda: [])
        c: Sequence[float] = field(default_factory=lambda: [1.0])
        d: Sequence[str] = ("a", "b")
        e: str = "dummy"

    def test_a_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: --a" in captured.err

    def test_default(self):
        config = parse(self.Config, ["--a", "1"])
        assert config.a == [1]
        assert config.b == []
        assert config.c == [1.0]
        assert config.d == ("a", "b")
        assert config.e == "dummy"

    def test_list_args(self):
        config = parse(self.Config, ["--a", "1", "--b", "a", "b", "--e", "value"])
        assert config.b == ["a", "b"]

    def test_sequence_args(self):
        config = parse(self.Config, ["--a", "1", "--c", "2.0", "2.5"])
        assert config.c == [2.0, 2.5]

    def test_sequence_args_tuple(self):
        config = parse(self.Config, ["--a", "1", "--d", "c"])
        assert config.d == ["c"]

    def test_invalid_type(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--a", "1", "--c", "abc"])
        captured = capsys.readouterr()
        assert "error: argument --c: invalid float value:" in captured.err


class TestUnion:
    @dataclass
    class Config:
        a: int
        b: Optional[int] = None
        c: Union[int, str] = "b"
        d: Union[None, int] = None
        e: Optional[Union[int, float]] = None
        f: float = 2.0

    def test_default(self):
        config = parse(self.Config, ["--a", "1"])
        assert config.a == 1
        assert config.b is None
        assert config.c == "b"
        assert config.d is None
        assert config.e is None

    def test_parse_optional(self):
        config = parse(self.Config, ["--a", "1", "--b", "2"])
        assert config.b == 2

    def test_parse_optional_invalid(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--a", "1", "--b", "2.0"])
        captured = capsys.readouterr()
        assert "argument --b: invalid typing.Optional[int] value:" in captured.err

    @mark.parametrize("value, result", [("1.0", "1.0"), ("11", 11)])
    def test_parse_union(self, value: str, result: Union[int, str]):
        config = parse(self.Config, ["--a", "1", "--c", value])  # type: ignore
        assert config.c == result

    def test_parse_inverted_optional(self):
        config = parse(self.Config, ["--a", "1", "--d", "2"])
        assert config.d == 2

    @mark.parametrize("value, result", [("1.0", 1.0), ("11", 11)])
    def test_parse_optional_union(self, value: str, result: Union[int, str]):
        config = parse(self.Config, ["--a", "1", "--e", value])  # type: ignore
        assert config.e == result


if version_info >= (3, 10):

    class TestUnionType:
        @dataclass
        class Config:
            a: int
            b: int | None = None
            c: int | str = "b"

        def test_default(self):
            config = parse(self.Config, ["--a", "1"])
            assert config.a == 1
            assert config.b is None
            assert config.c == "b"

        def test_parse_optional(self):
            config = parse(self.Config, ["--a", "1", "--b", "2"])
            assert config.b == 2

        def test_parse_optional_invalid(self, capsys):
            with raises(SystemExit):
                parse(self.Config, ["--a", "1", "--b", "2.0"])
            captured = capsys.readouterr()
            assert "argument --b: invalid int | None value:" in captured.err

        @mark.parametrize("value, result", [("1.0", "1.0"), ("11", 11)])
        def test_parse_union(self, value: str, result: Union[int, str]):
            config = parse(self.Config, ["--a", "1", "--c", value])  # type: ignore
            assert config.c == result
