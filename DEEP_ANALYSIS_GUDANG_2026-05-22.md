# ANALISIS MENDALAM — PORTAL GUDANG (WAREHOUSE)
## CV. Dewi Aditya ERP
**Tanggal:** 22 Mei 2026  
**Metode:** Investigasi kode langsung (API endpoint + koleksi database + alur bisnis)

---

## PRINSIP ANALISIS

Saya menelusuri setiap modul sampai ke:
1. Endpoint API yang dipanggil (`fetch('/api/...')`)
2. Koleksi MongoDB yang digunakan (`db.xxx`)
3. Alur bisnis garment factory yang dilayani

---

## BAGIAN 1 — PETA LENGKAP PORTAL GUDANG

### 1A. INVENTORI

| Menu Item | ID | Komponen | API Endpoint | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|-------------|------------|---------------------|
| Master Material | `wh-materials` | `RahazaMaterialsModule` | `/api/rahaza/materials` | `rahaza_materials` | CRUD master semua tipe material (yarn, accessory, fg, packaging) |
| Stok & Pergerakan | `wh-stock` | `RahazaStockModule` | `/api/rahaza/material-stock` `/api/rahaza/material-movements` | `rahaza_material_stock` `rahaza_material_movements` | View stok semua tipe + adjustment + receive + transfer antar gudang |
| Material Issue | `wh-material-issue` | `RahazaMaterialIssueModule` | `/api/rahaza/material-issues` | `rahaza_material_issues` | Pengeluaran bahan ke lantai produksi, linked ke Work Order |
| **Master Aksesoris** | `wh-accessory-master` | `RahazaMaterialsModule` | `/api/rahaza/materials` | `rahaza_materials` | **SAMA PERSIS dengan Master Material — hanya filter type=accessory** |
| **Stok & Pergerakan (Aksesoris)** | `wh-accessory-stock` | `RahazaStockModule` | `/api/rahaza/material-stock` | `rahaza_material_stock` | **SAMA PERSIS dengan Stok & Pergerakan — TANPA filter tambahan (menampilkan semua tipe)** |
| Inventory & Pergerakan FG | `wh-fg` | `RahazaFGInventoryModule` | `/api/rahaza/materials?type=fg` `/api/rahaza/fg-movements` `/api/rahaza/fg-issues` | `rahaza_materials` `rahaza_fg_movements` `rahaza_fg_issues` | View FG inventory + issue FG keluar (sample, surat jalan internal) |
| Unified Inventory Viewer | `unified-inventory` | `UnifiedInventoryModule` | `/api/wms/stock/unified` | Aggregasi dari multiple collections | View terpadu semua inventori (bahan baku + aksesoris + FG) dalam satu tabel |

### 1B. OPERASIONAL GUDANG

| Menu Item | ID | Komponen | API Endpoint | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|-------------|------------|---------------------|
| Purchase Order (PO) | `wh-purchase-orders` | `PurchaseOrderModule` | `/api/rahaza/purchase-orders` | `rahaza_purchase_orders` | Buat & approve PO untuk bahan baku/material dari supplier |
| Penerimaan Barang (GRN) | `wh-receiving` | `ReceivingModule` | `/api/wms/legacy/receiving` | Legacy WMS collection | Terima barang dari supplier, catat GRN |
| Delivery Orders (DO/Surat Jalan) | `do-management` | `DOManagementModule` | `/api/dewi/cmt/delivery-orders` | `dewi_cmt_delivery_orders` | Buat DO: kirim kain potong dari gudang **ke vendor CMT** (outbound WIP) |
| Fulfillment (Order→FG Out) | `fulfillment` | `FulfillmentModule` | `/api/fulfillment/*` | `fulfillment_*` | Alokasi FG ke sales orders → dispatch pengiriman ke customer |
| Supplier Scorecard & AQL | `wh-supplier-scorecard` | `SupplierScorecardModule` | `/api/rahaza/grn-qc/supplier-scorecard` | Derived dari GRN data | Scorecard performa supplier berdasarkan data GRN + AQL sampling calculator |
| Put-Away | `wh-putaway` | `PutAwayModule` | `/api/wms/legacy/putaway` `/api/wms/legacy/locations` | Legacy WMS collections | Assign barang yang diterima ke lokasi/bin tertentu dalam gudang |
| Pick List | `wh-picklist` | `WMSPickListModule` | `/api/wms/picklist` | `wms_picklists` | Generate instruksi pengambilan barang untuk dipenuhi |
| **Stok Opname** | `wh-opname` | `OpnameModule` | `/api/wms/legacy/opname` `/api/wms/legacy/locations` | Legacy WMS collection | Hitung stok fisik dan cocokkan — **SISTEM LEGACY** |
| Lokasi / Bin | `wh-bin` | `LocationsModule` | `/api/wms/legacy/locations` | Legacy WMS location collection | CRUD master lokasi/rak/bin dalam gudang |
| **Transaksi Aksesoris** | `wh-accessory-ops` | `AccessoryModule` | `/api/acc/*` | `acc_items` `acc_stock_movements` `acc_internal_requests` `acc_opname` | Master aksesoris + stok + opname + pinjam + purchase request — **SISTEM AKSESORIS TERPISAH** |
| Inbox Request Aksesoris (RnD) | `warehouse-accessory-requests` | `AccessoryRequestInbox` | `/api/acc/internal-requests` | `acc_internal_requests` | Lihat dan approve request aksesoris yang dibuat oleh tim RnD |
| Return & Refund | `wh-returns` | `WHReturnsModule` | `/api/wh/returns` | `wh_returns` | Proses retur barang dari customer: terima → inspect → resolve |
| Alert, Reorder & Undo | `warehouse-smart` | `WarehouseSmartModule` | `/api/warehouse/alerts` `/api/warehouse/smart-reorder` | Derived data | Notifikasi stok rendah/rak penuh + rekomendasi reorder + undo transaksi |

