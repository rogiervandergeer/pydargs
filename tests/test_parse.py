import sys
from dataclasses import dataclass, field
from json import loads
from typing import Literal, Optional

from pytest import mark, raises

from pydargs import parse


class TestParseCustomParser:
    def test_parser_optional(self) -> None:
        @dataclass
        class TConfig:
            arg: Optional[list[int]] = field(default=None, metadata=dict(parser=loads))

        t = parse(TConfig, [])
        assert t.arg is None

        t = parse(TConfig, ["--arg", "[1, 2]"])
        assert t.arg == [1, 2]

        t = parse(TConfig, ["--arg", '{"1": 2}'])
        assert t.arg == {"1": 2}

    def test_parser_required(self, capsys) -> None:
        @dataclass
        class TConfig:
            arg: list[int] = field(metadata=dict(parser=loads))

        with raises(SystemExit):
            parse(TConfig, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: --arg" in captured.err

        t = parse(TConfig, ["--arg", "[1, 2]"])
        assert t.arg == [1, 2]

    def test_parser_invalid(self, capsys) -> None:
        @dataclass
        class TConfig:
            arg: list[int] = field(metadata=dict(parser=loads))

        with raises(SystemExit):
            parse(TConfig, ["--arg", "[1, 2"])
        captured = capsys.readouterr()
        assert "argument --arg: invalid loads value: '[1, 2" in captured.err


class TestNotImplemented:
    def test_set(self) -> None:
        @dataclass
        class TConfig:
            a: set[int]

        with raises(NotImplementedError):
            parse(TConfig, ["--a", "1", "1", "2"])

    def test_tuple(self) -> None:
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
        d: str = field(init=False)
        z: str = "dummy"

        def __post_init__(self):
            self.d = "post_init"

    def test_ignore_default(self) -> None:
        config = parse(self.Config, [])
        assert config.a == 5
        assert config.b == "something"
        assert config.c is False
        assert config.d == "post_init"
        assert config.z == "dummy"

    def test_ignore_valid(self) -> None:
        config = parse(self.Config, ["--a", "1", "--c"])
        assert config.a == 1
        assert config.b == "something"
        assert config.c is True

    @mark.parametrize("args", [["--b", "2"], ["--d", "something_else"]])
    def test_ignore_invalid(self, capsys, args) -> None:
        with raises(SystemExit):
            parse(self.Config, args)
        captured = capsys.readouterr()
        assert f"error: unrecognized arguments: {' '.join(args)}" in captured.err

    def test_ignore_invalid_no_default(self, capsys) -> None:
        @dataclass
        class TConfig:
            a: str = field(metadata={"ignore_arg": True})
            b: int = 5

        with raises(TypeError):
            parse(TConfig, [])

    def test_property_with_init_false_no_default(self) -> None:
        @dataclass
        class Config:
            a: int = 5
            d: str = field(init=False)
            z: str = "dummy"

        config = parse(Config, [])
        assert getattr(config, "d", None) is None


class TestPositional:
    @dataclass
    class Config:
        a: Literal["a", "b"] = field(default="a", metadata={"positional": True})
        z: str = field(default="dummy")

    def test_ignore_default(self) -> None:
        config = parse(self.Config, [])
        assert config.a == "a"
        assert config.z == "dummy"

    @mark.parametrize("args", [["b", "--z", "Z"], ["--z", "Z", "b"]])
    def test_order(self, args: list[str]) -> None:
        config = parse(self.Config, args)  # type: ignore
        assert config.a == "b"
        assert config.z == "Z"

    def test_positional_with_default(self) -> None:
        @dataclass
        class Config:
            positional: int = field(default=123, metadata=dict(positional=True))

        config = parse(Config, ["321"])
        assert config.positional == 321

        config = parse(Config, [])
        assert config.positional == 123

    def test_positional_with_default_factory(self) -> None:
        @dataclass
        class Config:
            positional: int = field(default_factory=lambda: 123, metadata=dict(positional=True))

        config = parse(Config, ["321"])
        assert config.positional == 321

        config = parse(Config, [])
        assert config.positional == 123

    def test_default_factory_modification(self) -> None:
        @dataclass
        class Config:
            positional: list[int] = field(default_factory=lambda: [123], metadata=dict(positional=True))

        config_1 = parse(Config, [])
        config_1.positional.append(456)
        assert config_1.positional == [123, 456]

        config_2 = parse(Config, [])
        assert config_2.positional == [123]

    def test_list_positional(self) -> None:
        @dataclass
        class Config:
            positional: list[int] = field(default_factory=lambda: [1, 2, 3], metadata=dict(positional=True))

        config = parse(Config, ["3", "2", "1"])
        assert config.positional == [3, 2, 1]

        config = parse(Config, [])
        assert config.positional == [1, 2, 3]


class TestHelp:
    @dataclass
    class Config:
        an_integer: int = field(metadata={"positional": True, "metavar": "I"})
        a_string: str = "abc"
        a_literal: Literal["a", "b"] = field(default="a", metadata={"positional": True, "help": "a or b"})
        flag: bool = field(default=True, metadata={"as_flags": True, "short_option": "-f"})
        another_string: str = field(default="xyz", metadata={"metavar": "AS"})

    @mark.parametrize(
        "help_string",
        [
            "usage: prog [-h] [--a-string A_STRING] [-f | --flag | --no-flag]",
            "  {a,b}                 a or b (default: a)",
            "  --a-string A_STRING   (default: abc)",
            "  -f, --flag, --no-flag",  # The default may come on the next line
            "  --another-string AS   (default: xyz)",
        ],
    )
    def test_help(self, capsys, help_string: str) -> None:
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out.replace("\n", "")

    def test_short_option_must_have_dash(self) -> None:
        @dataclass
        class InvalidConfig:
            an_integer: int = field(metadata={"short_option": "s"})

        with raises(ValueError):
            parse(InvalidConfig, [])


class TestSysArgv:
    @dataclass
    class Config:
        positional: str = field(default="positional", metadata=dict(positional=True))
        a: int = 5
        z: str = "dummy"

    def test_empty_argv(self, monkeypatch) -> None:
        monkeypatch.setattr(sys, "argv", ["name_of_program"])
        config = parse(self.Config)
        assert config.positional == "positional"
        assert config.a == 5
        assert config.z == "dummy"

    def test_non_empty_argv(self, monkeypatch) -> None:
        monkeypatch.setattr(sys, "argv", ["name_of_program", "--a", "3"])
        config = parse(self.Config)
        assert config.positional == "positional"
        assert config.a == 3
        assert config.z == "dummy"

    def test_with_positional_argv(self, monkeypatch) -> None:
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

    def test_with_args_and_kwargs(self) -> None:
        config = parse(self.Config, ["--a", "1", "--z", "2"], prog="pydargs")
        assert config.a == 1
        assert config.z == "2"

    def test_with_kwargs(self) -> None:
        config = parse(self.Config, allow_abbrev=False)
        assert config.a == 5
        assert config.z == "dummy"

    def test_allow_abbrev(self) -> None:
        config = parse(self.Config, ["--so", "something_else"])
        assert config.some_long_argument == "something_else"
        assert config.a == 5
        assert config.z == "dummy"

    def test_disallow_abbrev(self, capsys) -> None:
        with raises(SystemExit):
            parse(self.Config, ["--so", "something_else"], allow_abbrev=False)
        captured = capsys.readouterr()
        assert "error: unrecognized arguments: --so something_else" in captured.err
