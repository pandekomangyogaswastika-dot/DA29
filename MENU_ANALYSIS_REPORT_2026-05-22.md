# LAPORAN ANALISIS MENU — CV. Dewi Aditya ERP
**Tanggal:** 22 Mei 2026  
**Analyst:** E2 Agent  
**Scope:** HR Portal, Marketing Portal, Inventory/Gudang Portal, Produksi & Maklon Portal  
**Status:** FINAL — Siap untuk Review & Keputusan

---

## BAGIAN 0 — STATUS VERIFIKASI GAP (GAP_ANALYSIS_REPORT.md)

Semua gap yang tercantum di `GAP_ANALYSIS_REPORT.md` sudah **TERVERIFIKASI SELESAI**:

| Gap | Status | Lokasi Implementasi |
|-----|--------|---------------------|
| Communication Hub — File Attachment | ✅ SELESAI | `CommunicationHubPortal.jsx:handleFileUpload` + `POST /api/comm/channels/{id}/upload` |
| Communication Hub — Message Edit/Delete | ✅ SELESAI | `handleEditMessage` + `handleDeleteMessage` + `DELETE /api/comm/messages/{id}` |
| Asset Management — Asset Transfer | ✅ SELESAI | `AssetManagementPortal.jsx:TransferDialog` + `POST /api/assets/{id}/transfer` |
| Asset Management — Photo Upload | ✅ SELESAI | `AssetManagementPortal.jsx:photoInputRef` + `POST /api/assets/{id}/upload-photo` |
| Workspace Portal | ✅ SELESAI | `WorkspacePortal.jsx` (1364 baris) — spreadsheet editor penuh |
| Marketing Seed Data | ⚠️ SEBAGIAN | Hanya accounts (3 akun demo), selebihnya BELUM: KOL, LiveHost, Orders, Content Calendar, dll |

---

## BAGIAN 1 — TEMUAN KRITIS: MODUL BROKEN

> **Definisi:** Modul yang ada di sidebar navigation tapi **TIDAK terdaftar** di `moduleRegistry.js`.  
> **Dampak:** Klik menu → tampil ManagementDashboard (fallback), bukan modul yang dimaksud.  
> **Cara Verifikasi:** `MODULE_REGISTRY[currentModule] || DEFAULT_MODULE` → fallback ke ManagementDashboard

### 🔴 P0 — BROKEN (Klik = Blank/Default Dashboard)

| No | Portal | Menu | Module ID | Status |
|----|--------|------|-----------|--------|
| 1 | **Maklon** | OPERASIONAL > CMT Assignment | `maklon-cmt` | ❌ Tidak di registry |
| 2 | **Maklon** | OPERASIONAL > Packing & Pengiriman | `maklon-packing` | ❌ Tidak di registry |
| 3 | **Produksi** | OPERASIONAL HARIAN > 🏭 Eksekusi > Papan Rework | `prod-rework-board` | ❌ Tidak di registry |
| 4 | **Produksi** | MONITORING > Real-time > Pengaturan Alert | `prod-alert-settings` | ❌ Tidak di registry |

**Rekomendasi:** 
- `maklon-cmt` & `maklon-packing` → Hapus dari sidebar (fungsi sudah digantikan oleh `maklon-po` + `cmt-progress`)
- `prod-rework-board` → Hapus dari OPERASIONAL HARIAN, karena `prod-rework-analytics` sudah ada sebagai redirect ke Production Dashboard > tab quality
- `prod-alert-settings` → Hapus dari sidebar (tidak ada modul untuk ini, atau perlu dibuat)

---

## BAGIAN 2 — ANALISIS PORTAL HR (SDM)

### Struktur Menu Saat Ini

