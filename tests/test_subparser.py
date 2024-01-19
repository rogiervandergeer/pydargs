from dataclasses import dataclass, field
from typing import Union
from sys import version_info

from pytest import mark, raises

from pydargs import parse


@dataclass
class Action1:
    a: int
    b: str = "abc"


@dataclass
class Action2:
    c: int = 42
    b: str = "abc"
    e: str = field(default="def", metadata=dict(positional=True))


@dataclass
class Action3:
    d: float
    e: list[str] = field(default_factory=lambda: ["def"])


@dataclass
class Action4:
    sub_action: Union[Action1, Action2]
    string4: str = "four"


class TestParseAction:
    @dataclass
    class Config:
        action: Union[Action1, Action2]
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    @mark.parametrize(
        "help_string",
        [
            "usage: prog [-h] [--var VAR] [--flag | --no-flag]",
            "{Action1,action1,Action2,action2} ...",
            "action:  {Action1,action1,Action2,action2}",
        ],
    )
    def test_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out.replace("\n", "")

    @mark.skipif(version_info < (3, 10), reason="python3.9 prints s slightly different help")
    @mark.parametrize(
        "help_string",
        ["prog Action1 [-h] --a A [--b B]", "options:  -h"],
    )
    def test_action_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["Action1", "--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        for line in captured.out.split("\n"):
            print(line)
        assert help_string in captured.out.replace("\n", "")
        assert "prog Action1 [-h] --a A [--b B]" in captured.out.replace("\n", "")

    def test_is_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: action" in captured.err

    def test_flag(self, capsys):
        config = parse(self.Config, ["--flag", "Action2"])
        assert isinstance(config.action, Action2)
        assert config.action.c == 42
        assert config.action.b == "abc"
        assert config.flag is True

        # Verify that the order matters
        with raises(SystemExit):
            parse(self.Config, ["Action2", "--flag"])
        captured = capsys.readouterr()
        assert "unrecognized arguments: --flag" in captured.err

    def test_action_args(self):
        config = parse(self.Config, ["Action1", "--a", "12"])
        assert config.action.a == 12
        assert config.flag is False

    def test_parse_positional(self):
        config = parse(self.Config, ["Action2", "positional", "--c", "12"])
        assert config.action.c == 12
        assert config.action.e == "positional"
        assert config.flag is False


class TestDoubleAction:
    @dataclass
    class Config:
        action: Union[Action1, Action2]
        second_action: Union[Action1, Action2, Action3] = field(default_factory=lambda: Action1(a=1))
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_is_not_allowed(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "error: cannot have multiple subparser arguments" in captured.err


class TestActionDefault:
    @dataclass
    class Config:
        mode: Union[Action1, Action2, Action3] = field(default_factory=lambda: Action1(0))
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_is_not_required(self, capsys):
        config = parse(self.Config, [])
        assert config.mode == Action1(0)
        assert config.var == 12
        assert not config.flag

    def test_args(self, capsys):
        config = parse(self.Config, ["--flag", "Action3", "--d", "0"])
        assert isinstance(config.mode, Action3)
        assert config.mode.d == 0
        assert config.flag is True

        # Verify that the order matters
        with raises(SystemExit):
            parse(self.Config, ["Action2", "--flag"])
        captured = capsys.readouterr()
        assert "unrecognized arguments: --flag" in captured.err


class TestNestedAction:
    @dataclass
    class Config:
        mode: Union[Action1, Action2, Action3, Action4] = field(default_factory=lambda: Action1(0))
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_is_not_required(self, capsys):
        config = parse(self.Config, [])
        assert config.mode == Action1(0)
        assert config.var == 12
        assert not config.flag

    def test_args(self, capsys):
        config = parse(self.Config, ["Action4", "Action1", "--a", "-3"])
        assert isinstance(config.mode, Action4)
        assert isinstance(config.mode.sub_action, Action1)
        assert config.mode.sub_action.a == -3


class TestCollision:
    @dataclass
    class Config:
        action: Union[Action1, Action2]
        a: int = 2
        d: int = 3

    def test_help(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["Action1", "--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert "prog Action1 [-h] --a A [--b B]" in captured.out.replace("\n", "")

    def test_collision(self, capsys):
        config = parse(self.Config, ["--a", "4", "--d", "4", "Action1", "--a", "3"])
        assert config.action.a == 3
        assert config.d == 4
        assert config.a == 4

    def test_other_option(self):
        config = parse(self.Config, ["--a", "4", "--d", "4", "Action2"])
        assert config.action.c == 42
        assert config.d == 4
        assert config.a == 4


class TestPositionalAndSubparser:
    @dataclass
    class Config:
        positional_1: str = field(metadata=dict(positional=True))
        action: Union[Action1, Action2]
        flag: bool = field(default=False, metadata=dict(as_flags=True))
        positional_2: str = field(default="five", metadata=dict(positional=True))

    def test_warn_positional_after_subparser(self, recwarn):
        _ = parse(
            self.Config,
            ["positional", "Action1", "--a", "12", "--b", "20"],
        )
        assert len(recwarn) == 1

    def test_parse_positional(self, recwarn):
        config = parse(
            self.Config,
            ["positional", "Action1", "--a", "12", "--b", "20"],
        )
        assert config.positional_1 == "positional"


class TestParseActionInNested:
    @dataclass
    class Config:
        sub: Action4
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    @mark.parametrize(
        "help_string",
        [
            "usage: prog [-h] [--sub-string4 SUB_STRING4] [--var VAR] [--flag | --no-flag]",
            "{Action1,action1,Action2,action2} ...",
            "action:  {Action1,action1,Action2,action2}",
        ],
    )
    def test_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out.replace("\n", "")

    def test_action_help(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["Action1", "--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert "prog Action1 [-h] --sub-a SUB_A [--sub-b SUB_B]" in captured.out.replace("\n", "")

    def test_is_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: sub_sub_action" in captured.err

    def test_flag(self, capsys):
        config = parse(self.Config, ["--flag", "Action2"])
        assert isinstance(config.sub, Action4)
        assert isinstance(config.sub.sub_action, Action2)
        assert config.flag is True

        # Verify that the order matters
        with raises(SystemExit):
            parse(self.Config, ["Action2", "--flag"])
        captured = capsys.readouterr()
        assert "unrecognized arguments: --flag" in captured.err

    def test_action_args(self):
        config = parse(self.Config, ["Action1", "--sub-a", "12"])
        assert config.sub.sub_action.a == 12
        assert config.flag is False

    def test_parse_positional(self):
        config = parse(self.Config, ["Action2", "positional", "--sub-c", "12"])
        assert config.sub.sub_action.c == 12
        assert config.sub.sub_action.e == "positional"
        assert config.flag is False
