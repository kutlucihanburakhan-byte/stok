
import streamlit as st
import pandas as pd
from db import get_conn, exec_sp, query_df

st.set_page_config(page_title="Stok Takip (Streamlit + MSSQL)", page_icon="📦", layout="wide")

st.title("📦 Stok Takip — Streamlit + MSSQL")

with st.sidebar:
    st.header("Bağlantı")
    ok = False
    try:
        conn = get_conn()
        ok = True
        st.success("MSSQL bağlantısı OK")
    except Exception as e:
        st.error(f"Bağlantı hatası: {e}")
        st.stop()

tab1, tab2, tab3 = st.tabs(["Ekle/Artır (SP)", "Ara (TVF)", "Özet (View)"])

with tab1:
    st.subheader("Stok Ekle / Artır (Stored Procedure)")
    col1, col2, col3, col4 = st.columns([2,2,1,1])
    with col1:
        malzeme = st.text_input("MalzemeKod", value="IPE100")
    with col2:
        kalite = st.text_input("Kalite", value="S235JR")
    with col3:
        boymm = st.text_input("Boy (mm)", value="6000")
    with col4:
        adet = st.number_input("Adet (+)", min_value=1, step=1, value=10)

    if st.button("Ekle/Artır (SP)"):
        try:
            boy_val = int(boymm) if boymm.strip() else None
            exec_sp("dbo.Sp_StokEkleVeyaArtir", (malzeme, kalite or None, boy_val, int(adet)))
            st.success("Stok güncellendi.")
        except Exception as e:
            st.error(f"Hata: {e}")

with tab2:
    st.subheader("Ara (TVF: dbo.Fn_StokAra)")
    q = st.text_input("Ara (Malzeme içeren)", value="IPE")
    if st.button("Ara (TVF)"):
        try:
            df = query_df("SELECT StokID, MalzemeKod, Kalite, BoyMM, Adet, OlusturmaTS FROM dbo.Fn_StokAra(%s)", (q,))
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Hata: {e}")

with tab3:
    st.subheader("Özet Görünüm (View: dbo.Vw_StokOzet)")
    if st.button("Özet Görünüm (View)"):
        try:
            df = query_df("SELECT MalzemeKod, Kalite, BoyMM, ToplamAdet FROM dbo.Vw_StokOzet")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Hata: {e}")