```
SDM / HRIS
├── KARYAWAN & ORGANISASI
│   ├── Dashboard SDM                    [hr-dashboard]
│   ├── Data Karyawan & Kontrak          [hr-employees]
│   ├── Struktur Organisasi              [hr-org-chart]
│   ├── Aset Karyawan                    [hr-assets]
│   └── HR Admin & Seed (BARU)          [hr-admin]
│
├── REKRUTMEN & TALENT
│   ├── 📋 Proses Rekrutmen [header]
│   │   ├── Job Posting & ATS            [hr-recruitment]
│   │   └── AI Resume Screening (AI)     [hr-resume-screening]
│   ├── 👋 Onboarding [header]
│   │   └── Onboarding Checklist         [hr-onboarding]
│   └── 💼 Career Development [header]
│       └── Internal Job Board (BARU)    [hr-job-board]
│
├── KEHADIRAN & SHIFT
│   ├── ⏰ Absensi & Clock In/Out [header]
│   │   ├── Absensi Harian (Manual)      [hr-attendance]
│   │   ├── Absen Otomatis (BARU)        [hr-auto-attendance]
│   │   └── Approval Absen (BARU)        [hr-attendance-approval]
│   ├── 📅 Shift & Jadwal Kerja [header]
│   │   └── Auto Shift Scheduler (BARU)  [hr-shift-scheduler]
│   ├── 🌙 Lembur & Overtime [header]
│   │   └── Request Lembur (BARU)        [hr-overtime]
│   └── 🏖️ Cuti & Izin [header]
│       ├── Izin & Cuti                  [hr-leave]
│       └── Saldo Cuti (BARU)            [hr-leave-balances]
│
├── KINERJA & PENGEMBANGAN
│   ├── 🎯 KPI & Goal Setting [header]
│   │   └── KPI Bulanan (Operasional)    [hr-kpi]
│   ├── 📊 Performance Review [header]
│   │   ├── Annual Review (Tahunan)      [hr-performance]
│   │   └── 360° Feedback (BARU)         [hr-360-feedback]
│   └── 📚 Learning & Development [header]
│       └── Learning Management          [hr-lms]
│
├── PENGGAJIAN
│   ├── Profil Gaji Karyawan             [hr-payroll-profiles]
│   ├── Tunjangan Tetap                  [hr-payroll-allowances]
│   ├── Kenaikan Gaji (Approval) (BARU)  [hr-salary-adjustments]
│   └── Penggajian & Slip                [hr-payroll-run]
│
└── AI-POWERED HR & LAPORAN
    ├── 📊 AI Insights & Analytics [header]
    │   ├── HR Dashboard dengan AI       [hr-ai-insights]
    │   ├── Predictive Attrition (AI)    [hr-attrition]
    │   └── Skill Gap Analysis (BARU)    [hr-skill-gap]
    ├── 🤖 AI Tools [header]
    │   └── Performance Coaching AI (AI) [hr-coaching]
    ├── ⚡ Action Items [header]
    │   └── Automated Recommendations    [ai-actions]   ← SHARED dengan Production
    └── Laporan & Analitik SDM           [hr-reports]
```

### Temuan HR Portal

| No | Temuan | Kategori | Detail |
|----|--------|----------|--------|
| 1 | `ai-actions` muncul di HR **dan** Production | ⚠️ Shared Module | Module ID sama `AIActionsModule`. Menampilkan semua action items lintas departemen, bukan filter per-konteks. Bisa membingungkan HR: "ini action production apa HR?" |
| 2 | Sub-section header terlalu dalam | ⚠️ UX | Section KEHADIRAN punya 4 sub-header (⏰ 📅 🌙 🏖️), membuat sidebar sangat panjang. User harus scroll jauh. |
| 3 | `hr-admin` badge "BARU" di KARYAWAN & ORGANISASI | ⚠️ Placement | HR Admin & Seed sebaiknya di bagian SISTEM/PENGATURAN, bukan di data karyawan |
| 4 | `hr-assets` (Aset Karyawan) vs Portal Aset | ✅ BEDA | hr-assets = aset yang DIPINJAM karyawan (laptop, HP). Asset Portal = aset perusahaan (mesin, kendaraan). BERBEDA, tidak redundant. |
| 5 | `hr-kpi` vs `kpi-portal` di Portal Saya | ✅ BEDA | hr-kpi = admin manage KPI semua karyawan. kpi-portal = self-service view KPI sendiri. BERBEDA, tidak redundant. |
| 6 | `hr-lms` tunggal tanpa quiz/certificate di sidebar | ⚠️ Missing Sub-menu | LMS punya fitur Quiz & Certificate tapi tidak ada shortcut ke sana |

**Rekomendasi HR:**
- Collapse sub-header section KEHADIRAN menjadi accordion atau kurangi header level
- Pindahkan `hr-admin` ke section SISTEM atau beri label yang lebih jelas
- `ai-actions` di HR: tambahkan filter konteks = 'hr' agar action yang ditampilkan relevan

---

## BAGIAN 3 — ANALISIS PORTAL MARKETING

### Struktur Menu Saat Ini

