# ANALISIS MENDALAM — PORTAL PRODUKSI & MAKLON
## CV. Dewi Aditya ERP
**Tanggal:** 22 Mei 2026  
**Metode:** Investigasi kode + API endpoint + koleksi database + alur bisnis

---

## PENTING: MEMAHAMI DUA KONSEP YANG SERING DICONFUSE

Sebelum membaca analisis ini, penting dipahami bahwa di sistem ini ada DUA istilah yang sering diconfuse:

**"Maklon"** = Klien eksternal yang MEMESAN ke CV. Dewi Aditya untuk dibuatkan produk  
→ CV. Dewi Aditya sebagai **PRODUSEN**, klien sebagai **PEMBERI ORDER**  
→ Contoh: Merk X minta Dewi Aditya jahitkan 500 baju  

**"CMT"** = Vendor jahit eksternal yang DIPEKERJAKAN oleh CV. Dewi Aditya untuk sub-kontrak  
→ CV. Dewi Aditya sebagai **PEMBERI KERJA**, vendor CMT sebagai **PENERIMA KERJA**  
→ Contoh: Dewi Aditya kirim kain potong ke konveksi Y untuk dijahit  

Kedua ini arah aliran yang **BERLAWANAN** tapi sering tercampur di portal yang sama.

---

## BAGIAN 1 — PETA LENGKAP PORTAL PRODUKSI

### 1A. OPERASIONAL HARIAN

| Menu Item | ID | Komponen | API Endpoint | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|-------------|------------|---------------------|
| Dashboard Produksi | `production-dashboard` | `ProductionDashboardModule` | `/api/rahaza/production-dashboard` | Aggregasi | Ringkasan KPI produksi: OEE, output, backlog, alert |
| Pengiriman (Surat Jalan) | `prod-shipments` | `RahazaShipmentsModule` | `/api/rahaza/shipments` | `rahaza_shipments` | Kirim FG ke customer dari sales order, buat surat jalan |
| Production Wizard | `prod-wizard` | `ProductionWizardModule` | `/api/rahaza/wizard/*` | Aggregasi | Quick-start guide: Buat order → WO → assign lini dalam 1 flow |
| Material Issue (Bulk) | `prod-bulk-mi` | `RahazaBulkMIModule` | `/api/rahaza/bulk-material-issues` | `rahaza_material_issues` | Keluarkan material ke produksi sekaligus untuk banyak WO |
| Order Produksi | `prod-orders` | `RahazaOrdersModule` | `/api/rahaza/orders` | `rahaza_orders` | CRUD sales/production orders (dokumen induk pesanan) |
| Work Order | `prod-work-orders` | `RahazaWorkOrdersModule` | `/api/rahaza/work-orders` | `rahaza_work_orders` | CRUD WO (pecahan dari order per ukuran/gaya, unit produksi terkecil) |
| Penelusuran Bundle | `prod-bundles` | `RahazaBundlesModule` | `/api/rahaza/bundles` | `rahaza_bundles` | Trace bundle (satuan kain potong) dari cutting sampai packing |
| Reservasi Material | `prod-material-reservation` | `RahazaMaterialReservationModule` | `/api/rahaza/material-reservation` | `rahaza_material_reservations` | Reservasi bahan baku untuk WO tertentu sebelum dikonsumsi |
| **Proses Cutting** | `prod-cutting` | `CuttingProcessModule` | `/api/dewi/cutting/*` | `dewi_cutting_requests` `dewi_cutting_batches` | Lifecycle cutting PLANNING: request → approve → buat batch cutting |
| Assign Lini Hari Ini | `prod-assignments` | `RahazaLineAssignmentsModule` | `/api/rahaza/line-assignments` | `rahaza_line_assignments` | Assign WO ke lini produksi untuk hari tertentu |
| Serah Terima Shift | `prod-shift-handover` | `RahazaShiftHandoverModule` | `/api/rahaza/shift-handovers` | `rahaza_shift_handovers` | Catatan serah terima antar shift: WIP, isu, target sisa |
| ~~Papan Rework~~ | `prod-rework-board` | ❌ TIDAK ADA | ❌ Tidak terdaftar | ❌ | **BROKEN** — modul tidak ada di registry |

### 1B. PROSES INTI (5 TAHAP)

