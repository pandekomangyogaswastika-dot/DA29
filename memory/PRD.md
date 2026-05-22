# DA25 ERP — Product Requirements Document

## Original Problem Statement
Pengembangan lanjutan aplikasi ERP CV. Dewi Aditya (DA25). Fokus area:
- LiveHost Management System (Phase 1-4) — SELESAI
- P2 Tasks: SOP PDF, Asset Utilization, Predictive Maintenance, Thread Conversations — SELESAI
- Multi-Currency (Task E) — DIBATALKAN oleh user
- Portal Marketing: Account Clarity Improvements — SELESAI

## User Personas
- Admin / Super Admin: Pengelola seluruh sistem
- Finance Staff: Kelola invoice, payment, laporan keuangan
- Marketing Staff (PIC): Kelola akun marketplace, input sales, manage KOL & LiveHost

## Language Requirement
SELALU balas user dalam Bahasa Indonesia.

---

## Architecture
- Frontend: React (lazy-loaded modules via moduleRegistry.js)
- Backend: FastAPI (Python)
- Database: MongoDB
- Auth: JWT

## Key Collections
- marketing_platform_accounts: akun marketplace (Shopee, TikTok, Tokopedia, dll)
- marketing_sales_data: data penjualan harian per akun
- marketing_kol_creators: creator dengan assigned_account_ids[]
- marketing_livehost: host dengan assigned_account_ids[]
- marketing_livehost_shifts: shift per host per akun
- fx_rates: DIHAPUS (multi-currency dibatalkan)
- fx_revaluation_runs: DIHAPUS (multi-currency dibatalkan)

---

## What's Been Implemented

