# ANALISIS MENDALAM — PORTAL HR & MARKETING
## CV. Dewi Aditya ERP
**Tanggal:** 22 Mei 2026

---

## BAGIAN 1 — PORTAL HR

### 1A. PETA LENGKAP

| Menu Item | ID | Komponen | API Endpoint | Koleksi DB | Fungsi Sesungguhnya |
|-----------|-----|----------|-------------|------------|---------------------|
| Dashboard SDM | `hr-dashboard` | `HRDashboardModule` | `/api/rahaza/hr/dashboard` | Aggregasi | KPI SDM: headcount, turnover, absensi summary |
| Data Karyawan & Kontrak | `hr-employees` | `HREmployeesModule` | `/api/rahaza/employees` | `rahaza_employees` | CRUD karyawan + kontrak kerja |
| Struktur Organisasi | `hr-org-chart` | `HROrgChartModule` | `/api/rahaza/org-chart` | `rahaza_departments` | Visualisasi hierarki departemen/jabatan |
| Aset Karyawan | `hr-assets` | `HRAssetModule` | `/api/rahaza/employee-assets` | `rahaza_employee_assets` | Aset yang DIPINJAMKAN ke karyawan (laptop, HP, seragam) |
| HR Admin & Seed | `hr-admin` | `HRAdminModule` | `/api/rahaza/hr/admin/*` | Semua HR collections | Seed data demo + admin reset + data cleaner |
| Job Posting & ATS | `hr-recruitment` | `HRATSModule` | `/api/rahaza/recruitment/*` | `rahaza_job_postings` `rahaza_applications` | Buat lowongan + terima & track lamaran |
| AI Resume Screening | `hr-resume-screening` | `HRResumeScreeningModule` | `/api/rahaza/resume-screening` | `rahaza_applications` | AI filter CV lamaran berdasarkan kriteria jabatan |
| Onboarding Checklist | `hr-onboarding` | `HROnboardingModule` | `/api/rahaza/onboarding` | `rahaza_onboarding_checklists` | Checklist onboarding karyawan baru |
| Internal Job Board | `hr-job-board` | `HRJobBoardModule` | `/api/rahaza/internal-jobs` | `rahaza_internal_jobs` | Lowongan mutasi/promosi internal |
| Absensi Harian (Manual) | `hr-attendance` | `AttendanceModule` | `/api/rahaza/attendance` | `rahaza_attendance` | Input & view absensi manual (admin/supervisor) |
| Absen Otomatis (BARU) | `hr-auto-attendance` | `RahazaAutoAttendanceModule` | `/api/rahaza/attendance/auto-config` `/api/rahaza/attendance/webauthn/*` | `rahaza_attendance` `rahaza_webauthn_devices` | Konfigurasi biometric (WebAuthn) + lihat log absensi otomatis |
| Approval Absen (BARU) | `hr-attendance-approval` | `RahazaAttendanceApprovalModule` | `/api/rahaza/attendance/approvals` | `rahaza_attendance_approvals` | Approve/reject request koreksi absensi dari karyawan |
| Auto Shift Scheduler | `hr-shift-scheduler` | `HRShiftSchedulerModule` | `/api/rahaza/shift-schedule` | `rahaza_shift_schedules` | Generate jadwal shift otomatis berdasarkan rules |
| Request Lembur | `hr-overtime` | `HROvertimeModule` | `/api/rahaza/overtime` | `rahaza_overtime_requests` | Submit + approve request lembur karyawan |
| Izin & Cuti | `hr-leave` | `LeaveManagementModule` | `/api/rahaza/leave-requests` | `rahaza_leave_requests` | Submit + approve request cuti/izin |
| Saldo Cuti | `hr-leave-balances` | `LeaveBalancesModule` | `/api/rahaza/leave-balances` | `rahaza_leave_balances` | Lihat & adjust saldo cuti per karyawan |
| KPI Bulanan (Operasional) | `hr-kpi` | `KPIManagementModule` | `/api/rahaza/kpi` | `rahaza_kpi_records` | Admin set + review KPI bulanan semua karyawan |
| Annual Review (Tahunan) | `hr-performance` | `PerformanceReviewModule` | `/api/rahaza/performance-reviews` | `rahaza_performance_reviews` | Form review tahunan: self-assessment + manager review |
| 360° Feedback | `hr-360-feedback` | `HR360FeedbackModule` | `/api/rahaza/360-feedback` | `rahaza_360_feedback` | Feedback multi-rater: peer, bawahan, atasan |
| Learning Management | `hr-lms` | `HRLMSModule` | `/api/rahaza/lms/*` | `rahaza_courses` `rahaza_enrollments` `rahaza_quiz` | CRUD kursus, enrollment, quiz, sertifikat PDF |
| Profil Gaji Karyawan | `hr-payroll-profiles` | (modul payroll) | `/api/rahaza/payroll/profiles` | `rahaza_payroll_profiles` | Master gaji pokok + komponen gaji per karyawan |
| Tunjangan Tetap | `hr-payroll-allowances` | (modul allowances) | `/api/rahaza/payroll/allowances` | `rahaza_payroll_allowances` | Setup jenis tunjangan dan nilai per jabatan/individu |
| Kenaikan Gaji (Approval) | `hr-salary-adjustments` | (modul adjustments) | `/api/rahaza/payroll/salary-adjustments` | `rahaza_salary_adjustments` | Request & approve kenaikan gaji + history perubahan |
| Penggajian & Slip | `hr-payroll-run` | (modul payroll-run) | `/api/rahaza/payroll/run` | `rahaza_payroll_runs` | Generate slip gaji bulanan + approval + export |
| HR Dashboard dengan AI | `hr-ai-insights` | `RahazaAIModule` ❗ | `/api/rahaza/ai/*` | Aggregasi | **SAMA PERSIS dengan prod-ai-insights** — chatbot AI, tidak ada filter HR |
| Predictive Attrition | `hr-attrition` | `HRAttritionModule` | `/api/rahaza/hr/attrition` | Derived | Prediksi risiko resign per karyawan (model AI) |
| Skill Gap Analysis | `hr-skill-gap` | `HRSkillGapModule` | `/api/rahaza/hr/skill-gap` | Derived | Gap analisis skill karyawan vs kebutuhan jabatan |
| Performance Coaching AI | `hr-coaching` | `HRCoachingModule` | `/api/rahaza/hr/coaching` | `rahaza_coaching_sessions` | AI saran coaching per karyawan berdasarkan KPI/review |
| Automated Recommendations | `ai-actions` | `AIActionsModule` ❗ | `/api/rahaza/ai/actions` | `rahaza_ai_actions` | **SAMA dengan di Portal Produksi** — lintas departemen |
| Laporan & Analitik SDM | `hr-reports` | `HRReportsModule` | `/api/rahaza/hr/reports` | Aggregasi | Export laporan HR: headcount, turnover, absensi, payroll |

