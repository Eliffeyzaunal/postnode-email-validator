import pytest

from app.parser import InputError, parse_bytes


def test_csv_header_and_semicolon():
    assert parse_bytes("email;name\na@example.com;A\n".encode(), "x.csv") == ["a@example.com"]


def test_txt():
    assert parse_bytes(b"a@example.com\n\nb@example.com\n", "x.txt") == ["a@example.com", "b@example.com"]


def test_extension_rejected():
    with pytest.raises(InputError):
        parse_bytes(b"a@example.com", "x.xlsx")