```
Marketing
├── OPERASIONAL PENJUALAN
│   ├── 📊 Overview
│   │   └── Marketing Overview           [marketing-overview]
│   │
│   ├── 💼 Multi-Channel Sales
│   │   ├── Manage Accounts              [marketing-accounts]
│   │   ├── Input Sales Harian           [marketing-sales]
│   │   ├── Universal Smart Import       [marketing-import]
│   │   ├── Unified Orders               [marketing-orders]
│   │   └── Kelola Komplain              [marketing-complaints]
│   │
│   ├── 🏪 Marketplace & Katalog
│   │   ├── Manajemen Katalog            [marketing-catalog]
│   │   ├── Channel Manager (Lama)       [toko-channels]   ← LEGACY
│   │   └── Harga & Flashsale (Lama)     [toko-pricing]    ← LEGACY
│   │
│   ├── ⭐ KOL & Creator
│   │   ├── KOL & Creator Mgmt           [marketing-kol]
│   │   ├── Kreator Requests (BARU)      [marketing-kreator-requests]
│   │   └── LiveHost Management (BARU)   [marketing-livehost]  ← ❓ MISPLACEMENT
│   │
│   └── 📅 Konten & Kampanye
│       ├── Content Calendar             [marketing-content-calendar]
│       ├── Discount Campaign            [marketing-discounts]
│       └── Product Launch Manager       [marketing-product-launches]
│
├── ANALYTICS & AI
│   ├── 📊 Performa
│   │   ├── Account Health               [marketing-health]
│   │   ├── Sales Performance            [marketing-performance]
│   │   ├── Ads Performance              [marketing-ads]
│   │   └── Live Sessions                [marketing-live]   ← ❓ MISPLACEMENT
│   │
│   ├── 📋 Laporan PIC
│   │   ├── Laporan Harian (BARU)        [marketing-daily-report]
│   │   ├── Laporan Bulanan (BARU)       [marketing-monthly-report]
│   │   └── Target Bulanan (BARU)        [marketing-targets]
│   │
│   └── 🤖 AI Tools
│       ├── AI Marketing Insights        [marketing-ai-insights]
│       ├── Advanced AI Features         [marketing-advanced-ai]
│       ├── AI Content Generator (AI)    [marketing-ai-content]
│       ├── AI Image Generator (AI)      [marketing-ai-image]
│       ├── KOL Leaderboard              [marketing-kol-leaderboard]  ← ❓ MISPLACEMENT
│       └── Scheduler & Otomasi          [marketing-scheduler]        ← ❓ MISPLACEMENT
│
├── TASK MANAGEMENT
│   ├── Kanban Board                     [marketing-tasks]
│   ├── Approval Inbox                   [marketing-approvals]
│   └── Task Templates                   [marketing-templates]
│
├── AFTER SALES & SUPPORT
│   ├── Rating & Review Management       [marketing-reviews]
│   ├── Returns & Refunds Tracking       [marketing-returns]
│   └── Database Pengiriman Sample       [marketing-samples]
│
└── PENGATURAN
    ├── API Integration Settings         [marketing-integration-settings]
    └── Notifikasi & Provider            [maklon-notifications]  ← ❓ MODULE SILANG
```

### Temuan Marketing Portal

| No | Temuan | Kategori | Detail |
|----|--------|----------|--------|
| 1 | `toko-channels` & `toko-pricing` berlabel "(Lama)" | ⚠️ Legacy | Kedua modul ini legacy. Fungsi `toko-channels` sebaiknya sudah tergantikan oleh `marketing-accounts` (AccountManagementModule). `toko-pricing` sebagian digantikan `marketing-discounts`. Perlu dikonfirmasi apakah ada data/fungsi unik. |
| 2 | `marketing-live` (Live Sessions Analytics) di grup 📊 Performa | ⚠️ Misplacement | Live Sessions adalah analytics siaran. Lebih tepat di ⭐ KOL & Creator atau 📅 Konten section karena terkait konten live. |
| 3 | `marketing-livehost` (LiveHost Management = HR SDM host) di ⭐ KOL & Creator | ⚠️ Misplacement | LiveHostModule mengelola SDM host (shift, absensi, gaji host), BUKAN analytics KOL. Seharusnya di section sendiri "👥 Manajemen Tim Live" atau di OPERASIONAL PENJUALAN. |
| 4 | `marketing-kol-leaderboard` di 🤖 AI Tools | ⚠️ Misplacement | KOL Leaderboard adalah ranking KOL, bukan AI tool. Sebaiknya di ⭐ KOL & Creator section. |
| 5 | `marketing-scheduler` di 🤖 AI Tools | ⚠️ Misplacement | Scheduler & Otomasi adalah scheduling tool, bukan AI. Sebaiknya di 📅 Konten & Kampanye section. |
| 6 | 4 item AI berurutan di 🤖 AI Tools | ⚠️ Terlalu padat | `marketing-ai-insights`, `marketing-advanced-ai`, `marketing-ai-content`, `marketing-ai-image` — semua BERBEDA dan valid, tapi padat. Bisa dijadikan 1 modul bertab "AI Suite". |
| 7 | `maklon-notifications` di Marketing PENGATURAN | ⚠️ Module Silang | `maklon-notifications` adalah module Maklon, bukan Marketing. Di Marketing muncul karena dipinjam untuk notif setting. Seharusnya punya module sendiri `marketing-notifications`. |
| 8 | `marketing-live` vs `marketing-livehost` | ✅ BERBEDA | LiveSessionModule = analytics performa siaran (GMV, viewers, dll). LiveHostModule = manajemen SDM host (shift, absensi, pembayaran). TIDAK redundant tapi penempatan section salah. |
| 9 | `marketing-returns` vs `wh-returns` | ✅ BERBEDA | marketing-returns = tracking retur dari sisi order pelanggan. wh-returns = penerimaan fisik barang retur ke gudang. BEDA workflow, tidak redundant. |