### 1B. MASALAH HR

**Masalah #1 — Sub-header Section Terlalu Dalam**

Section KEHADIRAN punya 4 sub-header dengan total 7 item:
```
KEHADIRAN & SHIFT
├── ⏰ Absensi & Clock In/Out [header]
│   ├── Absensi Harian (Manual)     [hr-attendance]
│   ├── Absen Otomatis (BARU)       [hr-auto-attendance]
│   └── Approval Absen (BARU)       [hr-attendance-approval]
├── 📅 Shift & Jadwal Kerja [header]
│   └── Auto Shift Scheduler        [hr-shift-scheduler]
├── 🌙 Lembur & Overtime [header]
│   └── Request Lembur              [hr-overtime]
└── 🏖️ Cuti & Izin [header]
    ├── Izin & Cuti                 [hr-leave]
    └── Saldo Cuti                  [hr-leave-balances]
```

4 header untuk 7 item adalah over-categorization. Setiap header hanya berisi 1-3 item.

**Solusi:** 1 header "KEHADIRAN, SHIFT & CUTI" dengan 7 item flat, atau 2 header (Kehadiran & Shift | Cuti & Lembur)

**Masalah #2 — `hr-attendance` vs `hr-auto-attendance` TIDAK SALING TERINTEGRASI**

- `hr-attendance` = input manual absensi
- `hr-auto-attendance` = konfigurasi WebAuthn + lihat log auto
- Kedua sistem tulis ke `rahaza_attendance` yang SAMA, tapi user tidak perlu buka keduanya kecuali mereka perlu konfigurasi biometric
- `hr-auto-attendance` seharusnya hanya tampil jika fitur WebAuthn diaktifkan

