"""
ETL de microdatos EPH (INDEC) -> CSV listo para PostgreSQL (tabla eph.fact_persona_trimestre).

Uso:
    python etl/procesar_eph.py data/raw            # carpeta con los EPH_usu_*_txt.zip del INDEC
    psql -f sql/01_schema.sql
    psql -c "\\copy eph.fact_persona_trimestre FROM 'data/processed/fact_persona_trimestre.csv' WITH (FORMAT csv, HEADER true)"
    psql -f sql/02_indicadores_desde_microdatos.sql

Descarga: https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos (EPH continua, formato txt).
Notas:
- Los nombres de archivo cambian entre trimestres (usu_individual_T126.txt, EPH_usu_personas_4to.trim_2020...).
- Separador ';'. Se conservan solo personas activas (ESTADO 1 o 2) con ponderador > 0.
- PP04D_COD viene a veces sin el cero inicial: la calificación se toma del 5° dígito tras completar a 5.
"""
import io
import os
import re
import sys
import zipfile

import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
OUT = "data/processed"
os.makedirs(OUT, exist_ok=True)

COLS = ["CODUSU", "NRO_HOGAR", "COMPONENTE", "ANO4", "TRIMESTRE", "REGION", "AGLOMERADO", "PONDERA",
        "CH06", "CH12", "CH13", "NIVEL_ED", "ESTADO", "CAT_OCUP", "INTENSI", "PP04D_COD", "PP07H"]


def leer_individual(zip_path: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if re.search(r"individual|personas", n, re.I))
        raw = z.read(name).decode("latin-1")
    df = pd.read_csv(io.StringIO(raw), sep=";", dtype=str, low_memory=False)
    df.columns = [c.strip().upper() for c in df.columns]
    return df[COLS]


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    num = [c for c in COLS if c not in ("CODUSU", "PP04D_COD")]
    for c in num:
        df[c] = pd.to_numeric(df[c].str.replace(",", "."), errors="coerce")
    df = df[df["ESTADO"].isin([1, 2]) & (df["PONDERA"] > 0)].copy()
    df["PERIODO"] = df["ANO4"].astype(int).astype(str) + "Q" + df["TRIMESTRE"].astype(int).astype(str)
    df["PP04D_COD"] = df["PP04D_COD"].fillna("").str.replace(r"\D", "", regex=True)
    out = pd.DataFrame({
        "periodo": df["PERIODO"], "anio": df["ANO4"], "trimestre": df["TRIMESTRE"],
        "codusu": df["CODUSU"], "nro_hogar": df["NRO_HOGAR"], "componente": df["COMPONENTE"],
        "region": df["REGION"], "aglomerado": df["AGLOMERADO"], "pondera": df["PONDERA"],
        "edad": df["CH06"], "ch12": df["CH12"], "ch13": df["CH13"], "nivel_ed": df["NIVEL_ED"],
        "estado": df["ESTADO"], "cat_ocup": df["CAT_OCUP"], "intensi": df["INTENSI"],
        "pp04d_cod": df["PP04D_COD"], "pp07h": df["PP07H"],
    })
    int_cols = [c for c in out.columns if c not in ("periodo", "codusu", "pp04d_cod", "pondera")]
    out[int_cols] = out[int_cols].astype("Int64")
    return out


def tasa(df: pd.DataFrame) -> float:
    """Tasa de desocupación ponderada (%)."""
    w = df["pondera"]
    return 100 * w[df["estado"] == 2].sum() / w.sum()


if __name__ == "__main__":
    zips = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".zip") and "usu" in f.lower())
    frames = []
    for f in zips:
        d = limpiar(leer_individual(os.path.join(SRC, f)))
        print(f"{f}: {len(d):,} personas activas · TD = {tasa(d):.2f}%")
        frames.append(d)
    fact = pd.concat(frames, ignore_index=True)
    fact.to_csv(os.path.join(OUT, "fact_persona_trimestre.csv"), index=False)
    print("Guardado:", len(fact), "filas ->", OUT)
