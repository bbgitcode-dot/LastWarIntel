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


def test_rank_highlight_profiles_are_calibrated_to_first_visible_row():
    from web.routes.reviews import _enrich_review_item

    alliance_rank_1 = _enrich_review_item({"screenshot": "Screenshot_20260702-082010.png", "ranking_type": "alliance_power", "rank": 1})
    hero_rank_1 = _enrich_review_item({"screenshot": "Screenshot_20260702-082210.png", "ranking_type": "total_hero_power", "rank": 1})
    assert alliance_rank_1["rank_highlight_style"].startswith("top:13.")
    assert hero_rank_1["rank_highlight_style"].startswith("top:13.")
    assert alliance_rank_1["rank_highlight_label"] == "Rank 1"


def test_command_center_exposes_operational_readiness_drilldown_cards():
    html = (ROOT / "web/templates/command_center.html").read_text(encoding="utf-8")
    service = (ROOT / "application/command_center/service.py").read_text(encoding="utf-8")
    models = (ROOT / "application/command_center/models.py").read_text(encoding="utf-8")

    assert "Operational Readiness" in html
    assert "operational-status-card" in html
    assert "server-health-strip" in html
    assert 'href="{{ card.href }}"' in html
    assert "/servers?status=operational" in service
    assert "/reviews?status=open" in service
    assert "/quality?filter=missing-data" in service
    assert "/imports?status=failed" in service
    assert "OperationalReadiness" in models
    assert "OperationalStatusCard" in models
    assert "ServerHealthItem" in models


def test_workflow_pages_accept_operational_readiness_drilldown_filters():
    imports_route = (ROOT / "web/routes/imports.py").read_text(encoding="utf-8")
    quality_route = (ROOT / "web/routes/quality.py").read_text(encoding="utf-8")
    servers_route = (ROOT / "web/routes/servers.py").read_text(encoding="utf-8")
    reviews_route = (ROOT / "web/routes/reviews.py").read_text(encoding="utf-8")
    imports_html = (ROOT / "web/templates/imports.html").read_text(encoding="utf-8")
    quality_html = (ROOT / "web/templates/quality.html").read_text(encoding="utf-8")
    servers_html = (ROOT / "web/templates/servers.html").read_text(encoding="utf-8")
    reviews_html = (ROOT / "web/templates/reviews.html").read_text(encoding="utf-8")

    assert 'request.query_params.get("status"' in imports_route
    assert 'request.query_params.get("filter"' in quality_route
    assert 'request.query_params.get("status"' in servers_route
    assert 'request.query_params.get("status"' in reviews_route
    assert "DRILL-DOWN" in imports_html
    assert "DRILL-DOWN" in quality_html
    assert "DRILL-DOWN" in servers_html
    assert "DRILL-DOWN" in reviews_html


def test_operational_readiness_model_counts_pending_and_missing_servers():
    from application.command_center.service import CommandCenterService
    from application.operational_import.models import (
        DataGuardStatusView,
        OperationalImportDashboard,
        ServerImportView,
    )

    latest_import = OperationalImportDashboard(
        has_import=True,
        source="test",
        servers=[550, 554],
        imports=[
            ServerImportView("source-a", 554, "Alliance Power", 16, "Ready", 100, 0, 1),
            ServerImportView("source-b", 554, "Total Hero Power", 17, "Ready", 100, 0, 1),
            ServerImportView("source-c", 550, "Total Hero Power", 9, "Ready", 100, 0, 1),
        ],
        data_guard=DataGuardStatusView("Review", 0, 0, []),
    )
    readiness = CommandCenterService()._build_operational_readiness(latest_import)

    assert readiness.total_servers >= 2
    assert any(card.href == "/reviews?status=open" for card in readiness.cards)
    assert any(card.href == "/quality?filter=missing-data" for card in readiness.cards)
    assert readiness.pending_review_servers >= 1
    assert readiness.missing_data_servers >= 1
