# DEVELOPMENT PLAN — Portal Produksi & Portal Maklon
## CV. Dewi Aditya ERP System
**Dibuat:** 22 Mei 2026  
**Status:** FINAL — Siap untuk Development  
**Dibuat oleh:** Analisis mendalam + diskusi dengan Owner CV. Dewi Aditya

---

## 📌 KONTEKS BISNIS (WAJIB DIPAHAMI SEBELUM CODING)

### Model Bisnis CV. Dewi Aditya
CV. Dewi Aditya **BUKAN pabrik garmen**. Mereka adalah **koordinator produksi** dengan dua model bisnis:

**Model A — Produksi Internal (Brand Sendiri):**
- CV. DA sebagai brand owner → produksi produk fashion sendiri
- Material (kain roll) dibeli dari supplier → masuk WMS CV. DA
- Proses: Cutting di CV. DA → kirim ke Vendor CMT eksternal → terima FG → jual di marketplace
- Revenue: Penjualan produk di Shopee/Tokopedia/TikTok Shop

**Model B — Maklon/CMT Service (untuk Klien Eksternal):**
- CV. DA sebagai jasa koordinator CMT untuk brand/PT lain
- Klien kirim bahan (kain sudah di-cutting) → CV. DA koordinasikan ke Vendor CMT → kirim barang jadi ke klien
- Material: Kain dari klien (sudah dipotong/cutting). Aksesoris bisa dari klien ATAU dari stok CV. DA (dihitung sebagai penjualan aksesoris)
- Revenue: CMT fee dari klien (tagihan jasa jahit + margin koordinasi)

### Vendor CMT Eksternal
- Pool vendor yang SAMA dipakai untuk Model A dan Model B
- Lebih dari 20 vendor aktif
- CV. DA tidak punya mesin jahit sendiri — semua proses jahit di vendor

### Modul yang TIDAK RELEVAN (akan di-hide/disable):
- Andon Board (untuk pabrik punya lini sendiri)
- Line Board Real-time (sama)
- Machine Downtime Log (mesin milik vendor CMT, bukan CV. DA)

---

## 🏗️ ARSITEKTUR DATA BARU

### A. IDENTIFIKASI ORDER

#### Maklon Order Identifier (BARU)
```
PO Level (dewi_maklon_pos):
  po_number:   MKL-{CLIENT_CODE}-{YYYY}-{NNNN}   ← identifier utama dari buyer
  client_id:   FK ke dewi_maklon_clients
  po_date:     tanggal PO masuk
  deadline:    target selesai keseluruhan
  status:      draft | confirmed | in_production | partial_delivered | completed | invoiced | cancelled
  
  items[]:  ← BARU (ganti dari dewi_maklon_orders yang lama)
    seri_no:    S01, S02, S03 ... ← identifier per item (bisa sama antar item beda artikel)
    artikel:    kode artikel produk dari buyer
    sku_code:   SKU lengkap
    color:      warna
    size:       ukuran
    qty:        quantity
    cmt_rate_per_pcs: harga jahit per pcs untuk item ini
    
  summary:
    total_qty:  sum(items[].qty)
    total_value: sum(items[].qty × cmt_rate_per_pcs)

Contoh Real:
  PO: MKL-CLT001-2026-0001 | Klien: Brand X | Deadline: 15 Jun 2026
  items:
    S01 | artikel: DRESS-001 | color: BLACK | size: S | qty: 100 | rate: Rp 25.000
    S01 | artikel: DRESS-001 | color: BLACK | size: M | qty: 150 | rate: Rp 25.000
    S02 | artikel: DRESS-001 | color: WHITE | size: S | qty: 80  | rate: Rp 25.000
    S03 | artikel: BLOUSE-002| color: RED   | size: M | qty: 200 | rate: Rp 22.000
```

> **CATATAN PENTING:** Seri No adalah identifier per item/baris dalam PO. Item berbeda BISA punya seri yang sama (misal S01 bisa ada di beberapa baris untuk artikel/warna/size berbeda). Seri bukan berarti 1 batch produksi terpisah.

#### Internal Production Order Identifier
```
Production Order (rahaza_orders — diperkuat):
  po_number:  PO-INT-{YYYY}-{NNNN}  ← standarisasi nomor
  type:       "internal"
  items[]:
    model_id, size_id, color, qty
    → setiap item di-generate 1 Work Order
```

### B. INVENTORY — STRUKTUR BARU (WAJIB DIIMPLEMENTASIKAN)

**Prinsip Utama:** Semua inventory HARUS punya flag kepemilikan dan kategori.