### 2026-05 Session 28 — lanjutan v21 (KPI + Annual Review Seed)
- [x] Root cause fix: `create_token` sekarang encode `employee_id` dalam JWT
- [x] `_get_linked_employee` di dewi_kpi.py: 3-tier lookup (JWT→user_id→email) bukan hanya JWT
- [x] `sync-user-employee-ids` endpoint: sync 5 karyawan terhubung
- [x] Annual Review seed-demo: 2 cycles, 6 KPIs, 8 assignments, 3 reviews
- [x] KPI seed: 3 periode (Feb-Apr 2026) + 14 results published untuk 5 karyawan
- [x] Portal Saya KPI Saya: Siti Rahayu lihat Feb 82(B), Mar 79(C), Apr 84(B) dengan breakdown per komponen
- [x] My Workspace: Notepad, Todo, Reminder, Kalender, Quick Links — berjalan ✅
- [x] Dokumen Saya: Upload + lihat dokumen — berjalan ✅  
- [x] Slip Gaji Saya: Rp 12.503.844 take-home Mei 2026 — berjalan ✅
- [x] KPI Saya: "Belum ada periode" (correct — belum ada seed KPI per karyawan) ✅
- [x] Semua 7 Portal Saya API endpoint: 200 OK untuk siti@dewiaditya.id
- [x] Portal HR Rating: 9.5/10 — semua modul berjalan end-to-end
- [x] HRPerformanceModule: KPI Monthly Trend panel di review dialog — fetch /api/dewi/kpi/trend/{employee_id}, tampilkan kotak skor per bulan warna hijau/kuning/merah
- [x] openReviewDialog diubah async untuk fetch KPI data sebelum dialog terbuka
- [x] AI Career Coach fix: `get_career_profile` sekarang resolve employee via user_id→email fallback (bukan user.id yang salah)
- [x] Career Coach profile kini pakai LMS enrollments + da_kpi_results + dewi_recruitment_jobs
- [x] Portal Saya AI Career Coach: Siti Rahayu bisa lihat profil karir + Generate Career Report
- [x] Leave carry-forward: scheduler job `leave_carry_forward` setiap 1 Jan 01:00, carry min(remaining, 5) hari ke tahun baru
- [x] Manager notification: saat cuti diajukan, notif ke `employee.manager_id` + HR (bukan broadcast ke semua manager)
- [x] Leave list response: enriched dengan `manager_name`, `employee_dept`, `leave_type_request_type`
- [x] BPJS payment: `POST /payroll-runs/{id}/pay-bpjs` → Dr Hutang BPJS / Cr Bank + tombol "B" di payroll run
- [x] PPh21 payment: `POST /payroll-runs/{id}/pay-pph21` → Dr Hutang PPh21 / Cr Bank + tombol "P" di payroll run
- [x] Notifikasi payslip siap: saat finalize run, kirim notif ke setiap karyawan yang linked (user_id) dengan take-home amount
- [x] LMS completion: saat course selesai + lulus, kirim notif ke karyawan + HR
- [x] PortalSayaPayslip: tampilkan rekap kehadiran (hari hadir, total jam, lembur) di detail slip
- [x] Seed connected demo: endpoint `/seed-connected` buat leave_balances (70), leave_requests (4), overtime_requests (3)
- [x] Portal Saya sekarang hidup: Siti Rahayu punya cuti tahunan 3 hari tersisa, riwayat cuti tampil real
- [x] `post_payroll_payment()` di rahaza_posting.py: Dr 2-1200 Hutang Gaji / Cr [bank_code]
- [x] `void_payroll_payment()` untuk reverse payment JE
- [x] Posting profile `payroll_payment` diseed: debit_salary_payable=2-1200, credit_bank_default=1-1201
- [x] Endpoint POST /payroll-runs/{id}/pay + void-payment + retry-post alias
- [x] RahazaPayrollRunModule: tombol 💸 + dialog pilih bank/tanggal + badge biru payment JE
- [x] Verified: JE-20260531-0001 finalize + JE-20260531-0002 payment bayar Rp 103.855.745 ke Bank BCA
- [x] Seed CoA 84 akun (termasuk 6-2100 Gaji, 2-1200 Hutang Gaji, 2-1301 PPh21, 2-1500 BPJS)
- [x] Seed 10 posting profiles (payroll_finalize sudah ada dengan mapping benar)
- [x] Payroll finalize → auto-create JE: Dr 6-2100 Gaji / Cr 2-1200 Hutang Gaji + 2-1301 PPh21 + 2-1500 BPJS
- [x] RahazaPayrollRunModule: kolom "GL Jurnal" dengan badge hijau JE number, klik navigate ke Finance Journal List
- [x] Retry Post button untuk run finalized yang gagal posting
- [x] Finance Journal List sudah punya filter source_module=payroll_finalize
- [x] Verified: PR-20260522-002 → JE-20260531-0001 (Gross Rp 125jt)
- [x] `rahaza_self.py` `_get_employee_for_user()` diperbaiki: cek user_id di employees (baru) → users.employee_id (lama) → email fallback
- [x] auto-link + manual link juga set `users.employee_id` untuk backward-compat
- [x] SelfServicePortal Kehadiran Saya: berfungsi via `/api/rahaza/self/attendance` (linked=True)
- [x] Multi-level approval leave: > 7 hari kerja → step 1 (supervisor) → `pending_hr_approval` → step 2 (HR) → `approved`
- [x] `approval_level_required`, `current_approval_level`, `approval_step_1`, `approval_step_2` disimpan di leave_request
- [x] RahazaLeaveModule: badge "Menunggu Supervisor" / "Menunggu HR" / "2-Level" + tombol Approve HR terpisah
- [x] PortalSayaCuti: badge `pending_hr_approval` = "Menunggu HR" (warna biru)
- [x] `POST /api/rahaza/employees/auto-link-users` — idempotent, link by email match
- [x] 4 user demo dibuat (@dewiaditya.id) + auto-linked ke employee record
- [x] PortalSayaPayslip: endpoint diperbaiki (pakai /api/portal-saya/me/payslips)
- [x] PortalSayaCuti: endpoint diperbaiki (pakai /portal-saya/me/leaves + me/leave-balance + me/employee)
- [x] Verified: siti@dewiaditya.id bisa login, lihat saldo 12 tipe cuti, ajukan cuti dari Portal Saya
- [x] LWOP auto-deduction di payroll run: fetch approved LWOP leaves → daily_rate = base/working_days → potongan otomatis masuk ke deductions
- [x] PPh21 dihitung dari gross SETELAH potongan LWOP (lebih akurat)
- [x] Backend: `POST /api/rahaza/employees/{eid}/link-user` — tautkan akun login ke karyawan
- [x] Backend: `GET /api/rahaza/employees/resolve-by-user/{user_id}` — resolve employee dari user_id atau email
- [x] Backend: `dewi_portal_saya_hr.py` — endpoint Portal Saya yang benar: me/employee, me/payslips, me/leaves, me/leave-balance
- [x] Frontend: HREmployeeModule — tombol link user (ikon user, hijau jika sudah terhubung), Link User Dialog
- [x] PortalSayaPayslip: update ke endpoint /api/portal-saya/me/payslips yang berfungsi
- [x] Seed 20 hari libur nasional Indonesia 2026 via existing production calendar
- [x] `_count_working_days_db()` async helper — exclude Sabtu/Minggu + libur dari production_calendar
- [x] `GET /leaves/working-days` endpoint — preview real-time di frontend
- [x] `holidays_in_period` field di leave_request document
- [x] RahazaLeaveModule: live preview amber box saat pilih tanggal
- [x] PortalSayaCuti: live preview + tampil nama libur yang masuk periode
**Naming:** Tidak di-rename (high risk, low value — documented as technical debt)
**Leave/Permit Phase 1:**
- [x] 12 tipe izin/cuti baru sesuai UU No. 13/2003 (ANNUAL, SICK, MATERNITY, MARRIAGE, CHILD_BIRTH, dll)
- [x] Backend: `request_type` (cuti/sakit/izin), `requires_document`, `max_days_without_doc`, `doc_note`, `legal_basis`
- [x] Backend: `/leaves/upload-document` endpoint (multipart, simpan ke /app/uploads/leave_docs/)
- [x] Backend: working days calculation (exclude Sabtu/Minggu)
- [x] Backend: `is_half_day` + `half_day_period` (AM/PM) support
- [x] Backend: `/leaves/{id}/cancel` — batalkan approved, kembalikan saldo
- [x] Backend: document validation (reject if requires_doc dan tidak ada attachment)
- [x] Frontend: `RahazaLeaveModule` — full rewrite dengan tabs, request type badges, document upload, cancel flow
- [x] Frontend: `PortalSayaCuti` — rewrite dengan self-service, grouped leave types, document upload, employee resolve via email
- [x] Seed functions complaints/reviews/returns diupdate pakai real platform accounts
- [x] Seed function health diupdate pakai real platform accounts + simpan account_id FK
- [x] `/api/marketing/health/accounts` sekarang baca dari marketing_platform_accounts (bukan health collection)
- [x] Migration endpoint POST /api/marketing/reports/admin/migrate-seed-accounts — update 40 complaints, 40 reviews, 30 returns, reset health data
- [x] AccountDetailPage tab Komplain(40) + Reviews(40) sekarang tampil data real
- [x] Backend: account_id filter di complaints, reviews, returns list endpoints
- [x] Frontend: ActiveAccountBar di Complaints, Reviews, Returns, Ads Performance, Live Sessions, Account Health  
- [x] AccountDetailPage: 6 tab (Sales, KOL, LiveHost, + Orders, Komplain, Reviews baru)
- [x] Sidebar: "Channel Manager (Lama)" dan "Harga & Flashsale (Lama)" label legacy
- [x] build_creator_target_pdf(): PDF generator ReportLab untuk target KOL/Creator (header, ringkasan, tabel per creator dengan warna pencapaian)
- [x] Endpoint GET /api/marketing/targets/creator/export-pdf → download PDF
- [x] AccountTargetsModule tab KOL/Creator: tombol "Export PDF"
- [x] KOLCreatorModule: fetch per-month creator targets, tampilkan progress bar Revenue + Sesi di creator card
- [x] AccountDetailPage tab KOL Creator: fetch creator targets, tampilkan progress bar inline per creator
- [x] Backend: `/api/marketing/targets/creator` + `/api/marketing/targets/creator/monthly-summary` — target per-bulan per-creator (revenue, sessions, viewers)
- [x] AccountTargetsModule: 2 tabs — "Platform Akun" (existing) + "KOL / Creator" (baru) dengan tabel target vs aktual, tombol Set/Edit per creator, KPI cards ringkasan
- [x] monthly_report_pdf.py: PDF generator dengan ReportLab (header, KPI summary, tabel per akun dengan warna on-track/warning/behind)
- [x] Endpoint GET /api/marketing/reports/monthly/export-pdf → download PDF langsung dari browser
- [x] MonthlyReportModule: tombol "Export PDF" → download file
- [x] Scheduler: job `scan_overdue_marketing_tasks` berjalan setiap 17:00, kirim notif ke assigned + PIC untuk setiap task overdue (dedup per hari)
- [x] Scheduler: kirim in-app notification ke `pic_user_id` setelah auto-create task sales + health alert
- [x] DailyReportModule: tombol "Eksekusi" inline per akun yang belum input → QuickSalesDialog (isi revenue/orders, langsung trigger complete-action)
- [x] AccountDetailPage: section "Target Bulan Ini" dengan progress bar inline (revenue + orders)
- [x] Backend: PlatformAccountUpdate + `pic_user_id` field — denormalize `pic_user_name` otomatis
- [x] AccountManagementModule: dropdown PIC di form edit, tampilkan nama PIC di card
- [x] Scheduler sudah menggunakan `pic_user_id` untuk auto-assign task
- [x] TaskCard: AccountBadge per task, ⚡ indicator actionable task, guard bypass drag-to-done
- [x] Backend: marketing_targets.py (target per akun per bulan, monthly summary)
- [x] Backend: marketing_reports.py (daily report + monthly report endpoints)
- [x] Frontend: AccountTargetsModule (set/edit target per akun)
- [x] Frontend: DailyReportModule (status input sales + pending tasks + health alerts)
- [x] Frontend: MonthlyReportModule (target vs actual + task completion + mini chart)
- [x] Sidebar: menu 'LAPORAN PIC' dengan 3 item baru di Analytics & AI
- [x] SalesPerformanceDashboard: tambah filter by specific account (dropdown Akun di panel Filter)
- [x] MarketingDashboard: Revenue Chart filter per-akun (dropdown)
- [x] AccountCard: tombol "Lihat Detail" + klik card → navigasi ke AccountDetailPage
- [x] Hapus semua kode multi-currency (backend + frontend)
- [x] AccountBadge component (platform-colored badges: Shopee=oranye, TikTok=pink, Tokopedia=hijau)
- [x] useActiveMarketingAccount hook (localStorage persistence lintas modul)
- [x] ActiveAccountBar component (sticky bar ganti akun aktif)
- [x] SalesDataEntryModule: ActiveAccountBar, hapus auto-select, visual konfirmasi akun
- [x] KOLCreatorModule: AccountBadge di card creator, filter by account, SessionFormModal filter akun
- [x] LiveHostModule: AccountBadge di kolom Assigned Accounts, filter by account, AddShiftModal filter akun
- [x] Bug fix: ShiftsTab crash (SelectItem empty string value)

