"""Unit tests for the orders worker's pure helpers."""

from main import parse_tick_interval


def test_parses_valid_interval():
    assert parse_tick_interval("5") == 5.0
    assert parse_tick_interval("0.5") == 0.5


def test_defaults_on_missing_or_empty():
    assert parse_tick_interval(None) == 2.0
    assert parse_tick_interval("") == 2.0
    assert parse_tick_interval("   ") == 2.0


def test_defaults_on_non_numeric():
    assert parse_tick_interval("abc") == 2.0


def test_defaults_on_non_positive():
    assert parse_tick_interval("0") == 2.0
    assert parse_tick_interval("-3") == 2.0


def test_custom_default():
    assert parse_tick_interval(None, default=10.0) == 10.0