| Menu Item | ID | Komponen | processCode | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|------------|------------|---------------------|
| 1 · Cutting | `prod-exec-cutting` | `ProcessExecutionModule` | `CUTTING` | `rahaza_process_execution` | **EKSEKUSI** cutting harian: input output qty per shift, scan QC |
| 2 · Jahit (CMT) | `prod-exec-sewing` | `ProcessExecutionModule` | `SEWING` | `rahaza_process_execution` | Eksekusi jahit internal harian: output per lini per shift |
| 3 · Finishing | `prod-exec-finishing` | `ProcessExecutionModule` | `FINISHING` | `rahaza_process_execution` | Eksekusi finishing: setrika, tag, quality check |
| 4 · QC Final | `prod-exec-qc` | `ProcessExecutionModule` | `QC` | `rahaza_process_execution` | QC gate final: pass/fail per bundle, catat reject |
| 5 · Packing | `prod-exec-packing` | `ProcessExecutionModule` | `PACKING` | `rahaza_process_execution` | Eksekusi packing internal: pack per size/bundle |
| Manajemen CMT | `prod-cmt` | `CMTManagementModule` | — | `dewi_cmt_partners` `dewi_cmt_jobs` `dewi_cmt_deliveries` `dewi_cmt_payments` | **Manajemen vendor CMT**: database kontraktor, assignment job, terima hasil jahit, bayar |
| Packing & Opname CMT | `prod-cmt-packing` | `CMTPackingModule` | — | `prod_cmt_receipts` | Terima hasil jahit dari CMT: input qty actual per line item (BEDA dari prod-exec-packing!) |
| Kekurangan Komponen | `production-cmt-component-requests` | `CMTComponentRequestModule` | — | `cmt_component_requests` | Vendor CMT request komponen tambahan (kancing, thread, dll) ke internal |
| Rework / Revisi | `prod-exec-rework` | `ProcessExecutionModule` | `REWORK` | `rahaza_process_execution` | Track proses rework: scan bundle reject, assign ke lini rework |

### 1C. MONITORING & ANALYTICS

| Menu Item | ID | Komponen | API Endpoint | Fungsi Sesungguhnya |
|-----------|-----|----------|-------------|---------------------|
| Papan Lini Real-time | `prod-line-board` | `LineBoardModule` | `/api/rahaza/line-board` | Live view output per lini hari ini, auto-refresh 30 detik |
| Papan Andon | `prod-andon-board` | `AndonBoardModule` | `/api/rahaza/andon-board` | Alert sistem Andon: line stop, helper request, QC issue |
| ~~Pengaturan Alert~~ | `prod-alert-settings` | ❌ TIDAK ADA | ❌ | **BROKEN** — modul tidak ada di registry |
| Pareto Cacat | `prod-pareto` | `RahazaParetoModule` | `/api/rahaza/pareto` | Analitik cacat produksi: Pareto chart per defect type |
| First Pass Yield (FPY) | `prod-fpy` | `RahazaFPYModule` | `/api/rahaza/fpy` | Metric FPY per lini: % output lolos QC tanpa rework |
| AQL Sampling Tool | `prod-aql-calculator` | `RahazaAQLCalculatorModule` | — | Kalkulator AQL sampling size untuk QC |
| Log Downtime Mesin | `prod-downtime` | `RahazaDowntimeModule` | `/api/rahaza/downtime-events` | Catat downtime mesin: mesin apa, berapa lama, alasan |
| Backlog & Forecast | `prod-backlog` | `RahazaBacklogModule` | `/api/rahaza/backlog` | Backlog WO yang belum selesai + AI forecast penyelesaian |
| AI Insights & Chatbot | `prod-ai-insights` | `RahazaAIModule` | `/api/rahaza/ai/*` | AI chatbot analitik produksi + ringkasan konteks produksi |
| AI Action Items | `ai-actions` | `AIActionsModule` | `/api/rahaza/ai/actions` | Recommended actions dari AI, cross-departemen |
| Predictive Maintenance | `prod-predictive-maintenance` | `PredictiveMaintenanceModule` | `/api/prod/predictive/*` | Prediksi kebutuhan maintenance mesin berbasis pola downtime |

---

## BAGIAN 2 — MASALAH PRODUKSI