**Rekomendasi Marketing:**
1. Pindahkan `marketing-livehost` → Section baru "👥 Tim Live" atau gabung ke OPERASIONAL PENJUALAN
2. Pindahkan `marketing-kol-leaderboard` → ⭐ KOL & Creator section
3. Pindahkan `marketing-scheduler` → 📅 Konten & Kampanye section  
4. Pindahkan `marketing-live` → ⭐ KOL & Creator section atau 📅 Konten
5. `toko-channels` (Lama) → **Konfirmasi dulu** apakah masih dipakai, jika tidak hapus
6. `toko-pricing` (Lama) → **Konfirmasi dulu** apakah masih dipakai, jika tidak hapus
7. Ganti `maklon-notifications` di Marketing PENGATURAN dengan module Marketing sendiri

---

## BAGIAN 4 — ANALISIS PORTAL INVENTORY/GUDANG

### Struktur Menu Saat Ini

```
Gudang
├── INVENTORI
│   ├── Dashboard Gudang                 [warehouse-dashboard]
│   ├── 📦 Bahan Baku & Material [header]
│   │   ├── Master Material              [wh-materials]
│   │   ├── Stok & Pergerakan            [wh-stock]
│   │   └── Material Issue               [wh-material-issue]
│   ├── ✨ Aksesoris & Finishing [header]
│   │   ├── Master Aksesoris             [wh-accessory-master]
│   │   └── Stok & Pergerakan            [wh-accessory-stock]
│   ├── 👕 Produk Jadi (FG) [header]
│   │   └── Inventory & Pergerakan FG    [wh-fg]
│   └── Unified Inventory Viewer (BARU)  [unified-inventory]
│
├── OPERASIONAL GUDANG
│   ├── Purchase Order (PO)              [wh-purchase-orders]
│   ├── Penerimaan Barang (GRN)          [wh-receiving]
│   ├── Delivery Orders (DO/Surat Jalan) [do-management]       ← Perhatian (lihat no. 3)
│   ├── Fulfillment (Order → FG Out)     [fulfillment]
│   ├── Supplier Scorecard & AQL         [wh-supplier-scorecard]
│   ├── Put-Away                         [wh-putaway]
│   ├── Pick List (BARU)                 [wh-picklist]
│   ├── Stok Opname                      [wh-opname]
│   ├── Lokasi / Bin                     [wh-bin]
│   ├── Transaksi Aksesoris              [wh-accessory-ops]
│   ├── Inbox Request Aksesoris (BARU)   [warehouse-accessory-requests]
│   ├── Return & Refund (BARU)           [wh-returns]
│   └── Alert, Reorder & Undo (BARU)     [warehouse-smart]
│
└── GARMENT WMS (ADVANCED)
    ├── WMS Scanner (Barcode) (BARU)     [wms]
    ├── Fabric Roll Tracking [P0]        [wms-fabric-rolls]
    ├── Surat Jalan [P0]                 [wms-delivery-notes]  ← Perhatian (lihat no. 3)
    ├── CMT Material Dispatch [P1]       [wms-cmt-dispatches]
    └── Opname Enhanced (AI) [P1]        [wms-opname-enhanced]
```

### Temuan Gudang/Inventory Portal

