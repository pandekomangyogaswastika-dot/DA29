import { useState, useEffect, useCallback, useRef, useMemo, Suspense } from 'react';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/theme/ThemeToggle';
import { CommandPalette } from './CommandPalette';
import { NotificationBell } from './NotificationBell';
import ModuleHelpDrawer from './userGuide/ModuleHelpDrawer';
import ModuleTour from './userGuide/ModuleTour';
import UserGuideDialog from './userGuide/UserGuideDialog';
import { ProductionUIProvider } from '@/contexts/ProductionUIContext';
import ProductionWizardModule from './ProductionWizardModule';
import QuickInputPanel from './QuickInputPanel';
import ProductionInputFAB from './ProductionInputFAB';
import ErrorBoundary from '../ErrorBoundary';
import MobileBottomNav from './MobileBottomNav';
import {
  Search, X, ChevronLeft, ChevronDown, Menu, LogOut, Command as CommandIcon,
  HelpCircle, Sun,
  // Dashboards
  LayoutDashboard, Gauge, LineChart, Warehouse, UserCog,
  // Management / Admin
  TrendingUp, FileSpreadsheet, Shirt, UserCircle2, Users, ShieldCheck,
  KeyRound, History, Building2, FileCog, BookOpen, UserPlus, GraduationCap, Palette,
  // Production operational
  LayoutGrid, CalendarClock, ClipboardList, ClipboardSignature, Boxes,
  Hammer, UserCheck, Activity, BarChart4, Siren, AlertTriangle, Truck, Tv2, Zap,
  ClipboardPen, Package, CalendarDays, CalendarCheck,
  // Production process stages
  Cable, Link2, Scissors, ClipboardCheck, Droplets, PackageOpen, RotateCcw, Waves, Paintbrush,
  // Production master
  Map, Workflow, Timer, Wrench, Factory, HardHat, Ruler, ListTree, BookMarked,
  // Warehouse
  Archive, PackageMinus, PackagePlus, ArrowRightLeft, MapPin, Sparkles, Lock, Award, Send,
  // Finance — Accounting Core
  FolderTree, BookCheck, Scale, Book, CalendarRange, Settings2,
  FileText, Hourglass, Wallet,
  // Finance — Operasional
  ReceiptText, Landmark, Receipt, PieChart, Calculator, HandCoins, Files,
  CreditCard, FilePlus, Banknote, BarChart3, Shield, ShieldAlert,
  // HR
  Clock, Contact, Calendar, Briefcase,
  // AI & Self
  Brain, Target, UserCircle, CheckSquare, Settings,
  // New portals (Maklon + Toko)
  Star, MessageSquare, ShoppingCart, Bell, Store, Scan,
  // Phase 5 — Catalog + Marketing (Week 4-7)
  Layers, ShoppingBag, AlertCircle, HeartPulse, MousePointer, Video,
  // Phase 3 Week 8-10 — Content Calendar, Discounts, Product Launch
  Tag, Rocket,
  // Phase 3 Week 13 — Fitur Internal
  ThumbsUp, PackageSearch, PackageCheck,
  // Session 12 — AI Content Tools & KOL Leaderboard
  Trophy, Image as ImageIcon,
  // Session 15 — HR AI & Portal Saya Extensions
  FileSearch, TrendingDown, Lightbulb, FileText as FileTextIcon, Eye, MessageSquare as MessageSquareIcon,
  // IA Improvements - Box icon for headers
  Box,
  // Session 26 — Portal RnD icons
  FlaskConical, TestTube, Beaker,
  // Session 28 — LiveHost Management icon
  Radio
} from 'lucide-react';

// Portal labels shown as badge next to brand (top-left). Click brand to go back to selector.
const PORTAL_LABEL = {
  management: 'Manajemen',
  production:  'Produksi',
  warehouse:   'Gudang',
  finance:     'Keuangan',
  hr:          'SDM / HRIS',
  maklon:      'Maklon',
  toko:        'Marketing',
  rnd:         'RnD & Desain',
  self:        'Portal Saya',
  collaboration: 'Portal Kolaborasi',  // NEW: Communication + Workspace + Learning
  assets:      'Manajemen Aset',
};