### MASALAH #1 — DUA SISTEM CUTTING YANG TIDAK TERHUBUNG (KRITIS)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Sistem A: CuttingProcessModule (prod-cutting)                               │
│  ─────────────────────────────────────────────────────────────────────────── │
│  API:     /api/dewi/cutting/requests, /api/dewi/cutting/batches              │
│  DB:      dewi_cutting_requests, dewi_cutting_batches                        │
│  Fungsi:  PLANNING — buat request cutting, approve, buat batch               │
│  Data:    model, qty_requested, fabric_rolls, status: draft/approved/batched │
│                                                                              │
│  Sistem B: ProcessExecutionModule (prod-exec-cutting, processCode=CUTTING)  │
│  ─────────────────────────────────────────────────────────────────────────── │
│  API:     /api/rahaza/execution/process/CUTTING/board                       │
│  DB:      rahaza_process_execution                                           │
│  Fungsi:  TRACKING HARIAN — input output qty per shift per lini             │
│  Data:    process_code, line_id, qty_output, defects, date                  │
│                                                                              │
│  KONEKSI ANTARA KEDUANYA: ❌ TIDAK ADA                                       │
│  Batch dari Sistem A TIDAK otomatis masuk ke Sistem B                       │
│  Staff cutting harus input manual di kedua sistem                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Alur yang seharusnya:**
```
CuttingProcessModule → approve batch → OTOMATIS masuk queue di ProcessExecutionModule
                                       sebagai "planned output untuk hari ini"
```

**Akibat sistem tidak terhubung:**
- Supervisor harus buka 2 menu berbeda untuk 1 proses fisik yang sama
- Data di Sistem A dan B bisa tidak konsisten (quantity cutting)
- Tidak ada cara mudah tau: "dari 1000 pcs yang di-batch cutting, sudah berapa yang benar-benar dipotong hari ini?"

---

### MASALAH #2 — prod-cmt-packing vs prod-exec-packing: BEDA TAPI NAMA MEMBINGUNGKAN

| | `prod-exec-packing` | `prod-cmt-packing` |
|-|---------------------|---------------------|
| **Komponen** | `ProcessExecutionModule` (processCode=PACKING) | `CMTPackingModule` |
| **API** | `/api/rahaza/execution/process/PACKING/board` | `/api/prod/cmt-receipts` |
| **Koleksi** | `rahaza_process_execution` | `prod_cmt_receipts` |
| **Untuk apa** | Packing INTERNAL produksi (in-house) | Packing hasil jahit dari vendor CMT (receipt) |
| **Redundant?** | ✅ TIDAK — benar-benar beda | ✅ TIDAK — benar-benar beda |

**Masalah:** Nama "Packing" muncul di 2 tempat berbeda. User bingung mana yang dipakai.  
**Solusi:** Rename `prod-cmt-packing` → "Penerimaan Jahit CMT" (lebih akurat, langsung jelas ini tentang receipt dari CMT)

---

### MASALAH #3 — prod-ai-insights DAN hr-ai-insights: KOMPONEN YANG SAMA PERSIS

```javascript
// moduleRegistry.js baris 565-566:
'prod-ai-insights': RahazaAIModule,
'hr-ai-insights':   RahazaAIModule,  // ← IDENTIK, tidak ada props berbeda
```

Kedua modul memanggil endpoint yang SAMA `/api/rahaza/ai/*` dengan data yang SAMA. User produksi dan HR melihat konten AI yang identik. Ini adalah TRUE REDUNDANCY dalam hal tampilan, tapi secara fungsional belum ada filter berdasarkan departemen.

---

### MASALAH #4 — 5 TAHAP EKSEKUSI SEBAGAI 5 MENU TERPISAH

5 menu `prod-exec-cutting`, `prod-exec-sewing`, `prod-exec-finishing`, `prod-exec-qc`, `prod-exec-packing` semuanya menggunakan **komponen yang sama** (`ProcessExecutionModule`) dengan `processCode` berbeda. Ini adalah desain yang correct dari sisi kode, tapi dari sisi UX:

- Sidebar menjadi sangat panjang (5 item hanya untuk tahap eksekusi)
- User yang perlu lihat semua tahap harus buka 5 halaman berbeda
- Tidak ada view "lintas tahap" dalam 1 layar

**Alternatif lebih baik:** 1 menu "Eksekusi 5 Tahap" dengan tab navigasi internal (Cutting | Sewing | Finishing | QC | Packing)

---

## BAGIAN 3 — PETA LENGKAP PORTAL MAKLON

### 3A. KLIEN & ORDER

| Menu Item | ID | Komponen | API | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|-----|------------|---------------------|
| Dashboard Maklon | `maklon-dashboard` | `MaklonDashboardModule` | `/api/dewi/maklon/*` | Aggregasi | KPI maklon: total order, in-progress, revenue |
| Data Klien Maklon | `maklon-clients` | `MaklonClientsModule` | `/api/dewi/maklon/clients` | `dewi_maklon_clients` | Database klien yang pesan produksi ke Dewi Aditya |
| **PO Maklon (Baru)** | `maklon-po` | `MaklonPOModule` | `/api/dewi/maklon/pos` | `dewi_maklon_pos` `dewi_maklon_dispatches` | **SISTEM BARU**: PO dari klien, konfirmasi, dispatch material |
| **Order Maklon (Lama)** | `maklon-orders` | `MaklonOrderModule` | `/api/dewi/maklon/orders` | `dewi_maklon_orders` (+ creates `rahaza_work_orders`) | **SISTEM LAMA**: Order dari klien, generate WO internal |
| Sample Management | `maklon-samples` | `MaklonSamplesModule` | `/api/dewi/maklon/samples` | `dewi_maklon_samples` | Track sample request dari klien maklon |
| Tracking Produksi | `maklon-tracking` | `MaklonProductionTracking` | `/api/dewi/maklon/orders/{id}/stage-qty` | Derived dari `dewi_maklon_orders` | Input qty per tahap untuk order di **SISTEM LAMA** |

