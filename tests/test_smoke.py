"""Smoke test for runway_client — verifies the package imports cleanly."""
import importlib


def test_import():
    mod = importlib.import_module("runway_client")
    assert mod is not None


def test_main_module_importable():
    # `python3 -m runway_client` works iff this import works
    importlib.import_module("runway_client.__main__")