### Session 28 sebelumnya (handoff summary)
- [x] Phase 4 LiveHost: Portal, Shifts, Scripts, Training, SSE Notifications
- [x] Task A: SOP LiveHost PDF (reportlab)
- [x] Task C: Asset Utilization Report
- [x] Task D: Predictive Maintenance Alerts
- [x] Task B: Slack-style Thread Conversations

---

## Session 8 — Production & Maklon Overhaul (IN PLANNING)

### Scope lengkap:
Lihat `/app/memory/PRODUCTION_MAKLON_DEVELOPMENT_PLAN.md`

### Key Changes:
- Maklon PO+Seri model baru (dewi_maklon_pos collection)
- Inventory ownership separation (cv_da vs maklon_client)
- Multi-dispatch per PO maklon dengan history
- Vendor CMT Portal standalone (/vendor-cmt)
- Finance integration maklon → AR/AP GL posting
- BOM Maklon dynamic (estimasi + aktual)
- Online Order fulfillment bridge ke inventory FG
- Cutting WIP tracking → inventory movement

---

## Prioritized Backlog

### P0 — Harus dikerjakan
- Phase 1: Data model foundation (Maklon PO, Inventory ownership, RnD separation)
- Phase 3: Portal Maklon revamp (PO+Seri, dispatch, material klien)
- Phase 4: Finance maklon integration (AR/AP GL)

