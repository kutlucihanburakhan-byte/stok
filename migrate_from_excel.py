import os, argparse, sys
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from slugify import slugify

def get_engine():
    url = os.environ.get("DATABASE_URL", "sqlite:///data.db")
    eng = create_engine(url, future=True)
    return eng, url

def read_excel(excel_path):
    xl = pd.ExcelFile(excel_path)
    out = {}
    for sh in xl.sheet_names:
        df = pd.read_excel(excel_path, sheet_name=sh)
        # Normalize column names
        df.columns = [str(c).strip().lower() for c in df.columns]
        out[sh.upper()] = df
    return out

def to_sql(df, table, eng):
    # dtype inference handled by pandas sqlalchemy writer
    df.to_sql(table, eng, if_exists="replace", index=False)

def create_base_tables(dfs, eng):
    # URUNLER
    if "URUNLER" not in dfs:
        print("HATA: URUNLER sayfası bulunamadı.", file=sys.stderr)
        sys.exit(1)
    to_sql(dfs["URUNLER"], "urunler", eng)

    # HAREKETLER (opsiyonel)
    if "HAREKETLER" in dfs:
        to_sql(dfs["HAREKETLER"], "hareketler", eng)

    # FIRE_DEPOSU (opsiyonel)
    if "FIRE_DEPOSU" in dfs:
        to_sql(dfs["FIRE_DEPOSU"], "fire_deposu", eng)

def create_indexes_constraints(eng, url):
    # Basic indexes & constraints (portable)
    with eng.begin() as con:
        # try to add unique constraints where logical
        try:
            con.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_urunler_product_id ON urunler(product_id);"))
        except Exception:
            pass
        try:
            con.execute(text("CREATE INDEX IF NOT EXISTS idx_urunler_tur ON urunler(tur);"))
        except Exception:
            pass
        try:
            con.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_hareketler_hareket_id ON hareketler(hareket_id);"))
        except Exception:
            pass
        for col in ("product_id","tarih"):
            try:
                con.execute(text(f"CREATE INDEX IF NOT EXISTS idx_hareketler_{col} ON hareketler({col});"))
            except Exception:
                pass
        try:
            con.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_fire_hareket_id ON fire_deposu(hareket_id);"))
        except Exception:
            pass

def detect_types_and_create_views(dfs, eng, materialize_types=False):
    # Profile types from URUNLER.tur
    tur_values = []
    if "URUNLER" in dfs and "tur" in dfs["URUNLER"].columns:
        tur_values = sorted(v for v in dfs["URUNLER"]["tur"].dropna().astype(str).unique())
    # Create type views
    with eng.begin() as con:
        for tur in tur_values:
            slug = slugify(tur, separator='_')
            name = f"urunler__{slug}"
            if materialize_types:
                # Materialize as physical table
                con.execute(text(f"DROP TABLE IF EXISTS {name};"))
                con.execute(text(f"CREATE TABLE {name} AS SELECT * FROM urunler WHERE tur = :tur;"), {"tur": tur})
            else:
                # Create a view
                # SQLite lacks CREATE OR REPLACE VIEW; do drop first
                try:
                    con.execute(text(f"DROP VIEW IF EXISTS {name};"))
                except Exception:
                    pass
                con.execute(text(f"CREATE VIEW {name} AS SELECT * FROM urunler WHERE tur = :tur;"), {"tur": tur})

        # stok_kullanim view: hareketler'den kullanım/çıkış filtrele
        try:
            con.execute(text("DROP VIEW IF EXISTS stok_kullanim;"))
        except Exception:
            pass
        con.execute(text("""
        CREATE VIEW stok_kullanim AS
        SELECT *
        FROM hareketler
        WHERE lower(coalesce(hareket_turu,'')) IN ('kullanim','kullanım','cikis','çıkış','cikis','cıkış')
              OR (miktar < 0)
        """))

        # stok_giris view
        try:
            con.execute(text("DROP VIEW IF EXISTS stok_giris;"))
        except Exception:
            pass
        con.execute(text("""
        CREATE VIEW stok_giris AS
        SELECT *
        FROM hareketler
        WHERE lower(coalesce(hareket_turu,'')) IN ('giris','giriş')
              OR (miktar > 0)
        """))

        # stok_ozet view: net miktar
        try:
            con.execute(text("DROP VIEW IF EXISTS stok_ozet;"))
        except Exception:
            pass
        con.execute(text("""
        CREATE VIEW stok_ozet AS
        WITH g AS (
            SELECT product_id, SUM(miktar) AS giren
            FROM stok_giris
            GROUP BY product_id
        ),
        k AS (
            SELECT product_id, SUM(ABS(miktar)) AS cikan
            FROM stok_kullanim
            GROUP BY product_id
        )
        SELECT u.product_id,
               u.tur,
               u.boyut,
               u.kalite,
               COALESCE(g.giren,0) AS giren,
               COALESCE(k.cikan,0) AS cikan,
               COALESCE(g.giren,0) - COALESCE(k.cikan,0) AS kalan
        FROM urunler u
        LEFT JOIN g ON g.product_id = u.product_id
        LEFT JOIN k ON k.product_id = u.product_id;
        """))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", required=True, help="Kaynak Excel dosyası (örn. stok_db.xlsx)")
    ap.add_argument("--materialize-types", action="store_true", help="Profil tipi view yerine fiziksel tablo üret")
    args = ap.parse_args()

    eng, url = get_engine()
    dfs = read_excel(args.excel)

    create_base_tables(dfs, eng)
    create_indexes_constraints(eng, url)
    detect_types_and_create_views(dfs, eng, materialize_types=args.materialize_types)

    print("✅ Aktarım tamamlandı.")
    print("Veritabanı:", url)
    print("Örnek sorgular:")
    print("  SELECT * FROM urunler LIMIT 10;")
    print("  SELECT * FROM stok_ozet ORDER BY kalan ASC LIMIT 10;")

if __name__ == "__main__":
    main()
