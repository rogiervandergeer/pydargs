from argparse import ArgumentError
from dataclasses import dataclass, field
from json import dumps
from pathlib import Path
from typing import Optional

from yaml import dump

from pytest import raises, warns

from pydargs import parse


@dataclass
class SubSubConfig:
    q: str = "q"


@dataclass
class SubConfig:
    a: int = 42
    b: str = field(default="abc", metadata=dict(help="a string"))
    s: SubSubConfig = field(default_factory=SubSubConfig)


class TestParseFromFile:
    @dataclass
    class Config:
        a: int = 5
        b: str = field(default="something", metadata={"ignore_arg": True})
        c: bool = field(default=False, metadata=dict(ignore_arg=False, as_flags=True))
        s: SubConfig = field(default_factory=SubConfig)
        z: str = "dummy"

    def test_parse_no_file(self) -> None:
        config = parse(self.Config, [], add_config_file_argument=True)
        assert config.a == 5
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"

    def test_parse_with_file(self, tmp_path: Path) -> None:
        (tmp_path / "config.json").write_text(dumps({"a": 6}))
        config = parse(self.Config, ["--config-file", str((tmp_path / "config.json"))], add_config_file_argument=True)
        assert config.a == 6
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"

    def test_parse_with_file_override(self, tmp_path: Path) -> None:
        (tmp_path / "config.json").write_text(dumps({"a": 6}))
        config = parse(
            self.Config, ["--config-file", str((tmp_path / "config.json")), "--a", "7"], add_config_file_argument=True
        )
        assert config.a == 7
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"

    def test_nested_with_file_and_override(self, tmp_path: Path) -> None:
        (tmp_path / "config.yaml").write_text(dump({"a": 6, "s": {"a": 1, "b": "c", "s": {"q": "z"}}}))
        config = parse(
            self.Config, ["--config-file", str((tmp_path / "config.yaml")), "--s-b", "d"], add_config_file_argument=True
        )
        assert config.a == 6
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"
        assert config.s.a == 1
        assert config.s.b == "d"
        assert config.s.s.q == "z"

    def test_nested_with_prefixed_keys(self, tmp_path: Path) -> None:
        (tmp_path / "config.yaml").write_text(dump({"a": 6, "s_a": 1, "s": {"b": "c"}}))
        config = parse(self.Config, ["--config-file", str((tmp_path / "config.yaml"))], add_config_file_argument=True)
        assert config.a == 6
        assert config.s.a == 1
        assert config.s.b == "c"

    def test_nested_with_duplicate_keys(self, tmp_path: Path) -> None:
        (tmp_path / "config.yaml").write_text(dump({"a": 6, "s_a": 1, "s": {"a": 2, "b": "c"}}))
        with raises(KeyError) as e:
            parse(self.Config, ["--config-file", str((tmp_path / "config.yaml"))], add_config_file_argument=True)
        assert str(e.value) == "'Collision between keys in config file on key s_a.'"

    def test_parse_with_nonexistent_file(self, tmp_path: Path) -> None:
        with raises(FileNotFoundError):
            parse(self.Config, ["--config-file", str((tmp_path / "config.json"))], add_config_file_argument=True)

    def test_parse_with_extra_fields(self, tmp_path: Path) -> None:
        (tmp_path / "config.json").write_text(dumps({"a": 6, "d": "this_is_extra"}))
        with warns(UserWarning) as warnings:
            parse(self.Config, ["--config-file", str((tmp_path / "config.json"))], add_config_file_argument=True)
        assert (
            str(warnings[0].message) == "The following keys from the provided configuration file were not consumed: d"
        )


class TestParseFromFileNoDefaults:
    @dataclass
    class Config:
        a: int
        b: str = field(metadata=dict(positional=True))
        s: SubConfig = field(default_factory=SubConfig)
        z: str = "dummy"

    def test_parse_with_file_fields_remain_required(self, tmp_path: Path, capsys) -> None:
        (tmp_path / "config.json").write_text(dumps({"a": 6, "b": "something"}))
        with raises(SystemExit):
            parse(self.Config, ["--config-file", str((tmp_path / "config.json"))], add_config_file_argument=True)
        captured = capsys.readouterr()
        assert "the following arguments are required: --a, b" in captured.err


class TestFileCollision:
    @dataclass
    class Config:
        a: int = 5
        config_file: Optional[Path] = None

    def test_parse_no_file(self) -> None:
        config = parse(self.Config, [], add_config_file_argument=False)
        assert config.a == 5
        assert config.config_file is None

    def test_parse_with_file(self, tmp_path: Path) -> None:
        with raises(ArgumentError):
            parse(self.Config, [], add_config_file_argument=True)
