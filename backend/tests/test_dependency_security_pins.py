from importlib.metadata import version


def test_asgi_security_versions_are_exactly_pinned() -> None:
    assert version("fastapi") == "0.141.1"
    assert version("starlette") == "1.6.0"
