#!/usr/bin/env python3
"""oracle_schema_dump.py — splits Oracle schema into per-module files for LLM use
Usage : python oracle_schema_dump.py [SCHEMA ...]   (default: ORACLE_USERNAME)
Output: oracle_schema/  directory with one .txt per module + _index.txt
"""
import os, sys
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Oracle EBS known module prefixes → friendly group name
_MODULE = {
    "GL":"Finance_GL", "XLA":"Finance_GL",
    "AP":"Finance_AP", "IBY":"Finance_AP",
    "AR":"Finance_AR", "HZ":"Finance_AR",
    "FA":"Finance_FA",
    "CE":"Finance_CE",
    "INV":"Inventory", "MTL":"Inventory", "MSC":"Inventory",
    "WIP":"Manufacturing", "BOM":"Manufacturing", "ENG":"Manufacturing",
    "MRP":"Manufacturing", "MPS":"Manufacturing", "CRP":"Manufacturing",
    "OPM":"Mfg_OPM", "GML":"Mfg_OPM", "GMD":"Mfg_OPM",
    "GMF":"Mfg_OPM", "GMP":"Mfg_OPM", "GMI":"Mfg_OPM",
    "OE":"OrderMgmt",  "ONT":"OrderMgmt", "OKC":"OrderMgmt",
    "WSH":"Shipping",  "WND":"Shipping",
    "PO":"Purchasing", "RCV":"Purchasing",
    "HR":"HR", "PER":"HR", "PAY":"HR", "BEN":"HR",
    "PA":"Projects",
    "QA":"Quality",
    "FND":"Foundation", "WF":"Foundation", "ICX":"Foundation",
    "AK":"Foundation",  "JTF":"Foundation",
    "XX":"Custom",
}

_TYPES = {
    "VARCHAR2":"V","NVARCHAR2":"NV","CHAR":"C","NCHAR":"NC",
    "NUMBER":"N","FLOAT":"FLT","INTEGER":"INT",
    "DATE":"D","CLOB":"CLOB","BLOB":"BLOB","RAW":"RAW","XMLTYPE":"XML",
}

def _typ(dt, cl, pr, sc):
    b = _TYPES.get(dt, dt[:5])
    if dt in ("VARCHAR2","NVARCHAR2","CHAR","NCHAR"):
        return f"{b}({cl})" if cl else b
    if dt == "NUMBER":
        if pr and sc and int(sc): return f"N({pr},{sc})"
        if pr: return f"N({pr})"
        return "N"
    if "TIMESTAMP" in dt: return "TS"
    return b

def _rows(n):
    if n < 0:          return "?"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n//1_000}k"
    return str(n)

def _prefix(tbl):
    return tbl.split("_")[0]

def _group(tbl):
    return _MODULE.get(_prefix(tbl), f"Misc_{_prefix(tbl)}")

def _init_client():
    import oracledb
    for d in [
        os.getenv("ORACLE_CLIENT_LIB_DIR", ""),
        r"C:\Program Files\Tableau\Tableau 2024.3\bin",
        r"C:\app\root\product\11.2.0\client_1\BIN",
    ]:
        if d and Path(d).exists():
            try: oracledb.init_oracle_client(lib_dir=d); return
            except: pass
    try: oracledb.init_oracle_client()
    except: pass

def _engine():
    from sqlalchemy import create_engine
    u  = os.environ["ORACLE_USERNAME"]
    pw = os.environ["ORACLE_PASSWORD"]
    h  = os.environ["ORACLE_HOST"]
    p  = os.getenv("ORACLE_PORT", "1521")
    sv = os.environ["ORACLE_SERVICE_NAME"]
    return create_engine(
        f"oracle+oracledb://{quote_plus(u)}:{quote_plus(pw)}@{h}:{p}/?service_name={quote_plus(sv)}",
        pool_pre_ping=True,
    )