### 1C. GARMENT WMS (ADVANCED)

| Menu Item | ID | Komponen | API Endpoint | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|-------------|------------|---------------------|
| WMS Scanner (Barcode) | `wms` | `WMSModule` | `/api/wms/buildings` `/api/wms/zones` `/api/wms/racks` `/api/wms/units` | `wms_buildings` `wms_zones` `wms_racks` | Setup struktur gudang (gedung→zona→rak→slot) + visual map rak + cetak barcode label |
| Fabric Roll Tracking | `wms-fabric-rolls` | `WMSFabricRollsModule` | `/api/wms/fabric-rolls` | `wms_fabric_rolls` | Track gulungan kain individual per barcode: QC, putaway, issue ke cutting |
| Surat Jalan (WMS) | `wms-delivery-notes` | `WMSDeliveryNotesModule` | `/api/wms/delivery-notes` | `wh_delivery_notes` | Buat & cetak PDF surat jalan outbound dari gudang ke **customer** |
| CMT Material Dispatch | `wms-cmt-dispatches` | `WMSCMTDispatchesModule` | `/api/wms/cmt-dispatches` | `wms_cmt_dispatches` | Dispatch material/fabric ke CMT vendor dengan AI smart recommendations |
| **Opname Enhanced (AI)** | `wms-opname-enhanced` | `WMSOpnameEnhancedModule` | `/api/wms/opname2/cycles` | `wms_opname2_cycles` | Cycle counting: opname berulang dengan variance analysis — **SISTEM BARU** |

---

## BAGIAN 2 — IDENTIFIKASI MASALAH MENDALAM

### MASALAH #1 — DUA SISTEM AKSESORIS YANG PARALEL (PALING KRITIS)

Ini adalah masalah terbesar di portal gudang. Ada **dua sistem yang benar-benar berbeda** untuk mengelola aksesoris:

**Sistem A** — Terintegrasi dalam `rahaza_materials`:
- Koleksi: `rahaza_materials` (dengan field `type: "accessory"`)
- Stok: `rahaza_material_stock`, `rahaza_material_movements`
- Diakses via: `wh-accessory-master` dan `wh-accessory-stock`
- Linked ke: Work Orders (material issue), Production flow

**Sistem B** — Sistem aksesoris tersendiri (`/api/acc/`):
- Koleksi: `acc_items`, `acc_stock_movements`, `acc_internal_requests`, `acc_opname`, `acc_loans`, `acc_purchase_requests`
- Diakses via: `wh-accessory-ops` (AccessoryModule)
- Linked ke: RnD requests, peminjaman internal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERTANYAAN FUNDAMENTAL: Aksesoris (kancing, resleting, label) ada di MANA? │
│                                                                               │
│ Jawaban sistem: Di DUA TEMPAT SEKALIGUS — dan data tidak sinkron!           │
│                                                                               │
│ Sistem A: rahaza_materials (type=accessory)                                  │
│   - Terintegrasi ke WO & production issue                                    │
│   - Stok di rahaza_material_stock                                             │
│                                                                               │
│ Sistem B: acc_items                                                           │
│   - Punya opname sendiri, peminjaman, purchase request                       │
│   - Stok di acc_stock_movements                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Dampak:**
- Staf gudang tidak tahu harus input di mana
- Aksesoris bisa double-entry di kedua sistem
- Laporan stok tidak bisa akurat (harus lihat dua tempat)
- Opname dilakukan dua kali (wh-opname untuk Sistem A, tab Opname di wh-accessory-ops untuk Sistem B)