// ── CV. Dewi Aditya · Portal-specific navigation ──────────────────────────
// Rules:
//   - Bahasa Indonesia untuk label menu (istilah teknis dipertahankan jika tidak ada padanan).
//   - Setiap ikon UNIK agar mudah dibedakan secara visual (rule from UX audit).
//   - Tidak ada moduleId duplikat antar portal (enforced by registry).
//   - Sections mendukung dua mode:
//       { items: [...] }  — list datar (default)
//       { groups: [{label, items}, ...] }  — dikelompokkan dengan sub-header di sidebar
//
// Navigation Refinement Phase 1:
//   - mgmt-products DIHAPUS dari Manajemen (redirect ke prod-models-bom)
//   - wh-material-reservation DIHAPUS dari Gudang (redirect ke prod-material-reservation)
//   - Production: Dashboard digabung (OEE+LineBalance+Rework+APS → tabs dalam prod-dashboard)
//   - Production: Model+BOM+Sizes → prod-models-bom (satu modul bertab)
//   - Production: QUALITY & ANALYTICS digabung ke MONITORING & ANALYTICS
//   - Production: TV Section dihapus dari nav → dipindah ke footer sidebar
//
// Navigation Refinement Phase 2:
//   - Rename: EKSEKUSI → OPERASIONAL HARIAN
//   - Rename: prod-employees → 'Operator & Skill Matrix'
//   - Rename: prod-bulk-mi → 'Material Issue (Bulk)'
//   - Rename: wh-material-issue → 'Material Issue (Single)'
//   - Rename: hr-employees → 'Data Karyawan & Kontrak'
//   - Tambah: mgmt-integrations (API Keys) di SISTEM
const PORTAL_NAV = {
  management: {
    title: 'Manajemen',
    sections: [
      {
        label: 'RINGKASAN',
        items: [
          { id: 'management-dashboard',  label: 'Dashboard Eksekutif',     icon: LayoutDashboard },
          { id: 'mgmt-overview',         label: 'Ringkasan Bisnis',        icon: TrendingUp },
          { id: 'phase7-reports',        label: 'Laporan & Dashboard (Maklon/CMT)', icon: BarChart3, badge: 'BARU' },
          { id: 'mgmt-reports',          label: 'Laporan',                 icon: FileSpreadsheet },
          { id: 'mgmt-rahaza-customers', label: 'Data Pelanggan',          icon: UserCircle2 },
          { id: 'rnd-dashboard',         label: 'Portal RnD (Shortcut)',   icon: FlaskConical, badge: 'PORTAL' },
        ]
      },
      {
        label: 'SISTEM',
        items: [
          { id: 'mgmt-users',        label: 'Manajemen Pengguna',   icon: Users },
          { id: 'mgmt-roles',        label: 'Manajemen Peran',       icon: Shield },
          { id: 'mgmt-role-matrix',  label: 'Matriks Hak Akses',    icon: KeyRound },
          { id: 'mgmt-activity',     label: 'Log Aktivitas',         icon: History },
          { id: 'mgmt-company',      label: 'Pengaturan Perusahaan', icon: Building2 },
          { id: 'mgmt-pdf',          label: 'Konfigurasi PDF',       icon: FileCog },
          { id: 'mgmt-integrations', label: 'Integrasi & API Keys',  icon: Zap },
          { id: 'mgmt-help',         label: 'Panduan Penggunaan',    icon: BookOpen },
        ]
      },
      {
        label: 'TOOLS & DIGEST',
        items: [
          { id: 'mgmt-tools',           label: 'Weekly Digest & Audit',   icon: BarChart3,  badge: 'BARU' },
          { id: 'ai-business-dashboard',label: 'AI Business Intelligence', icon: Brain,      badge: 'AI' },
          { id: 'mgmt-okr',             label: 'Strategic OKR Tracker',   icon: Target,     badge: 'BARU' },
          { id: 'ai-usage-monitor',     label: 'AI Usage Monitor',        icon: Activity,   badge: 'BARU' },
        ]
      },
    ]
  },

  production: {
    title: 'Produksi',
    sections: [
      {
        label: 'OPERASIONAL HARIAN',
        groups: [
          {
            label: '📊 Dashboard & Pengiriman',
            items: [
              { id: 'production-dashboard', label: 'Dashboard Produksi',           icon: Gauge },
              { id: 'prod-shipments',       label: 'Pengiriman (Surat Jalan)',      icon: Truck },
            ]
          },
          {
            label: '⚡ Quick Actions',
            items: [
              { id: 'prod-wizard',   label: 'Production Wizard',     icon: Zap },
              { id: 'prod-bulk-mi',  label: 'Material Issue (Bulk)',  icon: ClipboardPen },
            ]
          },
          {
            label: '📋 Order & Penjadwalan',
            items: [
              { id: 'prod-orders',               label: 'Order Produksi',      icon: ClipboardList },
              { id: 'prod-work-orders',           label: 'Work Order',          icon: ClipboardSignature },
              { id: 'prod-bundles',               label: 'Penelusuran Bundle',  icon: Boxes },
              { id: 'prod-material-reservation',  label: 'Reservasi Material',  icon: Lock },
            ]
          },
          {
            label: '🏭 Eksekusi Lantai Produksi',
            items: [
              { id: 'prod-cutting',        label: 'Proses Cutting',       icon: Scissors },
              { id: 'prod-assignments',    label: 'Assign Lini Hari Ini', icon: UserCheck },
              { id: 'prod-shift-handover', label: 'Serah Terima Shift',   icon: Package },
              { id: 'prod-rework-board',   label: 'Papan Rework',         icon: Hammer },
            ]
          },
        ]
      },
      {
        label: 'PROSES INTI (5 TAHAP)',
        groups: [
          {
            label: 'Tahap Produksi',
            items: [
              { id: 'prod-exec-cutting',   label: '1 · Cutting',    icon: Scissors },
              { id: 'prod-exec-sewing',    label: '2 · Jahit (CMT)', icon: Link2 },
              { id: 'prod-exec-finishing', label: '3 · Finishing',   icon: Droplets },
              { id: 'prod-exec-qc',        label: '4 · QC Final',    icon: ClipboardCheck },
              { id: 'prod-exec-packing',   label: '5 · Packing',     icon: PackageOpen },
            ]
          },
          {
            label: 'CMT & Sub-Proses',
            items: [
              { id: 'prod-cmt',                              label: 'Manajemen CMT',       icon: Factory },
              { id: 'prod-cmt-packing',                     label: 'Packing & Opname CMT', icon: PackageCheck, badge: 'BARU' },
              { id: 'production-cmt-component-requests',    label: 'Kekurangan Komponen',  icon: PackageSearch, badge: 'BARU' },
              { id: 'prod-exec-rework',                     label: 'Rework / Revisi',      icon: RotateCcw },
            ]
          },
        ]
      },
      {
        label: 'MONITORING & ANALYTICS',
        groups: [
          {
            label: 'Real-time',
            items: [
              { id: 'prod-line-board',     label: 'Papan Lini Real-time', icon: LayoutGrid },
              { id: 'prod-andon-board',    label: 'Papan Andon',          icon: AlertTriangle },
              { id: 'prod-alert-settings', label: 'Pengaturan Alert',     icon: Siren },
            ]
          },
          {
            label: 'Quality Analytics',
            items: [
              { id: 'prod-pareto',         label: 'Pareto Cacat',           icon: BarChart3 },
              { id: 'prod-fpy',            label: 'First Pass Yield (FPY)', icon: Target },
              { id: 'prod-aql-calculator', label: 'AQL Sampling Tool',      icon: Shield },
            ]
          },
          {
            label: 'Performance & AI',
            items: [
              { id: 'prod-downtime',                label: 'Log Downtime Mesin',     icon: Activity },
              { id: 'prod-backlog',                 label: 'Backlog & Forecast',     icon: TrendingUp },
              { id: 'prod-ai-insights',             label: 'AI Insights & Chatbot',  icon: Brain },
              { id: 'ai-actions',                   label: 'AI Action Items',        icon: CheckSquare },
              { id: 'prod-predictive-maintenance',  label: 'Predictive Maintenance', icon: Wrench, badge: 'BARU' },
            ]
          },
        ]
      },
      {
        label: 'MASTER DATA',
        groups: [
          {
            label: '📍 Lokasi & Workspace',
            items: [
              { id: 'prod-locations', label: 'Gedung & Zona',       icon: Map },
              { id: 'prod-lines',     label: 'Lini Produksi',       icon: Factory },
              { id: 'prod-machines',  label: 'Mesin Jahit/Cutting', icon: Wrench },
              { id: 'prod-shifts',    label: 'Shift Kerja',         icon: Timer },
            ]
          },
          {
            label: '📐 Proses & Standar',
            items: [
              { id: 'prod-processes',           label: 'Proses Produksi',    icon: Workflow },
              { id: 'prod-sop',                 label: 'SOP Produksi',       icon: BookMarked },
              { id: 'prod-defect-codes',        label: 'Master Kode Cacat',  icon: ShieldAlert },
              { id: 'prod-production-calendar', label: 'Kalender Produksi',  icon: CalendarDays },
            ]
          },
          {
            label: '👕 Produk & Tim',
            items: [
              { id: 'prod-models-bom', label: 'Master Produk & BOM',    icon: Shirt },
              { id: 'prod-employees',  label: 'Operator & Skill Matrix', icon: HardHat },
            ]
          },
        ]
      },
    ]
  },

  warehouse: {
    title: 'Gudang',
    sections: [
      {
        label: 'INVENTORI',
        items: [
          { id: 'warehouse-dashboard', label: 'Dashboard Gudang', icon: Warehouse },
          { id: 'inv-materials-header',   label: '📦 Bahan Baku & Material',  icon: Box,      isHeader: true },
          { id: 'wh-materials',           label: 'Master Material',           icon: Boxes,    indent: 1 },
          { id: 'wh-stock',               label: 'Stok & Pergerakan',         icon: Archive,  indent: 1 },
          { id: 'wh-material-issue',      label: 'Material Issue',            icon: PackageMinus, indent: 1 },
          { id: 'inv-accessories-header', label: '✨ Aksesoris & Finishing',  icon: Sparkles, isHeader: true },
          { id: 'wh-accessory-master',    label: 'Master Aksesoris',          icon: Boxes,    indent: 1 },
          { id: 'wh-accessory-stock',     label: 'Stok & Pergerakan',         icon: Archive,  indent: 1 },
          { id: 'inv-fg-header',          label: '👕 Produk Jadi (FG)',       icon: Package,  isHeader: true },
          { id: 'wh-fg',                  label: 'Inventory & Pergerakan FG', icon: Archive,  indent: 1 },
          { id: 'unified-inventory',      label: 'Unified Inventory Viewer',  icon: Boxes,    badge: 'BARU' },
        ]
      },
      {
        label: 'OPERASIONAL GUDANG',
        items: [
          { id: 'wh-purchase-orders',           label: 'Purchase Order (PO)',             icon: FileText },
          { id: 'wh-receiving',                 label: 'Penerimaan Barang (GRN)',         icon: PackagePlus },
          { id: 'do-management',                label: 'Delivery Orders (DO/Surat Jalan)', icon: Truck,         badge: 'BARU' },
          { id: 'fulfillment',                  label: 'Fulfillment (Order → FG Out)',    icon: Send,          badge: 'BARU' },
          { id: 'wh-supplier-scorecard',        label: 'Supplier Scorecard & AQL',       icon: Award,        badge: 'BARU' },
          { id: 'wh-putaway',                   label: 'Put-Away',                        icon: ArrowRightLeft },
          { id: 'wh-picklist',                  label: 'Pick List',                       icon: ClipboardList, badge: 'BARU' },
          { id: 'wh-opname',                    label: 'Stok Opname',                    icon: ClipboardCheck },
          { id: 'wh-bin',                        label: 'Lokasi / Bin',                   icon: MapPin },
          { id: 'wh-accessory-ops',             label: 'Transaksi Aksesoris',            icon: Sparkles },
          { id: 'warehouse-accessory-requests', label: 'Inbox Request Aksesoris (RnD)', icon: PackageSearch, badge: 'BARU' },
          { id: 'wh-returns',                   label: 'Return & Refund',                icon: RotateCcw,    badge: 'BARU' },
          { id: 'warehouse-smart',              label: 'Alert, Reorder & Undo',          icon: AlertTriangle, badge: 'BARU' },
        ]
      },
      {
        label: 'GARMENT WMS (ADVANCED)',
        items: [
          { id: 'wms',                label: 'WMS Scanner (Barcode)',   icon: Scan,      badge: 'BARU' },
          { id: 'wms-fabric-rolls',   label: 'Fabric Roll Tracking',   icon: Package,   badge: 'P0' },
          { id: 'wms-delivery-notes', label: 'Surat Jalan',            icon: FileText,  badge: 'P0' },
          { id: 'wms-cmt-dispatches', label: 'CMT Material Dispatch',  icon: Truck,     badge: 'P1' },
          { id: 'wms-opname-enhanced',label: 'Opname Enhanced (AI)',   icon: BarChart3, badge: 'P1' },
        ]
      },
    ]
  },

  finance: {
    title: 'Keuangan',
    sections: [
      {
        label: 'TRANSAKSI (AR & AP)',
        groups: [
          {
            label: '📥 Piutang (AR)',
            items: [
              { id: 'finance-dashboard', label: 'Dashboard Keuangan',    icon: LineChart },
              { id: 'fin-ar-invoices',   label: 'Invoice Penjualan (AR)', icon: ReceiptText },
              { id: 'fin-ar',            label: 'Daftar Piutang',         icon: HandCoins },
              { id: 'fin-invoices',      label: 'Rekap Invoice',          icon: Files },
            ]
          },
          {
            label: '📤 Hutang (AP)',
            items: [
              { id: 'fin-ap',             label: 'Hutang Vendor',       icon: CreditCard },
              { id: 'fin-manual-invoice', label: 'Invoice Manual',      icon: FilePlus },
              { id: 'fin-approval',       label: 'Persetujuan Invoice',  icon: ShieldAlert },
            ]
          },
        ]
      },
      {
        label: 'KAS & PEMBAYARAN',
        items: [
          { id: 'fin-cash',        label: 'Kas & Bank',              icon: Landmark },
          { id: 'fin-bank-recon',  label: 'Rekonsiliasi Bank',       icon: ArrowRightLeft },
          { id: 'fin-ai-cashflow', label: 'AI Cash Flow Prediction', icon: Brain },
          { id: 'fin-payments',    label: 'Pembayaran',              icon: Banknote },
          { id: 'fin-expenses',    label: 'Pengeluaran',             icon: Receipt },
        ]
      },
      {
        label: 'AKUNTANSI & LAPORAN',
        groups: [
          {
            label: 'Biaya & HPP',
            items: [
              { id: 'fin-cost-centers', label: 'Pusat Biaya',    icon: PieChart },
              { id: 'fin-hpp',          label: 'HPP / Costing',  icon: Calculator },
              { id: 'fin-recap',        label: 'Rekap Keuangan', icon: BarChart3 },
            ]
          },
          {
            label: 'Master & Jurnal',
            items: [
              { id: 'fin-coa',              label: 'Bagan Akun (COA)',  icon: FolderTree },
              { id: 'fin-journal-entry',    label: 'Jurnal Umum',       icon: BookCheck },
              { id: 'fin-journal-list',     label: 'Daftar Jurnal',     icon: FileText },
              { id: 'fin-posting-profiles', label: 'Profil Posting GL', icon: Settings2 },
              { id: 'fin-periods',          label: 'Periode Akuntansi', icon: CalendarRange },
            ]
          },
          {
            label: 'Laporan Keuangan',
            items: [
              { id: 'fin-trial-balance',  label: 'Neraca Saldo (TB)', icon: Scale },
              { id: 'fin-general-ledger', label: 'Buku Besar (GL)',   icon: Book },
              { id: 'fin-pnl',            label: 'Laba Rugi (P&L)',   icon: TrendingUp },
              { id: 'fin-balance-sheet',  label: 'Neraca',            icon: BarChart3 },
            ]
          },
          {
            label: 'Arus Kas, Aging & Aset',
            items: [
              { id: 'fin-cash-flow',   label: 'Laporan Arus Kas',         icon: Wallet },
              { id: 'fin-ap-aging',    label: 'Aging Hutang (AP)',         icon: Hourglass },
              { id: 'fin-budget',      label: 'Anggaran (Budget)',         icon: PieChart,   badge: 'BARU' },
              { id: 'fin-fixed-assets',label: 'Aset Tetap & Depresiasi',  icon: Package,    badge: 'BARU' },
            ]
          },
        ]
      },
    ]
  },

  hr: {
    title: 'SDM',
    sections: [
      {
        label: 'KARYAWAN & ORGANISASI',
        items: [
          { id: 'hr-dashboard',  label: 'Dashboard SDM',           icon: UserCog },
          { id: 'hr-employees',  label: 'Data Karyawan & Kontrak', icon: Users },
          { id: 'hr-org-chart',  label: 'Struktur Organisasi',     icon: LayoutGrid },
          { id: 'hr-assets',     label: 'Aset Karyawan',           icon: Package },
          { id: 'hr-admin',      label: 'HR Admin & Seed',         icon: Settings,   badge: 'BARU' },
        ]
      },
      {
        label: 'REKRUTMEN & TALENT',
        items: [
          { id: 'recruitment-process-header', label: '📋 Proses Rekrutmen',      icon: UserPlus,       isHeader: true },
          { id: 'hr-recruitment',             label: 'Job Posting & ATS',        icon: FileText,       indent: 1 },
          { id: 'hr-resume-screening',        label: 'AI Resume Screening',      icon: FileSearch,     badge: 'AI', indent: 1 },
          { id: 'onboarding-header',          label: '👋 Onboarding',            icon: ClipboardCheck, isHeader: true },
          { id: 'hr-onboarding',              label: 'Onboarding Checklist',     icon: ClipboardCheck, indent: 1 },
          { id: 'career-header',              label: '💼 Career Development',    icon: Briefcase,      isHeader: true },
          { id: 'hr-job-board',               label: 'Internal Job Board',       icon: Briefcase,      badge: 'BARU', indent: 1 },
        ]
      },
      {
        label: 'KEHADIRAN & SHIFT',
        items: [
          { id: 'attendance-header',      label: '⏰ Absensi & Clock In/Out', icon: Clock,       isHeader: true },
          { id: 'hr-attendance',          label: 'Absensi Harian (Manual)',  icon: Clock,       indent: 1 },
          { id: 'hr-auto-attendance',     label: 'Absen Otomatis',           icon: Scan,        badge: 'BARU', indent: 1 },
          { id: 'hr-attendance-approval', label: 'Approval Absen',           icon: CheckSquare, badge: 'BARU', indent: 1 },
          { id: 'shift-header',           label: '📅 Shift & Jadwal Kerja',  icon: Calendar,    isHeader: true },
          { id: 'hr-shift-scheduler',     label: 'Auto Shift Scheduler',     icon: Calendar,    badge: 'BARU', indent: 1 },
          { id: 'overtime-header',        label: '🌙 Lembur & Overtime',     icon: Hourglass,   isHeader: true },
          { id: 'hr-overtime',            label: 'Request Lembur',           icon: Hourglass,   badge: 'BARU', indent: 1 },
          { id: 'leave-header',           label: '🏖️ Cuti & Izin',          icon: Calendar,    isHeader: true },
          { id: 'hr-leave',               label: 'Izin & Cuti',              icon: Calendar,    indent: 1 },
          { id: 'hr-leave-balances',      label: 'Saldo Cuti',               icon: CalendarDays, badge: 'BARU', indent: 1 },
        ]
      },
      {
        label: 'KINERJA & PENGEMBANGAN',
        items: [
          { id: 'kpi-header',      label: '🎯 KPI & Goal Setting',    icon: Target,       isHeader: true },
          { id: 'hr-kpi',          label: 'KPI Bulanan (Operasional)', icon: Target,       indent: 1 },
          { id: 'review-header',   label: '📊 Performance Review',    icon: TrendingUp,   isHeader: true },
          { id: 'hr-performance',  label: 'Annual Review (Tahunan)',  icon: TrendingUp,   indent: 1 },
          { id: 'hr-360-feedback', label: '360° Feedback',            icon: MessageSquare, badge: 'BARU', indent: 1 },
          { id: 'learning-header', label: '📚 Learning & Development', icon: GraduationCap, isHeader: true },
          { id: 'hr-lms',          label: 'Learning Management',      icon: GraduationCap, indent: 1 },
        ]
      },
      {
        label: 'PENGGAJIAN',
        items: [
          { id: 'hr-payroll-profiles',   label: 'Profil Gaji Karyawan',     icon: Contact },
          { id: 'hr-payroll-allowances', label: 'Tunjangan Tetap',          icon: HandCoins },
          { id: 'hr-salary-adjustments', label: 'Kenaikan Gaji (Approval)', icon: TrendingUp, badge: 'BARU' },
          { id: 'hr-payroll-run',        label: 'Penggajian & Slip',        icon: Banknote },
        ]
      },
      {
        label: 'AI-POWERED HR & LAPORAN',
        items: [
          { id: 'ai-insights-header', label: '📊 AI Insights & Analytics', icon: Brain,        isHeader: true },
          { id: 'hr-ai-insights',     label: 'HR Dashboard dengan AI',     icon: Brain,        indent: 1 },
          { id: 'hr-attrition',       label: 'Predictive Attrition',       icon: TrendingDown, badge: 'AI', indent: 1 },
          { id: 'hr-skill-gap',       label: 'Skill Gap Analysis',         icon: Target,       badge: 'BARU', indent: 1 },
          { id: 'ai-tools-header',    label: '🤖 AI Tools',                icon: Lightbulb,    isHeader: true },
          { id: 'hr-coaching',        label: 'Performance Coaching AI',    icon: Lightbulb,    badge: 'AI', indent: 1 },
          { id: 'ai-actions-header',  label: '⚡ Action Items',            icon: CheckSquare,  isHeader: true },
          { id: 'ai-actions',         label: 'Automated Recommendations',  icon: CheckSquare,  indent: 1 },
          { id: 'hr-reports',         label: 'Laporan & Analitik SDM',     icon: BarChart3 },
        ]
      },
    ]
  },

  rnd: {
    title: 'RnD & Desain',
    sections: [
      {
        label: 'STYLE & SAMPLING',
        items: [
          { id: 'rnd-dashboard',           label: 'Dashboard RnD',              icon: LayoutDashboard },
          { id: 'rnd-styles',              label: 'Style & Tech Pack',           icon: Palette },
          { id: 'rnd-variants',            label: 'Varian Produk (Color/Size)',  icon: Layers,      badge: 'BARU' },
          { id: 'rnd-samples',             label: 'Sample Requests',             icon: FlaskConical },
          { id: 'rnd-revisions',           label: 'Revisi & Approval',           icon: ClipboardCheck },
          { id: 'rnd-accessory-requests',  label: 'Request Aksesoris',           icon: Package,     badge: 'BARU' },
        ]
      },
      {
        label: 'MATERIAL, POLA & MARKING',
        items: [
          { id: 'rnd-materials', label: 'Material Research',         icon: Beaker },
          { id: 'rnd-patterns',  label: 'Dokumentasi Pola & Marking', icon: Ruler, badge: 'BARU' },
        ]
      },
      {
        label: 'TECH PACK, COSTING & AI',
        items: [
          { id: 'rnd-techpack',           label: 'Tech Pack Manager',       icon: FileText,  badge: 'BARU' },
          { id: 'rnd-costing',            label: 'Sample Costing',          icon: Calculator },
          { id: 'rnd-hpp',                label: 'HPP Calculator',          icon: TrendingUp, badge: 'BARU' },
          { id: 'rnd-analytics',          label: 'RnD Analytics',           icon: BarChart3 },
          { id: 'rnd-kreator-requests',   label: 'Approve Kreator Request', icon: Users,     badge: 'BARU' },
        ]
      },
    ]
  },

  self: {
    title: 'Portal Saya',
    sections: [
      {
        label: 'PROFIL & KEHADIRAN',
        items: [
          { id: 'portal-dashboard', label: 'Dashboard Saya',    icon: LayoutDashboard },
          { id: 'portal-profile',   label: 'Profil Saya',       icon: UserCircle },
          { id: 'self-dashboard',   label: 'Kehadiran Saya',    icon: Clock },
          { id: 'portal-cuti',      label: 'Cuti & Lembur',     icon: Calendar },
          { id: 'portal-notifikasi',label: 'Notifikasi Inbox',  icon: Bell },
        ]
      },
      {
        label: 'KOMPENSASI & KINERJA',
        items: [
          { id: 'portal-payslip',       label: 'Slip Gaji Saya',   icon: Banknote },
          { id: 'kpi-portal',           label: 'KPI Saya',         icon: Target },
          { id: 'portal-annual-review', label: 'My Annual Review', icon: Target, badge: 'BARU' },
        ]
      },
      {
        label: 'PENGEMBANGAN, KARIR & DOKUMEN',
        items: [
          { id: 'portal-training',      label: 'Training Saya',  icon: BookOpen },
          { id: 'portal-peer-feedback', label: 'Peer Feedback',  icon: MessageSquareIcon, badge: 'BARU' },
          { id: 'portal-career-coach',  label: 'AI Career Coach', icon: Brain,             badge: 'AI' },
          { id: 'portal-workspace',     label: 'My Workspace',   icon: Star,              badge: 'BARU' },
          { id: 'portal-documents',     label: 'Dokumen Saya',   icon: FileTextIcon,      badge: 'BARU' },
        ]
      },
    ]
  },

  maklon: {
    title: 'Maklon',
    sections: [
      {
        label: 'KLIEN & ORDER',
        items: [
          { id: 'maklon-dashboard', label: 'Dashboard Maklon',    icon: Package },
          { id: 'maklon-clients',   label: 'Data Klien Maklon',   icon: Users },
          { id: 'maklon-po',        label: 'PO Maklon (Baru)',    icon: ClipboardList, badge: 'NEW' },
          { id: 'maklon-orders',    label: 'Order Maklon (Lama)', icon: ClipboardList },
          { id: 'maklon-samples',   label: 'Sample Management',   icon: ClipboardCheck },
          { id: 'maklon-tracking',  label: 'Tracking Produksi',   icon: Activity },
        ]
      },
      {
        label: 'OPERASIONAL',
        items: [
          { id: 'maklon-cmt',     label: 'CMT Assignment',         icon: Factory },
          { id: 'cmt-progress',   label: 'Progress & DO',          icon: BarChart3, badge: 'NEW' },
          { id: 'maklon-qc',      label: 'QC & Reject',            icon: ClipboardCheck },
          { id: 'maklon-packing', label: 'Packing & Pengiriman',   icon: PackageOpen },
        ]
      },
      {
        label: 'KEUANGAN & ANALITIK',
        items: [
          { id: 'maklon-billing',       label: 'Invoice & Billing',       icon: Banknote },
          { id: 'maklon-hpp',           label: 'HPP Jasa Jahit',          icon: Target },
          { id: 'maklon-sla-dashboard', label: 'SLA Dashboard & Lead Time', icon: Target, badge: 'BARU' },
          { id: 'maklon-ai-quote',      label: 'AI Quote Generator',      icon: Sparkles, badge: 'AI' },
        ]
      },
      {
        label: 'PENGATURAN',
        items: [
          { id: 'maklon-notifications', label: 'Notification Center', icon: Bell },
          { id: 'maklon-config',        label: 'System Config',       icon: Settings2 },
        ]
      },
    ]
  },

  toko: {
    title: 'Marketing',
    sections: [
      {
        label: 'OPERASIONAL PENJUALAN',
        groups: [
          {
            label: '📊 Overview',
            items: [
              { id: 'marketing-overview', label: 'Marketing Overview', icon: LayoutDashboard },
            ]
          },
          {
            label: '💼 Multi-Channel Sales',
            items: [
              { id: 'marketing-accounts',   label: 'Manage Accounts',        icon: Store },
              { id: 'marketing-sales',      label: 'Input Sales Harian',     icon: TrendingUp },
              { id: 'marketing-import',     label: 'Universal Smart Import', icon: FileSpreadsheet },
              { id: 'marketing-orders',     label: 'Unified Orders',         icon: ShoppingBag },
              { id: 'marketing-complaints', label: 'Kelola Komplain',        icon: AlertCircle },
            ]
          },
          {
            label: '🏪 Marketplace & Katalog',
            items: [
              { id: 'marketing-catalog', label: 'Manajemen Katalog', icon: Layers },
              { id: 'toko-channels',     label: 'Channel Manager (Lama)',  icon: Cable },
              { id: 'toko-pricing',      label: 'Harga & Flashsale (Lama)', icon: Zap },
            ]
          },
          {
            label: '⭐ KOL & Creator',
            items: [
              { id: 'marketing-kol',              label: 'KOL & Creator Mgmt', icon: Star },
              { id: 'marketing-kreator-requests', label: 'Kreator Requests',   icon: Users, badge: 'BARU' },
              { id: 'marketing-livehost',         label: 'LiveHost Management', icon: Radio, badge: 'BARU' },
            ]
          },
          {
            label: '📅 Konten & Kampanye',
            items: [
              { id: 'marketing-content-calendar', label: 'Content Calendar',       icon: Calendar },
              { id: 'marketing-discounts',        label: 'Discount Campaign',      icon: Tag },
              { id: 'marketing-product-launches', label: 'Product Launch Manager', icon: Rocket },
            ]
          },
        ]
      },
      {
        label: 'ANALYTICS & AI',
        groups: [
          {
            label: '📊 Performa',
            items: [
              { id: 'marketing-health',      label: 'Account Health',    icon: HeartPulse },
              { id: 'marketing-performance', label: 'Sales Performance', icon: BarChart3 },
              { id: 'marketing-ads',         label: 'Ads Performance',   icon: MousePointer },
              { id: 'marketing-live',        label: 'Live Sessions',     icon: Video },
            ]
          },
          {
            label: '📋 Laporan PIC',
            items: [
              { id: 'marketing-daily-report',   label: 'Laporan Harian',   icon: CalendarCheck, badge: 'BARU' },
              { id: 'marketing-monthly-report', label: 'Laporan Bulanan',  icon: BarChart3,     badge: 'BARU' },
              { id: 'marketing-targets',        label: 'Target Bulanan',   icon: Target,        badge: 'BARU' },
            ]
          },
          {
            label: '🤖 AI Tools',
            items: [
              { id: 'marketing-ai-insights',     label: 'AI Marketing Insights', icon: Brain },
              { id: 'marketing-advanced-ai',     label: 'Advanced AI Features',  icon: Sparkles },
              { id: 'marketing-ai-content',      label: 'AI Content Generator',  icon: Sparkles, badge: 'AI' },
              { id: 'marketing-ai-image',        label: 'AI Image Generator',    icon: ImageIcon, badge: 'AI' },
              { id: 'marketing-kol-leaderboard', label: 'KOL Leaderboard',       icon: Trophy },
              { id: 'marketing-scheduler',       label: 'Scheduler & Otomasi',   icon: Timer },
            ]
          },
        ]
      },
      {
        label: 'TASK MANAGEMENT',
        items: [
          { id: 'marketing-tasks',     label: 'Kanban Board',   icon: LayoutGrid },
          { id: 'marketing-approvals', label: 'Approval Inbox', icon: ClipboardCheck },
          { id: 'marketing-templates', label: 'Task Templates', icon: FileCog },
        ]
      },
      {
        label: 'AFTER SALES & SUPPORT',
        items: [
          { id: 'marketing-reviews', label: 'Rating & Review Management', icon: ThumbsUp },
          { id: 'marketing-returns', label: 'Returns & Refunds Tracking', icon: RotateCcw },
          { id: 'marketing-samples', label: 'Database Pengiriman Sample', icon: PackageSearch },
        ]
      },
      {
        label: 'PENGATURAN',
        items: [
          { id: 'marketing-integration-settings', label: 'API Integration Settings', icon: Settings },
          { id: 'maklon-notifications',            label: 'Notifikasi & Provider',    icon: Bell },
        ]
      },
    ]
  },

  // ─── Portal Kolaborasi ─────────────────────────────────────────────────────
  // NEW: Unified Communication + Workspace + Learning
  collaboration: {
    title: 'Portal Kolaborasi',
    sections: [
      {
        label: 'KOLABORASI',
        items: [
          { id: 'collaboration',        label: 'Portal Kolaborasi',    icon: MessageSquare },
          { id: 'collab-workspace',     label: 'My Workspace (Spreadsheet)', icon: FileText, badge: 'BARU' },
        ]
      }
    ]
  },

  // ─── Portal Manajemen Aset ─────────────────────────────────────────────────
  assets: {
    title: 'Manajemen Aset',
    sections: [
      {
        label: 'ASET',
        items: [
          { id: 'asset-dashboard', label: 'Dashboard Aset',     icon: LayoutDashboard },
          { id: 'asset-list',      label: 'Daftar Aset',        icon: Package },
          { id: 'asset-procurement', label: 'Request Pengadaan', icon: ShoppingCart },
        ]
      }
    ]
  },
};

