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

            columns = ["rank", "name", "power"]

            df = df[columns]

            sheet = f"{server}_{ranking_type}"

            df.to_excel(
                writer,
                sheet_name=sheet[:31],
                index=False
            )

    print(f"\nExcel geschrieben nach {output}")