```
Field tambahan di rahaza_material_stock (extend existing):
  ownership:          "cv_da" | "maklon_client"
  maklon_client_id:   nullable String (FK ke dewi_maklon_clients)
  maklon_po_ref:      nullable String (PO Number rujukan)
  inventory_category: "rm_internal"    ← raw material untuk produksi CV. DA
                    | "rm_maklon"      ← bahan titipan dari klien maklon
                    | "acc_internal"   ← aksesoris stok CV. DA
                    | "acc_maklon"     ← aksesoris titipan klien maklon
                    | "wip_internal"   ← kain sudah di-cutting, belum dijahit
                    | "wip_maklon"     ← tidak dipakai (klien kirim sudah di-cutting)
                    | "fg_internal"    ← barang jadi produksi CV. DA (untuk dijual online)
                    | "fg_maklon"      ← barang jadi maklon (milik klien, hold di gudang CV. DA)
```

**Penyatuan FG Inventory (KRITIS):**  
Saat ini ada konflik antara `rahaza_fg_inventory` (diisi oleh dewi_cmt_packing) dan `rahaza_material_stock` (diisi oleh wms scan_in).  
**Solusi:** Unifikasi ke `rahaza_material_stock` sebagai single source of truth. `dewi_cmt_packing` harus diarahkan menulis ke `rahaza_material_stock` dengan category=fg_internal/fg_maklon.

### C. CUTTING — ALUR WIP (PRODUKSI INTERNAL)

```
Kain Roll (wh_fabric_rolls, ownership=cv_da)
  → Issue untuk Cutting:
    - wh_fabric_roll_movements: movement_type = "issue", ref = cutting_batch_id
    - Sisa kain di roll berkurang (remaining_m/remaining_kg)
    
dewi_cutting_batches (DIPERLUAS):
  + source_production_type: "internal" (maklon tidak pakai modul ini)
  + wo_id: FK ke rahaza_work_orders
  + production_order_id: FK ke rahaza_orders
  + material_consumption[]: [{roll_id, yard_used, kg_used, pcs_cut}]
  + do_number: nullable (jika langsung dibuatkan DO ke CMT)
  
  Status flow: pending → approved → in_cutting → cut_done → sent_to_cmt
  
  Saat status = cut_done:
    → Tambah WIP inventory: rahaza_material_stock
      category = "wip_internal", ownership = "cv_da"
      material_id = FK ke produk WIP (model+size)
      qty = total_pcs_cut
      location = "WIP_AREA"
      
  Saat status = sent_to_cmt (via CMT Job + DO):
    → WIP inventory berkurang (scan_out WIP)
    → dewi_cmt_jobs.wip_qty_sent bertambah
    → DO Number digenerate
```

**CATATAN:** Konversi kain roll:
- Input: yard atau kg (bisa dikonfigurasi per material di master data)
- Konversi: 1 roll (unit master) → yard/kg (UoM kerja)
- Ini dihandle di wh_fabric_rolls (field: uom = "meter"|"kg", + tambah "yard")

### D. VENDOR CMT PORTAL & PROGRESS TRACKING

#### Dua Mode Operasi:
```
MODE 1: Vendor Portal (vendor yang bisa pakai sistem)
  Route: /vendor-cmt (standalone app, mirip /creator dan /livehost)
  Auth: akun dengan role = "cmt_vendor", linked ke dewi_cmt_partners.id
  
  Fitur:
  - Lihat list job assignments mereka
  - Kanban board per job: proses (queued → cutting* → sewing → finishing → qc → done)
    *cutting hanya untuk job yang memang cutting di vendor (bukan internal)
  - Input progress harian:
    Pilih job → pilih proses → isi qty_done hari ini
  - Lihat DO/surat jalan yang diterima
  - Read-only: spesifikasi produk, deadline, instruksi
  
MODE 2: Admin Input (untuk vendor yang tidak pakai sistem)
  Menu di Portal Produksi → "Laporan Progress CMT"
  Admin pilih: vendor, job, tanggal, proses, qty
  Sama persis dengan input vendor portal tapi dilakukan oleh admin
```

#### Data Model Progress:
```
dewi_cmt_progress_reports (collection BARU):
  id
  cmt_job_id:         FK ke dewi_cmt_jobs
  cmt_partner_id:     FK ke dewi_cmt_partners
  report_date:        tanggal laporan
  process_step:       "cutting" | "sewing" | "finishing" | "qc"
  qty_processed:      qty yang sudah diproses
  qty_passed:         qty lulus QC (untuk step qc)
  qty_failed:         qty gagal/cacat
  reported_by:        user_id yang input
  is_vendor_self_report: boolean (true=vendor input sendiri, false=admin input)
  notes:              catatan
  created_at
  
  → Dari reports ini, bisa dihitung progress kumulatif per job
  → Bisa generate laporan harian dan bulanan
```

