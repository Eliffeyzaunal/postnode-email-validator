import pytest

from app.parser import InputError, parse_bytes


def test_csv_header_and_semicolon():
    assert parse_bytes("email;name\na@example.com;A\n".encode(), "x.csv") == ["a@example.com"]


def test_txt():
    assert parse_bytes(b"a@example.com\n\nb@example.com\n", "x.txt") == ["a@example.com", "b@example.com"]


def test_extension_rejected():
    with pytest.raises(InputError):
        parse_bytes(b"a@example.com", "x.xlsx")

def test_csv_email_header_can_be_in_non_first_column():
    content = "name,e-mail\nA,a@example.com\nB,b@example.com\n".encode()
    assert parse_bytes(content, "x.csv") == ["a@example.com", "b@example.com"]


def test_csv_without_known_header_uses_first_column():
    content = "a@example.com;A\nb@example.com;B\n".encode()
    assert parse_bytes(content, "x.csv") == ["a@example.com", "b@example.com"]


def test_single_column_csv_works_when_sniffer_cannot_infer_delimiter():
    content = "email\na@example.com\nb@example.com\n".encode()
    assert parse_bytes(content, "x.csv") == ["a@example.com", "b@example.com"]


def test_csv_skips_blank_or_short_rows():
    content = "name,email\nA,\nB,b@example.com\n".encode()
    assert parse_bytes(content, "x.csv") == ["b@example.com"]


def test_utf8_bom_is_accepted():
    content = b"\xef\xbb\xbfemail\na@example.com\n"
    assert parse_bytes(content, "x.csv") == ["a@example.com"]


def test_invalid_utf8_is_rejected():
    with pytest.raises(InputError, match="UTF-8"):
        parse_bytes(b"\xff\xfe\xfa", "x.txt")


@pytest.mark.parametrize(
    ("content", "filename"),
    [
        (b"", "x.txt"),
        (b"\n\n", "x.txt"),
        (b"email\n", "x.csv"),
    ],
)
def test_empty_inputs_are_rejected(content, filename):
    with pytest.raises(InputError, match="e-posta adresi bulunamad"):
        parse_bytes(content, filename)


def test_row_limit_is_enforced():
    content = b"a@example.com\nb@example.com\n"
    with pytest.raises(InputError, match="en fazla 1 adres"):
        parse_bytes(content, "x.txt", max_rows=1)
