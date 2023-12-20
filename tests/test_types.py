from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from sys import version_info
from typing import Optional, Union

from pytest import mark, raises

from pydargs import parse


class TestBase:
    @dataclass
    class Config:
        a: int = field(metadata=dict(positional=True))
        b: str
        c: float = 1.0
        d: int = 4
        e: str = field(metadata=dict(positional=True), default="e")
        f: int = field(default_factory=lambda: 1)

    def test_a_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: a, --b" in captured.err

    def test_default(self):
        config = parse(self.Config, ["1", "--b", "b"])
        assert config.a == 1
        assert config.b == "b"
        assert config.c == 1.0
        assert config.d == 4
        assert config.e == "e"
        assert config.f == 1

    def test_shuffled(self):
        config = parse(self.Config, ["--b", "b", "1"])
        assert config.a == 1
        assert config.b == "b"

    @mark.parametrize(
        "args, attr, value",
        [(["--c", "1.23"], "c", 1.23), (["--d", "123"], "d", 123), (["--f", "2"], "f", 2)],
    )
    def test_args(self, args, attr, value):
        config = parse(self.Config, ["1", "--b", "b"] + args)
        assert getattr(config, attr) == value

    def test_second_positional(self):
        config = parse(self.Config, ["1", "f", "--b", "b"])
        assert config.e == "f"


class TestBytes:
    @dataclass
    class Config:
        a: bytes = b"a"
        b: bytes = field(default=b"b", metadata=dict(encoding="ascii"))
        z: int = 12

    def test_default(self):
        config = parse(self.Config, [])
        assert config.a == b"a"
        assert config.b == b"b"
        assert config.z == 12

    def test_encoding(self):
        config = parse(self.Config, ["--a", "ꀀ"])
        assert config.a == b"\xea\x80\x80"

    def test_invalid_encoding(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--b", "ꀀ"])
        captured = capsys.readouterr()
        assert "argument --b: invalid ascii value: 'ꀀ'\n" in captured.err


class TestList:
    @dataclass
    class Config:
        a: list[int]
        b: list[str] = field(default_factory=lambda: [], metadata=dict(positional=False))
        c: list[str] = field(default_factory=lambda: [], metadata=dict(positional=True, help="an important argument"))
        d: Sequence[float] = field(default_factory=lambda: [1.0])
        e: Sequence[str] = ("a", "b")
        f: str = "dummy"

    def test_a_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: --a" in captured.err

    def test_default(self):
        config = parse(self.Config, ["--a", "1"])
        assert config.a == [1]
        assert config.b == []
        assert config.d == [1.0]
        assert config.e == ("a", "b")
        assert config.f == "dummy"

    def test_list_args(self):
        config = parse(self.Config, ["--a", "1", "--b", "a", "b", "--f", "value"])
        assert config.b == ["a", "b"]

    def test_sequence_args(self):
        config = parse(self.Config, ["--a", "1", "--d", "2.0", "2.5"])
        assert config.d == [2.0, 2.5]

    def test_sequence_args_tuple(self):
        config = parse(self.Config, ["--a", "1", "--e", "d"])
        assert config.e == ["d"]

    def test_positional_args(self):
        config = parse(self.Config, ["x", "y", "--a", "1"])
        assert config.c == ["x", "y"]

    def test_invalid_type(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--a", "1", "--d", "abc"])
        captured = capsys.readouterr()
        assert "error: argument --d: invalid float value:" in captured.err


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
        d: bool = field(default=True, metadata=dict(as_flags=True))
        extra: bool = field(default=False, metadata=dict(as_flags=True, short_option="-x"))
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
        assert config.d is True
        assert config.extra is False
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

        config = parse(self.Config, ["--a", "false", "--extra"])
        assert config.extra is True

        config = parse(self.Config, ["--a", "false", "--no-extra"])
        assert config.extra is False

        config = parse(self.Config, ["--a", "false", "-x"])
        assert config.extra is True

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


class TestDate:
    @dataclass
    class Config:
        a_date: date
        another_date: date = date(2345, 6, 7)
        a_datetime: datetime = field(default_factory=datetime.now)
        a_formatted_date: date = field(default=date(2345, 6, 7), metadata=dict(date_format="%m/%d/%Y"))
        a_formatted_datetime: datetime = field(
            default_factory=datetime.now, metadata=dict(date_format="%m/%d/%Y %H:%M")
        )

    def test_defaults(self):
        config = parse(self.Config, ["--a-date", "2000-01-01"])
        assert config.another_date == date(2345, 6, 7)
        assert config.a_formatted_date == date(2345, 6, 7)

    def test_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "error: the following arguments are required: --a-date" in captured.err

    def test_optional(self):
        config = parse(
            self.Config, ["--a-date", "2000-01-01", "--another-date", "2012-12-12", "--a-datetime", "2020-02-03 04:05"]
        )
        assert config.another_date == date(2012, 12, 12)
        assert config.a_datetime == datetime(2020, 2, 3, 4, 5)

    def test_date_format(self):
        config = parse(self.Config, ["--a-date", "2000-01-01", "--a-formatted-date", "10/20/2000"])
        assert config.a_formatted_date == date(2000, 10, 20)

    def test_datetime_format(self):
        config = parse(self.Config, ["--a-date", "2000-01-01", "--a-formatted-datetime", "8/16/1999 23:45"])
        assert config.a_formatted_datetime == datetime(1999, 8, 16, 23, 45)