| No | Temuan | Kategori | Detail |
|----|--------|----------|--------|
| 1 | `wh-stock` vs `unified-inventory` | ✅ BERBEDA | wh-stock = Stok & pergerakan BAHAN BAKU saja. unified-inventory = View terpadu semua kategori (bahan baku + aksesoris + FG + WIP). BERBEDA scope, tidak redundant. |
| 2 | `wh-opname` vs `wms-opname-enhanced` | ✅ BERBEDA LEVEL | wh-opname = Basic opname sederhana. wms-opname-enhanced = Advanced cycle counting dengan variance analysis & AI. TIERING yang disengaja, tidak redundant. |
| 3 | `do-management` vs `wms-delivery-notes` | ⚠️ OVERLAPPING tapi berbeda | DOManagementModule = DO dari Production ke CMT vendor (WIP transfer). WMSDeliveryNotesModule = Surat Jalan PDF untuk outbound WH ke customer. BERBEDA TUJUAN. Tapi labeling "Surat Jalan" di keduanya membingungkan. Perlu rename yang lebih jelas. |
| 4 | `do-management` (Gudang) vs `prod-shipments` (Produksi) | ✅ BERBEDA | do-management = Transfer WIP ke CMT. prod-shipments = Pengiriman produk jadi ke pelanggan. BERBEDA tapi NAMA "Surat Jalan" di `prod-shipments` sidebar vs "Delivery Orders" di `do-management` membingungkan. |
| 5 | `wh-material-issue` (Single) di Inventori vs `prod-bulk-mi` (Bulk) di Produksi | ✅ BERBEDA | wh-material-issue = Pengeluaran material satu-satu. prod-bulk-mi = Pengeluaran material massal per Work Order. BEDA volume dan konteks. Ini sudah tepat dipisah. |
| 6 | Label ganda "Stok & Pergerakan" | ⚠️ UX | Sub-item "Stok & Pergerakan" muncul 2x (untuk Bahan Baku `wh-stock` dan untuk Aksesoris `wh-accessory-stock`). Label sama tapi module beda → membingungkan user. Beri nama lebih spesifik: "Stok Bahan Baku" dan "Stok Aksesoris". |
| 7 | Badge "P0" dan "P1" di GARMENT WMS | ⚠️ UX | Badge "P0", "P1" adalah internal prioritas development, bukan label untuk end-user. Ganti dengan badge yang lebih user-friendly atau hapus. |

**Rekomendasi Gudang:**
1. Rename `do-management` sidebar: "DO & Pengiriman CMT" (bukan "Delivery Orders (DO/Surat Jalan)")
2. Rename `wms-delivery-notes` sidebar: "Surat Jalan Keluar (PDF)" untuk membedakan
3. Rename sub-item "Stok & Pergerakan" yang pertama → "Stok Bahan Baku" dan kedua → "Stok Aksesoris"
4. Ganti badge "P0", "P1" di GARMENT WMS dengan "BETA" atau "ADVANCED"

---

## BAGIAN 5 — ANALISIS PORTAL PRODUKSI & MAKLON

### Struktur Menu PRODUKSI Saat Ini