**Akar masalah:** Sistem B (`/api/acc/`) dibuat kemudian sebagai sistem aksesoris mandiri, tapi Sistem A (rahaza_materials dengan type=accessory) sudah ada dan terintegrasi ke production flow. Keduanya tidak pernah digabungkan.

---

### MASALAH #2 — EMPAT ALIRAN "SURAT JALAN / DELIVERY" DENGAN NAMA MIRIP

Berikut pemetaan lengkap empat aliran pengiriman yang ada:

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ALIRAN A: Cutting → CMT Vendor (Outbound WIP ke vendor jahit)            │
│  ─────────────────────────────────────────────────────────────────────────│
│  DO Management (`do-management`)                                           │
│  API: /api/dewi/cmt/delivery-orders                                        │
│  DB: dewi_cmt_delivery_orders                                              │
│  JUGA: CMT Progress (`cmt-progress`) membuat DO dari endpoint yang sama!  │
│  → OVERLAP: 2 modul berbeda bisa buat delivery order ke CMT               │
│                                                                            │
│  ALIRAN B: CMT Vendor → Gudang (Inbound hasil jahit dari vendor)          │
│  ─────────────────────────────────────────────────────────────────────────│
│  CMT Management (`prod-cmt`) tab Deliveries                                │
│  API: /api/dewi/cmt/deliveries                                             │
│  DB: dewi_cmt_deliveries                                                   │
│                                                                            │
│  ALIRAN C: Gudang → Customer (Outbound produk jadi ke pembeli)            │
│  ─────────────────────────────────────────────────────────────────────────│
│  WMS Delivery Notes (`wms-delivery-notes`)                                 │
│  API: /api/wms/delivery-notes                                              │
│  DB: wh_delivery_notes                                                     │
│                                                                            │
│  ALIRAN D: Sales Order → Customer (Dari order penjualan ke pengiriman)    │
│  ─────────────────────────────────────────────────────────────────────────│
│  Pengiriman/Shipments (`prod-shipments`)                                   │
│  API: /api/rahaza/shipments                                                │
│  DB: rahaza_shipments                                                      │
└────────────────────────────────────────────────────────────────────────────┘
```

**Masalah nyata:**
- Aliran C dan D keduanya adalah "kirim ke customer" tapi pakai 2 sistem berbeda, 2 koleksi berbeda
- Aliran A dibuat dari 2 tempat berbeda (do-management dan cmt-progress)
- Semua diberi label "Surat Jalan" di UI → user bingung harus pakai yang mana

**Harusnya:**
- 1 sistem surat jalan, dengan tipe: `CMT_OUTBOUND | CMT_INBOUND | CUSTOMER_DELIVERY`
- Atau setidaknya UI yang sangat jelas membedakan fungsi masing-masing

---

### MASALAH #3 — TIGA SISTEM STOK OPNAME

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Sistem 1: OpnameModule (`wh-opname`)                                      │
│   API: /api/wms/legacy/opname                                             │
│   DB: Legacy WMS collection                                               │
│   Cakupan: Bahan baku (legacy, sistem lama)                               │
│   Status: LEGACY — masih berjalan tapi tidak dikembangkan                 │
│                                                                           │
│ Sistem 2: WMSOpnameEnhancedModule (`wms-opname-enhanced`)                │
│   API: /api/wms/opname2/cycles                                            │
│   DB: wms_opname2_cycles                                                  │
│   Cakupan: Advanced cycle counting untuk semua material                   │
│   Status: BARU — lebih lengkap, ada variance analysis                     │
│                                                                           │
│ Sistem 3: StokOpnameTab dalam AccessoryModule (`wh-accessory-ops`)        │
│   API: /api/acc/opname                                                    │
│   DB: acc_opname                                                          │
│   Cakupan: Aksesoris saja (Sistem B)                                      │
│   Status: Aktif, bagian dari sistem aksesoris terpisah                    │
└───────────────────────────────────────────────────────────────────────────┘
```

