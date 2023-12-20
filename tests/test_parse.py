import sys
from dataclasses import dataclass, field
from enum import Enum
from json import loads
from typing import Literal, Optional

from pytest import raises

from pydargs import parse


class TestParseCustomParser:
    def test_parser_optional(self):
        @dataclass
        class TConfig:
            arg: Optional[list[int]] = field(default=None, metadata=dict(parser=loads))

        t = parse(TConfig, [])
        assert t.arg is None

        t = parse(TConfig, ["--arg", "[1, 2]"])
        assert t.arg == [1, 2]

        t = parse(TConfig, ["--arg", '{"1": 2}'])
        assert t.arg == {"1": 2}

    def test_parser_required(self, capsys):
        @dataclass
        class TConfig:
            arg: list[int] = field(metadata=dict(parser=loads))

        with raises(SystemExit):
            parse(TConfig, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: --arg" in captured.err

        t = parse(TConfig, ["--arg", "[1, 2]"])
        assert t.arg == [1, 2]

    def test_parser_invalid(self, capsys):
        @dataclass
        class TConfig:
            arg: list[int] = field(metadata=dict(parser=loads))

        with raises(SystemExit):
            parse(TConfig, ["--arg", "[1, 2"])
        captured = capsys.readouterr()
        assert "argument --arg: invalid loads value: '[1, 2" in captured.err


class TestParseChoices:
    def test_enum(self, capsys):
        class AnEnum(Enum):
            one = 1
            two = 2
            three = 3

        @dataclass
        class TConfig:
            an_enum: AnEnum

        with raises(SystemExit):
            parse(TConfig, [])
        captured = capsys.readouterr()
        assert "error: the following arguments are required: --an-enum" in captured.err

        t = parse(TConfig, ["--an-enum", "one"])
        assert t.an_enum == AnEnum.one

    def test_str_enum(self, capsys):
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
        captured = capsys.readouterr()
        assert "error: the following arguments are required: --an-enum" in captured.err

        t = parse(TConfig, ["--an-enum", "one"])
        assert t.an_enum == AnEnum.one
        assert t.another_enum == AnEnum.three

        t = parse(TConfig, ["--an-enum", "one", "--another-enum", "two"])
        assert t.an_enum == AnEnum.one
        assert t.another_enum == AnEnum.two

    def test_str_literal(self, capsys):
        @dataclass
        class TConfig:
            a_literal: Literal["x", "y"] = "x"

        t = parse(TConfig, [])
        assert t.a_literal == "x"

        t = parse(TConfig, ["--a-literal", "y"])
        assert t.a_literal == "y"

        with raises(SystemExit):
            parse(TConfig, ["--a-literal", "z"])
        captured = capsys.readouterr()
        assert "error: argument --a-literal: invalid choice: 'z'" in captured.err

    def test_int_literal(self, capsys):
        @dataclass
        class TConfig:
            a_literal: Literal[1, 2] = 1

        t = parse(TConfig, [])
        assert t.a_literal == 1

        t = parse(TConfig, ["--a-literal", "2"])
        assert t.a_literal == 2

        with raises(SystemExit):
            parse(TConfig, ["--a-literal", "3"])
        captured = capsys.readouterr()
        assert "error: argument --a-literal: invalid choice: 3" in captured.err

    def test_fail_mixed_types(self):
        @dataclass
        class TConfig:
            a_literal: Literal[1, "2"] = 1

        with raises(NotImplementedError):
            parse(TConfig, [])


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


class TestIgnoreArg:
    @dataclass
    class Config:
        a: int = 5
        b: str = field(default="something", metadata={"ignore_arg": True})
        c: bool = field(default=False, metadata=dict(ignore_arg=False, as_flags=True))
        z: str = "dummy"

    def test_ignore_default(self):
        config = parse(self.Config, [])
        assert config.a == 5
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"

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

    def test_ignore_invalid_no_default(self, capsys):
        @dataclass
        class TConfig:
            a: str = field(metadata={"ignore_arg": True})
            b: int = 5

        with raises(TypeError):
            parse(TConfig, [])


class TestPositional:
    @dataclass
    class Config:
        a: Literal["a", "b"] = field(default="a", metadata={"positional": True})
        z: str = "dummy"

    def test_ignore_default(self):
        config = parse(self.Config, [])
        assert config.a == "a"
        assert config.z == "dummy"


class TestSysArgv:
    @dataclass
    class Config:
        positional: str = field(default="positional", metadata=dict(positional=True))
        a: int = 5
        z: str = "dummy"

    def test_empty_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["name_of_program"])
        config = parse(self.Config)
        assert config.positional == "positional"
        assert config.a == 5
        assert config.z == "dummy"

    def test_non_empty_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["name_of_program", "--a", "3"])
        config = parse(self.Config)
        assert config.positional == "positional"
        assert config.a == 3
        assert config.z == "dummy"

    def test_with_positional_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["name_of_program", "--a", "3", "positional_value"])
        config = parse(self.Config)
        assert config.positional == "positional_value"
        assert config.a == 3
        assert config.z == "dummy"


class TestKwargs:
    @dataclass
    class Config:
        a: int = 5
        some_long_argument: str = "something"
        z: str = "dummy"

    def test_with_args_and_kwargs(self):
        config = parse(self.Config, ["--a", "1", "--z", "2"], prog="pydargs")
        assert config.a == 1
        assert config.z == "2"

    def test_with_kwargs(self):
        config = parse(self.Config, [], allow_abbrev=False)
        assert config.a == 5
        assert config.z == "dummy"

    def test_allow_abbrev(self):
        config = parse(self.Config, ["--so", "something_else"])
        assert config.some_long_argument == "something_else"
        assert config.a == 5
        assert config.z == "dummy"

    def test_disallow_abbrev(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--so", "something_else"], allow_abbrev=False)
        captured = capsys.readouterr()
        assert "error: unrecognized arguments: --so something_else" in captured.err