**Delivery Order (DO) untuk CMT:**
```
dewi_cmt_delivery_orders (collection BARU):
  id
  do_number:          DO-CMT-{YYYYMMDD}-{NNN}
  cmt_job_id:         FK
  production_order_id: FK (internal) atau maklon_po_id (maklon)
  source_type:        "internal" | "maklon"
  created_by:         admin produksi (bukan finance, bukan approval khusus)
  do_date
  items[]:
    material_type:   "wip" (cut pieces) | "rm_maklon" (kain dari klien)
    description:     deskripsi
    qty:             jumlah
    unit:            pcs/yard/kg
    inventory_ref:   material_id yang keluar dari inventory
  status:            "draft" | "issued" | "received_by_vendor" | "cancelled"
  notes
  
  Saat DO issued:
    → scan_out material dari rahaza_material_stock (WIP atau material maklon)
    → dewi_cmt_jobs.do_ids[] ditambahkan
```

### E. MULTI-DISPATCH MAKLON

```
dewi_maklon_dispatches (collection BARU):
  id
  dispatch_number:    DISP-{CLIENT_CODE}-{YYYYMMDD}-{NNN}
  po_id:              FK ke dewi_maklon_pos
  po_number:          denormalized
  client_id:          FK
  dispatch_date
  
  items[]:            ← BEBAS (tidak harus berurutan, tidak harus semua seri)
    seri_no:          nomor seri dari PO
    artikel:          denormalized dari PO
    color:            
    size:             
    qty_dispatched:   qty yang dikirim dalam dispatch ini
    
  do_number:          delivery order number untuk pengiriman ke klien
  driver_name:        
  vehicle_no:         
  notes:
  status:             "draft" | "packed" | "dispatched" | "received_by_client"
  
  Computed di level PO:
    po.qty_total         = sum(items[].qty) dari dewi_maklon_pos
    po.qty_dispatched    = sum(semua dispatch.items[].qty_dispatched untuk po ini)
    po.qty_remaining     = po.qty_total - po.qty_dispatched
    po.delivery_status   = "not_started" | "partial" | "complete"
    
  Saat dispatch status = "dispatched":
    → FG Maklon keluar dari inventory (scan_out fg_maklon)
    → Finance: trigger AR Invoice update (qty shipped)
```

### F. FINANCE INTEGRATION — MAKLON

```
FLOW FINANCE MAKLON (BARU):

1. Saat PO Confirmed:
   → Buat AR Invoice DRAFT di rahaza_ar_invoices
     Dr AR (piutang) / Cr Pendapatan Jasa Maklon
     Amount: total_value dari PO (bisa direvisi)
   → AR Invoice terhubung ke maklon_po_id
   
2. Saat Aksesoris CV. DA dipakai untuk maklon klien:
   → Buat line item tambahan di AR Invoice (penjualan aksesoris)
   → Kurangi stok aksesoris CV. DA (scan_out acc_internal)
   → Catat sebagai pendapatan aksesoris
   
3. Saat CMT Vendor dibayar:
   → Buat AP Invoice ke vendor CMT di rahaza_ap_invoices
     Dr Biaya CMT (expense) / Cr AP Vendor
   → Link ke cmt_job_id
   → post_ap_invoice ke Finance GL
   
4. Saat Dispatch ke klien:
   → Update AR Invoice: qty_shipped, konfirmasi actual qty
   → Jika partial delivery: AR Invoice bisa partial (sesuai qty terkirim)
   → Saat fully delivered: finalize AR Invoice, bisa di-issue ke klien
   
5. Saat Klien Bayar:
   → post_ar_payment → Dr Bank / Cr AR
   → Update maklon_po.payment_status

6. DP dari klien (jika ada):
   → Catat sebagai advance payment
   → Offset dari AR Invoice saat final
```

### G. RnD SEPARATION

```
dewi_rnd_styles (EXISTING — extend):
+ rnd_type: "internal_product" | "maklon_product"

Untuk rnd_type = "internal_product":
  - Buat oleh team RnD CV. DA
  - Approval: draft → pending_owner_review → approved_for_launch
  - Saat approved: bisa "promote" ke rahaza_models (production master)
    → auto-create rahaza_models entry + sync BOM dari sample ke rahaza_boms
  
Untuk rnd_type = "maklon_product":
  - Spesifikasi dari klien/buyer (bukan desain CV. DA)
  - Link ke client_id (dewi_maklon_clients)
  - Tidak perlu approval internal (sudah di-approve buyer)
  - BOM dari klien → bisa diinput sebagai referensi
  - Tidak di-promote ke rahaza_models (produk bukan milik CV. DA)
  
Saat generate WO untuk Maklon:
  - WO source = "maklon"
  - product_ref = dewi_rnd_styles.id (tipe maklon) ATAU free text product_name
  - BOM untuk maklon = estimasi total per PO (bukan per pcs seperti internal)
```

### H. BOM — DYNAMIC + VERSIONING

