
# -*- coding: utf-8 -*-
"""
Tamamen Tarayıcıdan Çalışan Stok Uygulaması (Streamlit)
------------------------------------------------------
* Kurumsal PC'ye "pip install" gerekmez (cloud'da çalıştırın).
* Excel dosyasını (stok_db.xlsx) yükleyip işlem yapın, çıkışta güncel dosyayı indirin.
* Kalıcılık: "yükle → düzenle → indir" akışıyla sağlanır.

Sayfalar / Şemalar:
  - URUNLER(product_id, tur, boyut, kalite, created_at)
  - HAREKETLER(hareket_id, product_id, hareket_turu, miktar, birim, proje, aciklama, tarih, created_at)
  - FIRE_DEPOSU( ... HAREKETLER ile aynı kolonlar ... )

Hareket Türleri:
  - GIRIS, CIKIS, FIRE
Not: FIRE miktarı eşik (kg) üzerindeyse kayıt FIRE_DEPOSU tablosuna da kopyalanır.
"""
import io
import uuid
from datetime import datetime, date
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

APP_TZ = ZoneInfo("Europe/Istanbul")
DEFAULT_FIRE_THRESHOLD_KG = 1000.0

# ----------------------- Yardımcılar (DataFrame tabanlı) ---------------------
def empty_book():
    return {
        "URUNLER": pd.DataFrame(columns=["product_id","tur","boyut","kalite","created_at"]),
        "HAREKETLER": pd.DataFrame(columns=["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"]),
        "FIRE_DEPOSU": pd.DataFrame(columns=["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"]),
    }

def load_from_xlsx(file_bytes: bytes):
    x = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    data = empty_book()
    for name in data.keys():
        if name in x.sheet_names:
            df = pd.read_excel(x, sheet_name=name, engine="openpyxl")
            data[name] = df
    return data

