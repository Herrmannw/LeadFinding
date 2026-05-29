from leadbot_worker.pipeline.normalize import normalize_domain, normalize_name, normalize_phone


def test_normalize_name_removes_suffix_punctuation_and_ampersand() -> None:
    assert normalize_name("ABC Heating & Air, LLC") == "abc heating and air"


def test_normalize_phone_keeps_us_digits() -> None:
    assert normalize_phone("(713) 555-1234") == "7135551234"
    assert normalize_phone("+1 713.555.1234") == "17135551234"


def test_normalize_domain_removes_protocol_www_and_trailing_slash() -> None:
    assert normalize_domain("https://www.Example.com/") == "example.com"
    assert normalize_domain("example.com/services") == "example.com"