// Helper: apakah section mengandung moduleId (support items & groups)
function sectionContainsModule(section, moduleId) {
  if (!section) return false;
  if (section.items?.some(i => i.id === moduleId)) return true;
  if (section.groups?.some(g => g.items?.some(i => i.id === moduleId))) return true;
  return false;
}

// Helper: flatten section → list of items (menggabungkan groups)
function sectionFlatItems(section) {
  if (!section) return [];
  if (section.items?.length) return section.items;
  if (section.groups?.length) return section.groups.flatMap(g => g.items || []);
  return [];
}

// Helper: cari label menu berdasarkan currentModule (untuk topbar title)
export function findModuleLabel(portal, moduleId) {
  const nav = PORTAL_NAV[portal];
  if (!nav) return moduleId;
  for (const sec of nav.sections) {
    const all = sectionFlatItems(sec);
    const found = all.find(it => it.id === moduleId);
    if (found) return found.label;
  }
  return moduleId;
}

// ─── AccountMenuItem helper ────────────────────────────────────────────────
function AccountMenuItem({ icon: Icon, label, hint, onClick, testId }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-foreground/80 hover:text-foreground hover:bg-[var(--glass-bg-hover)] transition-colors duration-150"
      data-testid={testId}
    >
      <Icon className="w-4 h-4 shrink-0 text-foreground/50" />
      <span className="flex-1 text-left">{label}</span>
      {hint && <span className="text-[10px] text-foreground/30 font-mono">{hint}</span>}
    </button>
  );
}