### P1 — Penting
- AccountCard di MarketingDashboard: "Lihat Dashboard" masih console.log → belum navigate ke akun detail
- Revenue Chart di MarketingDashboard: chart masih agregat semua akun, belum bisa filter per-akun
- Halaman detail per-akun (klik akun → lihat semua data: sales history, orders, health, KOL, LiveHost)

### P2 — Nice to have
- Tambah platform baru selain Shopee/TikTok/Tokopedia (Lazada, Blibli)
- Search bar di AccountManagement module
- SalesPerformanceDashboard: tambah filter by specific account (bukan hanya platform)
- Bulk actions di AccountManagement

### Future / Backlog
- Evaluasi modul-modul yang belum dipakai atau ada duplikasi
- LiveHostModule.jsx (2300+ baris) — refactor ke sub-components
- CommunicationHubPortal & AssetManagementPortal juga sudah besar

---

## Key Files
- `/app/frontend/src/hooks/useActiveMarketingAccount.js` — localStorage hook
- `/app/frontend/src/components/erp/marketing/AccountBadge.jsx` — platform badge component
- `/app/frontend/src/components/erp/marketing/ActiveAccountBar.jsx` — account switcher bar
- `/app/frontend/src/components/erp/SalesDataEntryModule.jsx` — updated
- `/app/frontend/src/components/erp/KOLCreatorModule.jsx` — updated
- `/app/frontend/src/components/erp/marketing/LiveHostModule.jsx` — updated
- `/app/backend/routes/marketing.py` — account CRUD + health score
- `/app/backend/routes/marketing_kol.py` — KOL + creator endpoints
- `/app/backend/routes/marketing_livehost.py` — LiveHost endpoints

## Test Credentials
- admin@garment.com / Admin@123
