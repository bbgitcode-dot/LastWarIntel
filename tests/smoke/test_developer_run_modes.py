from pathlib import Path

from main import _parse_screenshot_patterns, _select_screenshots, parse_args


def test_parse_screenshot_patterns_accepts_comma_list():
    assert _parse_screenshot_patterns("a.png, b*.jpg,, c.png") == ["a.png", "b*.jpg", "c.png"]


def test_select_screenshots_filters_by_filename_glob(tmp_path: Path):
    for name in ["a.png", "b.jpg", "c.png", "notes.txt"]:
        (tmp_path / name).write_text("x", encoding="utf-8")

    selected = _select_screenshots(tmp_path, patterns=["c.*", "b.jpg"])

    assert [item.name for item in selected] == ["b.jpg", "c.png"]


def test_select_screenshots_limit_is_applied_after_filter(tmp_path: Path):
    for name in ["001.png", "002.png", "003.jpg"]:
        (tmp_path / name).write_text("x", encoding="utf-8")

    selected = _select_screenshots(tmp_path, patterns=["*.png"], limit=1)

    assert [item.name for item in selected] == ["001.png"]


def test_rebuild_reports_flag_parses_without_requiring_ocr():
    args = parse_args(["--rebuild-reports"])

    assert args.rebuild_reports is True
    assert args.screenshots == ""


def test_rebuild_reports_initializes_runtime_telemetry(monkeypatch, capsys):
    import main as main_module

    def fake_generate_command_center():
        return {
            "command_center": "output/command_center.html",
            "review_dashboard": "output/review_dashboard.html",
            "review_evidence_pack": "output/review_evidence_pack.html",
        }

    monkeypatch.setattr(main_module, "generate_command_center", fake_generate_command_center)

    main_module.main(["--rebuild-reports"])

    output = capsys.readouterr().out
    assert "Report rebuild completed" in output
    assert "Runtime telemetry:" in output
    assert "html_report_render" in output