```
BOM untuk Produksi Internal (rahaza_boms — EXISTING):
  Tetap per model_id + size_id
  + version number (sudah ada)
  + bom_type: "rnd_sample" | "production" | "revised"
  + approved_by, approved_at
  Saat WO released: snapshot BOM aktif diambil

BOM untuk Maklon (dewi_maklon_bom — COLLECTION BARU):
  id
  po_id:              FK ke dewi_maklon_pos
  bom_type:           "estimated" | "actual"
  
  materials[]:
    material_name
    material_category: "fabric" | "accessories" | "packaging" | "other"
    ownership:         "client_provided" | "cv_da_stock"
    unit:             yard/kg/pcs/etc
    qty_estimated:    total untuk seluruh PO
    qty_actual:       diisi setelah produksi selesai
    qty_per_pcs:      auto-calculate: qty_total / po.total_qty
    material_id:      nullable (FK ke rahaza_materials jika dari stok CV. DA)
    
  Mekanisme:
  - Awal: klien/admin isi total bahan yang dibutuhkan (qty_estimated)
  - Auto-calculate qty_per_pcs = qty_estimated / total_qty_po
  - Akhir produksi: isi qty_actual (berapa yang benar-benar terpakai)
  - Report: selisih estimasi vs aktual, efisiensi bahan
  
  Catatan: BOM Maklon tidak trigger material reservation otomatis
  (karena bahan dari klien, bukan dari stok CV. DA kecuali aksesoris)
```

---

## 📋 DEVELOPMENT PHASES

### PHASE 1 — FONDASI DATA MODEL (KRITIS, harus selesai dulu)
**Tujuan:** Perbaiki struktur data sebelum build UI baru.

#### 1.1 Maklon PO + Seri — Restrukturisasi
- [ ] Buat collection `dewi_maklon_pos` (menggantikan fungsi `dewi_maklon_orders`)
- [ ] Field: po_number (auto-generate), po_date, deadline, client_id, status
- [ ] Field items[]: seri_no, artikel, sku_code, color, size, qty, cmt_rate_per_pcs
- [ ] Migration: data `dewi_maklon_orders` lama → `dewi_maklon_pos` baru (jika ada data)
- [ ] Update WO generator: saat PO confirmed → auto-generate WO per item/seri
- [ ] Backend endpoints: CRUD dewi_maklon_pos + items management

#### 1.2 Inventory Separation — Tambah Field Ownership
- [ ] Add migration: tambah field `ownership`, `maklon_client_id`, `inventory_category` ke `rahaza_material_stock`
- [ ] Default untuk data existing: `ownership = "cv_da"`, `inventory_category = "rm_internal"` atau sesuai type
- [ ] Update semua endpoint yang write ke `rahaza_material_stock` untuk mengisi field baru
- [ ] Unifikasi FG Inventory: arahkan `dewi_cmt_packing` tulis ke `rahaza_material_stock` (bukan `rahaza_fg_inventory`)
- [ ] Update wms_receiving scan_in untuk terima parameter ownership/category

#### 1.3 RnD Separation
- [ ] Tambah field `rnd_type: "internal_product" | "maklon_product"` ke `dewi_rnd_styles`
- [ ] Tambah field `client_id` (nullable) untuk maklon products
- [ ] Buat endpoint "promote to production model" (rnd_type=internal_product → rahaza_models + rahaza_boms)
- [ ] Frontend: pisahkan tampilan dan form RnD Internal vs Maklon

---

### PHASE 2 — PORTAL PRODUKSI INTERNAL (REVAMP)
**Tujuan:** Perbaiki alur dari PO → Cutting → CMT → FG → Shipment untuk produksi internal.

#### 2.1 Production Order Standardization
- [ ] Standarisasi nomor: PO-INT-{YYYY}-{NNNN}
- [ ] Pastikan setiap item di PO generate 1 WO dengan identifier jelas
- [ ] UI: Tampilkan mapping PO → WO yang jelas

#### 2.2 Cutting Flow → Inventory WIP
- [ ] Extend `dewi_cutting_batches`:
  - Tambah: `wo_id`, `production_order_id`, `source_production_type = "internal"`
  - Tambah: `material_consumption[]` (roll_id, yard_used, pcs_cut)
- [ ] Saat cutting_batch status = `cut_done`:
  - Trigger inventory movement: `wh_fabric_rolls.remaining_m -= yard_used`
  - Tambah WIP ke `rahaza_material_stock` (category=wip_internal)
- [ ] Backend: endpoint approve cutting + consume material

#### 2.3 CMT Delivery Order (DO)
- [ ] Buat collection `dewi_cmt_delivery_orders`
- [ ] Admin Produksi buat DO dari cutting batch (bukan Finance)
- [ ] DO Issue → scan_out WIP dari inventory
- [ ] Link DO ke CMT Job
- [ ] Frontend: halaman buat/lihat DO dalam alur CMT job

#### 2.4 CMT Progress Tracking
- [ ] Buat collection `dewi_cmt_progress_reports`
- [ ] Backend endpoints: create/list progress reports (admin input + vendor input)
- [ ] Hitung: cumulative_progress per job, % complete per proses
- [ ] Laporan Harian: filter by date, vendor, job
- [ ] Laporan Bulanan: agregasi per vendor per bulan