### 3B. OPERASIONAL MAKLON

| Menu Item | ID | Komponen | API | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|-----|------------|---------------------|
| ~~CMT Assignment~~ | `maklon-cmt` | ❌ TIDAK ADA | ❌ | ❌ | **BROKEN** |
| Progress & DO | `cmt-progress` | `CMTProgressModule` | `/api/dewi/cmt/progress` `/api/dewi/cmt/delivery-orders` | `dewi_cmt_progress` `dewi_cmt_delivery_orders` | Track progress job CMT + buat DO kirim ke vendor CMT (BUKAN untuk maklon klien!) |
| QC & Reject | `maklon-qc` | `MaklonQCModule` | `/api/dewi/maklon/qc` | `dewi_maklon_qc` | QC untuk hasil jahit maklon: pass/fail, persentase reject |
| ~~Packing & Pengiriman~~ | `maklon-packing` | ❌ TIDAK ADA | ❌ | ❌ | **BROKEN** |

---

## BAGIAN 4 — MASALAH MAKLON

### MASALAH #5 — DUA SISTEM ORDER MAKLON YANG BERBEDA KOLEKSI

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SISTEM LAMA: MaklonOrderModule (maklon-orders)                              │
│  ─────────────────────────────────────────────────────────────────────────── │
│  API:     /api/dewi/maklon/orders                                            │
│  DB:      dewi_maklon_orders                                                 │
│  + Otomatis membuat: rahaza_work_orders (WO internal)                        │
│  Tracking:  stage-qty (5 tahap manual input qty)                             │
│  Plus:    maklon-tracking terhubung ke sistem ini                            │
│                                                                              │
│  SISTEM BARU: MaklonPOModule (maklon-po)                                    │
│  ─────────────────────────────────────────────────────────────────────────── │
│  API:     /api/dewi/maklon/pos                                               │
│  DB:      dewi_maklon_pos + dewi_maklon_dispatches                           │
│  TIDAK membuat: rahaza_work_orders (tidak terintegrasi ke produksi internal) │
│  Tracking:  dispatch-based (kirim material, terima hasil)                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Masalah kritis:**
1. Data order maklon TERSEBAR di dua koleksi berbeda
2. Sistem baru (maklon-po) tidak membuat WO, jadi order maklon baru tidak masuk ke tracking produksi internal
3. Laporan maklon tidak bisa akurat (harus combine 2 sistem)
4. `maklon-tracking` hanya bekerja untuk sistem LAMA (data dari `dewi_maklon_orders`)

### MASALAH #6 — cmt-progress ADA DI PORTAL MAKLON TAPI BUKAN TENTANG MAKLON KLIEN

`cmt-progress` di bagian OPERASIONAL portal Maklon menggunakan:
- API: `/api/dewi/cmt/progress` — ini untuk **internal CMT vendor** (kontraktor jahit)
- Bukan untuk maklon clients (yang memesan ke Dewi Aditya)

Ini adalah kesalahan penempatan yang signifikan. User yang membuka portal Maklon (yang mengurus klien maklon) akan menemukan menu "Progress & DO" yang sebenarnya mengurus pengiriman ke vendor CMT internal, bukan untuk klien mereka.

### MASALAH #7 — maklon-tracking TIDAK RELEVAN JIKA PAKAI SISTEM BARU

`maklon-tracking` hanya baca dari `dewi_maklon_orders` (sistem lama). Jika user sudah pakai `maklon-po` (sistem baru), tracking produksi mereka tidak tersedia. Ini akan menjadi masalah setelah migrasi ke sistem baru selesai.

---

## BAGIAN 5 — DIAGRAM ALUR BISNIS PRODUKSI & MAKLON

### Alur Produksi Internal:

