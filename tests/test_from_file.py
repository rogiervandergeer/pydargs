from dataclasses import dataclass, field
from json import dumps
from pathlib import Path
from yaml import dump


from pydargs import parse


@dataclass
class SubConfig:
    a: int = 42
    b: str = field(default="abc", metadata=dict(help="a string"))


class TestParseFromFile:
    @dataclass
    class Config:
        a: int = 5
        b: str = field(default="something", metadata={"ignore_arg": True})
        c: bool = field(default=False, metadata=dict(ignore_arg=False, as_flags=True))
        s: SubConfig = field(default_factory=SubConfig)
        z: str = "dummy"

    def test_parse_no_file(self) -> None:
        config = parse(self.Config, [], load_from_file=True)
        assert config.a == 5
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"

    def test_parse_with_file(self, tmp_path: Path) -> None:
        (tmp_path / "config.json").write_text(dumps({"a": 6}))
        config = parse(self.Config, ["--file", str((tmp_path / "config.json"))], load_from_file=True)
        assert config.a == 6
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"

    def test_parse_with_file_override(self, tmp_path: Path) -> None:
        (tmp_path / "config.json").write_text(dumps({"a": 6}))
        config = parse(self.Config, ["--file", str((tmp_path / "config.json")), "--a", "7"], load_from_file=True)
        assert config.a == 7
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"

    def test_nested_with_file_and_override(self, tmp_path: Path) -> None:
        (tmp_path / "config.yaml").write_text(dump({"a": 6, "s": {"a": 1, "b": "c"}}))
        config = parse(self.Config, ["--file", str((tmp_path / "config.yaml")), "--s-b", "d"], load_from_file=True)
        assert config.a == 6
        assert config.b == "something"
        assert config.c is False
        assert config.z == "dummy"
        assert config.s.a == 1
        assert config.s.b == "d"


# TODO: test without defaults in dataclass
# TODO: test positionals in dataclass
# TODO: nested
# TODO: test extra fields in config
# TODO: test 'file' field in config, collision
# TODO: test incorrect path