#### 2.5 FG Receive dari CMT (Fix Unifikasi)
- [ ] Arahkan `dewi_cmt_packing` approve → tulis ke `rahaza_material_stock` (bukan rahaza_fg_inventory)
  - Fields: ownership=cv_da, category=fg_internal, production_type=internal
  - Linked ke: wo_id, cutting_batch_id
- [ ] Pastikan scan_in di `wms_receiving` ter-sinkron dengan cmt_packing

#### 2.6 Shipment untuk Produksi Internal
- [ ] Shipment dispatch → scan_out dari `rahaza_material_stock` (fg_internal, ownership=cv_da)
- [ ] Validasi: qty yang di-dispatch tidak boleh melebihi available FG stock
- [ ] COGS posting otomatis ke Finance GL (sudah ada di post_cogs_shipment — pastikan berjalan)

---

### PHASE 3 — PORTAL MAKLON (REVAMP)
**Tujuan:** Rebuild alur maklon dengan PO+Seri, multi-dispatch, material klien, dan integrasi finance.

#### 3.1 Maklon PO CRUD + Seri Management
- [ ] Frontend: halaman buat PO Maklon baru
  - Input: client, po_date, deadline
  - Grid items: seri_no, artikel, sku, color, size, qty, cmt_rate
  - Auto-calculate total value
- [ ] Backend: `POST /api/dewi/maklon/pos` (create PO dengan items)
- [ ] Backend: `GET /api/dewi/maklon/pos` (list dengan summary qty, status)
- [ ] Backend: `GET /api/dewi/maklon/pos/{po_id}` (detail + items + dispatch history)
- [ ] Backend: `PUT /api/dewi/maklon/pos/{po_id}/items` (edit items sebelum confirmed)
- [ ] Backend: `POST /api/dewi/maklon/pos/{po_id}/confirm` (confirm → auto-generate WO per seri)
- [ ] Frontend: tampilan detail PO dengan progress tracker per seri

#### 3.2 WO Generation dari Maklon PO
- [ ] Saat PO confirmed: auto-generate WO untuk setiap item/seri
  - wo_number: MKLN-{PO_NO}-{SERI_NO}
  - source: "maklon"
  - linked_po_id, linked_seri_no, artikel, color, size
  - product_name_snapshot dari PO items
- [ ] WO bisa diassign ke CMT vendor (dewi_cmt_jobs)
- [ ] Progress tracking per WO → per seri → per PO

#### 3.3 Material Maklon — Receive dari Klien
- [ ] Frontend: form "Terima Material Maklon" (di halaman PO detail)
  - Input: jenis material, qty, unit, keterangan
  - Material masuk ke: `rahaza_material_stock` (ownership=maklon_client, category=rm_maklon/wip_maklon, maklon_client_id, maklon_po_ref)
- [ ] Tidak ada approval (admin produksi bisa langsung receive)
- [ ] Stock material klien terpisah dari stock CV. DA (filter by ownership di UI)

#### 3.4 Aksesoris dari Stok CV. DA untuk Maklon
- [ ] Saat konfirmasi PO: pilih item aksesoris dari stok CV. DA
- [ ] Line item tambahan di AR Invoice: "Aksesoris: [nama] × qty × harga"
- [ ] Saat dipakai: reserve dan issue dari `rahaza_material_stock` (ownership=cv_da, category=acc_internal)
- [ ] Finance: otomatis masuk ke AR Invoice sebagai additional charge ke klien

#### 3.5 BOM Maklon (Dynamic)
- [ ] Buat collection `dewi_maklon_bom`
- [ ] Frontend di halaman PO: tab "BOM"
  - Input estimasi: nama material, ownership (client/cv_da), total qty, unit
  - Auto-display: qty_per_pcs = total / po_qty
- [ ] Saat produksi selesai: isi actual usage
- [ ] Report: selisih estimasi vs aktual

#### 3.6 Multi-Dispatch Maklon
- [ ] Buat collection `dewi_maklon_dispatches`
- [ ] Backend: `POST /api/dewi/maklon/dispatches` (buat dispatch baru, pilih items bebas)
- [ ] Backend: `GET /api/dewi/maklon/pos/{po_id}/dispatches` (history dispatch per PO)
- [ ] Backend: `POST /api/dewi/maklon/dispatches/{id}/dispatch` (konfirmasi kirim)
- [ ] Frontend: halaman dispatch dengan:
  - Summary: total qty PO, sudah dikirim, sisa
  - Grid per seri: qty_to_dispatch (bisa partial)
  - Bebas pilih seri mana yang dikirim (tidak harus urut)
- [ ] Saat dispatch: FG Maklon keluar dari inventory (scan_out fg_maklon)

#### 3.7 DO untuk Klien Maklon
- [ ] Saat dispatch confirmed → auto-generate DO/surat jalan ke klien
  - Format: DISP-{CLIENT_CODE}-{DATE}-{NNN}
  - Isi: detail barang, qty, klien, alamat pengiriman