**Masalah #3 — `hr-assets` vs Portal Aset Management**

Keduanya memang BERBEDA tapi ada celah koordinasi:
- `hr-assets`: laptop/HP/seragam yang dipinjam karyawan → `rahaza_employee_assets`
- Portal Aset: mesin, kendaraan → `dewi_asset_*` dengan lifecycle depreciation

Idealnya asset yang tercatat di Portal Aset bisa di-assign ke karyawan dan muncul di `hr-assets` secara otomatis. Saat ini kedua sistem tidak terhubung.

**Masalah #4 — Payroll 4 Menu: Seharusnya 2**

```
Sekarang (4 menu):             Ideal (2 menu):
hr-payroll-profiles      →     Payroll Setup (tab: Profil Gaji | Tunjangan | Kenaikan)
hr-payroll-allowances    →     ↑ (digabung)
hr-salary-adjustments    →     ↑ (digabung)
hr-payroll-run           →     Proses Penggajian (tetap terpisah karena aksi kritikal)
```

**Masalah #5 — hr-ai-insights = prod-ai-insights (SAMA PERSIS)**

Kedua modul menggunakan `RahazaAIModule` dengan endpoint yang sama. Tidak ada filtering berdasarkan konteks HR vs Produksi. Seorang HR Manager membuka "HR Dashboard dengan AI" dan melihat chatbot yang juga membahas OEE mesin dan backlog produksi.

**Masalah #6 — KINERJA & PENGEMBANGAN: 3 sistem review berbeda tanpa integrasi**

```
hr-kpi       → KPI Bulanan (operasional target/realisasi bulanan)
hr-performance → Annual Review (tahunan, form narrative)
hr-360-feedback → 360° Feedback (multi-rater, peer assessment)
```

Ketiganya adalah modul review yang BERBEDA tapi datanya tidak saling terhubung. Idealnya annual review dan 360 feedback membaca dari data KPI untuk konteks. Saat ini ketiga sistem terpisah dan user harus input di 3 tempat berbeda untuk review 1 karyawan.

---

## BAGIAN 2 — PORTAL MARKETING

### 2A. TEMUAN KRITIS: DUA SISTEM ORDER/PENJUALAN PARALEL

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  SISTEM LAMA (masih aktif, masih punya data):                                │
│  ─────────────────────────────────────────────────────────────────────────── │
│  Collections: dewi_toko_orders, dewi_toko_channels, dewi_toko_products,     │
│               dewi_toko_flashsales, dewi_toko_returns, dll                   │
│  Menu: toko-channels (Lama), toko-pricing (Lama) — masih di sidebar         │
│  Dan: toko-orders, toko-packing, toko-shipping (redirect saja, tersembunyi) │
│                                                                              │
│  SISTEM BARU (aktif, terus dikembangkan):                                   │
│  ─────────────────────────────────────────────────────────────────────────── │
│  Collections: marketing_orders, marketing_platform_accounts,                 │
│               marketing_sales_data, marketing_catalogs, dll (40+ collections)│
│  Menu: semua marketing-* yang ada di sidebar saat ini                       │
│                                                                              │
│  STATUS: Kedua sistem ada di database secara BERSAMAAN                      │
│          Data lama di dewi_toko_* TIDAK dimigrasikan ke marketing_*         │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Implikasi:**
- Laporan penjualan historis ada di sistem lama (`dewi_toko_orders`)
- Penjualan baru masuk ke sistem baru (`marketing_orders`)
- Tidak ada cara mudah lihat laporan penjualan total (lama + baru)

### 2B. PETA LENGKAP PORTAL MARKETING