**Dampak:** Staf tidak tahu harus pakai opname yang mana. Hasilnya bisa tidak konsisten karena data di tiga koleksi berbeda.

---

### MASALAH #4 — MASTER DATA INVENTORI DI EMPAT MENU PADAHAL SUMBER DATA SAMA/MIRIP

```
Rahaza_materials (1 koleksi, field 'type' membedakan tipe):
├── wh-materials → tampil SEMUA tipe (yarn, accessory, fg, packaging)
│                  [Master Material di menu]
└── wh-accessory-master → tampil tipe=accessory SAJA
                          [Master Aksesoris di menu]

Rahaza_material_stock (1 koleksi):
├── wh-stock → tampil SEMUA (ada filter dropdown di dalam modul)
│             [Stok & Pergerakan - Bahan Baku di menu]
└── wh-accessory-stock → tampil SEMUA (TIDAK ADA filter tambahan!!)
                         [Stok & Pergerakan - Aksesoris di menu]
                         ← INI MENAMPILKAN PERSIS SAMA DENGAN wh-stock!

wh-fg → baca dari rahaza_materials (type=fg) + rahaza_fg_movements + rahaza_fg_issues
        [Inventory & Pergerakan FG di menu]

unified-inventory → aggregasi dari API berbeda (/api/wms/stock/unified)
                   [Unified Inventory Viewer di menu]
```

**Temuan kritikal:**
- `wh-stock` dan `wh-accessory-stock` menampilkan **data yang sama** (komponen RahazaStockModule yang sama, tidak ada props berbeda, tidak ada filter default)
- `wh-materials` sudah bisa filter ke aksesoris via dropdown di dalam modul → `wh-accessory-master` tidak memberikan nilai tambah apapun
- User yang membuka "Master Aksesoris" dan "Master Material" melihat data dari **tabel yang sama**

---

### MASALAH #5 — ALUR BISNIS PROCUREMENT YANG TERPUTUS

Alur ideal procurement di garment factory:
```
[Buat PO] → [Approve PO] → [Kirim ke supplier] → [Barang tiba] → [GRN] → [Put-Away ke bin]
```

Kenyataan di sistem saat ini:
```
[wh-purchase-orders: Buat & Approve PO]
         ↕ PUTUS DI SINI — tidak ada link otomatis
[wh-receiving: Buat GRN manual]
         ↕ PUTUS DI SINI — tidak ada link otomatis
[wh-putaway: Assign ke bin manual]
         ↕ PUTUS DI SINI — stok tidak otomatis naik
[wh-stock: Stok tetap manual di-adjust]
```

Bukti dari kode:
```javascript
// PurchaseOrderModule.jsx baris 274:
toast.info('Fitur Create GR dari PO akan tersedia setelah integrasi Warehouse selesai');
// ← Fitur PO→GRN BELUM TERHUBUNG, masih placeholder!
```

**Dampak:** Pengguna harus buka 3 modul berbeda dan input manual di setiap step. Error-prone dan membuang waktu.

---

### MASALAH #6 — WMS BARCODE (`wms`) DAN LOKASI/BIN (`wh-bin`) OVERLAP PARTIAL

```
wh-bin → LocationsModule → /api/wms/legacy/locations
         Fungsi: CRUD master lokasi/bin (LEGACY sistem)

wms → WMSModule → /api/wms/buildings, /api/wms/zones, /api/wms/racks
      Fungsi: Setup gedung→zona→rak (BARU, lebih lengkap)
```

Dua sistem manajemen lokasi yang berbeda, keduanya aktif. Sistem WMS baru lebih lengkap (gedung → zona → rak → slot + visual map + barcode label), tapi `wh-bin` masih menggunakan sistem legacy. Ketika staff membuat lokasi baru, harus pakai yang mana?

---

### MASALAH #7 — PICK LIST DAN MATERIAL ISSUE TIDAK TERHUBUNG

```
wh-picklist → generate daftar "ambil item X dari rak Y"
wh-material-issue → catat pengeluaran material ke produksi

Idealnya: material issue menghasilkan pick list → staff scanning ambil barang → konfirmasi → stok berkurang

Kenyataan: dua sistem terpisah tanpa link
```

---

## BAGIAN 3 — DIAGRAM BISNIS PROSES DAN MAPPING MODUL

### Alur 1: PENGADAAN BAHAN BAKU