- [ ] DO bisa di-print/download PDF

---

### PHASE 4 — FINANCE INTEGRATION MAKLON
**Tujuan:** Tutup gap kritis: maklon billing harus masuk Finance GL.

#### 4.1 AR Invoice dari Maklon PO
- [ ] Saat PO confirmed → auto-buat AR Invoice draft di `rahaza_ar_invoices`
  - source_module: "maklon_po"
  - linked_maklon_po_id
  - lines: [{desc: "Jasa CMT - {artikel}", qty, rate, subtotal}]
  - status: draft (bisa direvisi sebelum issued)
- [ ] Backend: fungsi `post_maklon_ar_invoice(db, po, user)` → posting ke GL
  - Dr Piutang Usaha (AR) / Cr Pendapatan Jasa Maklon
- [ ] Frontend: tombol "Buat Invoice" di halaman detail PO Maklon
- [ ] Frontend: tampilkan status invoice di PO detail

#### 4.2 AR Invoice Update saat Dispatch
- [ ] Saat dispatch confirmed: update AR Invoice qty dengan actual qty shipped
- [ ] Jika partial delivery: invoice bisa partial billing atau hold sampai complete
- [ ] Saat fully delivered: AR Invoice bisa di-issue ke klien
- [ ] Frontend: status tracking invoice vs delivery progress

#### 4.3 AP Invoice CMT Vendor
- [ ] Saat dewi_cmt_payments approve:
  - Auto-buat AP Invoice ke vendor di `rahaza_ap_invoices`
  - Posting GL: Dr Biaya Jasa CMT / Cr Hutang Usaha (AP Vendor)
- [ ] Backend: fungsi `post_cmt_ap_invoice(db, payment, user)`
- [ ] Frontend: tombol "Post ke Finance" di CMT Payment

#### 4.4 DP dari Klien (Advance Payment)
- [ ] Field di maklon_pos: `advance_payment: float` (default 0)
- [ ] Form input DP saat PO confirmed atau setelahnya
- [ ] Finance: DP masuk sebagai Uang Muka (Dr Bank / Cr Uang Muka Pelanggan)
- [ ] Saat AR Invoice final: offset DP dari total tagihan

---

### PHASE 5 — VENDOR CMT PORTAL (STANDALONE)
**Tujuan:** Portal mandiri untuk vendor CMT yang bisa pakai sistem.

#### 5.1 Auth & Routing
- [ ] User role baru: `cmt_vendor`
- [ ] Link user ke `dewi_cmt_partners.id`
- [ ] Route: `/vendor-cmt` (standalone app, mirip `/creator`)
- [ ] Login page khusus vendor CMT

#### 5.2 Portal Fitur
- [ ] **Dashboard Vendor**: ringkasan jobs aktif, deadline, total qty
- [ ] **Job List**: list semua job yang diassign ke vendor ini
- [ ] **Kanban Progress Board**: per job, proses (queued → sewing → finishing → qc → done)
  - Kartu per job bisa di-drag atau klik untuk update
- [ ] **Input Progress Harian**: pilih job → pilih proses → qty done hari ini → simpan
- [ ] **Riwayat Laporan**: list laporan yang sudah disubmit
- [ ] **DO/Surat Jalan**: lihat DO yang dikirim ke mereka (read-only)

#### 5.3 Admin Fallback (jika vendor tidak pakai sistem)
- [ ] Menu di Portal Produksi Admin: "Input Progress Vendor CMT"
- [ ] Form: pilih vendor, pilih job, tanggal, proses, qty
- [ ] Interface sama dengan vendor input, tapi dilakukan oleh admin
- [ ] Label: "Diinput oleh Admin" (is_vendor_self_report = false)

---

### PHASE 6 — ONLINE ORDER PORTAL (BRIDGE MARKETING → INVENTORY)
**Tujuan:** Menjembatani order dari marketplace (Marketing) dengan inventory FG (Gudang).

#### 6.1 Order Fulfillment Queue
- [ ] Extend `dewi_toko_orders` dengan field:
  - `fulfillment_status`: "pending" | "picking" | "packed" | "dispatched" | "delivered"
  - `inventory_items[]`: [{material_id, qty_allocated, location_id}]
  - `shipment_ref`: nullable (referensi pengiriman)
- [ ] Backend: endpoint `POST /api/toko/orders/{id}/allocate-inventory`
  - Pilih FG items dari stok (ownership=cv_da, category=fg_internal)
  - Reserve qty di inventory

#### 6.2 Fulfillment Flow
- [ ] Admin Inventory lihat queue order yang perlu disiapkan
- [ ] Picking: scan/assign FG items ke order
- [ ] Packing: konfirmasi semua item sudah dikemas
- [ ] Dispatch: konfirmasi kirim
  - → scan_out FG dari `rahaza_material_stock` (qty berkurang)
  - → post_cogs_shipment ke Finance GL (Dr COGS / Cr FG Inventory)
  - → tracking number marketplace di-input

