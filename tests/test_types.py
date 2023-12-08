from dataclasses import dataclass, field
from sys import version_info
from typing import Optional, Union

from pytest import mark, raises

from pydargs import parse


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


class TestBool:
    @dataclass
    class Config:
        a: bool
        b: bool = False
        c: bool = True
        d: bool = field(default=False, metadata=dict(as_flags=True))
        e: bool = field(default=True, metadata=dict(as_flags=True))
        z: int = 0

    def test_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "error: the following arguments are required: --a" in captured.err

    @mark.parametrize("arg, value", [("0", False), ("1", True), ("true", True), ("false", False)])
    def test_values(self, arg: str, value: bool):
        config = parse(self.Config, ["--a", arg])  # type: ignore
        assert config.a == value

    def test_defaults(self):
        config = parse(self.Config, ["--a", "false"])
        assert config.b is False
        assert config.c is True
        assert config.d is False
        assert config.e is True
        assert config.z == 0

    def test_invalid(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--a", "false", "--b", "invalid"])
        captured = capsys.readouterr()
        assert "error: argument --b: invalid bool value:" in captured.err

    def test_flags(self):
        config = parse(self.Config, ["--a", "false", "--d"])
        assert config.d is True

        config = parse(self.Config, ["--a", "false", "--no-d"])
        assert config.d is False

        config = parse(self.Config, ["--a", "false", "--e"])
        assert config.e is True

        config = parse(self.Config, ["--a", "false", "--no-e"])
        assert config.e is False

    def test_flag_argument(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--a", "false", "--e", "invalid"])
        captured = capsys.readouterr()
        assert "error: unrecognized arguments: invalid" in captured.err

    def test_bool_flag_no_default(self, capsys):
        @dataclass
        class TConfig:
            a: bool = field(metadata=dict(as_flags=True))

        with raises(SystemExit):
            parse(TConfig, [])
        captured = capsys.readouterr()
        assert "error: the following arguments are required: --a" in captured.err

        config = parse(TConfig, ["--a"])
        assert config.a is True
