from pathlib import Path

from parser.ocr_cache import OcrCache
from ocr.provider import OcrProviderInfo


class DummyReader:
    @property
    def info(self):
        return OcrProviderInfo(
            name="dummy",
            engine="dummy",
            metadata_languages=("en",),
            row_languages=("en", "ch_sim"),
            profile="test",
        )


def test_ocr_cache_reuses_observations_by_content_hash(tmp_path: Path):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"same image bytes")
    cache = OcrCache(tmp_path / "cache")
    reader = DummyReader()
    calls = {"count": 0}

    def compute(_reader, _image):
        calls["count"] += 1
        return [([[0, 0], [1, 0], [1, 1], [0, 1]], "Server 552", 0.91)]

    first = cache.get_or_compute(
        screenshot=screenshot,
        reader=reader,
        image=object(),
        mode="metadata",
        target_width=1440,
        target_height=3200,
        compute=compute,
    )
    second = cache.get_or_compute(
        screenshot=screenshot,
        reader=reader,
        image=object(),
        mode="metadata",
        target_width=1440,
        target_height=3200,
        compute=compute,
    )

    assert first == second
    assert calls["count"] == 1
    assert cache.stats.misses == 1
    assert cache.stats.hits == 1