#### 6.3 Sinkronisasi Marketing
- [ ] Ketika order di Marketing Portal ditandai sebagai "processing"
  - → Otomatis masuk ke fulfillment queue
- [ ] Ketika fulfillment selesai (dispatched)
  - → Update status di Marketing Portal

---

### PHASE 7 — LAPORAN & DASHBOARD
**Tujuan:** Reporting lengkap untuk semua flow baru.

#### 7.1 Dashboard Produksi Internal
- [ ] Summary: PO aktif, WO in progress, FG stock, WIP di cutting, WIP di vendor CMT
- [ ] Progress per PO: qty total → di cutting → di CMT → FG → shipped
- [ ] Vendor CMT performance: delivery rate, ketepatan deadline, avg progress harian

#### 7.2 Dashboard Maklon
- [ ] Summary: Active POs, total value, dispatch rate, outstanding AR
- [ ] Per PO card: progress bar (qty total, sudah dikirim, sisa)
- [ ] Finance summary: AR outstanding, AP outstanding, margin per PO

#### 7.3 Laporan Produksi Harian
- [ ] Filter: tanggal, vendor CMT, jenis (internal/maklon)
- [ ] Tabel: job, proses, qty_processed, qty_passed, qty_failed, kumulatif
- [ ] Export ke Excel/PDF

#### 7.4 Laporan Produksi Bulanan
- [ ] Agregasi per vendor CMT per bulan
- [ ] Total qty processed, pass rate, pembayaran CMT
- [ ] Comparison actual vs target

---

## ⚠️ CONSTRAINT & RULES YANG TIDAK BOLEH DILANGGAR

```
1. JANGAN split file monster yang sudah ada (dewi_kpi.py, HRKPIModule.jsx, dll)
   → Boleh tambah file baru, tapi file lama JANGAN dipecah
   
2. JANGAN tambah 3rd-party API integration tanpa instruksi eksplisit
   → No Shopee/TikTok API, No WhatsApp, No Google Calendar

3. File upload: gunakan local storage (/app/uploads)
   → No S3, No external storage

4. AI/LLM: Tidak ada kebutuhan di scope ini
   → Kecuali ada instruksi eksplisit dari owner

5. Modul yang di-hide/disable (tidak dihapus, hanya hidden dari sidebar):
   → Andon Board
   → Line Board Real-time
   → Machine Downtime Log
   → Operator & Skill Matrix (diganti dengan Vendor Performance Tracking)

6. Bahasa: Selalu balas user dalam Bahasa Indonesia

7. Database: garment_erp (MongoDB)
   → Jangan ubah MONGO_URL

8. Testing: Wajib jalankan testing_agent_v3 setiap selesai Phase
```

---

## 🔑 KOLEKSI DATABASE — RINGKASAN PERUBAHAN

### Collections BARU yang perlu dibuat:
```
dewi_maklon_pos              ← Menggantikan logika dewi_maklon_orders (PO + items/seri)
dewi_cmt_progress_reports    ← Progress harian dari vendor CMT
dewi_cmt_delivery_orders     ← DO surat jalan ke vendor CMT
dewi_maklon_dispatches       ← Multi-dispatch per PO maklon ke klien
dewi_maklon_bom              ← BOM Maklon (estimasi + aktual)
```

### Collections EXISTING yang perlu dimodifikasi:
```
rahaza_material_stock        ← + ownership, maklon_client_id, inventory_category, production_type
dewi_maklon_orders           ← Legacy, data lama keep, tidak dihapus. Gantikan dengan dewi_maklon_pos untuk flow baru
dewi_cutting_batches         ← + wo_id, production_order_id, material_consumption[], do_number
dewi_cmt_jobs                ← + wip_qty_sent, do_ids[], vendor_portal_enabled
dewi_rnd_styles              ← + rnd_type, client_id (untuk maklon product)
rahaza_ar_invoices           ← + linked_maklon_po_id, source_module = "maklon_po"
rahaza_work_orders           ← + linked_po_id (maklon), linked_seri_no, artikel, sku_code, color
```

### Collections yang TIDAK perlu diubah (biarkan):
```
dewi_cmt_partners            ← cukup
dewi_cmt_deliveries          ← cukup
dewi_maklon_clients          ← cukup
rahaza_orders                ← cukup (internal PO)
rahaza_boms                  ← cukup (internal BOM)
```

---

## 🗺️ FILE REFERENCES (file-file yang akan terpengaruh)