| Menu Item | ID | Komponen | API | Koleksi DB | Fungsi |
|-----------|-----|----------|-----|------------|--------|
| Marketing Overview | `marketing-overview` | `MarketingOverviewDashboard` | `/api/marketing/overview` | Aggregasi | Dashboard utama: GMV, orders, top accounts |
| Manage Accounts | `marketing-accounts` | `AccountManagementModule` | `/api/marketing/accounts` | `marketing_platform_accounts` | CRUD akun marketplace (Tokopedia, Shopee, dll) |
| Input Sales Harian | `marketing-sales` | `SalesInputModule` | `/api/marketing/sales` | `marketing_sales_data` | Input omzet/sales manual per akun per hari |
| Universal Smart Import | `marketing-import` | `UniversalImportModule` | `/api/marketing/import/*` | `marketing_import_*` | Import data dari CSV/Excel per platform |
| Unified Orders | `marketing-orders` | `UnifiedOrdersDashboard` | `/api/marketing/orders` | `marketing_orders` | Dashboard semua order dari semua platform |
| Kelola Komplain | `marketing-complaints` | `ComplaintsModule` | `/api/marketing/complaints` | `marketing_complaints` | Track dan resolve keluhan customer |
| Manajemen Katalog | `marketing-catalog` | `CatalogManagementModule` | `/api/marketing/catalog/*` | `marketing_catalogs` `marketing_catalog_items` | CRUD produk catalog untuk semua channel |
| Channel Manager (Lama) | `toko-channels` | `TokoChannelManagerModule` ❗ | `/api/dewi/toko/channels` | `dewi_toko_channels` | **SISTEM LAMA** — channel management di sistem toko lama |
| Harga & Flashsale (Lama) | `toko-pricing` | `TokoFlashSaleModule` ❗ | `/api/dewi/toko/flashsales` | `dewi_toko_flashsales` | **SISTEM LAMA** — flash sale di sistem toko lama |
| KOL & Creator Mgmt | `marketing-kol` | `KOLManagementModule` | `/api/marketing/kol/*` | `marketing_kol_creators` | CRUD kreator KOL: profil, rates, platform |
| Kreator Requests | `marketing-kreator-requests` | `KreatorRequestsModule` | `/api/marketing/creator/requests` | `marketing_creator_item_requests` | Request produk dari kreator: link ke katalog, approve |
| **LiveHost Management** | `marketing-livehost` | `LiveHostModule` | `/api/marketing/livehost` | `marketing_livehosts` `marketing_livehost_shifts` | Manajemen SDM host live: profil, jadwal shift, pembayaran |
| Content Calendar | `marketing-content-calendar` | `ContentCalendarModule` | `/api/marketing/content-calendar` | `marketing_content_calendar` | Jadwal konten: post date, platform, PIC, status |
| Discount Campaign | `marketing-discounts` | `DiscountCampaignModule` | `/api/marketing/discounts` | `marketing_discounts` | Setup & track diskon per campaign |
| Product Launch | `marketing-product-launches` | `ProductLaunchModule` | `/api/marketing/product-launches` | `marketing_product_launches` | Rencana & track peluncuran produk baru |
| Account Health | `marketing-health` | `AccountHealthModule` | `/api/marketing/account-health` | `marketing_account_health` | Metrik kesehatan per akun: skor, alert, trend |
| Sales Performance | `marketing-performance` | `SalesPerformanceModule` | `/api/marketing/performance` | Derived | Analitik performa penjualan per PIC/platform/periode |
| Ads Performance | `marketing-ads` | `AdsPerformanceModule` | `/api/marketing/ads` | `marketing_ads_data` | ROAS, CTR, biaya iklan per platform |
| **Live Sessions** | `marketing-live` | `LiveSessionModule` | `/api/marketing/live/sessions` | `marketing_live_sessions` | Analytics performa siaran live: views, GMV, konversi |
| Laporan Harian PIC | `marketing-daily-report` | `DailyReportModule` | `/api/marketing/daily-report` | `rahaza_daily_reports` (!) | Input laporan harian oleh PIC per area |
| Laporan Bulanan | `marketing-monthly-report` | `MonthlyReportModule` | `/api/marketing/monthly-report` | Derived | Ringkasan bulanan dari laporan harian |
| Target Bulanan | `marketing-targets` | `TargetsModule` | `/api/marketing/targets` | `marketing_account_targets` | Set target GMV bulanan per akun/PIC |
| AI Marketing Insights | `marketing-ai-insights` | `MarketingAIInsightsDashboard` | `/api/marketing/ai/insights` | Derived | Dashboard AI: trend, anomali, rekomendasi |
| Advanced AI Features | `marketing-advanced-ai` | `AdvancedAIModule` | `/api/marketing/ai/advanced` | `marketing_churn_scores` `marketing_dynamic_pricing_*` | Dynamic pricing, churn prediction, A/B testing |
| AI Content Generator | `marketing-ai-content` | `AIContentGeneratorModule` | `/api/marketing/ai/content` | `marketing_ai_content_history` | Generate caption, deskripsi produk via AI |
| AI Image Generator | `marketing-ai-image` | `AIImageGeneratorModule` | (EMERGENT LLM) | — | Generate gambar produk via AI |
| KOL Leaderboard ❗ | `marketing-kol-leaderboard` | `KOLLeaderboardModule` | `/api/marketing/kol/leaderboard` | Derived | Ranking KOL berdasarkan performa (GMV, followers, dll) — **di AI Tools section padahal bukan AI** |
| Scheduler & Otomasi ❗ | `marketing-scheduler` | `SchedulerModule` | `/api/marketing/scheduler` | `marketing_alert_settings` | Otomasi alert & laporan terjadwal — **di AI Tools section padahal bukan AI** |
| Kanban Board | `marketing-tasks` | `TaskManagementModule` | `/api/marketing/tasks` | `marketing_tasks` | Manajemen task marketing dengan Kanban board |
| Approval Inbox | `marketing-approvals` | `ApprovalInboxModule` | `/api/marketing/approvals` | Derived | Inbox untuk approve: diskon, anggaran, konten |
| Task Templates | `marketing-templates` | `TaskTemplatesModule` | `/api/marketing/task-templates` | `marketing_task_templates` | Template task yang bisa di-reuse untuk campaign |
| Rating & Review Mgmt | `marketing-reviews` | `ReviewManagementModule` | `/api/marketing/reviews` | `marketing_reviews` | Monitor dan respon review customer di marketplace |
| Returns & Refunds | `marketing-returns` | `ReturnsRefundsModule` | `/api/marketing/returns` | `marketing_returns` | Track retur dari sisi order customer |
| Database Sample | `marketing-samples` | `SampleDatabaseModule` | `/api/marketing/samples` | `marketing_samples` | Track pengiriman sample ke KOL/reseller |
| API Integration Settings | `marketing-integration-settings` | `IntegrationSettingsModule` | `/api/marketing/integration-settings` | `marketing_integration_settings` | API key untuk marketplace platforms |
| Notifikasi & Provider ❗ | `maklon-notifications` | `MaklonNotificationsModule` | `/api/dewi/maklon/notifications` | `dewi_maklon_notifications` | **MODULE MILIK MAKLON** — dipinjam untuk notif marketing |