def fetch(engine, schemas):
    from sqlalchemy import text, bindparam
    owners = [s.upper() for s in schemas]

    with engine.connect() as c:
        tbls = c.execute(text("""
            SELECT owner, table_name, NVL(num_rows,-1)
            FROM   all_tables
            WHERE  NVL(num_rows,-1) != 0
              AND  table_name NOT LIKE 'BIN$%'
              AND  owner IN :owners
            ORDER  BY owner, table_name
        """).bindparams(bindparam("owners", expanding=True)), {"owners": owners}).fetchall()
        if not tbls: return {}, []

        cols = c.execute(text("""
            SELECT owner, table_name, column_name,
                   data_type, char_length, data_precision, data_scale, nullable
            FROM   all_tab_columns
            WHERE  (owner, table_name) IN (
                       SELECT owner, table_name FROM all_tables
                       WHERE  NVL(num_rows,-1) != 0
                         AND  table_name NOT LIKE 'BIN$%'
                         AND  owner IN :owners
                   )
            ORDER  BY owner, table_name, column_id
        """).bindparams(bindparam("owners", expanding=True)), {"owners": owners}).fetchall()

        pks = {(r[0],r[1],r[2]) for r in c.execute(text("""
            SELECT cc.owner, cc.table_name, cc.column_name
            FROM   all_constraints c
            JOIN   all_cons_columns cc
                   ON c.owner=cc.owner AND c.constraint_name=cc.constraint_name
            WHERE  c.constraint_type='P' AND c.owner IN :owners
        """).bindparams(bindparam("owners", expanding=True)), {"owners": owners}).fetchall()}

        fk_raw = c.execute(text("""
            SELECT cc.owner, cc.table_name, cc.column_name,
                   rc.table_name, rcc.column_name
            FROM   all_constraints c
            JOIN   all_cons_columns cc
                   ON c.owner=cc.owner AND c.constraint_name=cc.constraint_name
            JOIN   all_constraints rc
                   ON c.r_owner=rc.owner AND c.r_constraint_name=rc.constraint_name
            JOIN   all_cons_columns rcc
                   ON rc.owner=rcc.owner AND rc.constraint_name=rcc.constraint_name
                   AND cc.position=rcc.position
            WHERE  c.constraint_type='R' AND c.owner IN :owners
        """).bindparams(bindparam("owners", expanding=True)), {"owners": owners}).fetchall()

    fk_col = {(r[0],r[1],r[2]): f"{r[3]}.{r[4]}" for r in fk_raw}
    # relations keyed by (src_table, dst_table)
    relations = [(f"{r[1]}.{r[2]}", f"{r[3]}.{r[4]}") for r in fk_raw]

    tables = {(r[0],r[1]): {"n": r[2], "c": []} for r in tbls}
    for owner, tbl, col, dt, cl, pr, sc, nn in cols:
        key = (owner, tbl)
        if key not in tables: continue
        typ = _typ(dt, cl, pr, sc)
        if   (owner,tbl,col) in pks:    ann = "*"
        elif (owner,tbl,col) in fk_col: ann = f"->{fk_col[(owner,tbl,col)]}"
        elif nn == "N":                 ann = "!"
        else:                           ann = ""
        tables[key]["c"].append(f"{col}:{typ}{ann}" if ann else f"{col}:{typ}")

    return tables, relations

def write_files(tables, relations, schemas, host, service, out_dir):
    out_dir.mkdir(exist_ok=True)
    key_line = "# *=PK  ->=FK  !=NN  N=NUMBER  V=VARCHAR2  D=DATE  TS=TIMESTAMP"

    # group tables
    groups = defaultdict(dict)
    for (owner, tbl), info in tables.items():
        groups[_group(tbl)][(owner, tbl)] = info

    # relation lookup: set of table names per group
    group_tables = {g: {tbl for (_o, tbl) in keys} for g, keys in groups.items()}

    written = {}
    for group, gtables in sorted(groups.items()):
        # only relations where EITHER side belongs to this group
        gtbl_names = group_tables[group]
        rel_lines = sorted({
            f"  {src} -> {dst}"
            for src, dst in relations
            if src.split(".")[0] in gtbl_names or dst.split(".")[0] in gtbl_names
        })

        lines = [key_line, ""]
        cur_owner = None
        for (owner, tbl), info in sorted(gtables.items()):
            if owner != cur_owner:
                if cur_owner: lines.append("")
                lines.append(f"[{owner}]")
                cur_owner = owner
            lines.append(f"{tbl}[{_rows(info['n'])}]: {' | '.join(info['c'])}")

        if rel_lines:
            lines += ["", "[RELATIONS]"] + rel_lines

        text = "\n".join(lines)
        fname = f"{group}.txt"
        (out_dir / fname).write_text(text, encoding="utf-8")
        written[group] = {
            "file": fname,
            "tables": len(gtables),
            "tokens": len(text) // 4,
        }

    # index file
    total_tbl = sum(v["tables"] for v in written.values())
    total_tok = sum(v["tokens"] for v in written.values())
    idx_lines = [
        f"# Oracle {host}/{service}  schemas={','.join(schemas)}",
        f"# {total_tbl} tables across {len(written)} modules  (~{total_tok:,} tokens total if all loaded)",
        "# Load only the module file(s) relevant to your query.",
        "",
        f"{'MODULE':<25} {'TABLES':>6}  {'~TOKENS':>8}  FILE",
        "-" * 60,
    ]
    for g, v in sorted(written.items(), key=lambda x: -x[1]["tables"]):
        idx_lines.append(f"{g:<25} {v['tables']:>6}  {v['tokens']:>8,}  {v['file']}")

    (out_dir / "_index.txt").write_text("\n".join(idx_lines), encoding="utf-8")
    return written

def main():
    schemas = sys.argv[1:] or [os.getenv("ORACLE_USERNAME", "APPS").upper()]
    print(f"Schemas: {schemas}")
    _init_client()
    engine = _engine()
    print("Fetching metadata …")
    tables, relations = fetch(engine, schemas)
    engine.dispose()
    if not tables:
        print("No non-empty tables found."); return

    out_dir = Path(__file__).parent / "oracle_schema"
    written = write_files(tables, relations, schemas,
                          os.getenv("ORACLE_HOST"), os.getenv("ORACLE_SERVICE_NAME"), out_dir)

    print(f"\n{len(tables)} tables → {len(written)} files in {out_dir}/")
    print(f"{'MODULE':<25} {'TABLES':>6}  {'~TOKENS':>8}")
    for g, v in sorted(written.items(), key=lambda x: -x[1]["tables"]):
        print(f"  {g:<23} {v['tables']:>6}  {v['tokens']:>8,}")
    total = sum(v["tokens"] for v in written.values())
    print(f"\n  Index: {out_dir}/_index.txt")
    print(f"  Total across all files: ~{total:,} tokens  |  largest single file: ~{max(v['tokens'] for v in written.values()):,} tokens")

if __name__ == "__main__":
    main()
