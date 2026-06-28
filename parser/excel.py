from pathlib import Path
import pandas as pd


def export(grouped, filename="output/lastwar_export.xlsx"):

    output = Path(filename)
    output.parent.mkdir(exist_ok=True)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        for (server, ranking_type), rows in grouped.items():

            df = pd.DataFrame(rows)

            if df.empty:
                continue

            if ranking_type == "total_hero_power":
                preferred_columns = [
                    "rank",
                    "alliance_tag",
                    "player_name",
                    "name",
                    "power",
                    "confidence",
                    "parse_status",
                    "parse_warnings",
                    "parse_corrections",
                    "normalized_identity",
                    "raw_text",
                    "source_file",
                ]
            else:
                preferred_columns = ["rank", "name", "power", "source_file", "raw_text"]

            columns = [column for column in preferred_columns if column in df.columns]
            df = df[columns]

            sheet = f"{server}_{ranking_type}"

            df.to_excel(
                writer,
                sheet_name=sheet[:31],
                index=False
            )

    print(f"\nExcel geschrieben nach {output}")