
# Stok Uygulaması (Streamlit, No Install)
# Burak için hazırlandı
import io, uuid
from datetime import datetime, date
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

APP_TZ = ZoneInfo("Europe/Istanbul")
DEFAULT_FIRE_THRESHOLD_KG = 1000.0

def empty_book():
    return {
        "URUNLER": pd.DataFrame(columns=["product_id","tur","boyut","kalite","created_at"]),
        "HAREKETLER": pd.DataFrame(columns=["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"]),
        "FIRE_DEPOSU": pd.DataFrame(columns=["hareket_id","product_id","hareket_turu","miktar","birim","proje","aciklama","tarih","created_at"]),
    }

def save_to_xlsx(book):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in book.items():
            df.to_excel(writer, sheet_name=name, index=False)
    buf.seek(0)
    return buf.read()

def compute_stock_balance(book, pid):
    df = book["HAREKETLER"]
    sub = df[df["product_id"] == pid]
    if sub.empty: return 0.0
    sub["hareket_turu"] = sub["hareket_turu"].str.upper()
    giris = sub.loc[sub["hareket_turu"]=="GIRIS","miktar"].sum()
    cikis = sub.loc[sub["hareket_turu"].isin(["CIKIS","FIRE"]),"miktar"].sum()
    return giris - cikis

st.set_page_config(page_title="Stok App", layout="wide")
st.title("🌐 Stok Uygulaması (No Install)")

if "book" not in st.session_state:
    st.session_state.book = empty_book()
book = st.session_state.book

tab = st.sidebar.radio("Menü", ["Yeni Ürün","Stok Girişi","Stok Sorgula"])

if tab=="Yeni Ürün":
    tur = st.text_input("Tür")
    boyut = st.text_input("Boyut")
    kalite = st.text_input("Kalite")
    if st.button("Ekle"):
        pid = str(uuid.uuid4())
        book["URUNLER"] = pd.concat([book["URUNLER"], pd.DataFrame([{
            "product_id": pid,"tur":tur,"boyut":boyut,"kalite":kalite,"created_at":datetime.now(APP_TZ).isoformat()
        }])], ignore_index=True)
        st.success("Ürün eklendi")

elif tab=="Stok Girişi":
    if book["URUNLER"].empty:
        st.warning("Önce ürün ekleyin")
    else:
        sel = st.selectbox("Ürün", book["URUNLER"]["tur"]+"|"+book["URUNLER"]["boyut"]+"|"+book["URUNLER"]["kalite"])
        miktar = st.number_input("Miktar",0.0)
        if st.button("Kaydet"):
            pid = book["URUNLER"].iloc[sel.index[0]]["product_id"]
            book["HAREKETLER"] = pd.concat([book["HAREKETLER"], pd.DataFrame([{
                "hareket_id": str(uuid.uuid4()),"product_id": pid,"hareket_turu":"GIRIS",
                "miktar":miktar,"birim":"kg","proje":"","aciklama":"","tarih":date.today().isoformat(),"created_at":datetime.now(APP_TZ).isoformat()
            }])], ignore_index=True)
            st.success("Kayıt eklendi")

elif tab=="Stok Sorgula":
    if book["URUNLER"].empty:
        st.info("Ürün yok")
    else:
        sel = st.selectbox("Ürün", book["URUNLER"]["tur"]+"|"+book["URUNLER"]["boyut"]+"|"+book["URUNLER"]["kalite"])
        pid = book["URUNLER"].iloc[sel.index[0]]["product_id"]
        bakiye = compute_stock_balance(book,pid)
        st.metric("Bakiye", f"{bakiye:.2f} kg")

st.download_button("📥 Excel indir", data=save_to_xlsx(book), file_name="stok_db.xlsx")
