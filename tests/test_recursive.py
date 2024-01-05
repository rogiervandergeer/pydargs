from argparse import ArgumentError
from dataclasses import dataclass, field

from pytest import mark, raises, warns

from pydargs import parse


@dataclass
class SubConfig:
    a: int = 42
    b: str = field(default="abc", metadata=dict(help="a string"))


@dataclass
class SubConfigWithRequiredField:
    a: int
    b: str = "abc"


@dataclass
class SubConfigWithPositional:
    a: int = field(default=42, metadata=dict(positional=True))
    b: str = "abc"


@dataclass
class NestedSub:
    a: int = 42
    b: SubConfig = field(default_factory=SubConfig)
    c: str = "abc"


class TestParseSubConfig:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: SubConfig = field(default_factory=SubConfig)
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    @mark.parametrize(
        "help_string",
        ["usage: prog [-h] [--sub-a SUB_A] [--sub-b SUB_B]", "sub:", "--sub-b SUB_B      a string (default: abc)"],
    )
    def test_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out.replace("\n", "")

    def test_parse(self, recwarn):
        config = parse(self.Config, ["mode"])
        assert len(recwarn) == 0
        assert config.mode == "mode"
        assert config.sub.a == 42
        assert config.sub.b == "abc"
        assert config.flag is False

    def test_flag(self):
        config = parse(self.Config, ["mode", "--flag"])
        assert config.mode == "mode"
        assert config.sub.a == 42
        assert config.sub.b == "abc"
        assert config.flag is True

    def test_set_sub(self):
        config = parse(self.Config, ["mode", "--sub-a", "1"])
        assert config.mode == "mode"
        assert config.sub.a == 1
        assert config.sub.b == "abc"
        assert config.flag is False


class TestSubConfigCollision:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: SubConfig = field(default_factory=SubConfig)
        sub_a: float = field(default=1.0)

    def test_parse(self):
        with raises(ArgumentError):
            parse(self.Config, ["mode"])


class TestWarnNonStandardDefault:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: SubConfig = field(default_factory=lambda: SubConfig(a=1))
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_warning(self):
        with warns(UserWarning):
            parse(self.Config, ["mode"])


class TestParseRequiredSubConfig:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: SubConfig = field()
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_parse(self):
        config = parse(self.Config, ["mode"])
        assert config.mode == "mode"
        assert config.sub.a == 42
        assert config.sub.b == "abc"
        assert config.flag is False

    def test_flag(self):
        config = parse(self.Config, ["mode", "--flag"])
        assert config.mode == "mode"
        assert config.sub.a == 42
        assert config.sub.b == "abc"
        assert config.flag is True

    def test_set_sub(self):
        config = parse(self.Config, ["mode", "--sub-a", "1"])
        assert config.mode == "mode"
        assert config.sub.a == 1
        assert config.sub.b == "abc"
        assert config.flag is False


class TestParseSubConfigWithRequiredField:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: SubConfigWithRequiredField
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_parse_required(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["mode"])
        captured = capsys.readouterr()
        assert "the following arguments are required: --sub-a" in captured.err

    def test_flag(self):
        config = parse(self.Config, ["mode", "--sub-a", "1", "--flag"])
        assert config.mode == "mode"
        assert config.sub.a == 1
        assert config.sub.b == "abc"
        assert config.flag is True

    def test_set_sub(self):
        config = parse(self.Config, ["mode", "--sub-a", "1", "--sub-b", "def"])
        assert config.mode == "mode"
        assert config.sub.a == 1
        assert config.sub.b == "def"
        assert config.flag is False


class TestParseSubConfigWithPositional:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: SubConfigWithPositional = field(default_factory=SubConfigWithPositional)
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_help(self, capsys):
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert "mode [sub_a]" in captured.out

    def test_parse(self):
        config = parse(self.Config, ["mode"])
        assert config.mode == "mode"
        assert config.sub.a == 42
        assert config.sub.b == "abc"
        assert config.flag is False

    def test_flag(self):
        config = parse(self.Config, ["mode", "1", "--flag"])
        assert config.mode == "mode"
        assert config.sub.a == 1
        assert config.sub.b == "abc"
        assert config.flag is True

    def test_set_sub(self):
        config = parse(
            self.Config,
            ["mode", "1", "--sub-b", "def"],
        )
        assert config.mode == "mode"
        assert config.sub.a == 1
        assert config.sub.b == "def"
        assert config.flag is False


class TestParsePositionalSubConfig:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: SubConfig = field(default_factory=SubConfig, metadata=dict(positional=True))
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    def test_parse(self):
        with raises(ValueError):
            parse(self.Config, ["mode"])


class TestParseNestedSubConfig:
    @dataclass
    class Config:
        mode: str = field(metadata=dict(positional=True))
        sub: NestedSub = field(default_factory=NestedSub)
        flag: bool = field(default=False, metadata=dict(as_flags=True))

    @mark.parametrize(
        "help_string",
        [
            "usage: prog [-h] [--sub-a SUB_A] [--sub-b-a SUB_B_A]",
            "sub_b:",
            "--sub-b-b SUB_B_B  a string (default: abc)\n",
        ],
    )
    def test_help(self, capsys, help_string: str):
        with raises(SystemExit):
            parse(self.Config, ["--help"], prog="prog")  # type: ignore
        captured = capsys.readouterr()
        assert help_string in captured.out

    def test_parse(self):
        config = parse(self.Config, ["mode"])
        assert config.mode == "mode"
        assert config.sub.a == 42
        assert config.sub.b.a == 42
        assert config.sub.b.b == "abc"
        assert config.sub.c == "abc"
        assert config.flag is False

    def test_sub(self):
        config = parse(self.Config, ["mode", "--sub-a", "1", "--flag"])
        assert config.mode == "mode"
        assert config.sub.a == 1
        assert config.sub.b.a == 42
        assert config.sub.b.b == "abc"
        assert config.sub.c == "abc"
        assert config.flag is True

    def test_sub_sub(self):
        config = parse(
            self.Config,
            ["mode", "--sub-a", "1", "--sub-b-a", "21", "--sub-b-b", "def"],
        )
        assert config.sub.a == 1
        assert config.sub.b.a == 21
        assert config.sub.b.b == "def"
        assert config.sub.c == "abc"
        assert config.flag is False
