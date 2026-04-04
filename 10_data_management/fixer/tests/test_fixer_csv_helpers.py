# Offline tests for fixer chunking + set_cell semantics + parse_function_arguments (no Ollama / no network)
# Run: python 10_data_management/fixer/tests/test_fixer_csv_helpers.py

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

fixer_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(fixer_root))

from functions import parse_function_arguments, split_df_into_row_chunks


def apply_set_cell(df: pd.DataFrame, args: dict) -> pd.DataFrame:
    rid = int(args["row_id"])
    col = str(args.get("column_name") or "")
    nv = str(args.get("new_value") or "")
    ev = args.get("expected_old_value")
    rids = pd.to_numeric(df["row_id"], errors="coerce")
    i = df.index[rids == rid][0]
    old = df.at[i, col]
    old = "" if pd.isna(old) else str(old)
    if ev is not None:
        evs = "" if pd.isna(ev) else str(ev)
        if old != evs:
            return df
    df = df.copy()
    df.at[i, col] = nv
    return df


def main() -> None:
    print("test_fixer_csv_helpers: split_df_into_row_chunks ...")
    # 11 rows like R datasets::iris[1:11, ] + row_id
    iris2 = pd.DataFrame({"row_id": range(1, 12), "x": range(11)})
    ch = split_df_into_row_chunks(iris2, 4)
    assert len(ch) == 3 and len(ch[0]) == 4 and len(ch[1]) == 4 and len(ch[2]) == 3
    ch10 = split_df_into_row_chunks(iris2, 10)
    assert len(ch10) == 2 and len(ch10[0]) == 10 and len(ch10[1]) == 1
    ch1 = split_df_into_row_chunks(iris2, 1)
    assert len(ch1) == 11
    assert len(split_df_into_row_chunks(iris2.iloc[0:0], 5)) == 0
    d30 = pd.DataFrame({"row_id": [str(i) for i in range(1, 31)], "sku": ["X"] * 30})
    ch30 = split_df_into_row_chunks(d30, 10)
    assert len(ch30) == 3 and len(ch30[0]) == 10 and len(ch30[1]) == 10 and len(ch30[2]) == 10
    print("   OK")

    print("test_fixer_csv_helpers: apply_set_cell ...")
    df = pd.DataFrame({"row_id": ["1", "2", "3"], "qty": ["0", "5", "1 1"]})
    df = apply_set_cell(df, {"row_id": 1, "column_name": "qty", "new_value": "", "expected_old_value": "0"})
    assert str(df.loc[df["row_id"] == "1", "qty"].iloc[0]) == ""
    df = apply_set_cell(df, {"row_id": 3, "column_name": "qty", "new_value": "11", "expected_old_value": "1 1"})
    assert str(df.loc[df["row_id"] == "3", "qty"].iloc[0]) == "11"
    df2 = apply_set_cell(df, {"row_id": 2, "column_name": "qty", "new_value": "9", "expected_old_value": "wrong"})
    assert str(df2.loc[df2["row_id"] == "2", "qty"].iloc[0]) == "5"
    print("   OK")

    print("test_fixer_csv_helpers: parse_function_arguments ...")
    assert parse_function_arguments(None) == {}
    assert parse_function_arguments("{}") == {}
    j = '{"row_id":2,"column_name":"qty","new_value":"7"}'
    p = parse_function_arguments(j)
    assert p["row_id"] == 2 and p["column_name"] == "qty" and p["new_value"] == "7"
    print("   OK")

    print("test_fixer_csv_helpers: parcels WKT parses as GeoDataFrame ...")
    parcels_path = fixer_root / "data" / "parcels_zoning_raw.csv"
    if parcels_path.is_file():
        import geopandas as gpd

        d = pd.read_csv(parcels_path)
        x = gpd.GeoDataFrame(d, geometry=gpd.GeoSeries.from_wkt(d["wkt"]), crs=4326)
        assert len(x) >= 1 and bool(x.geometry.is_valid.all())
    else:
        print("   (skip: no parcels_zoning_raw.csv)")
    print("   OK")

    print("test_fixer_csv_helpers: all passed.")


if __name__ == "__main__":
    main()
