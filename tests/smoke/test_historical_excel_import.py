from pathlib import Path

import pandas as pd

from application.command_center.service import CommandCenterService
from importer.historical_excel_import import import_historical_excels


def test_historical_excel_import_loads_reference_rankings(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "input"
    data_dir = tmp_path / "data"
    input_dir.mkdir()
    data_dir.mkdir()

    s5 = input_dir / "LastWarS5_post_Transfer.xlsx"
    s6 = input_dir / "LastWarS6_pre-season.xlsx"

    with pd.ExcelWriter(s5) as writer:
        pd.DataFrame({
            "#": [1, 2],
            "Server": [554, 554],
            "Alliance": ["KOLT", "TOS"],
            "Strength": [20_527_387_472, 11_756_681_920],
        }).to_excel(writer, sheet_name="postTransfer", index=False)
        pd.DataFrame({
            "#": [1],
            "Server": [554],
            "Alliance": ["KOLT"],
            "Player": ["Narizo"],
            "Strength": [231_819_940],
        }).to_excel(writer, sheet_name="pre gold vein THP", index=False)
    with pd.ExcelWriter(s6) as writer:
        pd.DataFrame({"Server": [556], "Alliance": ["7yq"], "Strength": [26_931_004_010]}).to_excel(writer, sheet_name="Alliances", index=False)
        pd.DataFrame({"Server": [556], "Alliance": ["7yq"], "Player": ["Kevnin C"], "THP": [304_126_796]}).to_excel(writer, sheet_name="Players", index=False)

    monkeypatch.chdir(tmp_path)
    report = import_historical_excels(input_dir=input_dir, report_path=data_dir / "historical_import_report.json")

    assert report.rows_imported == 5
    assert report.servers == [554, 556]
    assert (data_dir / "lastwarintel.sqlite").exists()
    assert (data_dir / "historical_import_report.json").exists()


def test_command_center_uses_historical_coverage_without_benchmark_files(tmp_path: Path, monkeypatch):
    input_dir = tmp_path / "input"
    data_dir = tmp_path / "data"
    input_dir.mkdir()
    data_dir.mkdir()
    s6 = input_dir / "LastWarS6_pre-season.xlsx"
    with pd.ExcelWriter(s6) as writer:
        pd.DataFrame({"Server": [556], "Alliance": ["7yq"], "Strength": [26_931_004_010]}).to_excel(writer, sheet_name="Alliances", index=False)
        pd.DataFrame({"Server": [556], "Alliance": ["7yq"], "Player": ["Kevnin C"], "THP": [304_126_796]}).to_excel(writer, sheet_name="Players", index=False)

    monkeypatch.chdir(tmp_path)
    import_historical_excels(input_dir=input_dir, report_path=data_dir / "historical_import_report.json")

    readiness = CommandCenterService(database_path=data_dir / "lastwarintel.sqlite").get_command_center().operational_readiness

    assert readiness.total_servers == 1
    assert readiness.operational_servers == 1
    assert readiness.coverage_percent == 100
    assert readiness.server_health[0].server == 556
    assert readiness.server_health[0].status == "Operational"