```
Business Process:
─────────────────────────────────────────────────────────────────────────────
KEBUTUHAN PRODUKSI → BUAT PO → APPROVE → KIRIM KE SUPPLIER → BARANG TIBA 
→ TERIMA BARANG (GRN) → PUT AWAY → STOK NAIK → SIAP DIPAKAI

Mapping ke modul:
─────────────────────────────────────────────────────────────────────────────
[wh-purchase-orders]  →  belum link  →  [wh-receiving]  →  belum link  →  [wh-putaway]
           ↑                                                                       ↓
    manual input                                               [wh-stock] manual adjust

Status: FLOW TERPUTUS di 2 titik
```

### Alur 2: PENGGUNAAN BAHAN KE PRODUKSI

```
Business Process:
─────────────────────────────────────────────────────────────────────────────
ORDER PRODUKSI → BUAT WO → RESERVASI MATERIAL → AMBIL DARI GUDANG → CUTTING

Mapping ke modul:
─────────────────────────────────────────────────────────────────────────────
[prod-orders] → [prod-work-orders] → [prod-material-reservation] → [wh-material-issue]
                                                                          ↓
                                                          (stok berkurang di rahaza_material_stock)

Status: FLOW TERHUBUNG dengan baik, hanya [wh-picklist] belum terintegrasi
```

### Alur 3: PRODUKSI CMT (OUTSOURCE)

```
Business Process:
─────────────────────────────────────────────────────────────────────────────
CUTTING SELESAI → KIRIM KAIN POTONG KE VENDOR CMT → VENDOR JAHIT 
→ HASIL JAHIT KEMBALI → QC → PACKING

Mapping ke modul:
─────────────────────────────────────────────────────────────────────────────
[prod-cutting] → [do-management] / [cmt-progress] ← OVERLAP: 2 modul bisa buat DO!
                       ↓
              (dewi_cmt_delivery_orders)
                       ↓
        Vendor jahit...
                       ↓
              [prod-cmt] tab Deliveries  ← INBOUND dari vendor
              (dewi_cmt_deliveries)
                       ↓
              [maklon-qc] / [prod-exec-qc]

Status: FLOW ADA OVERLAP di pembuatan DO
```

### Alur 4: PENGIRIMAN KE CUSTOMER

```
Business Process:
─────────────────────────────────────────────────────────────────────────────
ORDER MASUK → ALOKASI STOK FG → PICK BARANG → PACK → BUAT SURAT JALAN → KIRIM

Mapping ke modul (BERMASALAH):
─────────────────────────────────────────────────────────────────────────────
[wh-fg] atau [unified-inventory]
       ↓ (tidak terhubung langsung)
[fulfillment] → alokasi + dispatch
       ↓ (tidak terhubung)
[wh-picklist] → generate pick list
       ↓ (tidak terhubung)
[wms-delivery-notes] → buat surat jalan PDF
       ATAU
[prod-shipments] → buat shipment dari sales order

Status: DUA SISTEM OUTBOUND PARALEL, tidak ada satu alur tunggal yang jelas
```

### Alur 5: STOK OPNAME

```
Business Process:
─────────────────────────────────────────────────────────────────────────────
JADWAL OPNAME → HITUNG FISIK → BANDINGKAN DENGAN SISTEM → BUAT SELISIH → ADJUST

Mapping ke modul (3 sistem!):
─────────────────────────────────────────────────────────────────────────────
Bahan Baku (legacy):     [wh-opname]              → /api/wms/legacy/opname
Bahan Baku (baru):       [wms-opname-enhanced]    → /api/wms/opname2/cycles
Aksesoris (sistem B):    Tab dalam [wh-accessory-ops] → /api/acc/opname

Status: TIGA SISTEM TIDAK SINKRON, opname tidak bisa dikerjakan dalam satu alur
```

---

## BAGIAN 4 — REKOMENDASI ARSITEKTUR IDEAL

### Konsolidasi Inventori (dari 7 item → 3 item)

**Sekarang (7 item, konfusing):**
- Master Material
- Stok & Pergerakan (Bahan Baku) ← sama data
- Master Aksesoris ← subset dari Master Material
- Stok & Pergerakan (Aksesoris) ← PERSIS SAMA dengan Stok Bahan Baku
- Inventory & Pergerakan FG
- Transaksi Aksesoris ← sistem berbeda!
- Unified Inventory Viewer

