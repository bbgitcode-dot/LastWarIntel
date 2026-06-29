from ocr.provider_factory import get_selected_provider_name


def test_default_provider_is_easy(monkeypatch):
    monkeypatch.delenv("SENTINEL_OCR_PROVIDER", raising=False)
    assert get_selected_provider_name() == "easy"


def test_provider_can_be_selected_by_env(monkeypatch):
    monkeypatch.setenv("SENTINEL_OCR_PROVIDER", "paddle")
    assert get_selected_provider_name() == "paddle"


def test_explicit_provider_overrides_env(monkeypatch):
    monkeypatch.setenv("SENTINEL_OCR_PROVIDER", "paddle")
    assert get_selected_provider_name("easy") == "easy"
