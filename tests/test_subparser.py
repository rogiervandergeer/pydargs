from dataclasses import dataclass, field
from typing import Union
from sys import version_info

from pytest import mark, raises

from pydargs import parse


@dataclass
class Command1:
    a: int
    b: str = "abc"


@dataclass
class Command2:
    c: int = 42
    b: str = "abc"
    e: str = field(default="def", metadata=dict(positional=True))


@dataclass
class Command3:
    d: float
    e: list[str] = field(default_factory=lambda: ["def"])


@dataclass
class Command4:
    sub_action: Union[Command1, Command2]
    string4: str = "four"


class TestParseCommand:
    @dataclass
    class Config:
        command: Union[Command1, Command2]
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    @mark.parametrize(
        "help_string",
        [
            "usage: prog [-h] [--var VAR] [--flag | --no-flag]",
            "{Command1,command1,Command2,command2} ...",
            "command:  {Command1,command1,Command2,command2}",
        ],
    )
    def test_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out.replace("\n", "")

    @mark.skipif(version_info < (3, 10), reason="python3.9 prints a slightly different help message")
    @mark.parametrize(
        "help_string",
        ["prog Command1 [-h] --a A [--b B]", "options:  -h"],
    )
    def test_action_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["Command1", "--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out.replace("\n", "")
        assert "prog Command1 [-h] --a A [--b B]" in captured.out.replace("\n", "")

    def test_is_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: command" in captured.err

    def test_flag(self, capsys):
        config = parse(self.Config, ["--flag", "Command2"])
        assert isinstance(config.command, Command2)
        assert config.command.c == 42
        assert config.command.b == "abc"
        assert config.flag is True

        # Verify that the order matters
        with raises(SystemExit):
            parse(self.Config, ["Command2", "--flag"])
        captured = capsys.readouterr()
        assert "unrecognized arguments: --flag" in captured.err

    def test_action_args(self):
        config = parse(self.Config, ["Command1", "--a", "12"])
        assert config.command.a == 12
        assert config.flag is False

    def test_parse_positional(self):
        config = parse(self.Config, ["Command2", "positional", "--c", "12"])
        assert config.command.c == 12
        assert config.command.e == "positional"
        assert config.flag is False


class TestDoubleAction:
    @dataclass
    class Config:
        action: Union[Command1, Command2]
        second_action: Union[Command1, Command2, Command3] = field(default_factory=lambda: Command1(a=1))
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
        mode: Union[Command1, Command2, Command3] = field(default_factory=lambda: Command1(0))
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_is_not_required(self, capsys):
        config = parse(self.Config, [])
        assert config.mode == Command1(0)
        assert config.var == 12
        assert not config.flag

    def test_args(self, capsys):
        config = parse(self.Config, ["--flag", "Command3", "--d", "0"])
        assert isinstance(config.mode, Command3)
        assert config.mode.d == 0
        assert config.flag is True

        # Verify that the order matters
        with raises(SystemExit):
            parse(self.Config, ["Command2", "--flag"])
        captured = capsys.readouterr()
        assert "unrecognized arguments: --flag" in captured.err


class TestNestedAction:
    @dataclass
    class Config:
        mode: Union[Command1, Command2, Command3, Command4] = field(default_factory=lambda: Command1(0))
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_is_not_required(self, capsys):
        config = parse(self.Config, [])
        assert config.mode == Command1(0)
        assert config.var == 12
        assert not config.flag

    def test_args(self, capsys):
        config = parse(self.Config, ["Command4", "Command1", "--a", "-3"])
        assert isinstance(config.mode, Command4)
        assert isinstance(config.mode.sub_action, Command1)
        assert config.mode.sub_action.a == -3


class TestCollision:
    @dataclass
    class Config:
        command: Union[Command1, Command2]
        a: int = 2  # Command1 also has a field named 'a'
        d: int = 3

    def test_help(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["Command1", "--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert "prog Command1 [-h] --a A [--b B]" in captured.out.replace("\n", "")

    def test_collision(self, capsys):
        config = parse(self.Config, ["--a", "4", "--d", "4", "Command1", "--a", "3"])
        assert config.command.a == 3
        assert config.d == 4
        assert config.a == 4

    def test_other_option(self):
        config = parse(self.Config, ["--a", "4", "--d", "4", "Command2"])
        assert config.command.c == 42
        assert config.d == 4
        assert config.a == 4


class TestPositionalAndSubparser:
    @dataclass
    class Config:
        positional_1: str = field(metadata=dict(positional=True))
        action: Union[Command1, Command2]
        flag: bool = field(default=False, metadata=dict(as_flags=True))
        positional_2: str = field(default="five", metadata=dict(positional=True))

    def test_warn_positional_after_subparser(self, recwarn):
        _ = parse(
            self.Config,
            ["positional", "Command1", "--a", "12", "--b", "20"],
        )
        assert len(recwarn) == 1

    def test_parse_positional(self, recwarn):
        config = parse(
            self.Config,
            ["positional", "Command1", "--a", "12", "--b", "20"],
        )
        assert config.positional_1 == "positional"


class TestParseActionInNested:
    @dataclass
    class Config:
        sub: Command4
        var: int = 12
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    @mark.parametrize(
        "help_string",
        [
            "usage: prog [-h] [--sub-string4 SUB_STRING4] [--var VAR] [--flag | --no-flag]",
            "{Command1,command1,Command2,command2} ...",
            "action:  {Command1,command1,Command2,command2}",
        ],
    )
    def test_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out.replace("\n", "")

    def test_action_help(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["Command1", "--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert "prog Command1 [-h] --sub-a SUB_A [--sub-b SUB_B]" in captured.out.replace("\n", "")

    def test_is_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, [])
        captured = capsys.readouterr()
        assert "the following arguments are required: sub_sub_action" in captured.err

    def test_flag(self, capsys):
        config = parse(self.Config, ["--flag", "Command2"])
        assert isinstance(config.sub, Command4)
        assert isinstance(config.sub.sub_action, Command2)
        assert config.flag is True

        # Verify that the order matters
        with raises(SystemExit):
            parse(self.Config, ["Command2", "--flag"])
        captured = capsys.readouterr()
        assert "unrecognized arguments: --flag" in captured.err

    def test_action_args(self):
        config = parse(self.Config, ["Command1", "--sub-a", "12"])
        assert config.sub.sub_action.a == 12
        assert config.flag is False

    def test_parse_positional(self):
        config = parse(self.Config, ["Command2", "positional", "--sub-c", "12"])
        assert config.sub.sub_action.c == 12
        assert config.sub.sub_action.e == "positional"
        assert config.flag is False
