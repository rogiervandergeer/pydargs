from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Literal

from pytest import raises

from pydargs import parse


@dataclass
class Config:
    a: int
    g: bool = field(metadata={"as_flags": True})
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


class TestParseChoices:
    def test_enum(self):
        class AnEnum(Enum):
            one = 1
            two = 2
            three = 3

        @dataclass
        class TConfig:
            an_enum: AnEnum

        with raises(SystemExit):
            parse(TConfig, [])

        t = parse(TConfig, ["--an-enum", "one"])
        assert t.an_enum == AnEnum.one

    def test_str_enum(self):
        class AnEnum(str, Enum):
            one = "one"
            two = "two"
            three = "three"

        @dataclass
        class TConfig:
            an_enum: AnEnum
            another_enum: AnEnum = AnEnum.three

        with raises(SystemExit):
            parse(TConfig, [])

        t = parse(TConfig, ["--an-enum", "one"])
        assert t.an_enum == AnEnum.one
        assert t.another_enum == AnEnum.three

        t = parse(TConfig, ["--an-enum", "one", "--another-enum", "two"])
        assert t.an_enum == AnEnum.one
        assert t.another_enum == AnEnum.two

    def test_str_literal(self):
        @dataclass
        class TConfig:
            a_literal: Literal["x", "y"] = "x"

        t = parse(TConfig, [])
        assert t.a_literal == "x"

        t = parse(TConfig, ["--a-literal", "y"])
        assert t.a_literal == "y"

        with raises(SystemExit):
            parse(TConfig, ["--a-literal", "z"])

    def test_int_literal(self):
        @dataclass
        class TConfig:
            a_literal: Literal[1, 2] = 1

        t = parse(TConfig, [])
        assert t.a_literal == 1

        t = parse(TConfig, ["--a-literal", "2"])
        assert t.a_literal == 2

        with raises(SystemExit):
            parse(TConfig, ["--a-literal", "3"])

    def test_fail_mixed_types(self):
        @dataclass
        class TConfig:
            a_literal: Literal[1, "2"] = 1

        with raises(NotImplementedError):
            parse(TConfig, [])


class TestParseDateTime:
    def test_required(self):
        @dataclass
        class TConfig:
            a_date: date

        with raises(SystemExit):
            parse(TConfig, [])

        t = parse(TConfig, ["--a-date", "1234-05-06"])
        assert t.a_date == date(1234, 5, 6)

    def test_optional(self):
        @dataclass
        class TConfig:
            a_date: date = date(2345, 6, 7)
            b_datetime: datetime = field(default_factory=datetime.now)

        t = parse(TConfig, [])
        assert t.a_date == date(2345, 6, 7)
        assert isinstance(t.b_datetime, datetime)

    def test_date_format(self):
        @dataclass
        class TConfig:
            a_date: date = field(metadata=dict(date_format="%m/%d/%Y"))
            b_datetime: datetime = field(default_factory=datetime.now, metadata=dict(date_format="%m/%d/%Y %H:%M"))

        t = parse(TConfig, ["--a-date", "8/16/1999"])
        assert t.a_date == date(1999, 8, 16)

        t = parse(TConfig, ["--a-date", "8/16/1999", "--b-datetime", "12/12/1991 23:45"])
        assert t.a_date == date(1999, 8, 16)
        assert t.b_datetime == datetime(1991, 12, 12, 23, 45)


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


class TestIgnore:
    @dataclass
    class Config:
        a: int = 5
        b: str = field(default="something", metadata={"ignore": True})
        c: bool = field(default=False, metadata=dict(ignore=False, as_flags=True))
        z: str = "dummy-for-late-binding-closure"

    def test_ignore_default(self):
        config = parse(self.Config, [])
        assert config.a == 5
        assert config.b == 5
        assert config.c == 5
        assert config.z == "dummy-for-late-binding-closure"

    def test_ignore_valid(self):
        config = parse(self.Config, ["--a", "1", "--c"])
        assert config.a == 1
        assert config.b == "something"
        assert config.c is True

    def test_ignore_invalid(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--b", "2"])
        captured = capsys.readouterr()
        assert "error: unrecognized arguments: --b 2" in captured.err
