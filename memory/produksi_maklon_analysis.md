# Dokumen Analisis — Portal Produksi & Portal Maklon
## CV. Dewi Aditya — ERP System

**Dibuat:** 22 Mei 2026  
**Status:** Draft untuk Review  
**Tujuan:** Dokumentasi hasil analisis arsitektur bisnis dan gap sistem sebelum development plan

---

## 1. Profil Bisnis CV. Dewi Aditya

### Identitas Bisnis
CV. Dewi Aditya adalah **perusahaan fashion e-commerce** yang menjalankan dua model bisnis secara bersamaan:
1. **Memproduksi dan menjual produk fashion sendiri** secara online (Shopee, Tokopedia, TikTok Shop, dll.)
2. **Menyediakan layanan maklon/CMT** untuk brand atau PT lain yang membutuhkan jasa produksi garmen

**Catatan penting:** CV. Dewi Aditya **bukan pabrik garmen**. Mereka **tidak memiliki mesin jahit atau operator produksi sendiri**. Seluruh proses CMT (cutting, making, trimming) dialihdayakan ke **vendor garment/CMT eksternal**.

---

## 2. Dua Model Bisnis Utama

### Model A — Produksi Produk Sendiri (In-House Brand)

**Deskripsi:**  
CV. Dewi Aditya sebagai **brand owner** yang mengembangkan koleksi produk sendiri dari tahap R&D hingga penjualan online.

**Alur Proses:**
```
R&D / Pengembangan Produk
    → Desain, pilih material, buat spesifikasi teknis
    → Iterasi sample dengan vendor CMT
    → Approval sample final

Persiapan Produksi
    → Finalisasi BOM (kain, aksesoris, label, packaging)
    → Buat Purchase Order ke supplier (kain roll, aksesoris)
    → Terima material masuk ke gudang (WMS)

Produksi (via Vendor CMT Eksternal)
    → Buat Production Order
    → Lempar ke vendor CMT/garment eksternal
    → Vendor cutting → jahit → trimming
    → CV. Dewi Aditya membayar ongkos CMT ke vendor

Pasca Produksi
    → Terima hasil dari vendor
    → QC incoming (CV. DA atau di vendor)
    → Finishing, packaging
    → Masuk stok gudang CV. DA

Distribusi
    → Jual via marketplace (Shopee, Tokopedia, TikTok Shop)
    → Dikelola Portal Marketing (Multi-akun marketplace)
```

**Karakteristik Biaya:**
- CV. DA menanggung: biaya kain + aksesoris + ongkos CMT vendor + packaging
- HPP = Material + CMT fee + Overhead koordinasi
- Revenue dari harga jual produk di marketplace

---

### Model B — Layanan Maklon (CMT Service untuk Klien Eksternal)

**Deskripsi:**  
CV. Dewi Aditya sebagai **CMT service provider** yang menerima order produksi dari brand atau PT lain, kemudian mengkoordinasikan produksi ke vendor CMT yang sama.

**Alur Proses:**
```
Akuisisi Klien
    → Brand/PT lain datang ke CV. DA
    → Negosiasi harga CMT rate, MOQ, lead time

Sample & Approval
    → Klien kirim spec & desain
    → Buat sample (via vendor CMT)
    → Revisi hingga klien approve

Order Masuk
    → Klien buat Purchase Order ke CV. DA
    → CV. DA konfirmasi order maklon
    → Kesepakatan material: klien kirim kain ATAU CV. DA beli + charge ke klien

Produksi (via Vendor CMT yang Sama)
    → CV. DA lempar ke vendor CMT yang sama dengan Model A
    → Koordinasi produksi, monitor progress, handle issue

Delivery & Billing
    → QC hasil produksi
    → Packing sesuai instruksi klien
    → Pengiriman ke klien
    → Invoice CMT fee ke klien → Revenue
```

**Karakteristik Biaya:**
- Tergantung kesepakatan material:
  - Klien kirim kain: CV. DA hanya charge CMT fee + margin koordinasi
  - CV. DA sediakan kain: HPP termasuk material, charge harga pokok + margin
- Revenue = CMT fee dari klien (harga ke klien > biaya ke vendor + koordinasi)

---

## 3. Hubungan Antar Proses