### Backend:
```
BARU:
/app/backend/routes/dewi_maklon_pos.py          ← PO + Seri management
/app/backend/routes/dewi_cmt_portal.py          ← Vendor CMT portal endpoints
/app/backend/routes/dewi_cmt_progress.py        ← Progress reports
/app/backend/routes/dewi_maklon_dispatch.py     ← Multi-dispatch management
/app/backend/routes/dewi_maklon_bom.py          ← BOM Maklon

DIMODIFIKASI:
/app/backend/routes/dewi_maklon.py              ← Extend + link ke dewi_maklon_pos
/app/backend/routes/dewi_cutting.py             ← Tambah inventory movement
/app/backend/routes/dewi_cmt.py                 ← Tambah DO support
/app/backend/routes/dewi_cmt_packing.py         ← Redirect FG ke rahaza_material_stock
/app/backend/routes/rahaza_inventory.py         ← Tambah ownership/category filter
/app/backend/routes/dewi_maklon_billing.py      ← Connect ke Finance GL
/app/backend/routes/rahaza_posting.py           ← Tambah post_maklon_ar_invoice, post_cmt_ap_invoice
/app/backend/routes/dewi_rnd.py                 ← Tambah rnd_type + promote endpoint
/app/backend/server.py                          ← Register route baru
```

### Frontend:
```
BARU:
/app/frontend/src/components/vendor-cmt/VendorCMTPortalApp.jsx    ← Standalone portal
/app/frontend/src/components/erp/MaklonPOModule.jsx               ← PO + Seri CRUD
/app/frontend/src/components/erp/MaklonDispatchModule.jsx         ← Multi-dispatch
/app/frontend/src/components/erp/CMTProgressModule.jsx            ← Progress tracking + input admin
/app/frontend/src/components/erp/CMTDeliveryOrderModule.jsx       ← DO management
/app/frontend/src/components/erp/MaklonBOMModule.jsx              ← BOM Maklon
/app/frontend/src/components/erp/InventoryOwnershipFilter.jsx     ← Filter component by ownership

DIMODIFIKASI:
/app/frontend/src/components/erp/MaklonOrderModule.jsx            ← Update ke PO baru
/app/frontend/src/components/erp/CMTManagementModule.jsx          ← Tambah DO + progress
/app/frontend/src/components/erp/CuttingProcessModule.jsx         ← Tambah inventory movement
/app/frontend/src/components/erp/RnDModule.jsx                    ← Tambah rnd_type separation
/app/frontend/src/components/erp/MaklonBillingModule.jsx          ← Connect ke Finance
/app/frontend/src/components/erp/WMSModule.jsx                    ← Tambah ownership filter
/app/frontend/src/App.js                                           ← Route /vendor-cmt
```

---

## ✅ SUCCESS CRITERIA PER PHASE

| Phase | Success Criteria |
|-------|-----------------|
| Phase 1 | Data model updated, migration berhasil, semua existing data tetap intact |
| Phase 2 | Bisa trace produksi internal dari PO → Cutting → CMT DO → FG receive → Shipment + COGS posted |
| Phase 3 | Bisa buat Maklon PO dengan items/seri, confirm PO, receive material klien, multi-dispatch dengan history |
| Phase 4 | Maklon invoice muncul di Finance AR, payment tercatat di GL, CMT cost muncul di Finance AP |
| Phase 5 | Vendor CMT bisa login, lihat jobs, update progress. Admin bisa input untuk vendor yang tidak pakai sistem |
| Phase 6 | Order dari marketplace masuk fulfillment queue, dispatch kurangi FG stock, COGS posted |
| Phase 7 | Laporan harian + bulanan tersedia, dashboard menampilkan data real dari semua phase |

---

## 🚦 URUTAN PRIORITY DEVELOPMENT

```
MUST DO (P0):
  Phase 1 → Phase 3 → Phase 4  (data model + maklon flow + finance)

SHOULD DO (P1):
  Phase 2 (produksi internal revamp)
  Phase 5 (vendor portal)

CAN DO LATER (P2):
  Phase 6 (online order bridge)
  Phase 7 (reporting)
```

---

## 📝 CATATAN UNTUK AGENT SELANJUTNYA

1. **Baca dulu file ini LENGKAP** sebelum mulai coding apapun.
2. **Jangan ubah** `dewi_maklon_orders.py` yang lama — buat `dewi_maklon_pos.py` sebagai tambahan baru. Legacy data tetap ada.
3. **Inventory ownership** adalah perubahan paling fundamental — lakukan dengan hati-hati, jangan sampai break existing inventory queries.
4. **Finance integration** membutuhkan pemahaman `rahaza_posting.py` — baca dulu sebelum tambah fungsi baru.
5. **Gunakan pola yang sama** dengan portal lain yang sudah ada (/creator, /livehost) untuk Vendor CMT Portal.
6. **Wajib testing** menggunakan testing_agent_v3 setelah setiap phase selesai.
7. **Update PRD.md** setelah setiap phase completed.
8. Admin user untuk testing: `admin@garment.com / Admin@123`

---

*Dokumen ini adalah Development Plan FINAL yang siap dieksekusi.*  
*Dibuat berdasarkan: analisis kode aktual + diskusi mendalam dengan Owner CV. Dewi Aditya.*  
*Last Updated: 22 Mei 2026*
