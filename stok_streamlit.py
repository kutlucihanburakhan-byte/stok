
# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, date
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd
import streamlit as st
from openpyxl import Workbook, load_workbook

APP_TZ = ZoneInfo("Europe/Istanbul")
DB_PATH = Path("stok_db.xlsx")
DEFAULT_FIRE_THRESHOLD_KG = 1000.0

# -------------------------- Excel Helpers -------------------------------
def ensure_workbook():
    if not DB_PATH.exists():
        wb = Workbook()
        ws = wb.active; ws.title = "URUNLER"
        ws.append(["product_id","tur","boyut","kalite","created_at"])
        ws2 = wb.create_sheet("HAREKETLER")
        ws2.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"])
        ws3 = wb.create_sheet("FIRE_DEPOSU")
        ws3.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"])
        wb.save(DB_PATH)
    else:
        wb = load_workbook(DB_PATH)
        if "URUNLER" not in wb.sheetnames:
            ws = wb.create_sheet("URUNLER")
            ws.append(["product_id","tur","boyut","kalite","created_at"])
        if "HAREKETLER" not in wb.sheetnames:
            ws2 = wb.create_sheet("HAREKETLER")
            ws2.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"])
        if "FIRE_DEPOSU" not in wb.sheetnames:
            ws3 = wb.create_sheet("FIRE_DEPOSU")
            ws3.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"])
        wb.save(DB_PATH)

def read_sheet(name): 
    ensure_workbook()
    try:
        return pd.read_excel(DB_PATH, sheet_name=name, engine="openpyxl")
    except Exception:
        return pd.DataFrame()

def write_sheet(name, df):
    with pd.ExcelWriter(DB_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=name, index=False)

def list_urunler():
    df = read_sheet("URUNLER")
    return df[df["product_id"].notna()] if not df.empty else df

def create_product(tur, boyut, kalite):
    df = list_urunler()
    pid = str(uuid.uuid4())
    now = datetime.now(APP_TZ).isoformat()
    new_row = pd.DataFrame([{"product_id":pid,"tur":tur.strip(),"boyut":boyut.strip(),"kalite":kalite.strip(),"created_at":now}])
    df_out = pd.concat([df, new_row], ignore_index=True) if not df.empty else new_row
    write_sheet("URUNLER", df_out)
    return pid

def append_hareket(pid, h_tur, miktar, birim="kg", proje="", aciklama="", tarih=None, fire_threshold=DEFAULT_FIRE_THRESHOLD_KG):
    if tarih is None: tarih = date.today().isoformat()
    created_at = datetime.now(APP_TZ).isoformat()
    hid = str(uuid.uuid4())
    df = read_sheet("HAREKETLER")
    new = pd.DataFrame([{"hareket_id":hid,"product_id":pid,"hareket_turu":h_tur,"miktar":float(miktar),
                         "birim":birim,"proje":proje,"aciklama":aciklama,"tarih":tarih,"created_at":created_at}])
    df_out = pd.concat([df, new], ignore_index=True) if not df.empty else new
    write_sheet("HAREKETLER", df_out)
    if h_tur.upper()=="FIRE" and float(miktar)>=float(fire_threshold):
        df_fire = read_sheet("FIRE_DEPOSU")
        df_fire_out = pd.concat([df_fire, new], ignore_index=True) if not df_fire.empty else new
        write_sheet("FIRE_DEPOSU", df_fire_out)
    return hid

def compute_stock_balance(pid):
    df = read_sheet("HAREKETLER")
    if df.empty: return 0.0
    sub = df[df["product_id"]==pid].copy()
    if sub.empty: return 0.0
    sub["hareket_turu"]=sub["hareket_turu"].str.upper()
    giris = sub.loc[sub["hareket_turu"]=="GIRIS","miktar"].sum()
    cikis = sub.loc[sub["hareket_turu"].isin(["CIKIS","FIRE"]),"miktar"].sum()
    return float(giris - cikis)

def list_hareketler(pid, limit=200):
    df = read_sheet("HAREKETLER")
    sub = df[df["product_id"]==pid].copy()
    if sub.empty: return sub
    sub["tarih"]=pd.to_datetime(sub["tarih"],errors="coerce")
    sub["created_at"]=pd.to_datetime(sub["created_at"],errors="coerce")
    return sub.sort_values(["tarih","created_at"],ascending=[False,False]).head(limit)

