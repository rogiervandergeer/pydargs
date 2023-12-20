from dataclasses import field

from pydargs import parse
from pytest import approx, importorskip, fixture, raises

pydantic = importorskip("pydantic")


class TestPydanticDataclass:
    @fixture
    def config(self):
        @pydantic.dataclasses.dataclass
        class Config:
            a: int = field(metadata=dict(positional=True))
            b: str
            c: float = 1.0
            d: int = 4
            e: str = field(metadata=dict(positional=True), default="e")
            f: int = field(default_factory=lambda: 1)

            @pydantic.field_validator("c")
            @classmethod
            def validate_c_is_positive(cls, v: float) -> float:
                if v <= 0:
                    raise ValueError("c must be positive")
                return v

        return Config

    def test_instantiate(self, config):
        c = parse(config, ["1", "--b", "b"])
        assert c.a == 1
        assert c.b == "b"
        assert c.c == 1.0
        assert c.d == 4
        assert c.e == "e"
        assert c.f == 1

    def test_validation(self, config):
        c = parse(config, ["1", "--b", "b", "--c", "1.5"])
        assert c.c == approx(1.5)

        with raises(pydantic.ValidationError):
            parse(config, ["1", "--b", "b", "--c", "-1.5"])