```
                    ┌────────────────────────────────┐
                    │       CV. DEWI ADITYA          │
                    │   (Brand + CMT Coordinator)    │
                    └────────────┬───────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────▼──────┐ ┌─────────▼──────┐ ┌────────▼───────┐
    │   R&D Produk   │ │   Klien Maklon │ │  Supplier      │
    │   Sendiri      │ │   (Brand Lain) │ │  (Kain, Aks.)  │
    └────────┬───────┘ └────────┬───────┘ └────────┬───────┘
             │                  │                  │
             └──────────────────▼──────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   VENDOR CMT/GARMENT  │
                    │   (Eksternal)         │
                    │   Cutting, Jahit,     │
                    │   Trimming            │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼──────────────────┐
              │                 │                   │
    ┌─────────▼──────┐         │          ┌────────▼───────┐
    │  Stok CV. DA   │         │          │  Kirim ke      │
    │  → Jual Online │         │          │  Klien Maklon  │
    └────────────────┘         │          └────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   QC, Finishing,    │
                    │   Packing           │
                    │   (di CV. DA atau   │
                    │   di vendor)        │
                    └─────────────────────┘
```

---

## 4. Analisis Sistem Saat Ini

### 4.1 Portal Produksi

**Scope sistem (35+ modul):**

| Area | Modul | Keterangan |
|---|---|---|
| Perencanaan | Order Produksi, Work Order, BOM | Ada, belum ada data |
| Eksekusi | 5 Langkah (Cutting→Jahit→Finishing→QC→Packing) | Ada |
| CMT | Manajemen CMT, Kekurangan Komponen | Ada |
| Bundle & Material | Bundle Tracking, Material Reservation | Ada |
| Real-time | Line Board, Andon Board | Ada (relevansi perlu dikaji) |
| Quality | Pareto Cacat, FPY, AQL | Ada |
| Mesin | Downtime, Predictive Maintenance | Ada (relevansi perlu dikaji) |
| AI | AI Insights, Chatbot | Ada |
| Master Data | Lini, Mesin, Shift, SOP, BOM | Ada |
| R&D | Product & BOM master, Operator Matrix | Ada |

**Integrasi yang sudah berfungsi:**
- ✅ Shipment → Finance (COGS posting via `post_cogs_shipment`)
- ✅ Work Order → Material Stock (reservation + consumption)
- ✅ Maklon Order → Work Order (auto-create WO saat order dikonfirmasi)
- ✅ Production Calendar (libur nasional exclude dari working days)
- ✅ Andon Alert → Notifikasi ke production manager
- ✅ HPP Snapshot per Work Order

### 4.2 Portal Maklon

**Scope sistem (15+ modul):**

| Area | Modul | Keterangan |
|---|---|---|
| CRM | Dashboard, Client Management | Ada |
| Order | Order Maklon, Sample Management | Ada |
| Produksi | Tracking, CMT Assignment, QC | Ada |
| Delivery | Packing & Pengiriman | Ada |
| Finance | Invoice & Billing, HPP Jasa Jahit | Ada — tapi TIDAK terposting ke GL |
| Analytics | SLA Dashboard, AI Quote Generator | Ada |

---

## 5. Gap Analysis

### 5.1 Gap Kritis (🔴 P0)

**Gap 1: Semua data kosong**
- Seluruh collection produksi: 0 records
- Seluruh collection maklon: 0 records
- Sistem tidak bisa dievaluasi fungsionalitasnya
- **Dampak:** Tidak bisa demo ke stakeholder, tidak bisa menemukan bug alur

**Gap 2: Maklon Billing ≠ Finance GL**
```
dewi_maklon_billing.py → dewi_maklon_invoices (collection sendiri)
                                    ↓
              TIDAK terposting ke rahaza_ar_invoices
              TIDAK ada GL posting (Dr AR / Cr Revenue Maklon)
```
- **Dampak:** Pendapatan maklon tidak masuk laporan keuangan sama sekali
- **Fix yang dibutuhkan:** Saat invoice maklon dibuat/dibayar → trigger `post_ar_invoice` ke Finance

### 5.2 Gap Penting (🟡 P1)

**Gap 3: Operator Produksi ≠ HR Karyawan**
- `rahaza_work_orders` menyimpan `operator_id` sebagai string bebas
- Tidak linked ke `rahaza_employees`
- **Dampak:** Tidak bisa tracking produktivitas per karyawan, tidak bisa hitung upah berbasis WO

**Gap 4: WO selesai → Shipment tidak otomatis**
- Work Order status "done" tidak trigger pembuatan Shipment
- HR harus manual buat Shipment dari WO yang selesai
- **Dampak:** Kemungkinan terlewat, tidak ada audit trail otomatis

**Gap 5: Ketidaksesuaian fitur dengan model bisnis**

Beberapa modul di Portal Produksi dibuat untuk pabrik yang **memiliki mesin dan operator sendiri**, sementara CV. DA adalah **coordinator/brand owner**:

| Modul | Relevansi untuk CV. DA |
|---|---|
| Line Board real-time | ⚠️ Kurang relevan — CV. DA tidak punya lini produksi sendiri |
| Andon Board | ⚠️ Kurang relevan — sama, ini untuk floor supervisor pabrik |
| Log Downtime Mesin | ⚠️ Kurang relevan — mesin milik vendor CMT |
| Operator & Skill Matrix | ⚠️ Perlu disesuaikan — operator adalah pekerja vendor CMT, bukan karyawan CV. DA |
| CMT Manajemen | ✅ SANGAT relevan — ini inti bisnis CV. DA |
| BOM | ✅ SANGAT relevan |
| Order Produksi → WO ke vendor | ✅ SANGAT relevan |
| HPP per WO | ✅ SANGAT relevan |

### 5.3 Gap Minor (🟢 P2)

| Gap | Keterangan |
|---|---|
| BOM validation saat create WO | Tidak ada auto-check apakah material cukup |
| Naming CMT ambigu | "CMT Manajemen" di Produksi = kita lempar ke vendor. Berbeda dengan Maklon (kita terima order) |
| R&D → Produksi traceability | Apakah ada link dari R&D product ke Production Order? |
| Klien portal maklon | Tidak ada self-service untuk klien melihat progress order mereka |

---

## 6. Perbedaan Fundamental: Produksi Sendiri vs Maklon

| Dimensi | Produksi Sendiri | Maklon |
|---|---|---|
| **Pemilik produk** | CV. Dewi Aditya | Klien eksternal (brand lain) |
| **Pemilik material** | CV. Dewi Aditya (beli kain) | Klien (kirim kain) ATAU CV. DA (charge ke klien) |
| **Vendor CMT** | Sama — vendor yang sama | Sama — vendor yang sama |
| **Output** | Stok CV. DA → jual online | Kirim ke klien |
| **Revenue model** | Jual produk di marketplace | CMT fee dari klien |
| **Finance flow** | COGS → Revenue (via marketplace) | AR Invoice ke klien → Revenue |
| **HPP** | Material + CMT + Overhead | CMT coordination fee + margin |
| **Portal utama** | Portal Produksi + Portal Marketing | Portal Maklon |

---

## 7. Pertanyaan Terbuka (Perlu Konfirmasi)

Sebelum development plan dibuat, beberapa hal perlu dikonfirmasi:

1. **Vendor CMT:** Apakah vendor CMT untuk produksi sendiri dan maklon adalah pool yang sama? Atau dipisah?

2. **QC & Packing lokasi:** Setelah barang jadi dari vendor CMT — dilakukan di gudang CV. DA atau tetap di vendor?

3. **Material maklon:** Ketika menerima order maklon, siapa yang biasanya menyediakan kain?

4. **Line Board & Andon Board:** Apakah modul-modul ini dipakai untuk memantau proses di vendor CMT (remote monitoring), atau memang tidak relevan?

5. **Klien portal:** Apakah klien maklon perlu akses portal sendiri untuk tracking order mereka?

6. **Hubungan Inventory ↔ Produksi:** Saat PO bahan baku masuk ke WMS, apakah otomatis ter-reserve untuk production order tertentu?

---

## 8. Rekomendasi Arsitektur (Draft)

Berdasarkan analisis, berikut pendekatan yang disarankan:

### Fokus Utama: Vendor CMT Management
Karena CV. DA adalah **koordinator** bukan **pabrik**, sistem produksi harus difokuskan pada:
- **Manajemen Purchase Order ke vendor CMT** (kirim, track, terima)
- **Progress monitoring per WO** (berapa yang sudah selesai dari vendor)
- **Penerimaan hasil** (incoming QC dari vendor)
- **Bukan** pada floor management internal (andon, line board real-time)

### Integrasi yang Harus Diperkuat
1. **Maklon Billing → Finance AR** (priority tertinggi)
2. **Work Order → Shipment** (otomatis draft shipment saat WO selesai)
3. **Material linkage** antara PO supplier → stok → reservasi untuk production order

### Simplifikasi yang Disarankan
- Hide/deprioritize modul yang hanya relevan untuk pabrik: Andon Board, Line Board real-time, Operator Skill Matrix (ganti dengan Vendor Performance tracking)
- Perkuat: CMT Vendor Management, BOM, HPP per order

---

*Dokumen ini adalah hasil analisis awal dan perlu divalidasi bersama stakeholder sebelum development plan final dibuat.*