# -------------------------- UI -------------------------------
st.set_page_config(page_title="Stok Uygulaması", layout="wide")
st.title("📦 Stok Uygulaması (Excel/Streamlit)")

ensure_workbook()
st.sidebar.header("Ayarlar & Yardım")
fire_threshold = st.sidebar.number_input("FIRE eşiği (kg)", value=float(DEFAULT_FIRE_THRESHOLD_KG), step=100.0, min_value=0.0)

# Demo verisi ekle
if st.sidebar.button("🔧 Demo verisi ekle"):
    # Ürün ve hareketler
    pid = create_product("IPE","120","S235JR")
    append_hareket(pid,"GIRIS",5000,"kg","DEMO","İlk giriş")
    append_hareket(pid,"CIKIS",1200,"kg","DEMO","Kullanım")
    append_hareket(pid,"FIRE",1500,"kg","DEMO","Kesim fire", fire_threshold=fire_threshold)
    st.sidebar.success("Demo verisi eklendi.")

tab = st.sidebar.radio("Menü", ["Stok Sorgula","Stok Girişi","Stoktan Kullan / Fire","Yeni Ürün","Fire Deposu / İndirme"])

urun_df = list_urunler()
label_series = (urun_df["tur"].fillna("")+" | "+urun_df["boyut"].fillna("")+" | "+urun_df["kalite"].fillna(""))
urun_map = dict(zip(label_series, urun_df["product_id"])) if not urun_df.empty else {}

def empty_state():
    st.info("Henüz ürün bulunamadı. Soldaki menüden **Yeni Ürün** ekleyin veya **🔧 Demo verisi ekle** tuşuna basın.\n\n"
            "Alternatif olarak mevcut `stok_db.xlsx` dosyanızı çalışma klasörüne koyabilirsiniz.")

if tab=="Stok Sorgula":
    st.subheader("🔎 Stok Sorgula")
    if not urun_map:
        empty_state()
    else:
        sel = st.selectbox("Ürün (Tür | Boyut | Kalite)", list(urun_map.keys()))
        pid = urun_map[sel]
        st.metric("Güncel Stok (kg)", f"{compute_stock_balance(pid):,.2f}")
        dfh = list_hareketler(pid,200)
        if dfh.empty:
            st.info("Bu ürüne ait hareket yok.")
        else:
            st.dataframe(dfh[["tarih","hareket_turu","miktar","birim","proje","aciklama","created_at"]], use_container_width=True)

elif tab=="Stok Girişi":
    st.subheader("➕ Stok Girişi")
    if not urun_map:
        empty_state()
    else:
        with st.form("giris"):
            sel = st.selectbox("Ürün", list(urun_map.keys()))
            miktar = st.number_input("Miktar (kg)",0.0, step=10.0, format="%.2f")
            proje = st.text_input("Proje","")
            aciklama = st.text_input("Açıklama","")
            tarih_inp = st.date_input("Tarih", value=date.today())
            ok = st.form_submit_button("Kaydet")
        if ok:
            append_hareket(urun_map[sel],"GIRIS",miktar,"kg",proje,aciklama,tarih_inp.isoformat(),fire_threshold)
            st.success("Giriş kaydedildi.")

elif tab=="Stoktan Kullan / Fire":
    st.subheader("➖ Stoktan Kullan / Fire")
    if not urun_map:
        empty_state()
    else:
        with st.form("cikis"):
            sel = st.selectbox("Ürün", list(urun_map.keys()))
            h_tur = st.selectbox("Hareket Türü", ["CIKIS","FIRE"])
            miktar = st.number_input("Miktar (kg)",0.0, step=10.0, format="%.2f")
            proje = st.text_input("Proje","")
            aciklama = st.text_input("Açıklama","")
            tarih_inp = st.date_input("Tarih", value=date.today())
            ok = st.form_submit_button("Kaydet")
        if ok:
            bakiye = compute_stock_balance(urun_map[sel])
            if h_tur in ("CIKIS","FIRE") and miktar>bakiye:
                st.warning(f"Mevcut bakiye {bakiye:,.2f} kg. Negatif bakiyeye düşecek.")
            append_hareket(urun_map[sel],h_tur,miktar,"kg",proje,aciklama,tarih_inp.isoformat(),fire_threshold)
            st.success(f"{h_tur} kaydedildi.")