```
Produksi
├── OPERASIONAL HARIAN
│   ├── 📊 Dashboard & Pengiriman
│   │   ├── Dashboard Produksi           [production-dashboard]
│   │   └── Pengiriman (Surat Jalan)     [prod-shipments]
│   │
│   ├── ⚡ Quick Actions
│   │   ├── Production Wizard            [prod-wizard]
│   │   └── Material Issue (Bulk)        [prod-bulk-mi]
│   │
│   ├── 📋 Order & Penjadwalan
│   │   ├── Order Produksi               [prod-orders]
│   │   ├── Work Order                   [prod-work-orders]
│   │   ├── Penelusuran Bundle           [prod-bundles]
│   │   └── Reservasi Material           [prod-material-reservation]
│   │
│   └── 🏭 Eksekusi Lantai Produksi
│       ├── Proses Cutting               [prod-cutting]        ← Perhatian (no. 1)
│       ├── Assign Lini Hari Ini         [prod-assignments]
│       ├── Serah Terima Shift           [prod-shift-handover]
│       └── Papan Rework                 [prod-rework-board]   ← 🔴 BROKEN
│
├── PROSES INTI (5 TAHAP)
│   ├── Tahap Produksi
│   │   ├── 1 · Cutting                  [prod-exec-cutting]   ← Perhatian (no. 1)
│   │   ├── 2 · Jahit (CMT)              [prod-exec-sewing]
│   │   ├── 3 · Finishing                [prod-exec-finishing]
│   │   ├── 4 · QC Final                 [prod-exec-qc]
│   │   └── 5 · Packing                  [prod-exec-packing]
│   │
│   └── CMT & Sub-Proses
│       ├── Manajemen CMT                [prod-cmt]
│       ├── Packing & Opname CMT (BARU)  [prod-cmt-packing]
│       ├── Kekurangan Komponen (BARU)   [production-cmt-component-requests]
│       └── Rework / Revisi              [prod-exec-rework]
│
├── MONITORING & ANALYTICS
│   ├── Real-time
│   │   ├── Papan Lini Real-time         [prod-line-board]
│   │   ├── Papan Andon                  [prod-andon-board]
│   │   └── Pengaturan Alert             [prod-alert-settings]  ← 🔴 BROKEN
│   │
│   ├── Quality Analytics
│   │   ├── Pareto Cacat                 [prod-pareto]
│   │   ├── First Pass Yield (FPY)       [prod-fpy]
│   │   └── AQL Sampling Tool            [prod-aql-calculator]
│   │
│   └── Performance & AI
│       ├── Log Downtime Mesin           [prod-downtime]
│       ├── Backlog & Forecast           [prod-backlog]
│       ├── AI Insights & Chatbot        [prod-ai-insights]
│       ├── AI Action Items              [ai-actions]          ← SHARED dengan HR
│       └── Predictive Maintenance (BARU)[prod-predictive-maintenance]
│
└── MASTER DATA
    ├── 📍 Lokasi & Workspace
    │   ├── Gedung & Zona                [prod-locations]
    │   ├── Lini Produksi                [prod-lines]
    │   ├── Mesin Jahit/Cutting          [prod-machines]
    │   └── Shift Kerja                  [prod-shifts]
    │
    ├── 📐 Proses & Standar
    │   ├── Proses Produksi              [prod-processes]
    │   ├── SOP Produksi                 [prod-sop]
    │   ├── Master Kode Cacat            [prod-defect-codes]
    │   └── Kalender Produksi            [prod-production-calendar]
    │
    └── 👕 Produk & Tim
        ├── Master Produk & BOM          [prod-models-bom]
        └── Operator & Skill Matrix      [prod-employees]
```

### Struktur Menu MAKLON Saat Ini

```
Maklon
├── KLIEN & ORDER
│   ├── Dashboard Maklon                 [maklon-dashboard]
│   ├── Data Klien Maklon                [maklon-clients]
│   ├── PO Maklon (Baru) [NEW]           [maklon-po]
│   ├── Order Maklon (Lama)              [maklon-orders]      ← LEGACY (masih aktif)
│   ├── Sample Management                [maklon-samples]
│   └── Tracking Produksi                [maklon-tracking]
│
├── OPERASIONAL
│   ├── CMT Assignment                   [maklon-cmt]         ← 🔴 BROKEN
│   ├── Progress & DO [NEW]              [cmt-progress]       ← Menggantikan maklon-cmt
│   ├── QC & Reject                      [maklon-qc]
│   └── Packing & Pengiriman             [maklon-packing]     ← 🔴 BROKEN
│
├── KEUANGAN & ANALITIK
│   ├── Invoice & Billing                [maklon-billing]
│   ├── HPP Jasa Jahit                   [maklon-hpp]
│   ├── SLA Dashboard & Lead Time (BARU) [maklon-sla-dashboard]
│   └── AI Quote Generator (AI)          [maklon-ai-quote]
│
└── PENGATURAN
    ├── Notification Center              [maklon-notifications]
    └── System Config                    [maklon-config]
```

### Temuan Produksi & Maklon

