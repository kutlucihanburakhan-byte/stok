# Excel → SQL Migrator (URUNLER / HAREKETLER / FIRE_DEPOSU)

Bu paket, **`stok_db.xlsx`** dosyasındaki sayfaları
aynı alan adlarıyla **SQL veritabanına** aktarır ve talebe uygun görünümler (view) oluşturur:

- **URUNLER → `urunler`** (ürün kartları / profil tanımları)
- **HAREKETLER → `hareketler`** (stok giriş/çıkış/kullanım hareketleri)
- **FIRE_DEPOSU → `fire_deposu`** (fire kayıtları)
- Her *profil tipi* için **view** oluşturulur: `urunler__<tur_slug>`
- Kullanım hareketleri için **view**: `stok_kullanim` (hareket_turu'na göre)
- Net stok özeti için **view**: `stok_ozet` (giriş - çıkış mantığı)

> İstersen view yerine fiziksel tablo (materialized/denormalized) da üretebiliriz;
> ilk revizyonda view kullandım (tekrar hesap güvenli olsun diye).

## 1) Kurulum

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Çalıştırma

```bash
# Varsayılan: SQLite (data.db) — aynı klasöre yazar
python migrate_from_excel.py --excel "stok_db.xlsx"

# PostgreSQL (Önerilen)
# DATABASE_URL=postgresql+psycopg2://USER:PASS@HOST:PORT/DBNAME
DATABASE_URL="postgresql+psycopg2://user:pass@host/db" \
python migrate_from_excel.py --excel "stok_db.xlsx"
```

> `DATABASE_URL` verilmezse `sqlite:///data.db` kullanılır.

## 3) Sonuç Nesneleri

- Tablolar: `urunler`, `hareketler`, `fire_deposu` (+ otomatik oluşturulacak index ve kısıtlar)
- View'lar:
  - **`urunler__<tur_slug>`**: `<tur>` değerine göre ürün alt setleri (ör. `urunler__ipe`, `urunler__hea`).
  - **`stok_kullanim`**: `hareketler` içinden kullanım/çıkış hareketlerinin filtresi.
  - **`stok_ozet`**: ürün bazlı *net stok* (giriş - çıkış).
- PostgreSQL kullanıyorsanız, isterseniz ikinci aşamada **materialized view** (MV) olarak da revize ederiz.

## 4) Şema Varsayımları

- `URUNLER(product_id, tur, boyut, kalite, created_at)`
- `HAREKETLER(hareket_id, product_id, hareket_turu, miktar, birim, proje, aciklama, tarih, created_at)`
- `FIRE_DEPOSU(hareket_id, product_id, hareket_turu, miktar, birim, proje, aciklama, tarih, created_at)`

> Excel kolon adlarınız halihazırda küçük harf ve uyumlu olduğu için **hiç yeniden adlandırma yapmıyoruz**.
> Değer tipleri best‑effort biçimde sayısal/tarih metin olarak çevrilir.

## 5) Genişletme / Revizyon

- `hareket_turu` sözlüğü (giriş/çıkış/kullanım/fire) şirket standardınıza göre parametrize edilebilir.
- `stok_ozet`'te proje/kalite/boyut kırılımları için ek view’lar üretebiliriz.
- Her profil tipi için *view yerine tablo* istiyorsanız `--materialize-types` bayrağı ile üretilebilir.
