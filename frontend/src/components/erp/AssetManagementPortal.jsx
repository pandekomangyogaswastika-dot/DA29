/**
 * Asset Management Portal — CV. Dewi Aditya ERP
 * Manajemen aset perusahaan + Procurement Request (Request Pengadaan)
 * Terintegrasi dengan Finance (journal entries otomatis)
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { toast } from 'sonner';
import AssetScannerModal from './AssetScannerModal';
import {
  Package, Plus, Search, Filter, RefreshCw, ChevronRight,
  LayoutDashboard, Wrench, Tag, ShoppingCart, TrendingDown,
  CheckCircle2, Clock, AlertTriangle, XCircle, Eye,
  Building2, CalendarDays, User, DollarSign, ArrowRight,
  FileText, CheckCheck, Trash2, History, Cpu, Car, Monitor,
  Boxes, MoreVertical, Edit, Send, X, ChevronDown, ChevronUp,
  Banknote, PackageCheck, Activity, QrCode, Barcode, Printer, Download, Scan, Upload,
  // Session 28 — Utilization Report & PM Alerts
  Gauge, TrendingUp, Zap, ShieldAlert, Bell, BellOff, AlertCircle,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartTooltip,
  PieChart, Pie, Cell, ResponsiveContainer, Legend
} from 'recharts';

const API = process.env.REACT_APP_BACKEND_URL || '';

async function apicall(method, path, token, body) {
  const opts = {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(`${API}${path}`, opts);
  // Always read body once, even on error responses
  let data;
  try {
    data = await r.json();
  } catch {
    data = {};
  }
  if (!r.ok) {
    const msg = data?.detail || data?.message || `HTTP ${r.status}`;
    throw Object.assign(new Error(msg), { status: r.status, data });
  }
  return data;
}

function fmtCurrency(v) {
  if (!v && v !== 0) return '-';
  return 'Rp ' + Number(v).toLocaleString('id-ID');
}

function fmtDate(s) {
  if (!s) return '-';
  return new Date(s).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
}

const STATUS_CONFIG = {
  active:           { label: 'Aktif',        color: 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30' },
  in_maintenance:   { label: 'Pemeliharaan', color: 'bg-amber-500/15 text-amber-600 border-amber-500/30' },
  disposed:         { label: 'Dilepas',      color: 'bg-red-500/15 text-red-600 border-red-500/30' },
  under_repair:     { label: 'Perbaikan',    color: 'bg-blue-500/15 text-blue-600 border-blue-500/30' },
  pending_disposal: { label: 'Menunggu Disposal', color: 'bg-orange-500/15 text-orange-700 border-orange-500/30' },
};

const PR_STATUS_CONFIG = {
  draft: { label: 'Draft', color: 'bg-muted text-muted-foreground' },
  submitted: { label: 'Menunggu Dept', color: 'bg-amber-500/15 text-amber-600 border-amber-500/30' },
  dept_approved: { label: 'Menunggu Finance', color: 'bg-blue-500/15 text-blue-600 border-blue-500/30' },
  finance_approved: { label: 'Menunggu Final', color: 'bg-violet-500/15 text-violet-600 border-violet-500/30' },
  approved: { label: 'Disetujui', color: 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30' },
  in_procurement: { label: 'Sedang Pengadaan', color: 'bg-cyan-500/15 text-cyan-600 border-cyan-500/30' },
  completed: { label: 'Selesai', color: 'bg-emerald-700/15 text-emerald-700 border-emerald-700/30' },
  rejected: { label: 'Ditolak', color: 'bg-red-500/15 text-red-600 border-red-500/30' },
  cancelled: { label: 'Dibatalkan', color: 'bg-muted text-muted-foreground' },
};

const PIE_COLORS = ['#6366f1','#22d3ee','#f59e0b','#ef4444','#10b981','#8b5cf6','#f97316'];

// ── KPI Card ──────────────────────────────────────────────────────────────
function KPICard({ label, value, sub, icon: Icon, accent }) {
  const accents = {
    blue: 'from-blue-500/10 to-blue-600/5 border-blue-500/20',
    emerald: 'from-emerald-500/10 to-emerald-600/5 border-emerald-500/20',
    amber: 'from-amber-500/10 to-amber-600/5 border-amber-500/20',
    violet: 'from-violet-500/10 to-violet-600/5 border-violet-500/20',
  };
  const iconColors = { blue: 'text-blue-500', emerald: 'text-emerald-500', amber: 'text-amber-500', violet: 'text-violet-500' };
  return (
    <Card className={`bg-gradient-to-br ${accents[accent] || accents.blue} border`}>
      <CardContent className="pt-4 pb-3 px-4">
        <div className="flex items-start justify-between mb-1">
          <Icon size={18} className={iconColors[accent] || 'text-blue-500'} />
        </div>
        <div className="text-xl font-bold">{value}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  );
}

// ── StatusBadge ────────────────────────────────────────────────────────────
function StatusBadge({ status, configMap }) {
  const cfg = configMap[status] || { label: status, color: 'bg-muted text-muted-foreground' };
  return <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${cfg.color}`}>{cfg.label}</span>;
}

// ── EditCategoryDialog ────────────────────────────────────────────────────
function EditCategoryDialog({ open, onClose, token, category, onUpdated }) {
  const [form, setForm] = useState({
    name: '', code: '', useful_life_years: 5, depr_method: 'straight_line',
    coa_asset_account: '', coa_depreciation_account: '',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (category) {
      setForm({
        name: category.name || '',
        code: category.code || '',
        useful_life_years: category.useful_life_years || 5,
        depr_method: category.depr_method || 'straight_line',
        coa_asset_account: category.coa_asset_account || '',
        coa_depreciation_account: category.coa_depreciation_account || '',
      });
    }
  }, [category]);

  const set = (k, v) => setForm(p => ({...p, [k]: v}));

  const submit = async () => {
    if (!form.name.trim()) { toast.error('Nama kategori wajib diisi'); return; }
    setLoading(true);
    try {
      const data = await apicall('PUT', `/api/assets/categories/${category.id}`, token, form);
      if (data.ok) {
        toast.success('Kategori berhasil diupdate');
        onUpdated();
        onClose();
      } else {
        toast.error(data.detail || 'Gagal update kategori');
      }
    } catch { toast.error('Gagal update kategori'); }
    finally { setLoading(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>Edit Kategori Aset</DialogTitle></DialogHeader>
        <div className="space-y-3 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Nama Kategori *</label>
              <Input placeholder="Peralatan IT" value={form.name}
                onChange={e => set('name', e.target.value)} className="mt-1" data-testid="cat-name-input" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Kode</label>
              <Input placeholder="IT" value={form.code}
                onChange={e => set('code', e.target.value)} className="mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Umur Manfaat (tahun)</label>
              <Input type="number" value={form.useful_life_years}
                onChange={e => set('useful_life_years', e.target.value)} className="mt-1" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Metode Depresiasi</label>
              <Select value={form.depr_method} onValueChange={v => set('depr_method', v)}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="straight_line">Garis Lurus</SelectItem>
                  <SelectItem value="double_declining">Saldo Menurun</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Separator className="my-3" />
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Mapping Chart of Accounts (COA)</p>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Akun COA Aset</label>
            <Input placeholder="Contoh: 1500 - Aset Tetap" value={form.coa_asset_account}
              onChange={e => set('coa_asset_account', e.target.value)} className="mt-1" data-testid="coa-asset-input" />
            <p className="text-[10px] text-muted-foreground mt-1">Akun untuk mencatat pembelian aset kategori ini</p>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Akun COA Depresiasi</label>
            <Input placeholder="Contoh: 1590 - Akumulasi Depresiasi" value={form.coa_depreciation_account}
              onChange={e => set('coa_depreciation_account', e.target.value)} className="mt-1" data-testid="coa-depr-input" />
            <p className="text-[10px] text-muted-foreground mt-1">Akun untuk mencatat akumulasi depresiasi</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button onClick={submit} disabled={loading} data-testid="save-category-btn">
            {loading ? 'Menyimpan...' : 'Simpan Perubahan'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── TransferAssetDialog ────────────────────────────────────────────────────
function TransferAssetDialog({ open, onClose, token, asset, onTransferred }) {
  const [form, setForm] = useState({
    to_location: '', to_department: '', to_employee_id: '', to_employee_name: '', reason: '', notes: '',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (asset) {
      setForm({
        to_location: asset.location || '',
        to_department: asset.department || '',
        to_employee_id: asset.assigned_to_id || '',
        to_employee_name: asset.assigned_to_name || '',
        reason: '', notes: '',
      });
    }
  }, [asset]);

  const set = (k, v) => setForm(p => ({...p, [k]: v}));

  const submit = async () => {
    if (!form.to_location.trim() && !form.to_department.trim() && !form.to_employee_id.trim()) {
      toast.error('Minimal 1 field harus diisi (lokasi/departemen/employee)');
      return;
    }
    setLoading(true);
    try {
      const data = await apicall('POST', `/api/assets/${asset.id}/transfer`, token, form);
      if (data.ok) {
        toast.success('Asset berhasil ditransfer');
        onTransferred();
        onClose();
      } else {
        toast.error(data.detail || 'Gagal transfer asset');
      }
    } catch { toast.error('Gagal transfer asset'); }
    finally { setLoading(false); }
  };

  if (!asset) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Transfer Asset</DialogTitle>
          <p className="text-sm text-muted-foreground">
            {asset.asset_number} - {asset.name}
          </p>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="bg-muted/40 rounded-lg p-3 space-y-2 text-sm">
            <p className="text-xs font-semibold text-muted-foreground uppercase">Lokasi Saat Ini</p>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div><span className="text-muted-foreground">Lokasi:</span> {asset.location || '-'}</div>
              <div><span className="text-muted-foreground">Dept:</span> {asset.department || '-'}</div>
              <div><span className="text-muted-foreground">Assigned:</span> {asset.assigned_to_name || '-'}</div>
            </div>
          </div>
          <Separator />
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Transfer Ke</p>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Lokasi Baru</label>
            <Input placeholder="Rak A-12, Gudang Utama..." value={form.to_location}
              onChange={e => set('to_location', e.target.value)} className="mt-1" data-testid="transfer-location-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Departemen Baru</label>
            <Input placeholder="Produksi, IT, Finance..." value={form.to_department}
              onChange={e => set('to_department', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Assign ke Employee (ID)</label>
            <Input placeholder="Employee ID" value={form.to_employee_id}
              onChange={e => set('to_employee_id', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Nama Employee</label>
            <Input placeholder="Nama lengkap" value={form.to_employee_name}
              onChange={e => set('to_employee_name', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Alasan Transfer *</label>
            <Input placeholder="Relokasi departemen, penugasan baru..." value={form.reason}
              onChange={e => set('reason', e.target.value)} className="mt-1" data-testid="transfer-reason-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Catatan (opsional)</label>
            <Input placeholder="Catatan tambahan..." value={form.notes}
              onChange={e => set('notes', e.target.value)} className="mt-1" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button onClick={submit} disabled={loading} data-testid="submit-transfer-btn">
            {loading ? 'Mentransfer...' : 'Transfer Asset'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─────────────────────────────────────────────────────────────────
// BulkImportDialog — Upload CSV/Excel, preview, column mapping, import
// ─────────────────────────────────────────────────────────────────
function BulkImportDialog({ open, onClose, token, categories, onImported }) {
  const [step, setStep] = useState(1); // 1=upload, 2=mapping, 3=result
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState(null); // { columns, preview, total_rows }
  const [mapping, setMapping] = useState({});  // assetField → csvColumn
  const [categoryId, setCategoryId] = useState('');
  const [result, setResult] = useState(null);
  const [rawRows, setRawRows] = useState([]);
  const fileRef = useRef(null);

  const ASSET_FIELDS = [
    { key: 'name', label: 'Nama Aset*', required: true },
    { key: 'purchase_date', label: 'Tanggal Beli* (YYYY-MM-DD)', required: true },
    { key: 'purchase_cost', label: 'Harga Beli*', required: true },
    { key: 'useful_life_months', label: 'Masa Manfaat (bulan)' },
    { key: 'residual_value', label: 'Nilai Residu' },
    { key: 'serial_number', label: 'No. Seri' },
    { key: 'brand', label: 'Merek' },
    { key: 'model', label: 'Model' },
    { key: 'location', label: 'Lokasi' },
    { key: 'department', label: 'Departemen' },
    { key: 'notes', label: 'Catatan' },
    { key: 'warranty_expiry_date', label: 'Expired Garansi' },
    { key: 'warranty_provider', label: 'Provider Garansi' },
    { key: 'insurance_policy_number', label: 'No. Polis Asuransi' },
    { key: 'insurance_provider', label: 'Provider Asuransi' },
    { key: 'insurance_expiry_date', label: 'Expired Asuransi' },
    { key: 'insurance_value', label: 'Nilai Pertanggungan' },
  ];

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await fetch(`${API}/api/assets/bulk-import/preview`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Gagal parse file');
      setPreviewData(data);
      // Auto-map: try to match column names to asset fields
      const autoMap = {};
      ASSET_FIELDS.forEach(f => {
        const match = data.columns.find(c =>
          c.toLowerCase().replace(/[^a-z0-9]/g,'') === f.key.toLowerCase().replace(/[^a-z0-9]/g,'')
          || c.toLowerCase().includes(f.key.toLowerCase())
        );
        if (match) autoMap[f.key] = match;
      });
      setMapping(autoMap);
      setStep(2);
    } catch (err) {
      toast.error(err.message || 'Gagal upload file');
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!categoryId) { toast.error('Pilih kategori terlebih dahulu'); return; }
    if (!mapping.name || !mapping.purchase_date || !mapping.purchase_cost) {
      toast.error('Mapping kolom Name, Tanggal Beli, dan Harga Beli wajib diisi');
      return;
    }
    setLoading(true);
    try {
      // Build mapped rows from rawRows (all rows, not just preview)
      // Re-fetch raw data from previewData — we stored rawRows earlier
      const mappedRows = rawRows.map(row => {
        const mapped = {};
        Object.entries(mapping).forEach(([field, col]) => {
          if (col) mapped[field] = row[col] || '';
        });
        return mapped;
      });
      const r = await fetch(`${API}/api/assets/bulk-import/execute`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: mappedRows, category_id: categoryId }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || 'Gagal import');
      setResult(data);
      setStep(3);
      if (data.created_count > 0) onImported?.();
    } catch (err) {
      toast.error(err.message || 'Gagal import');
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = () => {
    const url = `${API}/api/assets/bulk-import/template`;
    const a = document.createElement('a');
    a.href = url;
    a.setAttribute('download', 'template_import_aset.xlsx');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const reset = () => {
    setStep(1); setPreviewData(null); setMapping({}); setCategoryId('');
    setResult(null); setRawRows([]);
    if (fileRef.current) fileRef.current.value = '';
  };

  // When previewData arrives, also fetch full raw rows for import execution
  useEffect(() => {
    if (previewData && fileRef.current?.files[0]) {
      const file = fileRef.current.files[0];
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          // We need to get all rows; re-use preview (which includes all via backend)
          // rawRows is set from a dedicated full-data endpoint — but we have preview for now
          // Actually our /preview endpoint returns total_rows but only 5 rows in preview
          // For the full import, we'll send the whole file again in handleImport
          // rawRows is not needed for the redesigned approach
        } catch {}
      };
      reader.readAsArrayBuffer(file);
    }
  }, [previewData]);

  // Override handleImport to re-upload file for full data
  const handleImportWithFile = async () => {
    if (!categoryId) { toast.error('Pilih kategori terlebih dahulu'); return; }
    const requiredMaps = ['name', 'purchase_date', 'purchase_cost'];
    if (requiredMaps.some(k => !mapping[k])) {
      toast.error('Mapping kolom Name, Tanggal Beli, dan Harga Beli wajib diisi');
      return;
    }
    const file = fileRef.current?.files[0];
    if (!file) { toast.error('File tidak ditemukan, ulangi upload'); return; }
    setLoading(true);
    try {
      // 1) Re-parse file on backend to get all rows
      const previewForm = new FormData();
      previewForm.append('file', file);
      const previewR = await fetch(`${API}/api/assets/bulk-import/preview`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: previewForm,
      });
      const previewFull = await previewR.json();
      // 2) Build mapped rows — but /preview only returns 5 rows for display
      //    For real import, we send the raw file + mapping to a unified endpoint
      //    Let's call execute with the file directly using FormData + mapping JSON
      const execForm = new FormData();
      execForm.append('file', file);
      execForm.append('mapping', JSON.stringify(mapping));
      execForm.append('category_id', categoryId);
      const execR = await fetch(`${API}/api/assets/bulk-import/execute-file`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: execForm,
      });
      const data = await execR.json();
      if (!execR.ok) throw new Error(data.detail || 'Gagal import');
      setResult(data);
      setStep(3);
      if (data.created_count > 0) onImported?.();
      toast.success(`✅ ${data.created_count} aset berhasil diimport`);
    } catch (err) {
      toast.error(err.message || 'Gagal import');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { reset(); onClose(); } }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload size={18} /> Bulk Import Aset dari CSV/Excel
          </DialogTitle>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="flex items-center gap-2 text-xs mb-2">
          {['Upload File', 'Column Mapping', 'Hasil'].map((s, i) => (
            <span key={s} className={`flex items-center gap-1 ${step === i+1 ? 'text-primary font-semibold' : step > i+1 ? 'text-emerald-600' : 'text-muted-foreground'}`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] border ${step === i+1 ? 'border-primary bg-primary text-primary-foreground' : step > i+1 ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-muted-foreground'}`}>{i+1}</span>
              {s}
              {i < 2 && <span className="text-muted-foreground ml-1">›</span>}
            </span>
          ))}
        </div>

        {/* Step 1: Upload */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="bg-muted/40 rounded-lg p-4 text-sm space-y-1">
              <p className="font-medium">Panduan:</p>
              <p className="text-muted-foreground">Upload file CSV atau Excel (.xlsx). Kolom wajib: <strong>Nama Aset, Tanggal Beli, Harga Beli</strong>.</p>
            </div>
            <Button variant="outline" className="w-full" onClick={downloadTemplate}>
              <Download size={14} className="mr-2" /> Download Template Excel
            </Button>
            <div
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-muted/20 transition-colors"
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={32} className="mx-auto text-muted-foreground mb-2" />
              <p className="text-sm font-medium">Klik untuk pilih file</p>
              <p className="text-xs text-muted-foreground mt-1">CSV atau Excel (.xlsx, .xls)</p>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={handleFileUpload}
            />
            {loading && <p className="text-xs text-muted-foreground text-center">Memproses file...</p>}
          </div>
        )}

        {/* Step 2: Mapping */}
        {step === 2 && previewData && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Total: <strong>{previewData.total_rows}</strong> baris ditemukan</span>
              <Button variant="ghost" size="sm" onClick={() => setStep(1)}>← Ganti File</Button>
            </div>
            {/* Preview table */}
            <div className="overflow-x-auto rounded border">
              <table className="w-full text-xs">
                <thead className="bg-muted/40">
                  <tr>{previewData.columns.map(c => <th key={c} className="px-2 py-1.5 text-left font-medium truncate max-w-[100px]">{c}</th>)}</tr>
                </thead>
                <tbody>
                  {previewData.preview.map((row, ri) => (
                    <tr key={ri} className="border-t">
                      {previewData.columns.map(c => <td key={c} className="px-2 py-1 truncate max-w-[100px]" title={row[c]}>{row[c] || '-'}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Category selector */}
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">Kategori Aset*</label>
              <Select value={categoryId} onValueChange={setCategoryId}>
                <SelectTrigger><SelectValue placeholder="Pilih kategori..." /></SelectTrigger>
                <SelectContent>
                  {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {/* Column mapping */}
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-2">Mapping Kolom</label>
              <div className="grid grid-cols-2 gap-2">
                {ASSET_FIELDS.map(f => (
                  <div key={f.key} className="flex items-center gap-2">
                    <span className="text-xs w-40 shrink-0">{f.label}</span>
                    <Select value={mapping[f.key] || '__none__'} onValueChange={v => setMapping(p => ({...p, [f.key]: v === '__none__' ? '' : v}))}>
                      <SelectTrigger className="h-7 text-xs"><SelectValue placeholder="- abaikan -" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">- abaikan -</SelectItem>
                        {previewData.columns.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setStep(1)}>Kembali</Button>
              <Button onClick={handleImportWithFile} disabled={loading}>
                {loading ? 'Mengimport...' : `Import ${previewData.total_rows} Aset`}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step 3: Result */}
        {step === 3 && result && (
          <div className="space-y-4 text-center py-4">
            <div className="text-4xl">{result.error_count === 0 ? '✅' : '⚠️'}</div>
            <p className="text-lg font-bold">Import Selesai</p>
            <div className="grid grid-cols-2 gap-3 max-w-xs mx-auto text-sm">
              <div className="bg-emerald-500/10 rounded-lg p-3">
                <p className="text-2xl font-bold text-emerald-600">{result.created_count}</p>
                <p className="text-xs text-muted-foreground">Berhasil diimport</p>
              </div>
              <div className="bg-destructive/10 rounded-lg p-3">
                <p className="text-2xl font-bold text-destructive">{result.error_count}</p>
                <p className="text-xs text-muted-foreground">Gagal</p>
              </div>
            </div>
            {result.errors?.length > 0 && (
              <div className="text-left bg-muted/40 rounded-lg p-3 space-y-1 max-h-32 overflow-y-auto">
                <p className="text-xs font-medium">Detail Error:</p>
                {result.errors.map((e, i) => (
                  <p key={i} className="text-xs text-destructive">Baris {e.row}: {e.error}</p>
                ))}
              </div>
            )}
            <div className="flex gap-2 justify-center">
              <Button variant="outline" onClick={() => { reset(); onClose(); }}>Tutup</Button>
              <Button onClick={() => { reset(); }}>Import Lagi</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}


// ─────────────────────────────────────────────────────────────────
// DisposalRequestDialog — Request disposal untuk aset bernilai tinggi
// ─────────────────────────────────────────────────────────────────
function DisposalRequestDialog({ open, onClose, token, asset, onRequested }) {
  const [form, setForm] = useState({
    disposal_date: new Date().toISOString().slice(0, 10),
    disposal_value: '',
    reason: '',
  });
  const [loading, setLoading] = useState(false);
  const set = (k, v) => setForm(p => ({...p, [k]: v}));
  const nbv = asset ? (parseFloat(asset.purchase_cost || 0) - parseFloat(asset.accumulated_depreciation || 0)) : 0;

  const submit = async () => {
    if (!form.reason.trim()) { toast.error('Alasan disposal wajib diisi'); return; }
    setLoading(true);
    try {
      const data = await apicall('POST', `/api/assets/${asset.id}/request-disposal`, token, form);
      if (data?.id) {
        toast.success('Permintaan disposal dikirim untuk approval');
        onRequested?.();
        onClose();
      } else {
        toast.error(data?.detail || 'Gagal kirim permintaan');
      }
    } catch { toast.error('Gagal kirim permintaan'); }
    finally { setLoading(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="text-amber-500">⚠️</span> Request Disposal Aset
          </DialogTitle>
        </DialogHeader>
        {asset && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-sm space-y-1">
            <p className="font-medium">{asset.name}</p>
            <p className="text-muted-foreground text-xs">{asset.asset_number} · NBV: <strong className="text-amber-700">{fmtCurrency(nbv)}</strong></p>
            <p className="text-xs text-amber-700">⚠️ Aset bernilai tinggi — memerlukan approval Finance/Admin sebelum dilepas.</p>
          </div>
        )}
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Tanggal Pelepasan</label>
            <Input type="date" value={form.disposal_date} onChange={e => set('disposal_date', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Nilai Penjualan (Rp, isi 0 jika dibuang)</label>
            <Input type="number" placeholder="0" value={form.disposal_value} onChange={e => set('disposal_value', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Alasan Disposal *</label>
            <textarea
              className="w-full border rounded-md px-3 py-2 text-sm mt-1 min-h-[80px] bg-background resize-none"
              placeholder="Rusak total, tidak ekonomis diperbaiki..."
              value={form.reason}
              onChange={e => set('reason', e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button onClick={submit} disabled={loading} className="bg-amber-600 hover:bg-amber-700 text-white">
            {loading ? 'Mengirim...' : 'Kirim Request'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ─────────────────────────────────────────────────────────────────
// DisposalApprovalInbox — List disposal requests untuk Admin/Finance/Manager
// ─────────────────────────────────────────────────────────────────
function DisposalApprovalInbox({ token, userRole, onRefresh }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState('pending');
  const [reviewDialog, setReviewDialog] = useState(null); // { req, action: 'approve'|'reject' }
  const [notes, setNotes] = useState('');
  const [processing, setProcessing] = useState(false);
  const canReview = ['admin','superadmin','finance','manager'].includes(userRole);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apicall('GET', `/api/assets/disposal-requests?status=${filterStatus}`, token);
      if (Array.isArray(data)) setRequests(data);
    } catch { toast.error('Gagal memuat permintaan disposal'); }
    finally { setLoading(false); }
  }, [token, filterStatus]);

  useEffect(() => { load(); }, [load]);

  const handleReview = async () => {
    if (!reviewDialog) return;
    const { req, action } = reviewDialog;
    if (!notes.trim() && action === 'reject') { toast.error('Catatan wajib diisi saat menolak'); return; }
    setProcessing(true);
    try {
      const data = await apicall('PATCH', `/api/assets/disposal-requests/${req.id}/${action}`, token, { notes });
      if (data?.ok !== undefined) {
        toast.success(action === 'approve' ? '✅ Disposal disetujui & jurnal dibuat' : '❌ Disposal ditolak');
        setReviewDialog(null); setNotes('');
        load(); onRefresh?.();
      } else {
        toast.error(data?.detail || 'Gagal proses');
      }
    } catch { toast.error('Gagal proses'); }
    finally { setProcessing(false); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <p className="text-sm font-semibold flex-1">Permintaan Disposal Aset</p>
        {['pending','approved','rejected','all'].map(s => (
          <button key={s} onClick={() => setFilterStatus(s)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${filterStatus === s ? 'bg-primary text-primary-foreground border-primary' : 'text-muted-foreground hover:text-foreground'}`}>
            {s === 'pending' ? 'Menunggu' : s === 'approved' ? 'Disetujui' : s === 'rejected' ? 'Ditolak' : 'Semua'}
          </button>
        ))}
        <Button variant="outline" size="sm" onClick={load}><RefreshCw size={14} /></Button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-muted-foreground text-sm">Memuat...</div>
      ) : requests.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          Tidak ada permintaan disposal {filterStatus !== 'all' ? `dengan status "${filterStatus === 'pending' ? 'menunggu' : filterStatus}"` : ''}
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map(req => (
            <Card key={req.id} className={`border-l-4 ${req.status === 'pending' ? 'border-l-amber-500' : req.status === 'approved' ? 'border-l-emerald-500' : 'border-l-red-500'}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-sm truncate">{req.asset_name}</p>
                      <span className="text-xs text-muted-foreground font-mono">{req.asset_number}</span>
                      <Badge variant={req.status === 'pending' ? 'outline' : req.status === 'approved' ? 'default' : 'destructive'} className="text-[10px] shrink-0">
                        {req.status === 'pending' ? 'Menunggu' : req.status === 'approved' ? 'Disetujui' : 'Ditolak'}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 mt-2 text-xs text-muted-foreground">
                      <span>NBV: <strong className="text-foreground">{fmtCurrency(req.nbv || 0)}</strong></span>
                      <span>Nilai Jual: <strong className="text-foreground">{fmtCurrency(req.disposal_value || 0)}</strong></span>
                      <span>Tanggal: {fmtDate(req.disposal_date)}</span>
                      <span>Diminta: {fmtDate(req.requested_at)}</span>
                    </div>
                    <p className="text-xs mt-1.5 text-foreground/80">"{req.reason}"</p>
                    <p className="text-xs text-muted-foreground mt-1">Oleh: {req.requested_by_name}</p>
                    {req.review_notes && (
                      <p className="text-xs mt-1 text-muted-foreground italic">Catatan reviewer: {req.review_notes}</p>
                    )}
                  </div>
                  {canReview && req.status === 'pending' && (
                    <div className="flex gap-2 shrink-0">
                      <Button size="sm" variant="outline"
                        className="text-destructive border-destructive/30 hover:bg-destructive/10"
                        onClick={() => { setReviewDialog({ req, action: 'reject' }); setNotes(''); }}
                        data-testid={`reject-disposal-${req.id}`}>
                        Tolak
                      </Button>
                      <Button size="sm"
                        className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        onClick={() => { setReviewDialog({ req, action: 'approve' }); setNotes(''); }}
                        data-testid={`approve-disposal-${req.id}`}>
                        Setujui
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Review Dialog */}
      {reviewDialog && (
        <Dialog open={!!reviewDialog} onOpenChange={() => setReviewDialog(null)}>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle>{reviewDialog.action === 'approve' ? '✅ Setujui Disposal' : '❌ Tolak Disposal'}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="bg-muted/40 rounded-lg p-3 text-xs space-y-1">
                <p className="font-medium">{reviewDialog.req.asset_name}</p>
                <p className="text-muted-foreground">NBV: {fmtCurrency(reviewDialog.req.nbv || 0)}</p>
              </div>
              {reviewDialog.action === 'approve' && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-2 text-xs text-amber-700">
                  ⚠️ Menyetujui akan <strong>langsung melepas aset</strong> dan membuat jurnal Finance.
                </div>
              )}
              <div>
                <label className="text-xs font-medium text-muted-foreground">
                  Catatan {reviewDialog.action === 'reject' ? '(wajib)' : '(opsional)'}
                </label>
                <textarea
                  className="w-full border rounded-md px-3 py-2 text-sm mt-1 min-h-[70px] bg-background resize-none"
                  placeholder={reviewDialog.action === 'approve' ? 'Catatan persetujuan...' : 'Alasan penolakan...'}
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setReviewDialog(null)}>Batal</Button>
              <Button
                onClick={handleReview}
                disabled={processing}
                className={reviewDialog.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-destructive hover:bg-destructive/90 text-destructive-foreground'}
              >
                {processing ? 'Memproses...' : reviewDialog.action === 'approve' ? 'Ya, Setujui' : 'Ya, Tolak'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}


// ── CreateAssetDialog ─────────────────────────────────────────────────────
function CreateAssetDialog({ open, onClose, token, categories, onCreated }) {
  const [form, setForm] = useState({
    name: '', category_id: '', purchase_date: new Date().toISOString().slice(0, 10),
    purchase_cost: '', residual_value: '', useful_life_months: '',
    serial_number: '', brand: '', model: '', location: '', department: '', notes: '',
    // Warranty
    warranty_expiry_date: '', warranty_provider: '', warranty_terms: '',
    // Insurance
    insurance_policy_number: '', insurance_provider: '', insurance_expiry_date: '', insurance_value: '',
  });
  const [loading, setLoading] = useState(false);
  const set = (k, v) => setForm(p => ({...p, [k]: v}));

  const submit = async () => {
    if (!form.name.trim()) { toast.error('Nama aset wajib diisi'); return; }
    if (!form.purchase_cost || Number(form.purchase_cost) <= 0) { toast.error('Harga beli harus > 0'); return; }
    setLoading(true);
    try {
      const data = await apicall('POST', '/api/assets', token, {
        ...form,
        purchase_cost: Number(form.purchase_cost),
        residual_value: form.residual_value ? Number(form.residual_value) : undefined,
        useful_life_months: form.useful_life_months ? Number(form.useful_life_months) : undefined,
      });
      if (data.id) {
        toast.success(`Aset ${data.asset_number} berhasil didaftarkan`);
        onCreated(data); onClose();
      } else {
        toast.error(data.detail || 'Gagal mendaftarkan aset');
      }
    } catch { toast.error('Gagal mendaftarkan aset'); }
    finally { setLoading(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Daftarkan Aset Baru</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3 py-2">
          <div className="col-span-2">
            <label className="text-xs font-medium text-muted-foreground">Nama Aset *</label>
            <Input placeholder="Laptop Dell XPS 13..." value={form.name}
              onChange={e => set('name', e.target.value)} className="mt-1" data-testid="asset-name-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Kategori</label>
            <Select value={form.category_id} onValueChange={v => set('category_id', v)}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Pilih kategori..." />
              </SelectTrigger>
              <SelectContent>
                {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Tanggal Beli *</label>
            <Input type="date" value={form.purchase_date}
              onChange={e => set('purchase_date', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Harga Beli (Rp) *</label>
            <Input type="number" placeholder="5000000" value={form.purchase_cost}
              onChange={e => set('purchase_cost', e.target.value)} className="mt-1" data-testid="asset-cost-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Nilai Residu (Rp)</label>
            <Input type="number" placeholder="Otomatis 5%" value={form.residual_value}
              onChange={e => set('residual_value', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Umur Manfaat (bulan)</label>
            <Input type="number" placeholder="Dari kategori" value={form.useful_life_months}
              onChange={e => set('useful_life_months', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">No. Seri</label>
            <Input placeholder="SN-XXXX" value={form.serial_number}
              onChange={e => set('serial_number', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Merek / Merk</label>
            <Input placeholder="Dell, Lenovo, dll" value={form.brand}
              onChange={e => set('brand', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Model</label>
            <Input placeholder="XPS 13 9310" value={form.model}
              onChange={e => set('model', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Lokasi</label>
            <Input placeholder="Ruang IT, Lantai 2" value={form.location}
              onChange={e => set('location', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Departemen</label>
            <Input placeholder="IT, Produksi, dll" value={form.department}
              onChange={e => set('department', e.target.value)} className="mt-1" />
          </div>
          <div className="col-span-2">
            <label className="text-xs font-medium text-muted-foreground">Catatan</label>
            <Input placeholder="Catatan tambahan..." value={form.notes}
              onChange={e => set('notes', e.target.value)} className="mt-1" />
          </div>

          {/* Warranty Section */}
          <div className="col-span-2 pt-2 border-t">
            <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">🛡️ Garansi (Opsional)</p>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Tanggal Expired Garansi</label>
            <Input type="date" value={form.warranty_expiry_date}
              onChange={e => set('warranty_expiry_date', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Provider Garansi</label>
            <Input placeholder="Dell Support, Astra, dll" value={form.warranty_provider}
              onChange={e => set('warranty_provider', e.target.value)} className="mt-1" />
          </div>
          <div className="col-span-2">
            <label className="text-xs font-medium text-muted-foreground">Syarat Garansi</label>
            <Input placeholder="On-site 3 tahun, sparepart gratis" value={form.warranty_terms}
              onChange={e => set('warranty_terms', e.target.value)} className="mt-1" />
          </div>

          {/* Insurance Section */}
          <div className="col-span-2 pt-2 border-t">
            <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">🔒 Asuransi (Opsional)</p>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">No. Polis Asuransi</label>
            <Input placeholder="POL-2026-XXXX" value={form.insurance_policy_number}
              onChange={e => set('insurance_policy_number', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Provider Asuransi</label>
            <Input placeholder="Jasindo, Asuransi Jaya, dll" value={form.insurance_provider}
              onChange={e => set('insurance_provider', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Tanggal Expired Asuransi</label>
            <Input type="date" value={form.insurance_expiry_date}
              onChange={e => set('insurance_expiry_date', e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Nilai Pertanggungan (Rp)</label>
            <Input type="number" placeholder="50000000" value={form.insurance_value}
              onChange={e => set('insurance_value', e.target.value)} className="mt-1" />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">*Journal pembelian akan dibuat otomatis sebagai draft.</p>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button onClick={submit} disabled={loading} data-testid="create-asset-submit">
            {loading ? 'Menyimpan...' : 'Daftarkan Aset'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── AssetDetailDrawer ─────────────────────────────────────────────────────
function AssetDetailDrawer({ asset, token, open, onClose, onRefresh, onTransferClick, onRequestDisposalClick }) {
  const [deprPeriod, setDeprPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [assignForm, setAssignForm] = useState({ user_id: '', user_name: '', notes: '' });
  const [maintForm, setMaintForm] = useState({ type: 'corrective', description: '', cost: '', performed_by: '', maintenance_date: new Date().toISOString().slice(0, 10), status: 'completed' });
  const [activeTab, setActiveTab] = useState('info');
  const [loading, setLoading] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [assignments, setAssignments] = useState([]);
  const [maintenance, setMaintenance] = useState([]);
  const photoInputRef = useRef(null);

  useEffect(() => {
    if (!open || !asset) return;
    apicall('GET', `/api/assets/${asset.id}/assignments`, token).then(d => setAssignments(Array.isArray(d) ? d : [])).catch(() => {});
    apicall('GET', `/api/assets/${asset.id}/maintenance`, token).then(d => setMaintenance(Array.isArray(d) ? d : [])).catch(() => {});
  }, [open, asset, token]);

  if (!asset) return null;

  const nbv = (asset.purchase_cost || 0) - (asset.accumulated_depreciation || 0);
  const deprPct = asset.purchase_cost > 0
    ? Math.min(100, Math.round(asset.accumulated_depreciation / asset.purchase_cost * 100))
    : 0;
  
  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.type.startsWith('image/')) {
      toast.error('File harus berupa gambar');
      return;
    }
    
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Ukuran foto maksimal 5 MB');
      return;
    }
    
    setUploadingPhoto(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`${API}/api/assets/${asset.id}/upload-photo`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });
      
      if (!res.ok) throw new Error('Upload gagal');
      
      const data = await res.json();
      toast.success('Foto asset berhasil diupload');
      onRefresh();
    } catch (err) {
      toast.error('Gagal upload foto');
    } finally {
      setUploadingPhoto(false);
      if (photoInputRef.current) photoInputRef.current.value = '';
    }
  };

  const postDepr = async () => {
    if (!deprPeriod) return;
    setLoading(true);
    try {
      const d = await apicall('POST', `/api/assets/${asset.id}/depreciate/${deprPeriod}`, token, {});
      if (d.id) {
        toast.success(`Depresiasi ${deprPeriod} diposting: ${d.amount?.toLocaleString('id-ID')}`);
        onRefresh(); onClose();
      } else toast.error(d.detail || 'Gagal posting depresiasi');
    } catch (e) { toast.error(e.message || 'Gagal'); }
    finally { setLoading(false); }
  };

  const assignAsset = async () => {
    if (!assignForm.user_id) { toast.error('User ID wajib diisi'); return; }
    setLoading(true);
    try {
      await apicall('POST', `/api/assets/${asset.id}/assign`, token, assignForm);
      toast.success('Aset berhasil ditugaskan');
      onRefresh();
    } catch { toast.error('Gagal menugaskan aset'); }
    finally { setLoading(false); }
  };

  const addMaintenance = async () => {
    if (!maintForm.description) { toast.error('Deskripsi wajib diisi'); return; }
    setLoading(true);
    try {
      await apicall('POST', `/api/assets/${asset.id}/maintenance`, token, {
        ...maintForm, cost: Number(maintForm.cost) || 0,
      });
      toast.success('Pemeliharaan berhasil dicatat');
      const d = await apicall('GET', `/api/assets/${asset.id}/maintenance`, token);
      setMaintenance(Array.isArray(d) ? d : []);
      setMaintForm({ type: 'corrective', description: '', cost: '', performed_by: '', maintenance_date: new Date().toISOString().slice(0, 10), status: 'completed' });
    } catch { toast.error('Gagal'); }
    finally { setLoading(false); }
  };

  const disposeAsset = async () => {
    if (!window.confirm(`Yakin ingin melepas aset ${asset.asset_number}?`)) return;
    setLoading(true);
    try {
      const d = await apicall('POST', `/api/assets/${asset.id}/dispose`, token, { disposal_date: new Date().toISOString().slice(0,10), disposal_value: 0, reason: 'Disposal' });
      if (d.ok) { toast.success('Aset berhasil dilepas'); onRefresh(); onClose(); }
      else toast.error(d.detail || 'Gagal');
    } catch { toast.error('Gagal'); }
    finally { setLoading(false); }
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:w-[520px] overflow-y-auto" side="right">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Package size={16} />
            <span className="truncate">{asset.name}</span>
          </SheetTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-mono">{asset.asset_number}</span>
            <StatusBadge status={asset.status} configMap={STATUS_CONFIG} />
          </div>
        </SheetHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
          <TabsList className="w-full">
            <TabsTrigger value="info" className="flex-1">Info</TabsTrigger>
            <TabsTrigger value="depr" className="flex-1">Depresiasi</TabsTrigger>
            <TabsTrigger value="assign" className="flex-1">Penugasan</TabsTrigger>
            <TabsTrigger value="maint" className="flex-1">Pemeliharaan</TabsTrigger>
          </TabsList>

          {/* Info Tab */}
          <TabsContent value="info" className="space-y-3 mt-3">
            {/* Photo Section */}
            <div className="bg-muted/40 rounded-lg p-3">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Foto Asset</p>
              {asset.photo_url ? (
                <div className="relative group">
                  <img
                    src={`${API}${asset.photo_url}`}
                    alt={asset.name}
                    className="w-full h-48 object-cover rounded-lg border"
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => photoInputRef.current?.click()}
                    disabled={uploadingPhoto}>
                    <Edit size={14} className="mr-1" /> Ganti Foto
                  </Button>
                </div>
              ) : (
                <div className="border-2 border-dashed rounded-lg p-6 text-center">
                  <Package size={32} className="mx-auto text-muted-foreground/40 mb-2" />
                  <p className="text-xs text-muted-foreground mb-2">Belum ada foto</p>
                  <Button size="sm" variant="outline" onClick={() => photoInputRef.current?.click()} disabled={uploadingPhoto}>
                    {uploadingPhoto ? 'Uploading...' : 'Upload Foto'}
                  </Button>
                </div>
              )}
              <input
                type="file"
                ref={photoInputRef}
                onChange={handlePhotoUpload}
                accept="image/*"
                className="hidden"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              {[
                ['Kategori', asset.category_name], ['Lokasi', asset.location || '-'],
                ['Departemen', asset.department || '-'], ['No. Seri', asset.serial_number || '-'],
                ['Merek', asset.brand || '-'], ['Model', asset.model || '-'],
                ['Tgl Beli', fmtDate(asset.purchase_date)], ['Ditugaskan ke', asset.assigned_to_name || '-'],
              ].map(([k, v]) => (
                <div key={k} className="bg-muted/40 rounded-lg p-2.5">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{k}</p>
                  <p className="text-sm font-medium mt-0.5 truncate">{v}</p>
                </div>
              ))}
            </div>
            <div className="bg-muted/40 rounded-lg p-3 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Harga Beli</span>
                <span className="font-semibold">{fmtCurrency(asset.purchase_cost)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Akum. Depresiasi</span>
                <span className="font-semibold text-amber-600">{fmtCurrency(asset.accumulated_depreciation)}</span>
              </div>
              <Separator />
              <div className="flex justify-between text-sm font-bold">
                <span>Nilai Buku (NBV)</span>
                <span className="text-emerald-600">{fmtCurrency(nbv)}</span>
              </div>
              <Progress value={deprPct} className="h-2" />
              <p className="text-xs text-muted-foreground text-right">{deprPct}% terdepresiasi</p>
            </div>
            
            {/* Barcode & QR Actions */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Label & Barcode</p>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm" className="w-full" onClick={() => {
                  const url = `${API}/api/assets/${asset.id}/barcode`;
                  window.open(url, '_blank');
                }} data-testid="view-barcode-btn">
                  <Barcode size={14} className="mr-1" /> Lihat Barcode
                </Button>
                <Button variant="outline" size="sm" className="w-full" onClick={() => {
                  const url = `${API}/api/assets/${asset.id}/qrcode`;
                  window.open(url, '_blank');
                }} data-testid="view-qr-btn">
                  <QrCode size={14} className="mr-1" /> Lihat QR Code
                </Button>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="flex-1" onClick={() => {
                  const url = `${API}/api/assets/${asset.id}/label-pdf?template=standard`;
                  window.open(url, '_blank');
                }} data-testid="print-label-standard-btn">
                  <Printer size={14} className="mr-1" /> Label Standard (90x50mm)
                </Button>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="flex-1" onClick={() => {
                  const url = `${API}/api/assets/${asset.id}/label-pdf?template=sticker`;
                  window.open(url, '_blank');
                }}>
                  <Printer size={14} className="mr-1" /> Sticker Kecil (50x25mm)
                </Button>
                <Button variant="outline" size="sm" className="flex-1" onClick={() => {
                  const url = `${API}/api/assets/${asset.id}/label-pdf?template=a4`;
                  window.open(url, '_blank');
                }}>
                  <Printer size={14} className="mr-1" /> A4 Full Page
                </Button>
              </div>
            </div>
            
            {asset.status !== 'disposed' && asset.status !== 'pending_disposal' && (
              <div className="space-y-2">
                <Button variant="outline" size="sm" className="w-full" onClick={() => {
                  if (onTransferClick) onTransferClick(asset);
                }} data-testid="transfer-asset-btn">
                  <ArrowRight size={14} className="mr-1" /> Transfer Asset
                </Button>
                {/* Disposal: high-value (NBV > 5jt) require approval, else direct */}
                {(() => {
                  const cost = parseFloat(asset.purchase_cost || 0);
                  const accum = parseFloat(asset.accumulated_depreciation || 0);
                  const nbv = cost - accum;
                  const THRESHOLD = 5_000_000;
                  if (nbv > THRESHOLD) {
                    return (
                      <Button variant="outline" size="sm" className="w-full border-amber-500/40 text-amber-600 hover:bg-amber-500/10"
                        onClick={() => onRequestDisposalClick?.(asset)}
                        data-testid="request-disposal-btn">
                        ⚠️ Request Disposal (Perlu Approval)
                      </Button>
                    );
                  }
                  return (
                    <Button variant="destructive" size="sm" className="w-full" onClick={disposeAsset} disabled={loading}
                      data-testid="dispose-asset-btn">
                      <Trash2 size={14} className="mr-1" /> Lepas Aset (Dispose)
                    </Button>
                  );
                })()}
              </div>
            )}
            {asset.status === 'pending_disposal' && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-700">
                <p className="font-semibold">⏳ Menunggu Approval Disposal</p>
                <p className="mt-0.5">Permintaan pelepasan aset sedang menunggu review dari Finance/Admin.</p>
              </div>
            )}

            {/* Warranty Section */}
            {(asset.warranty_expiry_date || asset.warranty_provider) && (
              <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3 space-y-1.5">
                <p className="text-xs font-semibold text-blue-600 flex items-center gap-1.5">🛡️ Garansi</p>
                {asset.warranty_expiry_date && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Expired</span>
                    <span className={`font-medium ${
                      new Date(asset.warranty_expiry_date) < new Date() ? 'text-destructive' :
                      new Date(asset.warranty_expiry_date) < new Date(Date.now() + 30*86400000) ? 'text-amber-600' :
                      'text-foreground'
                    }`}>{fmtDate(asset.warranty_expiry_date)}
                      {new Date(asset.warranty_expiry_date) < new Date() ? ' ⚠️ EXPIRED' :
                       new Date(asset.warranty_expiry_date) < new Date(Date.now() + 30*86400000) ? ' ⏰ <30 hari' : ''}
                    </span>
                  </div>
                )}
                {asset.warranty_provider && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Provider</span>
                    <span className="font-medium">{asset.warranty_provider}</span>
                  </div>
                )}
                {asset.warranty_terms && (
                  <p className="text-xs text-muted-foreground">{asset.warranty_terms}</p>
                )}
              </div>
            )}

            {/* Insurance Section */}
            {(asset.insurance_policy_number || asset.insurance_provider) && (
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3 space-y-1.5">
                <p className="text-xs font-semibold text-emerald-600 flex items-center gap-1.5">🔒 Asuransi</p>
                {asset.insurance_policy_number && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">No. Polis</span>
                    <span className="font-mono text-xs">{asset.insurance_policy_number}</span>
                  </div>
                )}
                {asset.insurance_provider && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Provider</span>
                    <span className="font-medium">{asset.insurance_provider}</span>
                  </div>
                )}
                {asset.insurance_expiry_date && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Expired</span>
                    <span className={`font-medium ${
                      new Date(asset.insurance_expiry_date) < new Date() ? 'text-destructive' :
                      new Date(asset.insurance_expiry_date) < new Date(Date.now() + 30*86400000) ? 'text-amber-600' :
                      'text-foreground'
                    }`}>{fmtDate(asset.insurance_expiry_date)}
                      {new Date(asset.insurance_expiry_date) < new Date() ? ' ⚠️ EXPIRED' :
                       new Date(asset.insurance_expiry_date) < new Date(Date.now() + 30*86400000) ? ' ⏰ <30 hari' : ''}
                    </span>
                  </div>
                )}
                {asset.insurance_value > 0 && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Nilai Pertanggungan</span>
                    <span className="font-medium">{fmtCurrency(asset.insurance_value)}</span>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          {/* Depreciation Tab */}
          <TabsContent value="depr" className="space-y-3 mt-3">
            <Card>
              <CardContent className="pt-4 space-y-3">
                <p className="text-sm font-medium">Posting Depresiasi Bulanan</p>
                <div className="flex gap-2">
                  <Input type="month" value={deprPeriod}
                    onChange={e => setDeprPeriod(e.target.value)} className="flex-1" />
                  <Button size="sm" onClick={postDepr} disabled={loading} data-testid="post-depr-btn">
                    Posting
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Depresiasi bulanan: <span className="font-semibold">{fmtCurrency(asset.monthly_depreciation)}</span>
                </p>
              </CardContent>
            </Card>
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Riwayat Depresiasi</p>
              {(asset.depreciation_history || []).length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">Belum ada posting depresiasi</p>
              ) : (
                <div className="space-y-1">
                  {(asset.depreciation_history || []).map(d => (
                    <div key={d.id} className="flex items-center justify-between py-2 px-3 bg-muted/40 rounded-lg text-sm">
                      <span className="font-mono text-xs">{d.period}</span>
                      <span className="text-amber-600">{fmtCurrency(d.amount)}</span>
                      <span className="text-xs text-muted-foreground">{fmtCurrency(d.cumulative)} total</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* Assignment Tab */}
          <TabsContent value="assign" className="space-y-3 mt-3">
            {asset.assigned_to_id ? (
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3">
                <p className="text-xs text-emerald-600 font-medium">Sedang Ditugaskan</p>
                <p className="text-sm font-semibold">{asset.assigned_to_name}</p>
                <Button variant="outline" size="sm" className="mt-2" onClick={async () => {
                  await apicall('POST', `/api/assets/${asset.id}/unassign`, token, {});
                  toast.success('Aset dikembalikan'); onRefresh();
                }}>Kembalikan Aset</Button>
              </div>
            ) : (
              <Card>
                <CardContent className="pt-4 space-y-2">
                  <p className="text-sm font-medium">Tugaskan ke Karyawan</p>
                  <Input placeholder="ID Karyawan" value={assignForm.user_id}
                    onChange={e => setAssignForm(p => ({...p, user_id: e.target.value}))} />
                  <Input placeholder="Nama Karyawan" value={assignForm.user_name}
                    onChange={e => setAssignForm(p => ({...p, user_name: e.target.value}))} />
                  <Input placeholder="Catatan (opsional)" value={assignForm.notes}
                    onChange={e => setAssignForm(p => ({...p, notes: e.target.value}))} />
                  <Button size="sm" className="w-full" onClick={assignAsset} disabled={loading}>Tugaskan</Button>
                </CardContent>
              </Card>
            )}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Riwayat Penugasan</p>
              <div className="space-y-1">
                {assignments.map(a => (
                  <div key={a.id} className="flex items-center justify-between py-2 px-3 bg-muted/40 rounded-lg text-sm">
                    <span>{a.assigned_to_name}</span>
                    <span className="text-xs text-muted-foreground">{fmtDate(a.assigned_date)}{a.returned_date ? ` – ${fmtDate(a.returned_date)}` : ' (aktif)'}</span>
                  </div>
                ))}
                {assignments.length === 0 && <p className="text-xs text-muted-foreground text-center py-3">Belum pernah ditugaskan</p>}
              </div>
            </div>
          </TabsContent>

          {/* Maintenance Tab */}
          <TabsContent value="maint" className="space-y-3 mt-3">
            <Card>
              <CardContent className="pt-4 space-y-2">
                <p className="text-sm font-medium">Catat Pemeliharaan</p>
                <Select value={maintForm.type} onValueChange={v => setMaintForm(p => ({...p, type: v}))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="scheduled">Terjadwal</SelectItem>
                    <SelectItem value="corrective">Korektif</SelectItem>
                    <SelectItem value="preventive">Preventif</SelectItem>
                  </SelectContent>
                </Select>
                <Input placeholder="Deskripsi pemeliharaan..." value={maintForm.description}
                  onChange={e => setMaintForm(p => ({...p, description: e.target.value}))} />
                <Input type="number" placeholder="Biaya (Rp)" value={maintForm.cost}
                  onChange={e => setMaintForm(p => ({...p, cost: e.target.value}))} />
                <Input placeholder="Dilakukan oleh" value={maintForm.performed_by}
                  onChange={e => setMaintForm(p => ({...p, performed_by: e.target.value}))} />
                <Input type="date" value={maintForm.maintenance_date}
                  onChange={e => setMaintForm(p => ({...p, maintenance_date: e.target.value}))} />
                <Select value={maintForm.status} onValueChange={v => setMaintForm(p => ({...p, status: v}))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="completed">Selesai</SelectItem>
                    <SelectItem value="in_progress">Sedang Berjalan</SelectItem>
                    <SelectItem value="scheduled">Terjadwal</SelectItem>
                  </SelectContent>
                </Select>
                <Button size="sm" className="w-full" onClick={addMaintenance} disabled={loading}>Simpan Pemeliharaan</Button>
              </CardContent>
            </Card>
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Riwayat</p>
              <div className="space-y-1">
                {maintenance.map(m => (
                  <div key={m.id} className="py-2 px-3 bg-muted/40 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{m.description}</span>
                      <span className="text-xs text-muted-foreground">{fmtDate(m.maintenance_date)}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-muted-foreground">{m.type}</span>
                      {m.cost > 0 && <span className="text-xs text-amber-600">{fmtCurrency(m.cost)}</span>}
                    </div>
                  </div>
                ))}
                {maintenance.length === 0 && <p className="text-xs text-muted-foreground text-center py-3">Belum ada riwayat pemeliharaan</p>}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// UTILIZATION REPORT TAB (Session 28)
// ═══════════════════════════════════════════════════════════════════════════════
function UtilizationReportTab({ token, categories }) {
  // Default: last 90 days
  const today = new Date().toISOString().slice(0, 10);
  const ninetyDaysAgo = new Date(Date.now() - 90 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  const [dateFrom, setDateFrom] = useState(ninetyDaysAgo);
  const [dateTo, setDateTo] = useState(today);
  const [categoryId, setCategoryId] = useState('all');
  const [threshold, setThreshold] = useState(30);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('top'); // top | underutilized | idle

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        underutilized_threshold: String(threshold),
        limit: '100',
      });
      if (categoryId && categoryId !== 'all') params.append('category_id', categoryId);
      const data = await apicall('GET', `/api/assets/reports/utilization?${params}`, token);
      setReport(data);
    } catch (e) {
      toast.error(e.message || 'Gagal memuat utilization report');
    } finally {
      setLoading(false);
    }
  }, [token, dateFrom, dateTo, categoryId, threshold]);

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const exportCsv = async () => {
    try {
      const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        underutilized_threshold: String(threshold),
      });
      if (categoryId && categoryId !== 'all') params.append('category_id', categoryId);
      const res = await fetch(`${API}/api/assets/reports/utilization/export.csv?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Export gagal (${res.status})`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `asset_utilization_${dateFrom}_to_${dateTo}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('CSV berhasil diunduh');
    } catch (e) {
      toast.error(e.message || 'Export gagal');
    }
  };

  const summary = report?.summary || {};
  const detailRows = (
    view === 'top' ? report?.top_utilized :
    view === 'underutilized' ? report?.underutilized :
    report?.idle_assets
  ) || [];

  return (
    <div className="space-y-4" data-testid="utilization-report-tab">
      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Tanggal Mulai</label>
              <Input
                type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                data-testid="util-filter-date-from" className="h-9"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Tanggal Akhir</label>
              <Input
                type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                data-testid="util-filter-date-to" className="h-9"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Kategori</label>
              <Select value={categoryId} onValueChange={setCategoryId}>
                <SelectTrigger className="h-9" data-testid="util-filter-category">
                  <SelectValue placeholder="Semua kategori" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Semua kategori</SelectItem>
                  {(categories || []).map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                Underutil &lt; (%)
              </label>
              <Input
                type="number" min="0" max="100"
                value={threshold} onChange={e => setThreshold(parseInt(e.target.value || '0', 10))}
                data-testid="util-filter-threshold" className="h-9"
              />
            </div>
            <div className="flex items-end gap-2">
              <Button
                onClick={load} disabled={loading}
                data-testid="util-apply-button"
                className="h-9 flex-1"
              >
                <RefreshCw size={14} className={`mr-1.5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Memuat...' : 'Terapkan'}
              </Button>
              <Button
                variant="outline" onClick={exportCsv}
                data-testid="util-export-csv-button" className="h-9"
              >
                <Download size={14} className="mr-1" /> CSV
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard
          label="Total Aset Dievaluasi" value={summary.total_assets || 0}
          icon={Package} accent="blue"
          sub={`${summary.assets_in_use_today || 0} sedang dipakai hari ini`}
        />
        <KPICard
          label="Rata-Rata Utilization" value={`${summary.avg_utilization_pct || 0}%`}
          icon={Gauge} accent="emerald"
          sub={`${summary.fully_utilized_count || 0} aset ≥95% (full)`}
        />
        <KPICard
          label="Underutilized" value={summary.underutilized_count || 0}
          icon={AlertTriangle} accent="amber"
          sub={`< ${threshold}% utilization`}
        />
        <KPICard
          label="Idle Total" value={summary.idle_in_window_count || 0}
          icon={Zap} accent="violet"
          sub={`${fmtCurrency(summary.underutilized_value_at_risk || 0)} nilai berisiko`}
        />
      </div>

      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5">
                <TrendingUp size={14} className="text-emerald-500" />
                Per Kategori
              </CardTitle>
            </CardHeader>
            <CardContent>
              {report.by_category.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">Tidak ada data</p>
              ) : (
                <div className="space-y-2.5">
                  {report.by_category.map(c => (
                    <div key={c.category_id} data-testid={`util-cat-${c.category_id}`}>
                      <div className="flex items-center justify-between mb-1 text-xs">
                        <span className="font-medium">{c.category_name}</span>
                        <span className="text-muted-foreground">
                          {c.asset_count} aset · {c.avg_utilization_pct}%
                        </span>
                      </div>
                      <Progress value={c.avg_utilization_pct} className="h-1.5" />
                      <div className="flex items-center gap-3 mt-1 text-[10px] text-muted-foreground">
                        <span>Underutil: <b>{c.underutilized_count}</b></span>
                        <span>Idle: <b>{c.idle_count}</b></span>
                        <span>Cost: <b>{fmtCurrency(c.total_purchase_cost)}</b></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5">
                <User size={14} className="text-blue-500" />
                Top Pemegang Aset
              </CardTitle>
            </CardHeader>
            <CardContent>
              {report.by_assignee.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">
                  Belum ada penugasan dalam periode ini
                </p>
              ) : (
                <div className="space-y-2">
                  {report.by_assignee.slice(0, 8).map(a => (
                    <div
                      key={a.assignee_id}
                      data-testid={`util-assignee-${a.assignee_id}`}
                      className="flex items-center justify-between text-xs py-1.5 px-2 rounded hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full bg-blue-500/10 text-blue-600 flex items-center justify-center font-semibold text-[10px]">
                          {(a.assignee_name || '?').slice(0, 2).toUpperCase()}
                        </div>
                        <span className="font-medium">{a.assignee_name}</span>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold">{a.unique_assets} aset</p>
                        <p className="text-[10px] text-muted-foreground">{a.total_assigned_days} hari</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Daftar Aset</CardTitle>
            <div className="flex items-center gap-1">
              <Button
                size="sm" variant={view === 'top' ? 'default' : 'outline'}
                onClick={() => setView('top')} className="h-7 text-xs"
                data-testid="util-view-top"
              >
                Top Utilized
              </Button>
              <Button
                size="sm" variant={view === 'underutilized' ? 'default' : 'outline'}
                onClick={() => setView('underutilized')} className="h-7 text-xs"
                data-testid="util-view-underutilized"
              >
                Underutilized
                {summary.underutilized_count > 0 && (
                  <Badge className="ml-1.5 text-[10px] h-4 px-1 bg-amber-500">
                    {summary.underutilized_count}
                  </Badge>
                )}
              </Button>
              <Button
                size="sm" variant={view === 'idle' ? 'default' : 'outline'}
                onClick={() => setView('idle')} className="h-7 text-xs"
                data-testid="util-view-idle"
              >
                Idle
                {summary.idle_in_window_count > 0 && (
                  <Badge className="ml-1.5 text-[10px] h-4 px-1 bg-violet-500">
                    {summary.idle_in_window_count}
                  </Badge>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {detailRows.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm" data-testid="util-empty-detail">
              Tidak ada aset dalam kategori ini
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-muted-foreground border-b">
                    <th className="py-2 px-2">Aset</th>
                    <th className="py-2 px-2">Kategori</th>
                    <th className="py-2 px-2 text-right">Utilization</th>
                    <th className="py-2 px-2 text-right">Hari Aktif</th>
                    <th className="py-2 px-2">Assignee</th>
                    <th className="py-2 px-2">Last Activity</th>
                    <th className="py-2 px-2 text-right">Nilai</th>
                  </tr>
                </thead>
                <tbody>
                  {detailRows.map(r => (
                    <tr
                      key={r.asset_id}
                      data-testid={`util-row-${r.asset_id}`}
                      className="border-b last:border-b-0 hover:bg-muted/30"
                    >
                      <td className="py-2 px-2">
                        <p className="font-medium">{r.asset_name}</p>
                        <p className="text-[10px] text-muted-foreground font-mono">{r.asset_number}</p>
                      </td>
                      <td className="py-2 px-2">{r.category_name || '—'}</td>
                      <td className="py-2 px-2 text-right">
                        <span
                          className={`font-semibold ${
                            r.utilization_pct >= 80 ? 'text-emerald-600' :
                            r.utilization_pct >= 40 ? 'text-blue-600' :
                            r.utilization_pct > 0 ? 'text-amber-600' : 'text-red-600'
                          }`}
                        >
                          {r.utilization_pct}%
                        </span>
                      </td>
                      <td className="py-2 px-2 text-right">
                        {r.assigned_days} / {r.effective_window_days}
                      </td>
                      <td className="py-2 px-2">{r.current_assignee || <span className="text-muted-foreground">—</span>}</td>
                      <td className="py-2 px-2 text-muted-foreground text-[11px]">
                        {r.last_assigned_date ? fmtDate(r.last_assigned_date) : '—'}
                      </td>
                      <td className="py-2 px-2 text-right">{fmtCurrency(r.purchase_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════════════════
// PREDICTIVE MAINTENANCE ALERTS TAB (Session 28)
// ═══════════════════════════════════════════════════════════════════════════════

const SEVERITY_CONFIG = {
  critical: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-600', label: 'Critical' },
  warning:  { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-600', label: 'Warning' },
  info:     { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-600', label: 'Info' },
};

const KIND_CONFIG = {
  overdue:        { Icon: AlertTriangle, label: 'Overdue', color: 'text-red-500' },
  upcoming:       { Icon: Clock, label: 'Upcoming', color: 'text-amber-500' },
  stale:          { Icon: Activity, label: 'Stale', color: 'text-violet-500' },
  high_frequency: { Icon: TrendingUp, label: 'High Frequency', color: 'text-rose-500' },
  predicted:      { Icon: Gauge, label: 'Predicted', color: 'text-blue-500' },
};

function PMAlertCard({ alert, onAcknowledge, ackBusy }) {
  const sevCfg = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
  const kindCfg = KIND_CONFIG[alert.kind] || KIND_CONFIG.predicted;
  const KIcon = kindCfg.Icon;

  return (
    <div
      data-testid={`pm-alert-${alert.kind}-${alert.asset_id}`}
      className={`rounded-lg border ${sevCfg.border} ${sevCfg.bg} p-3.5`}
    >
      <div className="flex items-start gap-3">
        <div className={`shrink-0 w-9 h-9 rounded-lg bg-white/80 dark:bg-zinc-900/60 grid place-items-center ${kindCfg.color}`}>
          <KIcon size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="text-sm font-semibold">{alert.asset_name}</span>
            <span className="text-[10px] font-mono text-muted-foreground">{alert.asset_number}</span>
            <Badge variant="outline" className={`text-[10px] h-4 px-1 ${sevCfg.text}`}>
              {sevCfg.label}
            </Badge>
            <Badge variant="outline" className="text-[10px] h-4 px-1 capitalize">
              {kindCfg.label}
            </Badge>
          </div>
          <p className="text-xs text-foreground/70 leading-snug">{alert.recommended_action}</p>
          <div className="flex items-center gap-3 mt-2 text-[11px] text-muted-foreground flex-wrap">
            {alert.category_name && <span>📁 {alert.category_name}</span>}
            {alert.current_assignee && <span>👤 {alert.current_assignee}</span>}
            {alert.last_maintenance_date && <span>🛠️ Last: {alert.last_maintenance_date}</span>}
            {typeof alert.days_overdue === 'number' && (
              <span className="font-semibold text-red-600">⏰ {alert.days_overdue} hari telat</span>
            )}
            {typeof alert.days_until === 'number' && (
              <span className="font-semibold text-amber-600">⏳ {alert.days_until} hari lagi</span>
            )}
            {typeof alert.months_since_maintenance === 'number' && (
              <span className="font-semibold">📅 {alert.months_since_maintenance} bulan tanpa maintenance</span>
            )}
            {typeof alert.recent_count === 'number' && (
              <span className="font-semibold text-rose-600">
                🔄 {alert.recent_count}× dalam {alert.window_days} hari
              </span>
            )}
            {alert.predicted_next_due_date && (
              <span className="font-semibold text-blue-600">
                📊 Predicted: {alert.predicted_next_due_date}
              </span>
            )}
          </div>
        </div>
        <Button
          size="sm" variant="outline"
          onClick={() => onAcknowledge(alert)}
          disabled={ackBusy}
          data-testid={`pm-ack-${alert.kind}-${alert.asset_id}`}
          className="h-7 text-xs shrink-0"
        >
          <BellOff size={12} className="mr-1" /> Snooze
        </Button>
      </div>
    </div>
  );
}

function PredictiveMaintenanceTab({ token, categories }) {
  const [config, setConfig] = useState({
    upcoming_window_days: 30,
    stale_months: 6,
    high_frequency_window_days: 90,
    high_frequency_threshold: 3,
    category_id: 'all',
  });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all'); // all | overdue | upcoming | stale | high_frequency | predicted
  const [ackBusy, setAckBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        upcoming_window_days: String(config.upcoming_window_days),
        stale_months: String(config.stale_months),
        high_frequency_window_days: String(config.high_frequency_window_days),
        high_frequency_threshold: String(config.high_frequency_threshold),
      });
      if (config.category_id && config.category_id !== 'all') params.append('category_id', config.category_id);
      const data = await apicall('GET', `/api/assets/predictive-maintenance/alerts?${params}`, token);
      setReport(data);
    } catch (e) {
      toast.error(e.message || 'Gagal memuat alerts');
    } finally {
      setLoading(false);
    }
  }, [token, config]);

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const acknowledge = async (alert) => {
    setAckBusy(true);
    try {
      await apicall('POST', '/api/assets/predictive-maintenance/acknowledge', token, {
        asset_id: alert.asset_id,
        alert_kind: alert.kind,
        note: '',
      });
      toast.success(`Alert "${alert.asset_name}" di-snooze 30 hari`);
      await load();
    } catch (e) {
      toast.error(e.message || 'Gagal snooze');
    } finally {
      setAckBusy(false);
    }
  };

  const summary = report?.summary || {};

  const sections = [
    { kind: 'overdue', title: 'Overdue', list: report?.overdue || [], icon: AlertTriangle, color: 'text-red-500' },
    { kind: 'high_frequency', title: 'High Frequency', list: report?.high_frequency || [], icon: TrendingUp, color: 'text-rose-500' },
    { kind: 'upcoming', title: 'Upcoming', list: report?.upcoming || [], icon: Clock, color: 'text-amber-500' },
    { kind: 'predicted', title: 'Predicted', list: report?.predicted || [], icon: Gauge, color: 'text-blue-500' },
    { kind: 'stale', title: 'Stale (No Recent Maintenance)', list: report?.stale || [], icon: Activity, color: 'text-violet-500' },
  ];

  const visible = filter === 'all' ? sections : sections.filter(s => s.kind === filter);

  return (
    <div className="space-y-4" data-testid="pm-alerts-tab">
      {/* Config Bar */}
      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Upcoming Window</label>
              <Input
                type="number" min="1" max="365"
                value={config.upcoming_window_days}
                onChange={e => setConfig(p => ({ ...p, upcoming_window_days: parseInt(e.target.value || '30', 10) }))}
                data-testid="pm-config-upcoming-days"
                className="h-9"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Stale (bulan)</label>
              <Input
                type="number" min="1" max="36"
                value={config.stale_months}
                onChange={e => setConfig(p => ({ ...p, stale_months: parseInt(e.target.value || '6', 10) }))}
                data-testid="pm-config-stale-months"
                className="h-9"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">High Freq Window</label>
              <Input
                type="number" min="7" max="365"
                value={config.high_frequency_window_days}
                onChange={e => setConfig(p => ({ ...p, high_frequency_window_days: parseInt(e.target.value || '90', 10) }))}
                data-testid="pm-config-hf-days"
                className="h-9"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">High Freq Threshold</label>
              <Input
                type="number" min="2" max="20"
                value={config.high_frequency_threshold}
                onChange={e => setConfig(p => ({ ...p, high_frequency_threshold: parseInt(e.target.value || '3', 10) }))}
                data-testid="pm-config-hf-threshold"
                className="h-9"
              />
            </div>
            <div className="flex items-end">
              <Button
                onClick={load} disabled={loading}
                data-testid="pm-apply-button"
                className="h-9 w-full"
              >
                <RefreshCw size={14} className={`mr-1.5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Memuat...' : 'Terapkan'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary KPI */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KPICard
          label="Critical" value={summary.critical_count || 0}
          icon={AlertTriangle} accent="violet"
          sub="Memerlukan tindakan segera"
        />
        <KPICard
          label="Overdue" value={summary.overdue_count || 0}
          icon={AlertCircle} accent="amber"
        />
        <KPICard
          label="Upcoming" value={summary.upcoming_count || 0}
          icon={Clock} accent="blue"
        />
        <KPICard
          label="Stale + Predicted" value={(summary.stale_count || 0) + (summary.predicted_count || 0)}
          icon={Activity} accent="emerald"
        />
        <KPICard
          label="High Frequency" value={summary.high_frequency_count || 0}
          icon={TrendingUp} accent="violet"
          sub="Pola maintenance abnormal"
        />
      </div>

      {/* Filter pills */}
      <div className="flex items-center gap-1.5 flex-wrap" data-testid="pm-filter-pills">
        <Button
          size="sm" variant={filter === 'all' ? 'default' : 'outline'}
          onClick={() => setFilter('all')} className="h-7 text-xs"
          data-testid="pm-filter-all"
        >
          Semua ({summary.total_alerts || 0})
        </Button>
        {sections.map(s => (
          <Button
            key={s.kind}
            size="sm" variant={filter === s.kind ? 'default' : 'outline'}
            onClick={() => setFilter(s.kind)}
            disabled={s.list.length === 0}
            className="h-7 text-xs"
            data-testid={`pm-filter-${s.kind}`}
          >
            {s.title} ({s.list.length})
          </Button>
        ))}
      </div>

      {/* Sections */}
      {summary.total_alerts === 0 && !loading && (
        <Card data-testid="pm-empty-state">
          <CardContent className="py-12 text-center">
            <CheckCircle2 size={48} className="mx-auto text-emerald-500 mb-3" />
            <p className="text-base font-semibold">Tidak ada alert maintenance</p>
            <p className="text-xs text-muted-foreground mt-1">
              Semua aset dalam kondisi terkontrol berdasarkan parameter yang diatur.
            </p>
          </CardContent>
        </Card>
      )}

      {visible.map(s => {
        if (s.list.length === 0) return null;
        const Icon = s.icon;
        return (
          <Card key={s.kind} data-testid={`pm-section-${s.kind}`}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Icon size={15} className={s.color} />
                {s.title}
                <Badge className="text-[10px] h-4 px-1.5">{s.list.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {s.list.slice(0, 20).map(a => (
                <PMAlertCard
                  key={`${a.kind}-${a.asset_id}`}
                  alert={a}
                  ackBusy={ackBusy}
                  onAcknowledge={acknowledge}
                />
              ))}
              {s.list.length > 20 && (
                <p className="text-xs text-center text-muted-foreground mt-1">
                  ... dan {s.list.length - 20} alert lainnya
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}




// ── Procurement Request Form ────────────────────────────────────────────
function CreatePRDialog({ open, onClose, token, onCreated }) {
  const initialForm = {
    title: '', description: '', justification: '', priority: 'medium',
    request_type: 'asset', department: '',
    items: [{ name: '', specification: '', qty: 1, unit: 'pcs', estimated_price: '', notes: '' }],
  };
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const set = (k, v) => setForm(p => ({...p, [k]: v}));

  // Reset form whenever dialog re-opens (clear stale data)
  useEffect(() => {
    if (open) {
      setForm(initialForm);
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const setItem = (idx, k, v) => setForm(p => ({
    ...p,
    items: p.items.map((it, i) => i === idx ? {...it, [k]: v} : it)
  }));

  const addItem = () => setForm(p => ({ ...p, items: [...p.items, { name: '', specification: '', qty: 1, unit: 'pcs', estimated_price: '', notes: '' }] }));
  const removeItem = (idx) => setForm(p => ({ ...p, items: p.items.filter((_, i) => i !== idx) }));

  const totalEst = form.items.reduce((s, i) => s + (Number(i.estimated_price) || 0) * (Number(i.qty) || 1), 0);

  // Validity check (used for submit gating)
  const isValid = form.title.trim() !== '' && form.items.every(i => i.name && i.name.trim() !== '');

  // Dirty detection (untuk konfirmasi sebelum close)
  const isDirty =
    form.title.trim() !== '' ||
    form.description.trim() !== '' ||
    form.justification.trim() !== '' ||
    form.department.trim() !== '' ||
    form.items.some(i => (i.name || '').trim() !== '' || (i.specification || '').trim() !== '' || Number(i.estimated_price) > 0);

  const safeClose = () => {
    if (loading) return; // tidak boleh close saat submit
    if (isDirty) {
      if (!window.confirm('Form berisi data yang belum disimpan. Yakin ingin menutup?')) return;
    }
    onClose();
  };

  const submit = async () => {
    if (!form.title.trim()) { toast.error('Judul wajib diisi'); return; }
    if (form.items.some(i => !i.name)) { toast.error('Nama item wajib diisi'); return; }
    setLoading(true);
    try {
      const data = await apicall('POST', '/api/procurement/requests', token, {
        ...form,
        items: form.items.map(i => ({...i, qty: Number(i.qty) || 1, estimated_price: Number(i.estimated_price) || 0}))
      });
      if (data.id) {
        toast.success(`PR ${data.request_number} berhasil dibuat`);
        // Close dialog FIRST so UI updates immediately, then trigger reload.
        onClose();
        // defer onCreated to next tick so dialog close animation can start
        setTimeout(() => onCreated && onCreated(data), 0);
      } else {
        toast.error(data.detail || 'Gagal membuat request');
      }
    } catch {
      toast.error('Gagal membuat request');
    } finally {
      setLoading(false);
    }
  };

  // Ctrl/Cmd + Enter to submit
  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!loading && isValid) submit();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) safeClose(); }}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto" onKeyDown={handleKeyDown} data-testid="create-pr-dialog">
        <DialogHeader>
          <DialogTitle>Buat Request Pengadaan</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <Input placeholder="Judul request... *" value={form.title}
            onChange={e => set('title', e.target.value)} data-testid="pr-title-input" autoFocus />
          <div className="grid grid-cols-3 gap-2">
            <Select value={form.priority} onValueChange={v => set('priority', v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Prioritas Rendah</SelectItem>
                <SelectItem value="medium">Prioritas Sedang</SelectItem>
                <SelectItem value="high">Prioritas Tinggi</SelectItem>
                <SelectItem value="urgent">Mendesak</SelectItem>
              </SelectContent>
            </Select>
            <Select value={form.request_type} onValueChange={v => set('request_type', v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="asset">Aset</SelectItem>
                <SelectItem value="consumable">Habis Pakai</SelectItem>
                <SelectItem value="service">Jasa/Layanan</SelectItem>
                <SelectItem value="other">Lainnya</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Departemen" value={form.department}
              onChange={e => set('department', e.target.value)} />
          </div>
          <Input placeholder="Justifikasi kebutuhan..." value={form.justification}
            onChange={e => set('justification', e.target.value)} />

          {/* Items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">Daftar Item</p>
              <Button variant="outline" size="sm" onClick={addItem}><Plus size={12} className="mr-1" /> Tambah</Button>
            </div>
            <div className="space-y-2">
              {form.items.map((item, idx) => (
                <div key={idx} className="bg-muted/40 rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Input placeholder={`Item ${idx + 1} *`} value={item.name}
                      onChange={e => setItem(idx, 'name', e.target.value)} className="flex-1" />
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => removeItem(idx)}
                      disabled={form.items.length === 1}><X size={14} /></Button>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Input placeholder="Qty" type="number" value={item.qty}
                      onChange={e => setItem(idx, 'qty', e.target.value)} />
                    <Input placeholder="Satuan (pcs)" value={item.unit}
                      onChange={e => setItem(idx, 'unit', e.target.value)} />
                    <Input placeholder="Est. Harga (Rp)" type="number" value={item.estimated_price}
                      onChange={e => setItem(idx, 'estimated_price', e.target.value)} />
                  </div>
                  <Input placeholder="Spesifikasi / catatan" value={item.specification}
                    onChange={e => setItem(idx, 'specification', e.target.value)} />
                </div>
              ))}
            </div>
            <div className="mt-2 text-right text-sm">
              Total Estimasi: <span className="font-bold">{fmtCurrency(totalEst)}</span>
            </div>
          </div>
        </div>
        <DialogFooter className="flex items-center !justify-between gap-2">
          <span className="text-[10px] text-muted-foreground italic hidden sm:inline">
            Tip: tekan Ctrl+Enter untuk submit cepat
          </span>
          <div className="flex gap-2 ml-auto">
            <Button variant="outline" onClick={safeClose} disabled={loading} data-testid="create-pr-cancel">Batal</Button>
            <Button onClick={submit} disabled={loading || !isValid} data-testid="create-pr-submit">
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                  Menyimpan...
                </span>
              ) : 'Buat Request'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── PR Detail Drawer ───────────────────────────────────────────────────────────
function PRDetailDrawer({ pr, token, open, onClose, onRefresh, currentUser }) {
  const [loading, setLoading] = useState(false);
  const [comment, setComment] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  if (!pr) return null;

  const canApprove = ['submitted', 'dept_approved', 'finance_approved'].includes(pr.status);
  const canSubmit = pr.status === 'draft';
  const canCancel = ['draft', 'submitted'].includes(pr.status) &&
    (pr.requested_by === currentUser?.id || currentUser?.role === 'superadmin' || currentUser?.role === 'admin');

  const action = async (endpoint, body = {}) => {
    setLoading(true);
    try {
      const d = await apicall('POST', `/api/procurement/requests/${pr.id}/${endpoint}`, token, body);
      if (d.ok) { toast.success('Berhasil'); onRefresh(); onClose(); }
      else toast.error(d.detail || 'Gagal');
    } catch { toast.error('Gagal'); }
    finally { setLoading(false); }
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:w-[480px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <ShoppingCart size={16} />
            <span className="truncate">{pr.title}</span>
          </SheetTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-muted-foreground">{pr.request_number}</span>
            <StatusBadge status={pr.status} configMap={PR_STATUS_CONFIG} />
          </div>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          {/* Info */}
          <div className="grid grid-cols-2 gap-2">
            {[
              ['Pemohon', pr.requested_by_name], ['Departemen', pr.department || '-'],
              ['Prioritas', pr.priority], ['Tipe', pr.request_type],
              ['Tgl Dibuat', fmtDate(pr.created_at)], ['Total Est.', fmtCurrency(pr.total_estimated)],
            ].map(([k, v]) => (
              <div key={k} className="bg-muted/40 rounded-lg p-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{k}</p>
                <p className="text-sm font-medium">{v}</p>
              </div>
            ))}
          </div>

          {pr.justification && (
            <div className="bg-muted/40 rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-1">Justifikasi</p>
              <p className="text-sm">{pr.justification}</p>
            </div>
          )}

          {/* Items */}
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Daftar Item</p>
            <div className="space-y-1">
              {(pr.items || []).map((item, i) => (
                <div key={i} className="flex items-center justify-between py-2 px-3 bg-muted/40 rounded-lg">
                  <div>
                    <p className="text-sm font-medium">{item.name}</p>
                    {item.specification && <p className="text-xs text-muted-foreground">{item.specification}</p>}
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">{item.qty} {item.unit}</p>
                    <p className="text-sm font-medium">{fmtCurrency(item.total_price)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Timeline */}
          {(pr.approval_steps || []).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Timeline Approval</p>
              <div className="relative pl-4 space-y-3">
                <div className="absolute left-2 top-1 bottom-1 w-px bg-border" />
                {pr.approval_steps.map((s, i) => (
                  <div key={s.id || i} className="relative pl-4">
                    <div className={`absolute left-0 top-1 w-3 h-3 rounded-full border-2 border-background ${
                      s.action === 'approved' ? 'bg-emerald-500' : s.action === 'rejected' ? 'bg-red-500' : 'bg-primary'
                    }`} />
                    <p className="text-sm font-medium">{s.actor_name} <span className="text-muted-foreground font-normal text-xs">– {s.action}</span></p>
                    {s.comment && <p className="text-xs text-muted-foreground">{s.comment}</p>}
                    <p className="text-[10px] text-muted-foreground">{s.timestamp ? new Date(s.timestamp).toLocaleString('id-ID') : ''}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <Separator />
          <div className="space-y-2">
            {canSubmit && (
              <Button className="w-full" size="sm" onClick={() => action('submit')} disabled={loading}>
                <Send size={14} className="mr-1" /> Submit untuk Approval
              </Button>
            )}
            {canApprove && !showRejectInput && (
              <div className="flex gap-2">
                <Button className="flex-1" size="sm" variant="default" onClick={() => action('approve', { comment })} disabled={loading}>
                  <CheckCheck size={14} className="mr-1" /> Approve
                </Button>
                <Button className="flex-1" size="sm" variant="destructive" onClick={() => setShowRejectInput(true)}>
                  <X size={14} className="mr-1" /> Tolak
                </Button>
              </div>
            )}
            {showRejectInput && (
              <div className="space-y-2">
                <Input placeholder="Alasan penolakan..." value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)} />
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" className="flex-1"
                    onClick={() => action('reject', { reason: rejectReason })} disabled={loading}>
                    Konfirmasi Tolak
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setShowRejectInput(false)}>Batal</Button>
                </div>
              </div>
            )}
            {canCancel && (
              <Button variant="outline" size="sm" className="w-full text-red-500 hover:text-red-500"
                onClick={() => action('cancel')} disabled={loading}>
                Batalkan Request
              </Button>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ── Main Portal Component ───────────────────────────────────────────────────
export default function AssetManagementPortal({ token, user }) {
  const [mainTab, setMainTab] = useState('dashboard');
  const [dashData, setDashData] = useState(null);
  const [expiringAlerts, setExpiringAlerts] = useState(null);
  const [assets, setAssets] = useState([]);
  const [assetPagination, setAssetPagination] = useState({ total: 0, page: 1, total_pages: 1 });
  const [categories, setCategories] = useState([]);
  const [prData, setPrData] = useState([]);
  const [prInbox, setPrInbox] = useState([]);
  const [prTab, setPrTab] = useState('all');
  const [inboxScope, setInboxScope] = useState('relevant'); // relevant | all | mine
  const [inboxDept, setInboxDept] = useState(''); // optional dept filter (admin only)
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [selectedPR, setSelectedPR] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [showCreateAsset, setShowCreateAsset] = useState(false);
  const [showCreatePR, setShowCreatePR] = useState(false);
  const [showEditCategory, setShowEditCategory] = useState(false);
  const [showAssetScanner, setShowAssetScanner] = useState(false);
  const [showTransferAsset, setShowTransferAsset] = useState(false);
  const [assetToTransfer, setAssetToTransfer] = useState(null);
  const [showBulkImport, setShowBulkImport] = useState(false);
  const [showDisposalRequest, setShowDisposalRequest] = useState(false);
  const [assetForDisposal, setAssetForDisposal] = useState(null);
  const [assetSearch, setAssetSearch] = useState('');
  const [assetStatus, setAssetStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [prSearch, setPrSearch] = useState('');

  // Load dashboard
  const loadDashboard = useCallback(async () => {
    try {
      const d = await apicall('GET', '/api/assets/dashboard', token);
      setDashData(d);
    } catch {}
  }, [token]);

  // Load expiring alerts (warranty + insurance)
  const loadExpiringAlerts = useCallback(async () => {
    try {
      const d = await apicall('GET', '/api/assets/expiring-alerts?days=30', token);
      setExpiringAlerts(d);
    } catch {}
  }, [token]);

  // Load assets
  const loadAssets = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: 20 });
      if (assetSearch) params.set('search', assetSearch);
      if (assetStatus) params.set('status', assetStatus);
      const d = await apicall('GET', `/api/assets?${params}`, token);
      if (d.items) {
        setAssets(d.items);
        setAssetPagination(d.pagination);
      }
    } catch {}
    finally { setLoading(false); }
  }, [token, assetSearch, assetStatus]);

  // Load categories
  const loadCategories = useCallback(async () => {
    try {
      const d = await apicall('GET', '/api/assets/categories', token);
      if (Array.isArray(d)) setCategories(d);
    } catch (e) {
      console.warn('loadCategories error:', e.message);
    }
  }, [token]);

  // Load PRs
  const loadPRs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: 50 });
      if (prSearch) params.set('search', prSearch);
      const inboxParams = new URLSearchParams({ scope: inboxScope });
      if (inboxDept) inboxParams.set('department', inboxDept);
      const [all, inbox] = await Promise.all([
        apicall('GET', `/api/procurement/requests?${params}`, token),
        apicall('GET', `/api/procurement/inbox?${inboxParams}`, token),
      ]);
      if (all.items) setPrData(all.items);
      if (Array.isArray(inbox)) setPrInbox(inbox);
    } catch (e) {
      console.warn('loadPRs error:', e.message);
    }
  }, [token, prSearch, inboxScope, inboxDept]);

  useEffect(() => { loadDashboard(); loadCategories(); loadExpiringAlerts(); }, [loadDashboard, loadCategories, loadExpiringAlerts]);
  useEffect(() => { if (mainTab === 'assets') loadAssets(); }, [mainTab, loadAssets]);
  useEffect(() => { if (mainTab === 'procurement') loadPRs(); }, [mainTab, loadPRs]);

  const userRole = (user?.role || '').toLowerCase();
  const isAdminLike = userRole === 'admin' || userRole === 'superadmin';
  // Daftar departemen unik (untuk filter admin) — dari prInbox + prData
  const uniqueDepartments = Array.from(new Set(
    [...(prData || []), ...(prInbox || [])]
      .map(p => (p.department || '').trim())
      .filter(Boolean)
  )).sort();

  const summary = dashData?.summary || {};
  const byCat = (dashData?.by_category || []).map(c => ({ name: c.category || 'Lainnya', count: c.count }));

  return (
    <div className="p-4 space-y-4" data-testid="asset-mgmt-portal">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Package size={20} className="text-primary" />
            Manajemen Aset
          </h1>
          <p className="text-sm text-muted-foreground">Aset perusahaan, depresiasi, dan pengadaan</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={() => { loadDashboard(); loadAssets(); loadPRs(); loadExpiringAlerts(); }}>
            <RefreshCw size={14} className="mr-1" /> Refresh
          </Button>
          <Button size="sm" variant="outline" onClick={() => setShowAssetScanner(true)} data-testid="scan-asset-btn">
            <Scan size={14} className="mr-1" /> Scan Asset
          </Button>
          <Button size="sm" onClick={() => setShowCreateAsset(true)} data-testid="add-asset-btn">
            <Plus size={14} className="mr-1" /> Aset Baru
          </Button>
          <Button size="sm" variant="outline" onClick={() => setShowBulkImport(true)} data-testid="bulk-import-btn">
            <Upload size={14} className="mr-1" /> Import CSV/Excel
          </Button>
          <Button size="sm" variant="outline" onClick={() => setShowCreatePR(true)} data-testid="add-pr-btn">
            <ShoppingCart size={14} className="mr-1" /> Request Pengadaan
          </Button>
          <Button size="sm" variant="outline" onClick={async () => {
            const period = new Date().toISOString().slice(0, 7);
            if (!window.confirm(`Posting depresiasi massal untuk periode ${period}?`)) return;
            try {
              const d = await apicall('POST', `/api/assets/batch-depreciate/${period}`, token, {});
              toast.success(`Depresiasi massal: ${d.total_posted} aset diposting, ${d.total_skipped} dilewati`);
              loadDashboard();
            } catch { toast.error('Gagal batch depresiasi'); }
          }} data-testid="batch-depr-btn">
            <TrendingDown size={14} className="mr-1" /> Depresiasi Massal
          </Button>
        </div>
      </div>

      <Tabs value={mainTab} onValueChange={setMainTab}>
        <TabsList>
          <TabsTrigger value="dashboard" data-testid="tab-dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="assets" data-testid="tab-assets">Aset</TabsTrigger>
          <TabsTrigger value="categories" data-testid="tab-categories">Kategori</TabsTrigger>
          <TabsTrigger value="procurement" data-testid="tab-procurement">
            Pengadaan
            {prInbox.length > 0 && (
              <Badge className="ml-1.5 text-[10px] h-4 px-1.5 bg-amber-500 text-white">{prInbox.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="disposal-requests" data-testid="tab-disposal">
            ⚠️ Disposal
          </TabsTrigger>
          <TabsTrigger value="utilization" data-testid="tab-utilization">
            <Gauge size={13} className="mr-1" /> Utilization
          </TabsTrigger>
          <TabsTrigger value="pm-alerts" data-testid="tab-pm-alerts">
            <ShieldAlert size={13} className="mr-1" /> Maintenance Alerts
          </TabsTrigger>
        </TabsList>

        {/* DASHBOARD TAB */}
        <TabsContent value="dashboard" className="mt-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <KPICard label="Total Aset" value={summary.total_assets || 0} icon={Package} accent="blue" />
            <KPICard label="Total Nilai Buku" value={fmtCurrency(summary.total_nbv)} icon={Banknote} accent="emerald" />
            <KPICard label="Harga Perolehan" value={fmtCurrency(summary.total_purchase_cost)} icon={DollarSign} accent="violet" />
            <KPICard label="Depresiasi Bulan Ini" value={fmtCurrency(summary.depreciation_this_month)} icon={TrendingDown} accent="amber"
              sub={`${summary.in_maintenance || 0} dalam pemeliharaan`} />
          </div>

          {/* Warranty & Insurance Alert Banner */}
          {((summary.warranty_expiring_soon > 0) || (summary.insurance_expiring_soon > 0)) && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-4 flex items-start gap-3" data-testid="expiring-alerts-banner">
              <span className="text-2xl">⚠️</span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-amber-700">Perhatian — Garansi / Asuransi Akan Habis (≤30 hari)</p>
                <div className="flex gap-4 mt-1 text-xs text-amber-700">
                  {summary.warranty_expiring_soon > 0 && (
                    <span>🛡️ Garansi: <strong>{summary.warranty_expiring_soon}</strong> aset</span>
                  )}
                  {summary.insurance_expiring_soon > 0 && (
                    <span>🔒 Asuransi: <strong>{summary.insurance_expiring_soon}</strong> aset</span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Expiring Assets Detail Table */}
          {expiringAlerts && (
            Object.values(expiringAlerts).some(arr => arr.length > 0)
          ) && (
            <Card className="mb-4" data-testid="expiring-alerts-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <span className="text-amber-500">⏰</span> Garansi &amp; Asuransi Akan / Sudah Expired
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { key: 'warranty_expiring', label: '🛡️ Garansi — Akan Habis ≤30 hari', color: 'amber' },
                  { key: 'warranty_expired',  label: '🛡️ Garansi — Sudah Expired', color: 'red' },
                  { key: 'insurance_expiring', label: '🔒 Asuransi — Akan Habis ≤30 hari', color: 'amber' },
                  { key: 'insurance_expired',  label: '🔒 Asuransi — Sudah Expired', color: 'red' },
                ].map(({ key, label, color }) => {
                  const items = expiringAlerts[key] || [];
                  if (!items.length) return null;
                  return (
                    <div key={key}>
                      <p className={`text-xs font-semibold mb-1.5 text-${color === 'red' ? 'destructive' : 'amber-600'}`}>{label} ({items.length})</p>
                      <div className="space-y-1">
                        {items.slice(0, 5).map(a => (
                          <div key={a.id} className="flex items-center justify-between text-xs bg-muted/40 rounded px-3 py-1.5 cursor-pointer hover:bg-muted/70"
                            onClick={() => setSelectedAsset(a)}>
                            <span className="font-medium">{a.name}</span>
                            <span className="text-muted-foreground">{a.asset_number}</span>
                            <span className={color === 'red' ? 'text-destructive font-semibold' : 'text-amber-600'}>
                              {key.includes('warranty') ? fmtDate(a.warranty_expiry_date) : fmtDate(a.insurance_expiry_date)}
                            </span>
                          </div>
                        ))}
                        {items.length > 5 && <p className="text-xs text-muted-foreground pl-3">+{items.length - 5} lainnya</p>}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* By Category Chart */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Distribusi Aset per Kategori</CardTitle>
              </CardHeader>
              <CardContent className="h-52">
                {byCat.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={byCat} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                        {byCat.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                      </Pie>
                      <RechartTooltip />
                      <Legend wrapperStyle={{ fontSize: '11px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                    Belum ada data aset
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Recent Assets */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Aset Terbaru</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(dashData?.recent_assets || []).map(a => (
                    <div key={a.id} className="flex items-center justify-between py-2 px-3 bg-muted/40 rounded-lg">
                      <div>
                        <p className="text-sm font-medium">{a.name}</p>
                        <p className="text-xs text-muted-foreground">{a.category_name} · {a.asset_number}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold">{fmtCurrency(a.purchase_cost)}</p>
                        <StatusBadge status={a.status} configMap={STATUS_CONFIG} />
                      </div>
                    </div>
                  ))}
                  {(!dashData?.recent_assets || dashData.recent_assets.length === 0) && (
                    <p className="text-sm text-muted-foreground text-center py-4">Belum ada aset terdaftar</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ASSETS TAB */}
        <TabsContent value="assets" className="mt-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="relative flex-1 max-w-sm">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Cari aset..." className="pl-8" value={assetSearch}
                onChange={e => setAssetSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && loadAssets()} />
            </div>
            <Select value={assetStatus || 'all'} onValueChange={v => setAssetStatus(v === 'all' ? '' : v)}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Status</SelectItem>
                <SelectItem value="active">Aktif</SelectItem>
                <SelectItem value="in_maintenance">Pemeliharaan</SelectItem>
                <SelectItem value="disposed">Dilepas</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" onClick={() => loadAssets()}>
              <RefreshCw size={14} className="mr-1" /> Cari
            </Button>
          </div>

          <div className="rounded-xl border overflow-hidden">
            <table className="w-full" data-testid="asset-table">
              <thead className="bg-muted/40">
                <tr>
                  {['No. Aset','Nama','Kategori','Harga Beli','NBV','Status','Ditugaskan ke',''].map(h => (
                    <th key={h} className="text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide px-3 py-2.5">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr><td colSpan={8} className="text-center py-8 text-muted-foreground text-sm">Memuat...</td></tr>
                ) : assets.length === 0 ? (
                  <tr><td colSpan={8} className="text-center py-8 text-muted-foreground text-sm">Tidak ada aset ditemukan</td></tr>
                ) : (
                  assets.map(a => (
                    <tr key={a.id} className="hover:bg-muted/30 cursor-pointer transition-colors"
                      onClick={() => { setSelectedAsset(a); }}
                      data-testid={`asset-row-${a.id}`}>
                      <td className="px-3 py-2.5 text-xs font-mono text-muted-foreground">{a.asset_number}</td>
                      <td className="px-3 py-2.5 text-sm font-medium">{a.name}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{a.category_name}</td>
                      <td className="px-3 py-2.5 text-sm">{fmtCurrency(a.purchase_cost)}</td>
                      <td className="px-3 py-2.5 text-sm text-emerald-600 font-medium">
                        {fmtCurrency((a.purchase_cost || 0) - (a.accumulated_depreciation || 0))}
                      </td>
                      <td className="px-3 py-2.5"><StatusBadge status={a.status} configMap={STATUS_CONFIG} /></td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{a.assigned_to_name || '-'}</td>
                      <td className="px-3 py-2.5">
                        <Button variant="ghost" size="icon" className="h-7 w-7">
                          <ChevronRight size={14} />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {assetPagination.total > 0 && (
            <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <span>Total: {assetPagination.total} aset</span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={assetPagination.page <= 1}
                  onClick={() => loadAssets(assetPagination.page - 1)}>Sebelumnya</Button>
                <span className="self-center">{assetPagination.page} / {assetPagination.total_pages}</span>
                <Button variant="outline" size="sm" disabled={assetPagination.page >= assetPagination.total_pages}
                  onClick={() => loadAssets(assetPagination.page + 1)}>Selanjutnya</Button>
              </div>
            </div>
          )}
        </TabsContent>

        {/* CATEGORIES TAB */}
        <TabsContent value="categories" className="mt-4">
          <div className="mb-3">
            <p className="text-sm text-muted-foreground">
              Konfigurasi kategori aset dan mapping ke Chart of Accounts (COA) untuk integrasi finance
            </p>
          </div>
          <div className="rounded-xl border overflow-hidden">
            <table className="w-full" data-testid="category-table">
              <thead className="bg-muted/40">
                <tr>
                  {['Kode','Nama','Umur Manfaat','Metode Depresiasi','COA Aset','COA Depresiasi',''].map(h => (
                    <th key={h} className="text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide px-4 py-2.5">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {categories.map(c => (
                  <tr key={c.id} className="hover:bg-muted/30 transition-colors" data-testid={`category-row-${c.id}`}>
                    <td className="px-4 py-2.5 text-xs font-mono">{c.code}</td>
                    <td className="px-4 py-2.5 text-sm font-medium">{c.name}</td>
                    <td className="px-4 py-2.5 text-sm">{c.useful_life_years} tahun</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">
                      {c.depr_method === 'straight_line' ? 'Garis Lurus' : 'Saldo Menurun'}
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {c.coa_asset_account ? (
                        <span className="text-emerald-600 font-mono">{c.coa_asset_account}</span>
                      ) : (
                        <span className="text-muted-foreground italic">Belum diset</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {c.coa_depreciation_account ? (
                        <span className="text-amber-600 font-mono">{c.coa_depreciation_account}</span>
                      ) : (
                        <span className="text-muted-foreground italic">Belum diset</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <Button variant="ghost" size="sm" 
                        onClick={() => { setSelectedCategory(c); setShowEditCategory(true); }}
                        data-testid={`edit-cat-btn-${c.id}`}>
                        <Edit size={14} className="mr-1" /> Konfigurasi
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        {/* PROCUREMENT TAB */}
        <TabsContent value="procurement" className="mt-4">
          <Tabs value={prTab} onValueChange={setPrTab}>
            <TabsList>
              <TabsTrigger value="all">Semua Request</TabsTrigger>
              <TabsTrigger value="inbox">
                Inbox Approval
                {prInbox.length > 0 && (
                  <Badge className="ml-1 text-[10px] h-4 px-1.5 bg-amber-500 text-white">{prInbox.length}</Badge>
                )}
              </TabsTrigger>
            </TabsList>

            {/* All PRs */}
            <TabsContent value="all" className="mt-3">
              <div className="flex gap-2 mb-3">
                <div className="relative flex-1 max-w-sm">
                  <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="Cari request..." className="pl-8" value={prSearch}
                    onChange={e => setPrSearch(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && loadPRs()} />
                </div>
                <Button size="sm" onClick={loadPRs}><RefreshCw size={14} /></Button>
              </div>
              <div className="space-y-2">
                {prData.map(pr => (
                  <div key={pr.id}
                    className="flex items-center justify-between py-3 px-4 bg-[hsl(var(--card))] rounded-xl border cursor-pointer hover:bg-muted/30 transition-colors"
                    onClick={() => setSelectedPR(pr)}
                    data-testid={`pr-row-${pr.id}`}>
                    <div className="flex items-start gap-3">
                      <ShoppingCart size={16} className="text-muted-foreground mt-0.5" />
                      <div>
                        <p className="text-sm font-medium">{pr.title}</p>
                        <p className="text-xs text-muted-foreground">{pr.request_number} · {pr.requested_by_name}</p>
                      </div>
                    </div>
                    <div className="text-right flex items-center gap-3">
                      <div>
                        <p className="text-sm font-semibold">{fmtCurrency(pr.total_estimated)}</p>
                        <p className="text-xs text-muted-foreground">{fmtDate(pr.created_at)}</p>
                      </div>
                      <StatusBadge status={pr.status} configMap={PR_STATUS_CONFIG} />
                    </div>
                  </div>
                ))}
                {prData.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground">
                    <ShoppingCart size={32} className="mx-auto mb-2 opacity-40" />
                    <p className="text-sm">Belum ada request pengadaan</p>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Approval Inbox */}
            <TabsContent value="inbox" className="mt-3">
              {/* Filter Toolbar */}
              <div className="flex flex-wrap items-center gap-2 mb-3 p-3 bg-muted/30 rounded-lg border" data-testid="inbox-filter-toolbar">
                <span className="text-xs font-medium text-muted-foreground mr-1">Tampilkan:</span>
                <Select value={inboxScope} onValueChange={setInboxScope}>
                  <SelectTrigger className="h-8 w-[180px] text-xs" data-testid="inbox-scope-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="relevant">📥 Untuk Saya (sesuai role)</SelectItem>
                    {isAdminLike && <SelectItem value="all">🌐 Semua Pending</SelectItem>}
                    <SelectItem value="mine">📤 Permintaan Saya</SelectItem>
                  </SelectContent>
                </Select>
                {isAdminLike && uniqueDepartments.length > 0 && (
                  <Select value={inboxDept || '__all__'} onValueChange={(v) => setInboxDept(v === '__all__' ? '' : v)}>
                    <SelectTrigger className="h-8 w-[160px] text-xs" data-testid="inbox-dept-select">
                      <SelectValue placeholder="Semua Departemen" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__all__">Semua Departemen</SelectItem>
                      {uniqueDepartments.map(d => (
                        <SelectItem key={d} value={d}>{d}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                <Button variant="ghost" size="sm" className="h-8 px-2 text-xs ml-auto" onClick={loadPRs} data-testid="inbox-refresh-btn">
                  <RefreshCw size={12} className="mr-1" /> Muat ulang
                </Button>
              </div>

              <div className="space-y-2">
                {prInbox.map(pr => (
                  <div key={pr.id}
                    className={`flex items-center justify-between py-3 px-4 border rounded-xl cursor-pointer transition-colors ${
                      pr.can_approve === false
                        ? 'bg-muted/30 border-border/60 hover:bg-muted/50'
                        : 'bg-amber-500/5 border-amber-500/20 hover:bg-amber-500/10'
                    }`}
                    onClick={() => setSelectedPR(pr)}
                    data-testid={`inbox-item-${pr.request_number}`}>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">{pr.title}</p>
                        {pr.can_approve === false && (
                          <Badge variant="outline" className="text-[10px] h-4 px-1.5">read-only</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {pr.request_number} · {pr.requested_by_name} · {pr.department || '—'}
                      </p>
                    </div>
                    <div className="text-right flex items-center gap-3 shrink-0">
                      <span className="text-sm font-bold">{fmtCurrency(pr.total_estimated)}</span>
                      <StatusBadge status={pr.status} configMap={PR_STATUS_CONFIG} />
                    </div>
                  </div>
                ))}
                {prInbox.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground">
                    <CheckCheck size={32} className="mx-auto mb-2 opacity-40" />
                    <p className="text-sm">
                      {inboxScope === 'mine'
                        ? 'Anda belum memiliki request pending.'
                        : inboxScope === 'all'
                          ? 'Tidak ada request menunggu approval.'
                          : 'Tidak ada request yang menunggu persetujuan Anda.'}
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </TabsContent>

        {/* ── DISPOSAL REQUESTS TAB ─────────────────────────────────────── */}
        <TabsContent value="disposal-requests" className="mt-4" data-testid="disposal-requests-tab">
          <DisposalApprovalInbox
            token={token}
            userRole={user?.role}
            onRefresh={() => { loadAssets(); loadDashboard(); }}
          />
        </TabsContent>

        {/* ── UTILIZATION REPORT TAB (Session 28) ───────────────────────── */}
        <TabsContent value="utilization" className="mt-4">
          <UtilizationReportTab token={token} categories={categories} />
        </TabsContent>

        {/* ── PREDICTIVE MAINTENANCE ALERTS TAB (Session 28) ────────────── */}
        <TabsContent value="pm-alerts" className="mt-4">
          <PredictiveMaintenanceTab token={token} categories={categories} />
        </TabsContent>
      </Tabs>

      {/* Modals & Drawers */}
      <CreateAssetDialog
        open={showCreateAsset}
        onClose={() => setShowCreateAsset(false)}
        token={token}
        categories={categories}
        onCreated={(a) => { loadAssets(); loadDashboard(); }}
      />
      <BulkImportDialog
        open={showBulkImport}
        onClose={() => setShowBulkImport(false)}
        token={token}
        categories={categories}
        onImported={() => { loadAssets(); loadDashboard(); loadExpiringAlerts(); }}
      />
      <DisposalRequestDialog
        open={showDisposalRequest}
        onClose={() => { setShowDisposalRequest(false); setAssetForDisposal(null); }}
        token={token}
        asset={assetForDisposal}
        onRequested={() => { loadAssets(); loadDashboard(); setSelectedAsset(null); }}
      />
      <AssetDetailDrawer
        asset={selectedAsset}
        token={token}
        open={!!selectedAsset}
        onClose={() => setSelectedAsset(null)}
        onRefresh={() => { loadAssets(); loadDashboard(); }}
        onTransferClick={(asset) => { setAssetToTransfer(asset); setShowTransferAsset(true); }}
        onRequestDisposalClick={(asset) => { setAssetForDisposal(asset); setShowDisposalRequest(true); }}
      />
      <CreatePRDialog
        open={showCreatePR}
        onClose={() => setShowCreatePR(false)}
        token={token}
        onCreated={() => loadPRs()}
      />
      <PRDetailDrawer
        pr={selectedPR}
        token={token}
        open={!!selectedPR}
        onClose={() => setSelectedPR(null)}
        onRefresh={loadPRs}
        currentUser={user}
      />
      <EditCategoryDialog
        open={showEditCategory}
        onClose={() => { setShowEditCategory(false); setSelectedCategory(null); }}
        token={token}
        category={selectedCategory}
        onUpdated={() => { loadCategories(); }}
      />
      {showAssetScanner && (
        <AssetScannerModal
          token={token}
          onScanned={(asset, details) => {
            setShowAssetScanner(false);
            toast.success(`Asset ${asset.asset_number} berhasil di-scan!`, {
              description: `Lokasi: ${details.location || asset.location || '-'}`,
            });
            loadAssets();
            loadDashboard();
          }}
          onClose={() => setShowAssetScanner(false)}
        />
      )}
      <TransferAssetDialog
        open={showTransferAsset}
        onClose={() => { setShowTransferAsset(false); setAssetToTransfer(null); }}
        token={token}
        asset={assetToTransfer}
        onTransferred={() => { loadAssets(); loadDashboard(); }}
      />
    </div>
  );
}