| No | Temuan | Kategori | Detail |
|----|--------|----------|--------|
| 1 | `prod-cutting` vs `prod-exec-cutting` (CUTTING GANDA) | ✅ BERBEDA tapi membingungkan | `prod-cutting` (CuttingProcessModule) = Manajemen cutting orders: buat cutting request, approval, lifecycle status cutting. `prod-exec-cutting` (ProcessExecutionModule) = Eksekusi daily: scan output, track qty per shift/lini. BERBEDA alur kerja. Namun placement di 2 section berbeda (OPERASIONAL vs PROSES INTI) sering membingungkan user cutting mana yang dipakai sehari-hari. |
| 2 | `prod-rework-board` | 🔴 BROKEN | Tidak ada di moduleRegistry → fallback ManagementDashboard. Ada `prod-rework-analytics` sebagai redirect ke production-dashboard. `prod-exec-rework` sudah ada di PROSES INTI. Hapus `prod-rework-board` dari sidebar. |
| 3 | `prod-alert-settings` | 🔴 BROKEN | Tidak ada di moduleRegistry → fallback ManagementDashboard. Fungsionalitas alert sudah ada di `prod-andon-board` dan `warehouse-smart`. Hapus atau buat modul baru. |
| 4 | `ai-actions` shared Production & HR | ⚠️ Context Confusion | AIActionsModule tidak membedakan konteks (HR vs Production). User Production melihat HR action items dan sebaliknya. Perlu penambahan filter `context` parameter. |
| 5 | `maklon-cmt` | 🔴 BROKEN | Tidak di registry → fallback ManagementDashboard. Fungsionalitas digantikan `cmt-progress` (CMTProgressModule) yang sudah ada di bawahnya. Hapus `maklon-cmt`. |
| 6 | `maklon-packing` | 🔴 BROKEN | Tidak di registry → fallback ManagementDashboard. Fungsionalitas packing Maklon sudah ada di `prod-cmt-packing` (CMTPackingModule). Hapus `maklon-packing`. |
| 7 | `maklon-orders` (Lama) + `maklon-po` (Baru) | ⚠️ Migrasi Belum Selesai | Dua sistem order Maklon berjalan bersamaan. `maklon-orders` berlabel "(Lama)" tapi masih aktif. Perlu keputusan: kapan `maklon-orders` bisa dihapus dan data dimigrasikan ke `maklon-po`? |
| 8 | `prod-ai-insights` vs `hr-ai-insights` | ✅ BERBEDA | prod-ai-insights = AI untuk analitik produksi (OEE, bottleneck, defect prediction). hr-ai-insights = AI untuk HR analytics (attrition, engagement). BERBEDA domain. |
| 9 | PROSES INTI 5 Tahap — HANYA 5 proses yang terlihat | ⚠️ Missing Context | Registry punya `prod-exec-linking`, `prod-exec-rajut`, `prod-exec-sontek`, `prod-exec-steam`, `prod-exec-washer` (garment spesifik) yang sudah jadi redirect. Ini sudah benar (consolidate ke 5 tahap utama). |

---

## BAGIAN 6 — RINGKASAN MASALAH (PRIORITAS)

### 🔴 P0 — HARUS DIFIX SEGERA (Broken)

| # | Portal | Issue | Rekomendasi |
|---|--------|-------|-------------|
| 1 | Maklon | `maklon-cmt` (CMT Assignment) — BROKEN | **Hapus dari sidebar** — digantikan `cmt-progress` |
| 2 | Maklon | `maklon-packing` (Packing & Pengiriman) — BROKEN | **Hapus dari sidebar** — digantikan `prod-cmt-packing` |
| 3 | Produksi | `prod-rework-board` (Papan Rework) — BROKEN | **Hapus dari sidebar** — gunakan `prod-exec-rework` |
| 4 | Produksi | `prod-alert-settings` (Pengaturan Alert) — BROKEN | **Hapus dari sidebar** (atau buat modul baru) |

### 🟡 P1 — PERBAIKAN UX PENTING

| # | Portal | Issue | Rekomendasi |
|---|--------|-------|-------------|
| 5 | Marketing | `marketing-livehost` di KOL section | Pindah ke section baru "👥 Tim Live" |
| 6 | Marketing | `marketing-kol-leaderboard` di AI section | Pindah ke ⭐ KOL & Creator |
| 7 | Marketing | `marketing-scheduler` di AI section | Pindah ke 📅 Konten & Kampanye |
| 8 | Marketing | `marketing-live` di Performa section | Pindah ke ⭐ KOL & Creator |
| 9 | Gudang | Label ganda "Stok & Pergerakan" | Rename jadi "Stok Bahan Baku" dan "Stok Aksesoris" |
| 10 | Gudang | `do-management` naming konfusing | Rename sidebar label jadi "DO & Pengiriman CMT" |
| 11 | Gudang | Badge "P0", "P1" di WMS | Ganti dengan "BETA" atau "ADVANCED" |
| 12 | Maklon | `maklon-orders` (Lama) masih aktif | Tentukan timeline deprecation |

### 🟢 P2 — NICE TO HAVE

| # | Portal | Issue | Rekomendasi |
|---|--------|-------|-------------|
| 13 | HR | Sub-header section terlalu dalam | Collapse section atau kurangi level header |
| 14 | HR | `hr-admin` placement di KARYAWAN | Pindah ke SISTEM/PENGATURAN section |
| 15 | Marketing | `maklon-notifications` di Marketing PENGATURAN | Buat `marketing-notifications` sendiri |
| 16 | Marketing | `toko-channels` (Lama), `toko-pricing` (Lama) | Konfirmasi → hapus jika sudah tidak ada data unik |
| 17 | Produksi | `prod-cutting` vs `prod-exec-cutting` confusing | Rename: "Cutting Orders" vs "Eksekusi Cutting" |
| 18 | Produksi | `ai-actions` tanpa filter konteks | Tambah filter `context` = HR/Production |

