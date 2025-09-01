import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="SQL Görüntüleyici", page_icon="🗄️", layout="wide")
st.title("🗄️ Excel → SQL Migrator: Görüntüleyici")

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///data.db")
engine = create_engine(DB_URL, future=True)

@st.cache_data(ttl=5)
def q(sql):
    return pd.read_sql(sql, engine)

tabs = st.tabs(["urunler", "hareketler", "fire_deposu", "stok_kullanim", "stok_giris", "stok_ozet"])

with tabs[0]:
    st.dataframe(q("SELECT * FROM urunler ORDER BY product_id"), use_container_width=True)
with tabs[1]:
    try:
        st.dataframe(q("SELECT * FROM hareketler ORDER BY tarih DESC, hareket_id DESC"), use_container_width=True)
    except Exception as e:
        st.info("hareketler tablosu yok veya boş.")
with tabs[2]:
    try:
        st.dataframe(q("SELECT * FROM fire_deposu ORDER BY tarih DESC, hareket_id DESC"), use_container_width=True)
    except Exception as e:
        st.info("fire_deposu tablosu yok veya boş.")
with tabs[3]:
    try:
        st.dataframe(q("SELECT * FROM stok_kullanim ORDER BY tarih DESC"), use_container_width=True)
    except Exception as e:
        st.info("stok_kullanim görünümü yok.")
with tabs[4]:
    try:
        st.dataframe(q("SELECT * FROM stok_giris ORDER BY tarih DESC"), use_container_width=True)
    except Exception as e:
        st.info("stok_giris görünümü yok.")
with tabs[5]:
    try:
        st.dataframe(q("SELECT * FROM stok_ozet ORDER BY kalan ASC"), use_container_width=True)
    except Exception as e:
        st.info("stok_ozet görünümü yok.")