### 2C. MASALAH MARKETING

**Masalah #1 — `marketing-live` vs `marketing-livehost`: BEDA TAPI SALAH SECTION**

| | `marketing-live` (Live Sessions) | `marketing-livehost` (LiveHost Mgmt) |
|-|-----------------------------------|--------------------------------------|
| **Tentang** | Analytics konten siaran | SDM orang yang siaran |
| **API** | `/api/marketing/live/sessions` | `/api/marketing/livehost` |
| **DB** | `marketing_live_sessions` | `marketing_livehosts`, `marketing_livehost_shifts` |
| **Section saat ini** | 📊 Performa | ⭐ KOL & Creator |
| **Section yang tepat** | ⭐ KOL & Creator | Section baru "👥 Tim Live" |

`marketing-livehost` adalah modul HR (manajemen shift, pembayaran, jadwal host) tapi ada di section KOL. Ini membingungkan karena KOL section seharusnya tentang konten/kreator, bukan tentang jadwal kerja.

**Masalah #2 — Section "🤖 AI Tools" berisi 2 item yang BUKAN AI**

- `marketing-kol-leaderboard` → Ini ranking/statistik KOL, bukan fitur AI
- `marketing-scheduler` → Ini otomasi jadwal, bukan AI

Seharusnya:
- KOL Leaderboard → pindah ke ⭐ KOL & Creator
- Scheduler → pindah ke 📅 Konten & Kampanye atau PENGATURAN

**Masalah #3 — `maklon-notifications` di Marketing PENGATURAN**

Modul ini (`/api/dewi/maklon/notifications`) adalah milik portal Maklon dan membaca koleksi `dewi_maklon_notifications`. Ini di-hardcode ke sidebar Marketing padahal bukan milik Marketing. Marketing tidak punya notifikasi modul sendiri.

**Masalah #4 — `marketing-daily-report` menggunakan koleksi `rahaza_daily_reports`**