---

## BAGIAN 7 — LEGACY MODULES DI REGISTRY (Tidak di Sidebar)

Modul-modul ini masih ada di `moduleRegistry.js` tapi **tidak muncul di sidebar manapun**. Mereka hanya dapat diakses melalui direct URL atau command palette:

| Module ID | Type | Status | Rekomendasi |
|-----------|------|--------|-------------|
| `toko-dashboard-classic` | Redirect/Legacy | Di registry sebagai fallback | Pertahankan sebagai legacy redirect |
| `toko-dashboard-legacy` | Legacy | Fallback | Pertahankan sebagai legacy redirect |
| `toko-cs`, `toko-deals`, `toko-kol`, `toko-orders`, `toko-packing`, `toko-products`, `toko-returns`, `toko-shipping`, `toko-samples` | Old toko modules | Masih di registry | Bisa dihapus dari registry jika data sudah dimigrasikan ke marketing modules baru |
| `prod-bom`, `prod-models`, `prod-sizes` | Old, redirects | Redirect ke `prod-models-bom` | ✅ Sudah ditangani dengan redirect |
| `prod-oee`, `prod-line-balance`, `prod-aps-gantt` | Old, redirects | Redirect ke `production-dashboard` | ✅ Sudah ditangani dengan redirect |
| `prod-rework-analytics` | Redirect | Redirect ke `production-dashboard` quality tab | ✅ OK |
| `collab-communication` | Alias | Direct import CommunicationHubPortal | Bisa dihapus jika tidak digunakan |
| `cmt-component-requests` | Alias | Generic alias untuk `production-cmt-component-requests` | Pertahankan untuk backward compat |
| `self-dashboard` | Alias | Maps ke SelfServicePortal | Pertahankan untuk backward compat |
| `wh-material-reservation` | Redirect | Redirect ke `prod-material-reservation` | ✅ Sudah ditangani |
| `wh-accessory` | Old | No longer in sidebar | Bisa dihapus dari registry |
| `mgmt-customers` | Old | Maps to BuyersModule, not in sidebar | Bisa dihapus atau redirect ke `mgmt-rahaza-customers` |
| `mgmt-products` | Redirect | Redirect ke `prod-models-bom` | ✅ Sudah ditangani |
| `rnd-module`, `rnd-style-detail` | Internal | Digunakan secara programatik | Pertahankan |

---

## BAGIAN 8 — WORKSPACE PORTAL — KLARIFIKASI PENTING

Dua module "workspace" yang BERBEDA ada di sistem:

| | Portal Saya → `portal-workspace` | Portal Kolaborasi → `collab-workspace` |
|-|-----------------------------------|----------------------------------------|
| **Komponen** | `WorkspaceHub.jsx` (1004 baris) | `WorkspacePortal.jsx` (1364 baris) |
| **Fitur** | Notes (TipTap), Kanban, Calendar, Quick Links, Todos, Notif Toggle | Spreadsheet Editor (react-data-grid), share, version history, formula |
| **Target User** | Individual employee (portal saya) | Tim/kolaborasi (spreadsheet bersama) |
| **Label Sidebar** | "My Workspace" | "My Workspace (Spreadsheet)" |
| **Status** | ✅ Berfungsi | ✅ Berfungsi |

Keduanya sudah diimplementasikan dan BERBEDA fungsinya. Label "My Workspace" yang sama bisa membingungkan — rekomendasi rename:
- Portal Saya: **"Papan Kerja Pribadi"** (notes, kanban, kalender)
- Portal Kolaborasi: **"Dokumen & Spreadsheet"** (kolaborasi spreadsheet)

---

## KESIMPULAN EKSEKUTIF

**Total masalah ditemukan:** 18 item  
**Broken (P0):** 4 menu item tidak berfungsi (klik = ManagementDashboard)  
**UX Issues (P1):** 8 item salah section/label  
**Nice to Have (P2):** 6 item minor improvements  

**TIDAK ADA redundansi sejati** (dua modul yang melakukan hal persis sama dengan data yang sama). Semua yang terlihat mirip terbukti memiliki perbedaan scope, alur kerja, atau target pengguna.

**Prioritas Aksi:**
1. **SEGERA:** Fix 4 broken items (hapus dari sidebar atau daftarkan ke registry)
2. **Minggu Ini:** Reorganisasi section Marketing (items salah tempat)
3. **Sprint Berikutnya:** Perbaikan labels Gudang, deprecation plan `maklon-orders`
