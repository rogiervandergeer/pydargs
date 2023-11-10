from dataclasses import dataclass, field
from datetime import date, datetime

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