export default function PortalShell({ portal, user, token, onBack, onLogout, onPortalChange, children, currentModule, onModuleChange }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourSteps, setTourSteps] = useState(null); // null = not active
  const [guideOpen, setGuideOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false); // account dropdown
  const searchRef = useRef(null);
  const searchTimeout = useRef(null);
  const accountMenuRef = useRef(null);

  const nav = PORTAL_NAV[portal] || PORTAL_NAV.management;

  // ── Global module suggestions (semua portal) untuk Command Palette ──
  const moduleSuggestions = useMemo(() => {
    const out = [];
    Object.entries(PORTAL_NAV).forEach(([pid, p]) => {
      p.sections.forEach(sec => {
        const pushItem = (item, groupLabel = null) => {
          out.push({
            id: item.id,
            label: item.label,
            portal: PORTAL_LABEL[pid] || pid,
            portalId: pid,
            section: groupLabel ? `${sec.label} · ${groupLabel}` : sec.label,
            icon: item.icon,
          });
        };
        sec.items?.forEach(it => pushItem(it));
        sec.groups?.forEach(g => g.items?.forEach(it => pushItem(it, g.label)));
      });
    });
    return out;
  }, []);

  // ── Section-based nav (user's model): top pills = sections, left sidebar = items of active section ──
  const activeSectionIndex = Math.max(
    0,
    nav.sections.findIndex(s => sectionContainsModule(s, currentModule))
  );
  const activeSection = nav.sections[activeSectionIndex] || nav.sections[0];

  const handleSectionPillClick = (sectionLabel) => {
    const target = nav.sections.find(s => s.label === sectionLabel);
    if (!target) return;
    const firstItem = target.items?.[0] || target.groups?.[0]?.items?.[0];
    if (!firstItem) return;
    onModuleChange(firstItem.id);
    setMobileOpen(false);
  };

  // Close search on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setSearchOpen(false);
      }
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target)) {
        setAccountMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSearchInput = useCallback((q) => {
    setSearchQuery(q);
    if (!q.trim()) { setSearchResults([]); setSearchOpen(false); return; }
    setSearchOpen(true);
    clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await fetch(`/api/global-search?q=${encodeURIComponent(q)}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const data = await res.json();
        setSearchResults(data.results || []);
      } catch (e) {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, [token]);

  const handleSearchSelect = (result) => {
    onModuleChange(result.module);
    setSearchQuery('');
    setSearchResults([]);
    setSearchOpen(false);
  };

  // ── Render helper for sidebar nav item (uniform across flat items & grouped items)
  const renderNavItem = (item) => {
    // Handle header items (non-clickable category headers with emoji)
    if (item.isHeader) {
      if (collapsed) {
        // In collapsed mode, show just a separator
        return <div key={item.id} className="mx-2 my-2 h-px bg-[var(--glass-border)]" aria-hidden="true" />;
      }
      return (
        <div key={item.id} className="px-3 pt-3 pb-1.5 flex items-center gap-1.5" data-testid={`nav-header-${item.id}`}>
          <span className="text-[11px] font-semibold tracking-wide text-foreground/70">{item.label}</span>
        </div>
      );
    }
    
    const Icon = item.icon;
    const isActive = currentModule === item.id;
    const indentClass = item.indent ? `ml-${item.indent * 4}` : '';
    
    if (item.external && item.href) {
      if (collapsed) {
        return (
          <a
            key={item.id}
            href={item.href}
            target="_blank"
            rel="noopener noreferrer"
            className="relative w-full grid place-items-center h-10 rounded-xl transition-colors duration-150 text-foreground/60 hover:bg-[var(--glass-bg-hover)] hover:text-foreground"
            title={item.label}
            data-testid={`nav-item-${item.id}`}
          >
            <Icon className="w-4 h-4" />
          </a>
        );
      }
      return (
        <a
          key={item.id}
          href={item.href}
          target="_blank"
          rel="noopener noreferrer"
          className={`relative w-full flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition-[background-color,color] duration-150 text-foreground/60 hover:bg-[var(--glass-bg-hover)] hover:text-foreground/85 ${indentClass}`}
          data-testid={`nav-item-${item.id}`}
        >
          <Icon className="w-4 h-4 shrink-0" strokeWidth={2} />
          <span className="truncate">{item.label}</span>
          {item.badge && (
            <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]">
              {item.badge}
            </span>
          )}
        </a>
      );
    }
    if (collapsed) {
      return (
        <button
          key={item.id}
          onClick={() => { onModuleChange(item.id); setMobileOpen(false); }}
          className={`relative w-full grid place-items-center h-10 rounded-xl transition-colors duration-150
            ${isActive ? 'bg-[var(--nav-pill-active)] text-[hsl(var(--primary))]' : 'text-foreground/60 hover:bg-[var(--glass-bg-hover)] hover:text-foreground'}`}
          title={item.label}
          data-testid={`nav-item-${item.id}`}
        >
          {isActive && <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-full bg-[hsl(var(--primary))]" />}
          <Icon className="w-4 h-4" />
          {item.badge && (
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-[hsl(var(--primary))]" />
          )}
        </button>
      );
    }
    return (
      <button
        key={item.id}
        onClick={() => { onModuleChange(item.id); setMobileOpen(false); }}
        className={`relative w-full flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm
          transition-[background-color,color] duration-150 ease-[cubic-bezier(0.16,1,0.3,1)]
          ${isActive
            ? 'bg-[var(--nav-pill-active)] text-foreground'
            : 'text-foreground/60 hover:bg-[var(--glass-bg-hover)] hover:text-foreground/85'
          }
          ${indentClass}`}
        data-testid={`nav-item-${item.id}`}
      >
        {isActive && (
          <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-[hsl(var(--primary))]" aria-hidden="true" />
        )}
        <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[hsl(var(--primary))]' : ''}`} strokeWidth={2} />
        <span className="truncate">{item.label}</span>
        {item.badge && (
          <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]">
            {item.badge}
          </span>
        )}
      </button>
    );
  };

  // Wrap content with ProductionUIProvider if in production portal
  const contentWrapper = portal === 'production' ? (
    <ProductionUIProvider>
      <ErrorBoundary level="portal">
        {children}
      </ErrorBoundary>
      <ProductionInputFAB />
      <Suspense fallback={null}>
        <ProductionWizardModule token={token} isGlobalMount={true} />
        <QuickInputPanel token={token} />
      </Suspense>
    </ProductionUIProvider>
  ) : (
    <ErrorBoundary level="portal">
      {children}
    </ErrorBoundary>
  );

  return (
    <div className="flex flex-col h-screen" data-testid={`portal-shell-${portal}`}>
      {/* ╔═══════════════════════════════════════════════════════════════════╗
          ║  TOP BAR — Brand + Portal Badge + SECTION pills + Search + Theme   ║
          ╚═══════════════════════════════════════════════════════════════════╝ */}
      <header className="sticky top-0 z-40 border-b border-[var(--glass-border)] bg-[var(--card-surface)] backdrop-blur-[var(--glass-blur-strong)]">
        <div className="flex items-center gap-3 px-3 sm:px-5 py-2.5">
          {/* Mobile menu toggle */}
          <button
            className="md:hidden p-1.5 rounded-lg text-foreground/60 hover:text-foreground hover:bg-[var(--nav-pill-active)] transition-colors duration-150"
            onClick={() => setMobileOpen(true)}
            data-testid="mobile-menu-btn"
            aria-label="Buka menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Brand + Portal badge (click brand → back to portal selector) */}
          <button
            onClick={onBack}
            className="flex items-center gap-2.5 shrink-0 group transition-opacity duration-150 hover:opacity-80"
            data-testid="portal-back-btn"
            aria-label="Kembali ke pilih portal"
            title="Klik untuk ganti portal"
          >
            <div className="w-9 h-9 rounded-[12px] bg-gradient-to-br from-[hsl(var(--primary)/0.20)] to-[hsl(var(--accent)/0.20)] border border-[hsl(var(--primary)/0.30)] grid place-items-center text-[hsl(var(--primary))] group-hover:scale-105 transition-transform duration-150 shadow-[var(--shadow-glow-blue)]">
              {/* CV. Dewi Aditya — fashion brand mark (SVG inline) */}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M20.38 3.46 16 2 12 5.5 8 2 3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z" />
              </svg>
            </div>
            <div className="hidden md:flex flex-col leading-tight text-left">
              <span className="text-[10px] uppercase tracking-wider text-foreground/40 font-semibold">Portal</span>
              <span className="text-sm font-semibold text-foreground -mt-0.5">{PORTAL_LABEL[portal] || portal}</span>
            </div>
            <ChevronLeft className="hidden md:block w-3.5 h-3.5 text-foreground/30 ml-0.5 group-hover:text-foreground/60 transition-colors duration-150" />
          </button>

          {/* Section pill nav — THE MENU (sections of current portal) */}
          <nav
            className="hidden md:inline-flex items-center gap-1 rounded-full border border-[var(--glass-border)] bg-[var(--nav-pill-bg)] backdrop-blur-xl p-1 overflow-x-auto max-w-[55vw]"
            data-testid="section-pill-nav"
            aria-label="Menu portal"
          >
            {nav.sections.map((s, idx) => {
              const active = idx === activeSectionIndex;
              return (
                <button
                  key={s.label}
                  onClick={() => handleSectionPillClick(s.label)}
                  className={`relative inline-flex items-center gap-2 rounded-full px-3 lg:px-4 py-1.5 text-xs lg:text-sm font-medium whitespace-nowrap
                    transition-[background-color,color,box-shadow] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]
                    ${active
                      ? 'bg-[var(--nav-pill-active)] text-foreground shadow-[var(--shadow-glow-blue)]'
                      : 'text-foreground/60 hover:text-foreground hover:bg-[var(--nav-pill-active)]/60'
                    }`}
                  data-testid={`section-pill-${idx}`}
                  aria-pressed={active}
                  aria-label={`Menu ${s.label}`}
                >
                  <span className={active ? 'text-[hsl(var(--primary))]' : ''}>
                    {formatSectionLabel(s.label)}
                  </span>
                </button>
              );
            })}
          </nav>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Global Search */}
          <div ref={searchRef} className="relative hidden sm:block w-56 lg:w-72">
            <div className="flex items-center gap-2 border border-[var(--glass-border)] rounded-full px-3 py-1.5 bg-[var(--nav-pill-bg)] backdrop-blur-xl focus-within:border-[hsl(var(--primary)/0.4)] transition-colors duration-150">
              <Search className="w-3.5 h-3.5 text-foreground/40 shrink-0" />
              <input
                type="text"
                placeholder="Cari order, WO, SKU..."
                className="flex-1 bg-transparent text-xs text-foreground placeholder:text-foreground/40 focus:outline-none"
                value={searchQuery}
                onChange={e => handleSearchInput(e.target.value)}
                onFocus={() => searchQuery && setSearchOpen(true)}
                data-testid="topbar-global-search-input"
              />
              {searchQuery && (
                <button onClick={() => { setSearchQuery(''); setSearchResults([]); setSearchOpen(false); }} data-testid="search-clear-btn" aria-label="Bersihkan pencarian">
                  <X className="w-3.5 h-3.5 text-foreground/40 hover:text-foreground/70" />
                </button>
              )}
            </div>

            {searchOpen && (
              <div className="absolute top-full mt-1.5 left-0 right-0 rounded-[var(--radius-md)] border border-[var(--glass-border)] bg-[var(--popover-surface)] backdrop-blur-[var(--glass-blur-strong)] shadow-[var(--shadow-soft)] z-50 overflow-hidden">
                {searchLoading ? (
                  <div className="px-4 py-3 text-xs text-foreground/50 text-center">Mencari...</div>
                ) : searchResults.length === 0 ? (
                  <div className="px-4 py-3 text-xs text-foreground/40 text-center">Tidak ada hasil untuk "{searchQuery}"</div>
                ) : (
                  <div className="max-h-80 overflow-y-auto">
                    {searchResults.map((r, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSearchSelect(r)}
                        className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-[var(--glass-bg-hover)] text-left transition-colors duration-150 border-b border-[var(--glass-border)] last:border-0"
                        data-testid={`search-result-${idx}`}
                      >
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 bg-[var(--nav-pill-active)] text-foreground/70 uppercase">{r.type}</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">{r.label}</p>
                          {r.sub && <p className="text-[10px] text-foreground/50 truncate">{r.sub}</p>}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ── Right side: Notif + Account dropdown ── */}
          <div className="flex items-center gap-1.5 shrink-0">
            {/* Command Palette shortcut (keyboard only hint, small) */}
            <button
              onClick={() => setCmdkOpen(true)}
              className="hidden lg:inline-flex items-center gap-1.5 h-8 px-2.5 rounded-full border border-[var(--glass-border)] bg-[var(--nav-pill-bg)] text-foreground/50 hover:text-foreground hover:bg-[var(--nav-pill-active)] transition-colors duration-150"
              data-testid="topbar-cmdk-trigger"
              title="Command Palette (Ctrl/Cmd + K)"
              aria-label="Buka Command Palette"
            >
              <CommandIcon className="w-3 h-3" />
              <span className="text-[10px] font-semibold tracking-wider uppercase opacity-60">⌘K</span>
            </button>

            {/* Notification Bell */}
            <NotificationBell
              token={token}
              onNavigateModule={(moduleId) => { if (moduleId) onModuleChange(moduleId); }}
            />

            {/* ── Account Dropdown ── */}
            <div className="relative" ref={accountMenuRef}>
              <button
                onClick={() => setAccountMenuOpen(v => !v)}
                className="flex items-center gap-2 pl-1.5 pr-2.5 py-1 rounded-full border border-[var(--glass-border)] bg-[var(--nav-pill-bg)] hover:bg-[var(--nav-pill-active)] transition-colors duration-150 group"
                data-testid="topbar-account-btn"
                aria-label="Menu akun"
                aria-expanded={accountMenuOpen}
              >
                {/* Avatar */}
                <div className="w-7 h-7 rounded-full bg-[hsl(var(--primary)/0.15)] border border-[hsl(var(--primary)/0.25)] grid place-items-center text-[hsl(var(--primary))] text-xs font-bold shrink-0">
                  {user?.name?.[0]?.toUpperCase() || '?'}
                </div>
                {/* Name + role (hidden on sm) */}
                <div className="hidden md:flex flex-col leading-tight text-left">
                  <span className="text-xs font-medium text-foreground truncate max-w-[120px]">{user?.name || 'Pengguna'}</span>
                  <span className="text-[10px] text-foreground/50 capitalize">{user?.role || ''}</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-foreground/40 transition-transform duration-200 ${accountMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown panel */}
              {accountMenuOpen && (
                <div
                  className="absolute right-0 top-full mt-2 w-60 rounded-[var(--radius-lg)] border border-[var(--glass-border)] bg-[var(--popover-surface)] backdrop-blur-[var(--glass-blur-strong)] shadow-[var(--shadow-soft)] z-50 overflow-hidden"
                  data-testid="account-dropdown-menu"
                >
                  {/* User info header */}
                  <div className="px-4 py-3 border-b border-[var(--glass-border)]">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-[hsl(var(--primary)/0.15)] border border-[hsl(var(--primary)/0.25)] grid place-items-center text-[hsl(var(--primary))] text-sm font-bold shrink-0">
                        {user?.name?.[0]?.toUpperCase() || '?'}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-foreground truncate">{user?.name || 'Pengguna'}</p>
                        <p className="text-xs text-foreground/50 capitalize">{user?.role || ''}</p>
                      </div>
                    </div>
                  </div>

                  {/* Menu items */}
                  <div className="py-1.5">
                    {/* Command Palette */}
                    <AccountMenuItem
                      icon={CommandIcon}
                      label="Command Palette"
                      hint="⌘K"
                      onClick={() => { setAccountMenuOpen(false); setCmdkOpen(true); }}
                      testId="account-cmdk"
                    />
                    {/* Help */}
                    <AccountMenuItem
                      icon={HelpCircle}
                      label="Bantuan Modul"
                      onClick={() => { setAccountMenuOpen(false); setHelpOpen(true); }}
                      testId="account-help"
                    />
                    {/* Full Guide */}
                    <AccountMenuItem
                      icon={BookOpen}
                      label="Panduan Penggunaan"
                      onClick={() => { setAccountMenuOpen(false); setGuideOpen(true); }}
                      testId="account-guide"
                    />
                  </div>

                  {/* Theme toggle row */}
                  <div className="px-3 py-2 border-t border-[var(--glass-border)] flex items-center justify-between">
                    <span className="text-xs text-foreground/60 flex items-center gap-2">
                      <Sun className="w-3.5 h-3.5" />
                      Tema tampilan
                    </span>
                    <ThemeToggle />
                  </div>

                  {/* Logout */}
                  <div className="py-1.5 border-t border-[var(--glass-border)]">
                    <button
                      onClick={() => { setAccountMenuOpen(false); onLogout(); }}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors duration-150"
                      data-testid="topbar-logout-btn"
                    >
                      <LogOut className="w-4 h-4 shrink-0" />
                      Keluar
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ╔═══════════════════════════════════════════════════════════════════╗
          ║  BODY — Side Nav (items of active section) + Main Content         ║
          ╚═══════════════════════════════════════════════════════════════════╝ */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Sidebar — flat list of items belonging to ACTIVE section */}
        <aside
          className={`${collapsed ? 'md:w-[72px]' : 'md:w-[240px]'}
            fixed md:static inset-y-0 left-0 z-30 w-[260px]
            transition-[width,transform] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
            ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
          data-testid="portal-sidebar"
        >
          <div className="h-full flex flex-col bg-[var(--card-surface)] backdrop-blur-[var(--glass-blur-strong)] border-r border-[var(--glass-border)]">
            {/* Sidebar header: active section name + collapse toggle */}
            <div className="px-3 py-3 flex items-center justify-between border-b border-[var(--glass-border)]">
              {!collapsed && (
                <div className="flex items-center gap-2 min-w-0 px-1">
                  <div className="w-1 h-4 rounded-full bg-[hsl(var(--primary))] shrink-0" />
                  <span className="text-[11px] font-semibold tracking-wider text-foreground/70 uppercase truncate" data-testid="sidebar-active-section">
                    {formatSectionLabel(activeSection?.label || '')}
                  </span>
                </div>
              )}
              <button
                onClick={() => setCollapsed(!collapsed)}
                className="hidden md:grid place-items-center h-7 w-7 rounded-lg text-foreground/50 hover:text-foreground hover:bg-[var(--nav-pill-active)] transition-colors duration-150"
                data-testid="sidebar-toggle-btn"
                aria-label={collapsed ? 'Perluas menu' : 'Ciutkan menu'}
              >
                <Menu className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setMobileOpen(false)}
                className="md:hidden grid place-items-center h-7 w-7 rounded-lg text-foreground/50 hover:text-foreground hover:bg-[var(--nav-pill-active)]"
                aria-label="Tutup menu"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Mobile: show section dropdown at top of sidebar */}
            {mobileOpen && (
              <div className="md:hidden p-2 border-b border-[var(--glass-border)]">
                <select
                  value={activeSection?.label || ''}
                  onChange={e => handleSectionPillClick(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg border border-[var(--glass-border)] bg-[var(--input-surface)] text-xs text-foreground"
                  data-testid="mobile-section-select"
                >
                  {nav.sections.map(s => (
                    <option key={s.label} value={s.label}>{formatSectionLabel(s.label)}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Items (flat list OR grouped) of active section */}
            <nav className="flex-1 overflow-y-auto py-2 px-2" data-testid="sidebar-items">
              {activeSection?.groups?.length ? (
                <div className="space-y-3">
                  {activeSection.groups.map((g) => (
                    <div key={g.label}>
                      {!collapsed && (
                        <div className="px-3 pt-2 pb-1.5 flex items-center gap-1.5" data-testid={`sidebar-group-header-${g.label}`}>
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-foreground/40">{g.label}</span>
                          <div className="flex-1 h-px bg-[var(--glass-border)]" aria-hidden="true" />
                        </div>
                      )}
                      {collapsed && (
                        <div className="mx-2 my-1 h-px bg-[var(--glass-border)]" aria-hidden="true" />
                      )}
                      <div className="space-y-0.5">
                        {(g.items || []).map(renderNavItem)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-0.5">
                  {(activeSection?.items || []).map(renderNavItem)}
                  {(!activeSection?.items || activeSection.items.length === 0) && (
                    <div className="px-3 py-6 text-center text-xs text-foreground/40">Belum ada item di menu ini.</div>
                  )}
                </div>
              )}
            </nav>

            {/* Sidebar footer: Recent modules + TV link + breadcrumb */}
            {!collapsed && (
              <div className="px-3 py-2 border-t border-[var(--glass-border)] space-y-1">
                {/* Recent modules */}
                <RecentModulesFooter
                  portal={portal}
                  currentModule={currentModule}
                  onModuleChange={onModuleChange}
                />
                <p className="text-[10px] text-foreground/40 truncate" data-testid="topbar-module-title">
                  {findModuleLabel(portal, currentModule)}
                </p>
                {/* Phase 1.5: TV link moved from sidebar section to footer */}
                <a
                  href="/tv"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-[10px] text-foreground/40 hover:text-foreground/70 transition-colors duration-150 group"
                  data-testid="sidebar-tv-link"
                >
                  <Tv2 className="w-3 h-3 group-hover:text-[hsl(var(--primary))]" />
                  <span>Mode TV Lantai Produksi</span>
                </a>
              </div>
            )}
          </div>
        </aside>

        {/* Mobile overlay */}
        {mobileOpen && (
          <div
            className="fixed inset-0 bg-[var(--overlay-bg)] z-20 md:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Main content — add pb for mobile bottom nav on 'self' portal */}
        <main className={`flex-1 overflow-y-auto${portal === 'self' ? ' pb-14 md:pb-0' : ''}`}>
          <div className="max-w-[1400px] mx-auto p-4 sm:p-6">
            {contentWrapper}
          </div>
        </main>
      </div>

      {/* ── Mobile Bottom Nav \u2014 Portal Saya only \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 */}
      <MobileBottomNav
        portal={portal}
        currentModule={currentModule}
        onModuleChange={onModuleChange}
      />

      {/* ── Command Palette (Cmd+K) ─────────────────────────────────────── */}
      <CommandPalette
        open={cmdkOpen}
        onOpenChange={setCmdkOpen}
        currentPortal={portal}
        onSelectPortal={(pid) => { onPortalChange?.(pid); }}
        onSelectModule={(mid) => { onModuleChange?.(mid); }}
        onLogout={onLogout}
        moduleSuggestions={moduleSuggestions}
        token={token}
      />

      {/* ── Module Help Drawer (?) ──────────────────────────────────────── */}
      <ModuleHelpDrawer
        open={helpOpen}
        onOpenChange={setHelpOpen}
        moduleId={currentModule}
        onStartTour={(steps) => setTourSteps(steps)}
      />

      {/* ── Module Tour (interactive overlay) ───────────────────────────── */}
      {tourSteps && (
        <ModuleTour steps={tourSteps} onClose={() => setTourSteps(null)} />
      )}

      {/* ── Full User Guide Dialog (📖) ─────────────────────────────────── */}
      <UserGuideDialog open={guideOpen} onOpenChange={setGuideOpen} />
    </div>
  );
}

/* ── Recent Modules Footer \u2014 shows last 5 visited modules for quick nav \u2500\u2500\u2500 */
function RecentModulesFooter({ portal, currentModule, onModuleChange }) {
  const STORAGE_KEY = `erp_recent_${portal}`;
  const MAX = 5;

  const [recent, setRecent] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
    catch { return []; }
  });

  // Update recent list when module changes
  useEffect(() => {
    if (!currentModule) return;
    setRecent(prev => {
      const next = [currentModule, ...prev.filter(m => m !== currentModule)].slice(0, MAX);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentModule, portal]);

  // Show only those NOT currently active, max 4 items
  const shown = recent.filter(m => m !== currentModule).slice(0, 4);
  if (shown.length === 0) return null;

  return (
    <div className="mb-1">
      <p className="text-[10px] text-foreground/30 uppercase tracking-wider mb-1">Terakhir</p>
      <div className="space-y-0.5">
        {shown.map(modId => (
          <button
            key={modId}
            onClick={() => onModuleChange?.(modId)}
            className="w-full text-left px-2 py-1 rounded-md text-[11px] text-foreground/50 hover:text-foreground hover:bg-[var(--glass-bg-hover)] transition-colors duration-150 truncate"
            data-testid={`recent-module-${modId}`}
            title={modId}
          >
            {Object.keys(PORTAL_NAV).reduce((found, pid) => {
              if (found !== modId) return found;
              return findModuleLabel(pid, modId);
            }, modId)}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── helper: tampilkan label section lebih enak dibaca (ALL CAPS → Title Case),
   preserve akronim di dalam tanda kurung DAN daftar akronim terkenal ── */
const KNOWN_ACRONYMS = new Set(['HPP', 'AR', 'AP', 'SOP', 'BOM', 'OEE', 'QC', 'APS', 'KPI', 'ERP', 'TV', 'HR', 'WO']);
function formatSectionLabel(label) {
  if (!label) return '';
  return label
    .split(' ')
    .map(w => {
      if (!w) return '';
      // preserve acronyms within parens, e.g. (AR), (AP), (HPP), (F1)
      if (/^\(.+\)$/.test(w)) return w.toUpperCase();
      // preserve known acronyms (case-insensitive match)
      if (KNOWN_ACRONYMS.has(w.toUpperCase())) return w.toUpperCase();
      // everything else → Title Case (first letter upper, rest lower)
      return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
    })
    .join(' ');
}
