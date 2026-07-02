from pathlib import Path

from web.navigation import COMMAND_WORKFLOW, NAVIGATION


ROOT = Path(__file__).resolve().parents[2]


def test_visible_command_workflow_navigation_model_is_present():
    titles = [item.title for item in COMMAND_WORKFLOW]
    assert titles == ["Command", "Imports", "Quality", "Reviews", "Exports"]
    assert any(item.title == "Reviews" and item.url == "/reviews" for item in NAVIGATION)
    assert any(item.title == "Exports" and item.url == "/reports" for item in NAVIGATION)


def test_base_template_renders_sidebar_and_workflow_bar():
    html = (ROOT / "web/templates/base.html").read_text(encoding="utf-8")
    assert "workflow-bar" in html
    assert "workflow_navigation" in html
    assert "side-brand-subtitle" in html
    assert "nav-copy" in html


def test_command_import_quality_templates_cross_link_workflow_pages():
    command = (ROOT / "web/templates/command_center.html").read_text(encoding="utf-8")
    imports = (ROOT / "web/templates/imports.html").read_text(encoding="utf-8")
    quality = (ROOT / "web/templates/quality.html").read_text(encoding="utf-8")
    assert "Command Center Workflow" in command
    assert "href=\"/imports\"" in command
    assert "href=\"/quality\"" in command
    assert "href=\"/reviews\"" in command
    assert "Import Workflow Links" in imports
    assert "Quality Workflow Links" in quality


def test_review_detail_template_exists_and_is_linked():
    reviews = (ROOT / "web/templates/reviews.html").read_text(encoding="utf-8")
    detail = (ROOT / "web/templates/review_detail.html").read_text(encoding="utf-8")
    routes = (ROOT / "web/routes/reviews.py").read_text(encoding="utf-8")
    assert "Review Detail / Evidence" in reviews
    assert "REVIEW DETAIL" in detail
    assert "Review Choices" in detail
    assert "Explainability Trace" in detail
    assert 'target="_blank"' in detail
    assert "screenshot-preview" in detail
    assert "rank-highlight-overlay" in detail
    assert "review-workspace-grid" in detail
    assert "screenshot_url" in routes
    assert "rank_highlight_style" in routes
    assert '@router.get("/reviews/{history_key}")' in routes


def test_screenshot_static_mount_is_available_for_review_evidence():
    app = (ROOT / "web/app.py").read_text(encoding="utf-8")
    assert '"/screenshots"' in app
    assert 'StaticFiles(directory="screenshots"' in app


def test_review_items_are_enriched_with_safe_screenshot_urls():
    from web.routes.reviews import _enrich_review_item

    item = _enrich_review_item({"screenshot": "../bad/Screenshot_20260702-082210.png", "ranking_type": "total_hero_power", "rank": 3})
    assert item["screenshot_url"] == "/screenshots/Screenshot_20260702-082210.png"
    assert item["rank_highlight_style"].startswith("top:")
