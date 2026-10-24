from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MonitorInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=2048)
    interval_seconds: int = Field(default=30, ge=5, le=86400)
    timeout_seconds: int = Field(default=5, ge=1, le=30)
    expected_status: int = Field(default=200, ge=100, le=599)
    paused: bool = False
    repository: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.fragment
                or parsed.port not in {None, 80, 443, 8001}
                or any(ord(char) <= 32 or ord(char) == 127 for char in value)
                or "\\" in value
            ):
                raise ValueError()
        except ValueError:
            raise ValueError(
                "use an HTTP(S) URL without credentials or fragments on an allowed port"
            )
        return value