```
ORDER MASUK (prod-orders)
    ↓
BUAT WORK ORDERS (prod-work-orders) — pecah per ukuran/style
    ↓
RESERVASI MATERIAL (prod-material-reservation)
    ↓
ASSIGN KE LINI (prod-assignments)
    ↓
┌─────── SKENARIO A: In-house ──────┐   ┌─── SKENARIO B: Outsource CMT ───┐
│ CUTTING PLANNING (prod-cutting)   │   │ DO KE CMT (do-management        │
│     ↕ TIDAK TERHUBUNG             │   │          atau cmt-progress)      │
│ CUTTING EKSEKUSI (prod-exec-cuttg)│   │ TERIMA DARI CMT (prod-cmt)       │
│ JAHIT (prod-exec-sewing)          │   │                                  │
│ FINISHING (prod-exec-finishing)   │   └──────────────────────────────────┘
│ QC (prod-exec-qc)                 │              ↓ (masuk kembali ke bawah)
│ PACKING (prod-exec-packing)       │
└───────────────────────────────────┘
    ↓
PENGIRIMAN KE CUSTOMER (prod-shipments)
```

### Alur Maklon (External Client Orders):

```
KLIEN MINTA SAMPLE (maklon-samples)
    ↓
TERIMA ORDER MAKLON
    ├─ SISTEM LAMA: maklon-orders → auto-create rahaza_work_orders
    │       ↓
    │   TRACKING PRODUKSI (maklon-tracking) — input qty per tahap
    │       ↓
    └─ SISTEM BARU: maklon-po → tidak create WO (tracking manual)
    ↓
QC HASIL (maklon-qc)
    ↓
[PACKING — BROKEN, maklon-packing tidak ada di registry]
    ↓
INVOICE (maklon-billing)
```

---

## BAGIAN 6 — REKOMENDASI KONSOLIDASI

### Konsolidasi Portal Produksi

**OPERASIONAL HARIAN (dari 12 item → 7 item):**

| Sekarang | Konsolidasi | Catatan |
|----------|-------------|---------|
| Order Produksi + Work Order | → **Order & WO** (2 tab) | Hierarchy yang jelas |
| Reservasi Material + Material Issue Bulk + Assign Lini | → **Persiapan Produksi** (3 tab) | Semuanya langkah pre-production |
| Cutting (planning) + Eksekusi Cutting (5 tahap) | → **Eksekusi 5 Tahap** (tab: Cutting, Jahit, Finishing, QC, Packing) + link ke planning | Consolidate 5 exec + cutting planning |
| Serah Terima Shift | → Tetap (operasi harian kritis) | — |
| Papan Rework | → HAPUS (BROKEN, fungsinya di prod-exec-rework) | — |
| Production Wizard | → Tetap tapi pindah ke header quick-action | — |
| Pengiriman (Surat Jalan) | → Tetap | — |

**PROSES INTI (dari 9 item → 4 item):**

| Sekarang | Konsolidasi | Catatan |
|----------|-------------|---------|
| 5 × prod-exec-* | → **Eksekusi Produksi** (internal tab per tahap) | Sama component, beda processCode |
| prod-cmt, prod-cmt-packing, production-cmt-component-requests, prod-exec-rework | → **CMT & Sub-Proses** (tab: CMT Partners, Terima Jahit, Komponen, Rework) | Semuanya tentang CMT |

**MONITORING (dari 11 item → 5 item):**

| Sekarang | Konsolidasi |
|----------|-------------|
| prod-line-board + prod-andon-board + BROKEN alert-settings | → **Monitoring Real-time** (2 view) |
| prod-pareto + prod-fpy + prod-aql-calculator | → **Quality Analytics** (tab) |
| prod-downtime + prod-backlog + prod-predictive-maintenance | → **Performance & Prediksi** (tab) |
| prod-ai-insights + ai-actions | → **AI Insights** (tab: Insights, Actions) |

### Konsolidasi Portal Maklon

**KLIEN & ORDER (dari 6 item → 3 item):**

| Sekarang | Konsolidasi |
|----------|-------------|
| maklon-clients | → Tetap |
| maklon-po (baru) + maklon-orders (lama) | → **Satu sistem** (migrasi lama ke baru) |
| maklon-samples | → Tab di maklon-clients |
| maklon-tracking | → Tetap, tapi dihapus setelah migrasi |

**OPERASIONAL (dari 4 item → 2 item):**

| Sekarang | Konsolidasi |
|----------|-------------|
| maklon-cmt (BROKEN) | → HAPUS |
| cmt-progress | → **PINDAH ke Portal Produksi** (ini bukan tentang maklon clients) |
| maklon-qc | → Tetap |
| maklon-packing (BROKEN) | → HAPUS (atau buat modul baru) |

---

*Lanjut: Analisis Portal HR dan Marketing ada di dokumen terpisah*