**Ideal (3 item, efisien):**
```
1. Master Inventori
   Tab: [Bahan Baku] [Aksesoris] [Barang Jadi] [Packaging]
   → Satu CRUD modul dengan filter tab
   → Satu koleksi (rahaza_materials) — sudah ada field 'type'!
   → Sistem B (acc_items) harus DIMIGRASI atau dijadikan fitur tambahan

2. Stok & Pergerakan
   Tab: [Semua] [Bahan Baku] [Aksesoris] [Barang Jadi]
   → Satu module dengan filter
   → Tidak perlu sub-menu terpisah per tipe

3. Stok Opname
   Tab: [Semua] [Cycle Counting (Enhanced)] [History]
   → Satu sistem (pilih yang enhanced, deprecated yang legacy)
   → Cakupan semua tipe material termasuk aksesoris
```

### Konsolidasi Operasional Gudang (dari 13 item → 8 item)

**Sekarang (13 item, banyak yang terputus):**
Purchase Order, Penerimaan, DO, Fulfillment, Supplier Scorecard, Put-Away, Pick List, Opname, Lokasi/Bin, Transaksi Aksesoris, Inbox Aksesoris, Return, Alert/Smart

**Ideal (8 item):**
```
1. Pengadaan (PO + GRN)
   Tab: [Purchase Order] [Penerimaan (GRN)] [Supplier Scorecard]
   → Terhubung: PO approved → bisa buat GRN dari PO tersebut

2. Pengeluaran & Fulfillment
   Tab: [Material Issue → Produksi] [Pick List] [Fulfillment ke Customer]

3. Surat Jalan / Delivery
   Tab: [Ke Vendor CMT] [Dari CMT] [Ke Customer]
   → SATUKAN 3 aliran dalam 1 modul, bedakan via tab/tipe

4. Stok Opname (sudah dibahas di atas)

5. Put-Away & Lokasi
   Gabung wh-putaway + wh-bin dengan migrasi ke sistem WMS baru (bukan legacy)

6. Return & Refund (tetap)

7. Alert, Reorder & Undo (tetap, pindah ke monitoring section)

8. Request Aksesoris (inbox dari RnD — tetap)
```

### Konsolidasi WMS Advanced (dari 5 item → 3 item)

**Sekarang (5 item):**
WMS Scanner, Fabric Roll Tracking, Surat Jalan, CMT Dispatch, Opname Enhanced

**Ideal (3 item + Opname dipindah ke Operasional):**
```
1. Setup Gudang & Barcode
   Tab: [Struktur Gudang] [Barcode Setup] [Unit & Konversi]

2. Fabric Roll Management
   (tetap, spesifik untuk garment)

3. CMT Material Dispatch
   (tetap, perlu integrasi dengan DO Management di atas)
```

---

## BAGIAN 5 — RINGKASAN TEMUAN GUDANG

### Masalah Sesungguhnya (berurutan dari yang terberat)

| Prioritas | Masalah | Dampak Bisnis |
|-----------|---------|----------------|
| 🔴 P0 | Dua sistem aksesoris paralel (rahaza_materials + acc_items) | Data tidak konsisten, laporan stok salah, user bingung input di mana |
| 🔴 P0 | wh-stock dan wh-accessory-stock menampilkan DATA YANG SAMA (bukan bug tapi UX sangat buruk) | User buka 2 menu berbeda tapi lihat isi yang sama |
| 🔴 P0 | Alur procurement terputus (PO → GRN → Putaway tidak terhubung) | User harus input manual 3 kali, error-prone |
| 🟠 P1 | Empat "Surat Jalan" dengan label mirip, aliran berbeda | Staff tidak tahu pakai yang mana untuk scenario yang mana |
| 🟠 P1 | DO Management dan CMT Progress sama-sama bisa buat delivery order ke CMT | Risiko double DO untuk satu cutting batch |
| 🟠 P1 | Tiga sistem opname yang tidak sinkron | Opname tidak pernah menghasilkan data yang benar-benar akurat |
| 🟡 P2 | wh-bin (legacy) vs wms (baru) untuk manajemen lokasi | Setup gudang baru tidak tahu pakai sistem mana |
| 🟡 P2 | Pick List dan Material Issue tidak terhubung | Tidak ada panduan fisik untuk staf gudang saat ambil barang |
| 🟢 P3 | wh-materials dan wh-accessory-master adalah menu terpisah tapi sumber data sama | Navigasi menu yang berlebihan tanpa nilai tambah |

---

*Dokumen ini merupakan bagian dari seri analisis portal CV. Dewi Aditya ERP*  
*Portal berikutnya: Produksi & Maklon, HR, Marketing*