def save_to_xlsx(book: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in book.items():
            out = df.copy()
            out.to_excel(writer, sheet_name=name, index=False)
    buf.seek(0)
    return buf.read()

def list_urunler(book):
    df = book["URUNLER"]
    if df.empty: 
        return df
    return df[df["product_id"].notna()]

def find_product_id(book, tur: str, boyut: str, kalite: str):
    df = list_urunler(book)
    if df.empty: return None
    sel = df[
        df["tur"].fillna("").str.strip().eq(tur.strip()) &
        df["boyut"].fillna("").str.strip().eq(boyut.strip()) &
        df["kalite"].fillna("").str.strip().eq(kalite.strip())
    ]
    if sel.empty: return None
    return sel.iloc[0]["product_id"]

def create_product(book, tur, boyut, kalite):
    df = book["URUNLER"]
    pid = str(uuid.uuid4())
    now = datetime.now(APP_TZ).isoformat()
    new_row = pd.DataFrame([{
        "product_id": pid, "tur": tur.strip(), "boyut": boyut.strip(), "kalite": kalite.strip(), "created_at": now
    }])
    book["URUNLER"] = pd.concat([df, new_row], ignore_index=True)
    return pid

def append_hareket(book, product_id, hareket_turu, miktar, birim="kg", proje="", aciklama="", tarih=None, fire_threshold=DEFAULT_FIRE_THRESHOLD_KG):
    if tarih is None:
        tarih = date.today().isoformat()
    created_at = datetime.now(APP_TZ).isoformat()
    hid = str(uuid.uuid4())
    df = book["HAREKETLER"]
    new_row = pd.DataFrame([{
        "hareket_id": hid, "product_id": product_id, "hareket_turu": hareket_turu,
        "miktar": float(miktar), "birim": birim, "proje": proje, "aciklama": aciklama,
        "tarih": tarih, "created_at": created_at
    }])
    book["HAREKETLER"] = pd.concat([df, new_row], ignore_index=True)

    if hareket_turu.upper() == "FIRE" and float(miktar) >= float(fire_threshold):
        df_fire = book["FIRE_DEPOSU"]
        book["FIRE_DEPOSU"] = pd.concat([df_fire, new_row], ignore_index=True)
    return hid

def compute_stock_balance(book, product_id):
    df = book["HAREKETLER"]
    if df.empty: return 0.0
    sub = df[df["product_id"] == product_id].copy()
    if sub.empty: return 0.0
    sub["hareket_turu"] = sub["hareket_turu"].str.upper()
    giris = sub.loc[sub["hareket_turu"] == "GIRIS", "miktar"].sum()
    cikis = sub.loc[sub["hareket_turu"].isin(["CIKIS","FIRE"]), "miktar"].sum()
    return float(giris - cikis)

def list_hareketler(book, product_id, limit=200):
    df = book["HAREKETLER"]
    sub = df[df["product_id"] == product_id].copy()
    if sub.empty: return sub
    sub["tarih"] = pd.to_datetime(sub["tarih"], errors="coerce")
    sub["created_at"] = pd.to_datetime(sub["created_at"], errors="coerce")
    sub = sub.sort_values(by=["tarih","created_at"], ascending=[False, False]).head(limit)
    return sub

# ------------------------------- UI ------------------------------------------
st.set_page_config(page_title="Stok Uygulaması (Web)", layout="wide")
st.title("🌐 Kurulum Gerektirmeyen Stok Uygulaması")

with st.sidebar:
    st.header("Excel Yükle / İndir")
    uploaded = st.file_uploader("stok_db.xlsx yükle (opsiyonel)", type=["xlsx"])
    st.caption("Dosya yüklemezseniz boş bir kitapla başlayabilirsiniz.")
    fire_threshold = st.number_input("FIRE eşiği (kg)", value=float(DEFAULT_FIRE_THRESHOLD_KG), step=100.0, min_value=0.0)
    tab = st.radio("Menü", ["Stok Sorgula", "Stok Girişi", "Stoktan Kullan / Fire", "Yeni Ürün", "Fire Deposu"])

# Bellekte kitap
if "book" not in st.session_state:
    st.session_state.book = empty_book()

# Eğer dosya yüklendiyse içeri al
if uploaded is not None:
    try:
        st.session_state.book = load_from_xlsx(uploaded.read())
        st.success("Excel içeri aktarıldı.")
    except Exception as e:
        st.error(f"Excel okunamadı: {e}")

book = st.session_state.book

# Ürün listesi
urun_df = list_urunler(book)
urun_display = (urun_df["tur"].fillna("") + " | " + urun_df["boyut"].fillna("") + " | " + urun_df["kalite"].fillna("")).rename("label")
urun_map = dict(zip(urun_display, urun_df["product_id"])) if not urun_df.empty else {}

if tab == "Stok Sorgula":
    st.subheader("🔎 Stok Sorgula")
    if not urun_map:
        st.warning("Henüz ürün yok. Lütfen **Yeni Ürün** sekmesinden ekleyin veya Excel yükleyin.")
    else:
        sel = st.selectbox("Ürün (Tür | Boyut | Kalite)", list(urun_map.keys()))
        pid = urun_map.get(sel)
        if pid:
            bakiye = compute_stock_balance(book, pid)
            st.metric("Güncel Stok (kg)", f"{bakiye:,.2f}")
            hareketler = list_hareketler(book, pid, limit=200)
            if hareketler.empty:
                st.info("Bu ürüne ait hareket bulunamadı.")
            else:
                show_cols = ["tarih","hareket_turu","miktar","birim","proje","aciklama","created_at"]
                st.dataframe(hareketler[show_cols], use_container_width=True)

elif tab == "Stok Girişi":
    st.subheader("➕ Stok Girişi")
    if not urun_map:
        st.warning("Henüz ürün yok. Önce **Yeni Ürün** sekmesinden ekleyin.")
    else:
        with st.form("giris"):
            sel = st.selectbox("Ürün", list(urun_map.keys()), key="giris_sel")
            miktar = st.number_input("Miktar (kg)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
            proje = st.text_input("Proje", value="")
            aciklama = st.text_input("Açıklama", value="")
            tarih_inp = st.date_input("Tarih", value=date.today())
            ok = st.form_submit_button("Kaydet")
        if ok:
            pid = urun_map[sel]
            append_hareket(book, pid, "GIRIS", miktar, "kg", proje, aciklama, tarih_inp.isoformat(), fire_threshold)
            st.success("Stok girişi kaydedildi.")

elif tab == "Stoktan Kullan / Fire":
    st.subheader("➖ Stoktan Kullan / Fire")
    if not urun_map:
        st.warning("Henüz ürün yok. Önce **Yeni Ürün** sekmesinden ekleyin.")
    else:
        with st.form("cikis"):
            sel = st.selectbox("Ürün", list(urun_map.keys()), key="cikis_sel")
            hareket_turu = st.selectbox("Hareket Türü", ["CIKIS","FIRE"])
            miktar = st.number_input("Miktar (kg)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
            proje = st.text_input("Proje", value="")
            aciklama = st.text_input("Açıklama", value="")
            tarih_inp = st.date_input("Tarih", value=date.today())
            ok = st.form_submit_button("Kaydet")
        if ok:
            pid = urun_map[sel]
            bakiye = compute_stock_balance(book, pid)
            if hareket_turu in ("CIKIS","FIRE") and miktar > bakiye:
                st.warning(f"Mevcut bakiye {bakiye:,.2f} kg. Negatif bakiyeye düşecek.")
            append_hareket(book, pid, hareket_turu, miktar, "kg", proje, aciklama, tarih_inp.isoformat(), fire_threshold)
            st.success(f"{hareket_turu} kaydedildi.")

elif tab == "Yeni Ürün":
    st.subheader("🆕 Yeni Ürün")
    with st.form("urun"):
        tur = st.text_input("Tür")
        boyut = st.text_input("Boyut")
        kalite = st.text_input("Kalite")
        ok = st.form_submit_button("Ürün Oluştur")
    if ok:
        if not tur.strip() or not boyut.strip() or not kalite.strip():
            st.error("Tür, Boyut ve Kalite boş olamaz.")
        else:
            pid = find_product_id(book, tur, boyut, kalite)
            if pid:
                st.info("Bu ürün zaten mevcut.")
            else:
                create_product(book, tur, boyut, kalite)
                st.success("Ürün oluşturuldu.")

    st.markdown("### Mevcut Ürünler")
    if urun_df.empty:
        st.info("Henüz ürün yok.")
    else:
        st.dataframe(urun_df[["tur","boyut","kalite","product_id","created_at"]], use_container_width=True)

elif tab == "Fire Deposu":
    st.subheader("🔥 Fire Deposu")
    st.dataframe(book["FIRE_DEPOSU"], use_container_width=True)

st.divider()
# İndirme butonu (güncel state'i Excel olarak indir)
xlsx_bytes = save_to_xlsx(book)
st.download_button("📥 Güncel Excel'i indir (stok_db.xlsx)", data=xlsx_bytes, file_name="stok_db.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.caption("Kurulum gerektirmez • Tarayıcıdan yükle/düzenle/indir akışı • Europe/Istanbul")