Ini mencampur domain: laporan harian marketing menggunakan koleksi `rahaza_*` yang seharusnya untuk domain Produksi. Ini menunjukkan laporan ini mungkin adalah "laporan harian produksi oleh PIC marketing" bukan laporan sales — perlu konfirmasi use case.

**Masalah #5 — Seed Data Marketing Tidak Lengkap**

Collections yang ada data (`marketing_platform_accounts`: 3 akun demo):
- `marketing_orders` → KOSONG
- `marketing_kol_creators` → KOSONG
- `marketing_livehosts` → KOSONG
- `marketing_content_calendar` → KOSONG
- `marketing_live_sessions` → KOSONG
- `marketing_sales_data` → KOSONG

Semua modul marketing menampilkan empty state saat dibuka, membuat demo/testing tidak representatif.

---

## BAGIAN 3 — RINGKASAN SEMUA PORTAL

### DAFTAR MASALAH TERURUT PRIORITAS

**🔴 P0 — Broken/Kritis:**
1. `maklon-cmt` — BROKEN (tidak di registry)
2. `maklon-packing` — BROKEN (tidak di registry)
3. `prod-rework-board` — BROKEN (tidak di registry)
4. `prod-alert-settings` — BROKEN (tidak di registry)
5. **Dua sistem aksesoris** (rahaza_materials vs acc_items) — data tidak konsisten
6. **Dua sistem order maklon** (dewi_maklon_orders vs dewi_maklon_pos) — migrasi tidak selesai
7. **Alur procurement terputus** (PO → GRN → Putaway tidak terhubung)

**🟠 P1 — UX Signifikan:**
8. **Dua sistem cutting** tidak terhubung (planning vs eksekusi)
9. **Empat aliran Surat Jalan** dengan label mirip, user tidak tahu bedanya
10. `cmt-progress` di portal Maklon tapi bukan tentang klien maklon
11. `marketing-livehost` di section KOL padahal ini manajemen SDM
12. `marketing-kol-leaderboard` dan `marketing-scheduler` salah section (di AI Tools)
13. `hr-ai-insights` = `prod-ai-insights` tanpa filter konteks
14. Marketing seed data kosong (semua modul empty state)

**🟡 P2 — Nice to Have:**
15. `wh-stock` dan `wh-accessory-stock` menampilkan data yang sama
16. Sub-header HR section KEHADIRAN terlalu dalam (4 header untuk 7 item)
17. Payroll 4 menu padahal bisa 2 (dengan tab)
18. 5 menu eksekusi produksi padahal bisa 1 menu dengan tab
19. `maklon-notifications` di Marketing PENGATURAN padahal modul Maklon
20. `toko-channels` dan `toko-pricing` (Lama) masih di sidebar

---

## BAGIAN 4 — REKOMENDASI PRIORITAS TINDAKAN

### Tindakan Langsung (tanpa diskusi):
1. Hapus 4 menu BROKEN dari sidebar (`maklon-cmt`, `maklon-packing`, `prod-rework-board`, `prod-alert-settings`)
2. Rename `prod-cmt-packing` → "Penerimaan Jahit CMT"
3. Pindahkan `marketing-kol-leaderboard` → section KOL & Creator
4. Pindahkan `marketing-scheduler` → section Konten & Kampanye
5. Pindahkan `marketing-live` → section KOL & Creator
6. Seed marketing data (minimal 5-10 data per collections utama)

### Tindakan yang Butuh Keputusan Bisnis:
7. **Sistem aksesoris**: Pilih satu sistem (A atau B) lalu migrate data. System A (rahaza_materials) lebih terintegrasi ke produksi. System B (acc_items) lebih lengkap lifecycle-nya. Rekomendasi: gabungkan fitur lifecycle System B ke System A.
8. **Sistem order maklon**: Tentukan timeline deprecation `dewi_maklon_orders` setelah `dewi_maklon_pos` lengkap.
9. **Data toko lama**: Apakah `dewi_toko_*` masih dipakai? Jika tidak, hapus `toko-channels` dan `toko-pricing` dari sidebar.
10. **Koneksi cutting planning ke eksekusi**: Diperlukan development untuk menghubungkan `dewi_cutting_batches` dengan `rahaza_process_execution`.
11. **Pindahkan `cmt-progress`**: Dari portal Maklon ke portal Produksi (section CMT & Sub-Proses).