elif tab=="Yeni Ürün":
    st.subheader("🆕 Yeni Ürün")
    with st.form("urun"):
        tur = st.text_input("Tür")
        boyut = st.text_input("Boyut")
        kalite = st.text_input("Kalite")
        ok = st.form_submit_button("Ürün Oluştur")
    if ok:
        if not tur.strip() or not boyut.strip() or not kalite.strip():
            st.error("Tür, Boyut, Kalite boş olamaz.")
        else:
            create_product(tur,boyut,kalite)
            st.success("Ürün oluşturuldu.")

    st.markdown("### Mevcut Ürünler")
    if urun_df.empty:
        st.info("Henüz ürün yok.")
    else:
        st.dataframe(urun_df[["tur","boyut","kalite","product_id","created_at"]], use_container_width=True)

elif tab=="Fire Deposu / İndirme":
    st.subheader("🔥 Fire Deposu")
    st.dataframe(read_sheet("FIRE_DEPOSU"), use_container_width=True)
    if DB_PATH.exists():
        st.download_button("Excel'i indir (stok_db.xlsx)", data=DB_PATH.read_bytes(),
                           file_name="stok_db.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()
st.caption("Boş görünüyorsa: **Yeni Ürün** ekleyin veya soldaki **🔧 Demo verisi ekle** butonuna basın.")



# ===== Robust Excel helpers (corruption-safe) =====
import time
from zipfile import BadZipFile

def _fresh_workbook():
    wb = Workbook()
    ws = wb.active; ws.title = "URUNLER"
    ws.append(["product_id","tur","boyut","kalite","created_at"])
    ws2 = wb.create_sheet("HAREKETLER")
    ws2.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"])
    ws3 = wb.create_sheet("FIRE_DEPOSU")
    ws3.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"])
    wb.save(DB_PATH)

def ensure_workbook():
    """
    Workbook yoksa oluşturur. Varsa ve bozuk/eksikse otomatik onarır.
    Bozuk dosyalar (0 byte, yarım yazılmış, ZIP/EOF hatası) yakalanıp yeniden oluşturulur.
    """
    # Yoksa taze oluştur
    if not DB_PATH.exists() or DB_PATH.stat().st_size < 2000:
        _fresh_workbook()
        return

    # Varsa: güvenli şekilde yüklemeyi dene
    try:
        wb = load_workbook(DB_PATH)
    except (BadZipFile, EOFError, KeyError, OSError, ValueError):
        # Bozuk dosya -> sıfırdan oluştur
        DB_PATH.unlink(missing_ok=True)
        _fresh_workbook()
        return

    # Eksik sayfaları tamamla
    changed = False
    if "URUNLER" not in wb.sheetnames:
        ws = wb.create_sheet("URUNLER"); ws.append(["product_id","tur","boyut","kalite","created_at"]); changed = True
    if "HAREKETLER" not in wb.sheetnames:
        ws2 = wb.create_sheet("HAREKETLER"); ws2.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"]); changed = True
    if "FIRE_DEPOSU" not in wb.sheetnames:
        ws3 = wb.create_sheet("FIRE_DEPOSU"); ws3.append(["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"]); changed = True
    if changed:
        wb.save(DB_PATH)

def read_sheet(name):
    ensure_workbook()
    try:
        return pd.read_excel(DB_PATH, sheet_name=name, engine="openpyxl")
    except (BadZipFile, EOFError, KeyError, OSError, ValueError):
        # Onar ve tekrar dene
        DB_PATH.unlink(missing_ok=True)
        _fresh_workbook()
        return pd.read_excel(DB_PATH, sheet_name=name, engine="openpyxl")

def write_sheet(name, df):
    # 2 denemeli güvenli yazma
    for attempt in range(2):
        try:
            with pd.ExcelWriter(DB_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace") as w:
                df.to_excel(w, sheet_name=name, index=False)
            return
        except (BadZipFile, EOFError, KeyError, OSError, ValueError):
            DB_PATH.unlink(missing_ok=True)
            _fresh_workbook()
            if attempt == 1:
                raise
