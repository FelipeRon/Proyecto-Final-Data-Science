"""Publica las filas de la simulación en Snowflake conservando ids de replay."""
import csv
import json
import os
from pathlib import Path

import snowflake.connector

TABLES = {"predicciones": ("ID_PREDICCION", "id_prediccion"),
          "monitoreo": ("PERIODO", "periodo"), "alertas": ("CLAVE", None)}


def publish():
    names = ("ACCOUNT", "USER", "ROLE", "WAREHOUSE", "DATABASE", "PRIVATE_KEY_FILE")
    options = {name.lower(): os.environ[f"SNOWFLAKE_{name}"] for name in names}
    with snowflake.connector.connect(**options) as connection:
        cursor = connection.cursor()
        for name, (column, key) in TABLES.items():
            table = f"OBT.{name.upper()}"
            with Path(f"docs/{name}.csv").open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({column} VARCHAR, PAYLOAD VARIANT)")
            cursor.execute(f"BEGIN")
            try:
                for row in rows:
                    identifier = row[key] if key else f'{row["periodo"]}:{row["variable"]}'
                    cursor.execute(f"""
                        MERGE INTO {table} t USING (SELECT %s AS ID, PARSE_JSON(%s) AS DATA) s
                        ON t.{column}=s.ID WHEN MATCHED THEN UPDATE SET PAYLOAD=s.DATA
                        WHEN NOT MATCHED THEN INSERT ({column}, PAYLOAD) VALUES (s.ID,s.DATA)
                        """, (identifier, json.dumps(row)))
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            print(f"{table} {len(rows)} filas del replay")


if __name__ == "__main__":
    publish()
