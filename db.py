
import os
import pymssql
import pandas as pd

def _get_cfg():
    # Streamlit secrets preferred; fallback to env vars
    try:
        import streamlit as st
        cfg = st.secrets["mssql"]
    except Exception:
        cfg = {
            "server": os.getenv("MSSQL_SERVER", "localhost"),
            "port": int(os.getenv("MSSQL_PORT", "1433")),
            "user": os.getenv("MSSQL_USER", "sa"),
            "password": os.getenv("MSSQL_PASSWORD", ""),
            "database": os.getenv("MSSQL_DATABASE", "DemoDB"),
            "timeout": int(os.getenv("MSSQL_TIMEOUT", "5"))
        }
    return cfg

def get_conn():
    cfg = _get_cfg()
    conn = pymssql.connect(
        server=cfg["server"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=cfg.get("port", 1433),
        login_timeout=cfg.get("timeout", 5),
        timeout=cfg.get("timeout", 5),
        charset="UTF-8",
        as_dict=False,
    )
    return conn

def exec_sp(sp_name, params=()):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Use T-SQL EXEC with parameters
            placeholders = ", ".join(["%s"] * len(params))
            sql = f"EXEC {sp_name} {placeholders}" if placeholders else f"EXEC {sp_name}"
            cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()

def query_df(sql, params=()):
    conn = get_conn()
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    finally:
        conn.close()
