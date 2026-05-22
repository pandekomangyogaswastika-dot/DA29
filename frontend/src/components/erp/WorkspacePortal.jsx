/**
 * WorkspacePortal.jsx — Personal Document Management & Spreadsheet Editor
 * CV. Dewi Aditya ERP
 *
 * Features:
 *  P0: Create/edit/delete, Share Dialog, delete rows, add/delete columns
 *  P1: Auto-save (2s), permission badges, read-only mode, rename inline
 *  P2: Import dari modul Assets & Procurement
 *  P3: Excel import 2-step (preview + column mapping)
 *  P5: Cell formatting (Bold/Italic/Color/Align), Formula bar (=SUM/AVG/COUNT),
 *      Version history (save snapshot, view, restore)
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { DataGrid, SelectColumn } from 'react-data-grid';
import 'react-data-grid/lib/styles.css';
import {
  FileSpreadsheet, Plus, Search, Share2, Trash2, Edit3,
  Clock, Users, Download, Upload, Save, ChevronRight,
  Package, Loader2, X, Check, Lock, Crown, Eye, Pencil,
  Columns, RefreshCw, AlertCircle, History, RotateCcw,
  Bold, Italic, AlignLeft, AlignCenter, AlignRight,
  ChevronDown, Sigma, Palette,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const apicall = async (method, path, token, body = null) => {
  const opts = {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(`${API}${path}`, opts);
  let data;
  try { data = await r.json(); } catch { data = {}; }
  if (!r.ok) throw Object.assign(new Error(data?.detail || `HTTP ${r.status}`), { status: r.status });
  return data;
};

const fmtTime = (iso) => {
  if (!iso) return '-';
  const d = new Date(iso);
  const diffMins = Math.floor((Date.now() - d) / 60000);
  if (diffMins < 1) return 'Baru saja';
  if (diffMins < 60) return `${diffMins} mnt lalu`;
  const diffH = Math.floor(diffMins / 60);
  if (diffH < 24) return `${diffH} jam lalu`;
  return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: '2-digit' });
};

const fmtIso = (iso) => {
  if (!iso) return '';
  return new Date(iso).toLocaleString('id-ID', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const ACCESS_CONFIG = {
  owner:  { label: 'Milik Saya',  icon: Crown,  cls: 'bg-violet-100 text-violet-700 border-violet-200' },
  admin:  { label: 'Admin',       icon: Crown,  cls: 'bg-blue-100 text-blue-700 border-blue-200' },
  edit:   { label: 'Bisa Edit',   icon: Pencil, cls: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  view:   { label: 'Lihat Saja',  icon: Eye,    cls: 'bg-amber-100 text-amber-700 border-amber-200' },
};

const canEdit  = (lv) => ['owner','admin','edit'].includes(lv);
const canShare = (lv) => ['owner','admin'].includes(lv);

function AccessBadge({ level }) {
  const cfg = ACCESS_CONFIG[level] || ACCESS_CONFIG.view;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${cfg.cls}`}>
      <Icon size={10} />{cfg.label}
    </span>
  );
}

// ─── Formula Evaluator ───────────────────────────────────────────────────────

const evaluateFormula = (formula, rows, colKey) => {
  if (!formula.startsWith('=')) return formula;
  const expr = formula.slice(1).trim().toUpperCase();
  // Match =FUNC(col_key) e.g. =SUM(price)
  const m = expr.match(/^(SUM|AVG|COUNT|MIN|MAX)\(([\w]+)\)$/);
  if (!m) return formula; // unsupported
  const [, func, col] = m;
  const vals = rows
    .map(r => parseFloat(r[col]))
    .filter(v => !isNaN(v));
  if (vals.length === 0) return func === 'COUNT' ? 0 : '';
  switch (func) {
    case 'SUM':   return vals.reduce((a, b) => a + b, 0);
    case 'AVG':   return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2);
    case 'COUNT': return vals.length;
    case 'MIN':   return Math.min(...vals);
    case 'MAX':   return Math.max(...vals);
    default:      return formula;
  }
};

// ─── ShareDialog ──────────────────────────────────────────────────────────────

function ShareDialog({ open, onClose, document: doc, token, onShared }) {
  const [search, setSearch] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [shares, setShares] = useState([]);
  const [busy, setBusy] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (open && doc) {
      setShares(doc.permissions?.shared_with || []);
      setSearch(''); setResults([]);
    }
  }, [open, doc]);

  const handleSearch = (q) => {
    setSearch(q);
    clearTimeout(timerRef.current);
    if (!q.trim()) { setResults([]); return; }
    timerRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await apicall('GET', `/api/auth/users?search=${encodeURIComponent(q)}&limit=10`, token);
        const ex = new Set([...(shares.map(s => s.user_id)), doc?.owner_id]);
        setResults(Array.isArray(data) ? data.filter(u => !ex.has(u.id)) : []);
      } catch { setResults([]); } finally { setSearching(false); }
    }, 300);
  };

  const handleAdd = async (user, access = 'view') => {
    setBusy(user.id);
    try {
      await apicall('POST', `/api/workspace/documents/${doc.id}/share`, token, { user_id: user.id, access });
      const ns = { user_id: user.id, user_name: user.name, access };
      const newShares = [...shares, ns];
      setShares(newShares);
      setResults(prev => prev.filter(u => u.id !== user.id));
      toast.success(`${user.name} diberi akses ${access}`);
      if (onShared) onShared({ ...doc, permissions: { ...doc.permissions, shared_with: newShares } });
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };

  const handleChangeAccess = async (userId, access) => {
    setBusy(userId);
    try {
      await apicall('POST', `/api/workspace/documents/${doc.id}/share`, token, { user_id: userId, access });
      setShares(prev => prev.map(s => s.user_id === userId ? { ...s, access } : s));
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };

  const handleRevoke = async (userId, name) => {
    if (!window.confirm(`Cabut akses ${name}?`)) return;
    setBusy(userId);
    try {
      await apicall('DELETE', `/api/workspace/documents/${doc.id}/share/${userId}`, token);
      setShares(prev => prev.filter(s => s.user_id !== userId));
      toast.success(`Akses ${name} dicabut`);
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  };

  if (!doc) return null;
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md" data-testid="share-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Share2 size={18} />Bagikan "{doc.name}"</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <div className="relative">
            {searching ? <Loader2 size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 animate-spin text-muted-foreground" /> : <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />}
            <Input placeholder="Cari user..." value={search} onChange={e => handleSearch(e.target.value)} className="pl-8 text-sm" data-testid="share-search-input" />
          </div>
          {results.length > 0 && (
            <div className="border rounded-lg overflow-hidden">
              {results.map(u => (
                <div key={u.id} className="flex items-center justify-between p-2.5 hover:bg-muted/50 border-b last:border-0">
                  <div><p className="text-sm font-medium">{u.name}</p><p className="text-xs text-muted-foreground">{u.email}</p></div>
                  <div className="flex gap-1.5">
                    <Button size="sm" variant="outline" className="h-7 text-xs" disabled={busy === u.id} onClick={() => handleAdd(u,'view')}><Eye size={12} className="mr-1" />View</Button>
                    <Button size="sm" className="h-7 text-xs" disabled={busy === u.id} onClick={() => handleAdd(u,'edit')}><Pencil size={12} className="mr-1" />Edit</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <Separator />
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground mb-2">Akses saat ini</p>
          <div className="flex items-center justify-between py-2 px-2 rounded-md bg-muted/30">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-violet-100 flex items-center justify-center"><Crown size={13} className="text-violet-600" /></div>
              <div><p className="text-sm font-medium">{doc.owner_name || 'Owner'}</p><p className="text-xs text-muted-foreground">Pemilik</p></div>
            </div>
            <Badge variant="secondary" className="text-xs">Owner</Badge>
          </div>
          {shares.length === 0 && <p className="text-xs text-muted-foreground text-center py-3">Belum dibagikan ke siapapun</p>}
          {shares.map(s => (
            <div key={s.user_id} className="flex items-center justify-between py-2 px-2 rounded-md hover:bg-muted/20">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-bold">{(s.user_name||'?')[0].toUpperCase()}</div>
                <p className="text-sm">{s.user_name}</p>
              </div>
              <div className="flex items-center gap-2">
                <Select value={s.access} onValueChange={v => handleChangeAccess(s.user_id, v)} disabled={!!busy}>
                  <SelectTrigger className="h-7 w-[90px] text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="view">Lihat</SelectItem>
                    <SelectItem value="edit">Edit</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive" disabled={busy===s.user_id} onClick={() => handleRevoke(s.user_id, s.user_name)} data-testid={`share-revoke-${s.user_id}`}>
                  {busy===s.user_id ? <Loader2 size={12} className="animate-spin" /> : <X size={12} />}
                </Button>
              </div>
            </div>
          ))}
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose} className="w-full">Tutup</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── ManageColumnsDialog ──────────────────────────────────────────────────────

function AddColumnDialog({ open, onClose, onAdd }) {
  const [name, setName] = useState('');
  const [type, setType] = useState('text');
  const handleAdd = () => {
    if (!name.trim()) { toast.error('Nama kolom wajib diisi'); return; }
    const key = `${name.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'') || 'col'}_${Date.now()}`;
    onAdd({ key, name: name.trim(), type, editable: true, width: 160 });
    setName(''); setType('text'); onClose();
  };
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-sm" data-testid="add-column-dialog">
        <DialogHeader><DialogTitle>Tambah Kolom</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><label className="text-sm font-medium mb-1 block">Nama Kolom *</label>
            <Input placeholder="Contoh: Jumlah, Keterangan..." value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key==='Enter' && handleAdd()} autoFocus data-testid="add-column-name" /></div>
          <div><label className="text-sm font-medium mb-1 block">Tipe Data</label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger data-testid="add-column-type"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="text">Teks</SelectItem><SelectItem value="number">Angka</SelectItem></SelectContent>
            </Select></div>
        </div>
        <DialogFooter className="gap-2"><Button variant="outline" onClick={onClose}>Batal</Button><Button onClick={handleAdd} data-testid="add-column-submit">Tambah</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ManageColumnsDialog({ open, onClose, columns, onDelete, onAdd }) {
  const [showAdd, setShowAdd] = useState(false);
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-sm" data-testid="manage-columns-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Columns size={16} />Kelola Kolom</DialogTitle></DialogHeader>
        <ScrollArea className="max-h-56">
          <div className="space-y-1 pr-1">
            {columns.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">Belum ada kolom</p>}
            {columns.map((col, i) => (
              <div key={col.key} className="flex items-center justify-between p-2 rounded-md hover:bg-muted/30 border">
                <div><p className="text-sm font-medium">{col.name}</p><p className="text-xs text-muted-foreground capitalize">{col.type||'text'}</p></div>
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive"
                  onClick={() => window.confirm(`Hapus kolom "${col.name}"?`) && onDelete(col.key)}
                  data-testid={`delete-col-${i}`}><Trash2 size={12} /></Button>
              </div>
            ))}
          </div>
        </ScrollArea>
        {showAdd
          ? <AddColumnDialog open={showAdd} onClose={() => setShowAdd(false)} onAdd={(col) => { onAdd(col); setShowAdd(false); }} />
          : <Button variant="outline" className="w-full" onClick={() => setShowAdd(true)} data-testid="open-add-column"><Plus size={14} className="mr-1" />Tambah Kolom</Button>}
        <DialogFooter><Button variant="outline" onClick={onClose} className="w-full">Selesai</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Excel Import 2-Step Dialog ───────────────────────────────────────────────

function ImportExcelDialog({ open, onClose, token, onImported }) {
  const [step, setStep] = useState(1); // 1=upload, 2=mapping, 3=importing
  const [preview, setPreview] = useState(null); // { columns, preview_rows, total_rows }
  const [mapping, setMapping] = useState([]);   // [{ original_name, key, name, type, include }]
  const [docName, setDocName] = useState('');
  const [fileData, setFileData] = useState(null); // base64
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileRef = useRef(null);

  const reset = () => { setStep(1); setPreview(null); setMapping([]); setDocName(''); setFileData(null); };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.match(/\.xlsx?$/i)) { toast.error('File harus .xlsx atau .xls'); return; }
    setUploading(true);
    try {
      // Upload for preview
      const fd = new FormData(); fd.append('file', file);
      const res = await fetch(`${API}/api/workspace/documents/preview-excel`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Preview gagal');
      setPreview(data);
      setDocName(file.name.replace(/\.[^.]+$/, ''));
      setMapping(data.columns.map(c => ({ ...c, key: c.suggested_key, name: c.suggested_name })));

      // Also read as base64 for final import
      const reader = new FileReader();
      reader.onload = () => setFileData(reader.result.split(',')[1]);
      reader.readAsDataURL(file);

      setStep(2);
    } catch (e) { toast.error(e.message || 'Upload gagal'); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  };

  const handleImport = async () => {
    const included = mapping.filter(m => m.include);
    if (included.length === 0) { toast.error('Pilih minimal satu kolom'); return; }
    setImporting(true);
    try {
      const doc = await apicall('POST', '/api/workspace/documents/import-excel-mapped', token, {
        file_data: fileData,
        column_mapping: mapping,
        doc_name: docName || 'Import Excel',
      });
      toast.success(`${doc.content?.rows?.length || 0} baris berhasil diimport ke "${doc.name}"`);
      onImported(doc); onClose(); reset();
    } catch (e) { toast.error(e.message || 'Import gagal'); }
    finally { setImporting(false); }
  };

  const updateMapping = (idx, field, value) => {
    setMapping(prev => prev.map((m, i) => i === idx ? { ...m, [field]: value } : m));
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { onClose(); reset(); } }}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] flex flex-col" data-testid="import-excel-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload size={16} />
            Import Excel
            <span className="text-xs font-normal text-muted-foreground">Langkah {step} dari 2</span>
          </DialogTitle>
          <div className="flex gap-1 mt-2">
            {[1,2].map(s => (
              <div key={s} className={`h-1 flex-1 rounded-full ${step >= s ? 'bg-primary' : 'bg-muted'}`} />
            ))}
          </div>
        </DialogHeader>

        <ScrollArea className="flex-1 overflow-auto">
          {step === 1 && (
            <div className="flex flex-col items-center justify-center py-10 gap-4">
              <div className="w-16 h-16 rounded-2xl bg-emerald-100 flex items-center justify-center">
                <FileSpreadsheet size={32} className="text-emerald-600" />
              </div>
              <div className="text-center">
                <p className="font-medium">Pilih file Excel untuk diimport</p>
                <p className="text-sm text-muted-foreground mt-1">Format yang didukung: .xlsx, .xls</p>
              </div>
              <Button onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="excel-file-btn">
                {uploading ? <Loader2 size={14} className="animate-spin mr-1" /> : <Upload size={14} className="mr-1" />}
                {uploading ? 'Membaca file...' : 'Pilih File Excel'}
              </Button>
              <input ref={fileRef} type="file" accept=".xlsx,.xls" onChange={handleFileSelect} className="hidden" />
            </div>
          )}

          {step === 2 && preview && (
            <div className="space-y-4 p-1">
              {/* Summary */}
              <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                <FileSpreadsheet size={20} className="text-emerald-600" />
                <div>
                  <p className="text-sm font-medium">{preview.file_name}</p>
                  <p className="text-xs text-muted-foreground">{preview.total_rows} baris data · {preview.columns.length} kolom</p>
                </div>
              </div>

              {/* Doc name */}
              <div>
                <label className="text-sm font-medium mb-1 block">Nama Dokumen</label>
                <Input value={docName} onChange={e => setDocName(e.target.value)} placeholder="Nama spreadsheet..." data-testid="excel-doc-name" />
              </div>

              {/* Column Mapping */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium">Mapping Kolom</p>
                  <div className="flex gap-2">
                    <button className="text-xs text-primary" onClick={() => setMapping(prev => prev.map(m => ({ ...m, include: true })))}>Pilih semua</button>
                    <span className="text-muted-foreground">·</span>
                    <button className="text-xs text-muted-foreground" onClick={() => setMapping(prev => prev.map(m => ({ ...m, include: false })))}>Hapus semua</button>
                  </div>
                </div>
                <div className="border rounded-lg overflow-hidden">
                  <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-muted/40 text-xs font-medium text-muted-foreground border-b">
                    <div className="col-span-1">Import</div>
                    <div className="col-span-3">Kolom Excel</div>
                    <div className="col-span-4">Nama di Spreadsheet</div>
                    <div className="col-span-2">Tipe</div>
                    <div className="col-span-2">Contoh Data</div>
                  </div>
                  {mapping.map((m, idx) => (
                    <div key={idx} className={`grid grid-cols-12 gap-2 px-3 py-2 items-center border-b last:border-0 text-sm ${!m.include ? 'opacity-50' : ''}`}>
                      <div className="col-span-1">
                        <input type="checkbox" checked={m.include} onChange={e => updateMapping(idx, 'include', e.target.checked)} className="rounded" />
                      </div>
                      <div className="col-span-3 text-xs text-muted-foreground truncate" title={m.original_name}>{m.original_name}</div>
                      <div className="col-span-4">
                        <Input value={m.name} onChange={e => updateMapping(idx, 'name', e.target.value)} className="h-7 text-xs" disabled={!m.include} />
                      </div>
                      <div className="col-span-2">
                        <Select value={m.type} onValueChange={v => updateMapping(idx, 'type', v)} disabled={!m.include}>
                          <SelectTrigger className="h-7 text-xs"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="text">Teks</SelectItem>
                            <SelectItem value="number">Angka</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="col-span-2 text-xs text-muted-foreground truncate">
                        {preview.preview_rows[0]?.[m.original_name] || '-'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Data Preview */}
              <div>
                <p className="text-sm font-medium mb-2">Preview Data (10 baris pertama)</p>
                <div className="border rounded-lg overflow-x-auto">
                  <table className="text-xs w-full">
                    <thead className="bg-muted/40">
                      <tr>
                        {mapping.filter(m => m.include).map(m => (
                          <th key={m.original_name} className="px-3 py-2 text-left font-medium border-b border-r last:border-r-0 whitespace-nowrap">{m.name}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.preview_rows.map((row, ri) => (
                        <tr key={ri} className="border-b last:border-0 hover:bg-muted/20">
                          {mapping.filter(m => m.include).map(m => (
                            <td key={m.original_name} className="px-3 py-1.5 border-r last:border-r-0 whitespace-nowrap max-w-[120px] truncate">{row[m.original_name] || ''}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </ScrollArea>

        <DialogFooter className="gap-2 pt-3 border-t">
          {step === 2 && (
            <Button variant="outline" onClick={() => { setStep(1); setPreview(null); }} disabled={importing}>
              ← Kembali
            </Button>
          )}
          <Button variant="outline" onClick={() => { onClose(); reset(); }} disabled={importing || uploading}>Batal</Button>
          {step === 2 && (
            <Button onClick={handleImport} disabled={importing || mapping.filter(m => m.include).length === 0} data-testid="excel-import-submit">
              {importing ? <Loader2 size={14} className="animate-spin mr-1" /> : <Download size={14} className="mr-1" />}
              {importing ? 'Mengimport...' : `Import ${mapping.filter(m => m.include).length} Kolom`}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Import from Module Dialog ─────────────────────────────────────────────────

const ASSET_FIELDS = [
  { key: 'asset_number', label: 'Nomor Aset' }, { key: 'name', label: 'Nama' },
  { key: 'category_name', label: 'Kategori' }, { key: 'department', label: 'Departemen' },
  { key: 'location', label: 'Lokasi' }, { key: 'brand', label: 'Merek' },
  { key: 'model', label: 'Model' }, { key: 'serial_number', label: 'Serial Number' },
  { key: 'purchase_date', label: 'Tgl Perolehan' }, { key: 'purchase_cost', label: 'Harga Beli' },
  { key: 'residual_value', label: 'Nilai Sisa' }, { key: 'status', label: 'Status' },
  { key: 'assigned_to_name', label: 'Ditugaskan Ke' },
];
const PROCUREMENT_FIELDS = [
  { key: 'request_number', label: 'Nomor PR' }, { key: 'title', label: 'Judul' },
  { key: 'department', label: 'Departemen' }, { key: 'requested_by_name', label: 'Peminta' },
  { key: 'priority', label: 'Prioritas' }, { key: 'total_estimated', label: 'Total Estimasi' },
  { key: 'status', label: 'Status' },
];
const DEF_ASSET_FIELDS = ['asset_number','name','category_name','department','location','purchase_cost','status'];
const DEF_PR_FIELDS = ['request_number','title','department','requested_by_name','total_estimated','status'];

function ImportFromModuleDialog({ open, onClose, token, onImported }) {
  const [module, setModule] = useState('assets');
  const [docName, setDocName] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [selFields, setSelFields] = useState(DEF_ASSET_FIELDS);
  const [importing, setImporting] = useState(false);

  const allFields = module === 'assets' ? ASSET_FIELDS : PROCUREMENT_FIELDS;

  useEffect(() => {
    setSelFields(module === 'assets' ? DEF_ASSET_FIELDS : DEF_PR_FIELDS);
    setStatusFilter(''); setDeptFilter('');
  }, [module]);

  const handleImport = async () => {
    if (selFields.length === 0) { toast.error('Pilih minimal satu kolom'); return; }
    setImporting(true);
    try {
      const filters = {};
      if (statusFilter) filters.status = statusFilter;
      if (deptFilter) filters.department = deptFilter;
      const data = await apicall('POST', '/api/workspace/documents/import-from-module', token, {
        module, name: docName || undefined, filters, fields: selFields,
      });
      toast.success(`${data.imported_count} data berhasil diimport ke "${data.name}"`);
      onImported(data); onClose();
    } catch (e) { toast.error(e.message || 'Import gagal'); } finally { setImporting(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md" data-testid="import-module-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Package size={16} />Import dari Modul Sistem</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Modul Sumber</label>
            <Select value={module} onValueChange={setModule}>
              <SelectTrigger data-testid="import-module-select"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="assets">Manajemen Aset</SelectItem><SelectItem value="procurement">Pengadaan (PR)</SelectItem></SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Nama Dokumen (opsional)</label>
            <Input placeholder="Biarkan kosong untuk nama otomatis..." value={docName} onChange={e => setDocName(e.target.value)} data-testid="import-doc-name" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs font-medium text-muted-foreground mb-1 block">Filter Status</label><Input placeholder="Semua status" value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="text-sm h-8" /></div>
            <div><label className="text-xs font-medium text-muted-foreground mb-1 block">Filter Departemen</label><Input placeholder="Semua dept." value={deptFilter} onChange={e => setDeptFilter(e.target.value)} className="text-sm h-8" /></div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-muted-foreground">Pilih Kolom</label>
              <button className="text-xs text-primary" onClick={() => setSelFields(allFields.map(f => f.key))}>Pilih semua</button>
            </div>
            <div className="grid grid-cols-2 gap-1 max-h-40 overflow-y-auto border rounded-md p-2">
              {allFields.map(f => (
                <label key={f.key} className="flex items-center gap-1.5 text-xs cursor-pointer hover:bg-muted/30 rounded px-1 py-0.5">
                  <input type="checkbox" checked={selFields.includes(f.key)} onChange={() => setSelFields(prev => prev.includes(f.key) ? prev.filter(k => k !== f.key) : [...prev, f.key])} className="rounded" />
                  {f.label}
                </label>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={importing}>Batal</Button>
          <Button onClick={handleImport} disabled={importing || selFields.length === 0} data-testid="import-module-submit">
            {importing ? <Loader2 size={14} className="animate-spin mr-1" /> : <Download size={14} className="mr-1" />}
            {importing ? 'Mengimport...' : `Import ${module === 'assets' ? 'Aset' : 'Pengadaan'}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Version History Drawer ───────────────────────────────────────────────────

function VersionHistoryDrawer({ open, onClose, docId, token, onRestored }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(null);

  useEffect(() => {
    if (open && docId) {
      setLoading(true);
      apicall('GET', `/api/workspace/documents/${docId}/versions`, token)
        .then(setVersions).catch(() => toast.error('Gagal memuat versi'))
        .finally(() => setLoading(false));
    }
  }, [open, docId, token]);

  const handleRestore = async (v) => {
    if (!window.confirm(`Restore ke "${v.label}"? Perubahan yang belum disimpan akan hilang.`)) return;
    setRestoring(v.id);
    try {
      await apicall('POST', `/api/workspace/documents/${docId}/versions/${v.id}/restore`, token, {});
      toast.success(`Berhasil restore ke ${v.label}`);
      onRestored();
      onClose();
    } catch (e) { toast.error(e.message); } finally { setRestoring(null); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md" data-testid="version-history-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><History size={16} />Riwayat Versi</DialogTitle></DialogHeader>
        {loading
          ? <div className="flex justify-center py-8"><Loader2 size={24} className="animate-spin text-muted-foreground" /></div>
          : versions.length === 0
            ? <p className="text-sm text-muted-foreground text-center py-8">Belum ada versi tersimpan.<br /><span className="text-xs">Klik "Simpan" untuk membuat snapshot versi.</span></p>
            : (
              <ScrollArea className="max-h-96">
                <div className="space-y-2 pr-1">
                  {versions.map((v, idx) => (
                    <div key={v.id} className={`flex items-center justify-between p-3 rounded-lg border ${idx === 0 ? 'border-primary/40 bg-primary/5' : 'hover:bg-muted/30'}`}>
                      <div>
                        <p className="text-sm font-medium">{v.label}</p>
                        <p className="text-xs text-muted-foreground">{fmtIso(v.saved_at)} · {v.saved_by_name}</p>
                      </div>
                      <div className="flex gap-2 items-center">
                        {idx === 0 && <Badge variant="secondary" className="text-xs">Terbaru</Badge>}
                        {idx !== 0 && (
                          <Button variant="outline" size="sm" className="h-7 text-xs" disabled={restoring === v.id}
                            onClick={() => handleRestore(v)} data-testid={`restore-version-${idx}`}>
                            {restoring === v.id ? <Loader2 size={12} className="animate-spin mr-1" /> : <RotateCcw size={12} className="mr-1" />}
                            Restore
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )
        }
        <DialogFooter><Button variant="outline" onClick={onClose} className="w-full">Tutup</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Cell Formatting Toolbar ──────────────────────────────────────────────────

const COLORS = [
  { label: 'Merah',   val: '#ef4444' }, { label: 'Oranye',  val: '#f97316' },
  { label: 'Kuning',  val: '#eab308' }, { label: 'Hijau',   val: '#22c55e' },
  { label: 'Biru',    val: '#3b82f6' }, { label: 'Ungu',    val: '#a855f7' },
  { label: 'Default', val: '' },
];
const BG_COLORS = [
  { label: 'Merah Muda', val: '#fecaca' }, { label: 'Oranye Muda', val: '#fed7aa' },
  { label: 'Kuning Muda', val: '#fef08a' }, { label: 'Hijau Muda', val: '#bbf7d0' },
  { label: 'Biru Muda',  val: '#bfdbfe' }, { label: 'Ungu Muda',  val: '#e9d5ff' },
  { label: 'Default',    val: '' },
];

function FormattingToolbar({ selectedCell, formatting, onFormat, readOnly }) {
  const [showTextColor, setShowTextColor] = useState(false);
  const [showBgColor, setShowBgColor] = useState(false);

  if (readOnly || !selectedCell) return null;
  const key = selectedCell ? `${selectedCell.rowId}:${selectedCell.colKey}` : null;
  const fmt = key ? (formatting[key] || {}) : {};

  const apply = (k, v) => {
    if (!key) return;
    onFormat(key, { ...fmt, [k]: v });
  };
  const toggle = (k) => apply(k, !fmt[k]);

  return (
    <div className="flex items-center gap-1 px-3 py-1.5 bg-card border-b text-xs" data-testid="formatting-toolbar">
      <span className="text-muted-foreground mr-1 text-[10px]">FORMAT:</span>
      <Button variant={fmt.bold ? 'default' : 'ghost'} size="sm" className="h-6 w-6 p-0" onClick={() => toggle('bold')} title="Bold" data-testid="fmt-bold">
        <Bold size={12} />
      </Button>
      <Button variant={fmt.italic ? 'default' : 'ghost'} size="sm" className="h-6 w-6 p-0" onClick={() => toggle('italic')} title="Italic" data-testid="fmt-italic">
        <Italic size={12} />
      </Button>
      <div className="w-px h-4 bg-border mx-1" />
      <Button variant={fmt.align === 'left' ? 'default' : 'ghost'} size="sm" className="h-6 w-6 p-0" onClick={() => apply('align','left')} title="Rata Kiri" data-testid="fmt-align-left">
        <AlignLeft size={12} />
      </Button>
      <Button variant={fmt.align === 'center' ? 'default' : 'ghost'} size="sm" className="h-6 w-6 p-0" onClick={() => apply('align','center')} title="Tengah">
        <AlignCenter size={12} />
      </Button>
      <Button variant={fmt.align === 'right' ? 'default' : 'ghost'} size="sm" className="h-6 w-6 p-0" onClick={() => apply('align','right')} title="Rata Kanan">
        <AlignRight size={12} />
      </Button>
      <div className="w-px h-4 bg-border mx-1" />
      {/* Text color */}
      <div className="relative">
        <Button variant="ghost" size="sm" className="h-6 px-1.5 gap-1" onClick={() => { setShowTextColor(v => !v); setShowBgColor(false); }} title="Warna Teks" data-testid="fmt-text-color">
          <span className="text-xs font-bold" style={{ color: fmt.color || 'currentColor' }}>A</span>
          <ChevronDown size={8} />
        </Button>
        {showTextColor && (
          <div className="absolute top-7 left-0 z-50 bg-card border rounded-lg shadow-lg p-2 flex flex-wrap gap-1 w-28">
            {COLORS.map(c => (
              <button key={c.val} className={`w-5 h-5 rounded border-2 ${fmt.color === c.val ? 'border-primary' : 'border-transparent'} ${!c.val ? 'bg-muted text-[8px]' : ''}`}
                style={{ backgroundColor: c.val || undefined }}
                title={c.label}
                onClick={() => { apply('color', c.val); setShowTextColor(false); }}
              >{!c.val ? '−' : ''}</button>
            ))}
          </div>
        )}
      </div>
      {/* BG color */}
      <div className="relative">
        <Button variant="ghost" size="sm" className="h-6 px-1.5 gap-1" onClick={() => { setShowBgColor(v => !v); setShowTextColor(false); }} title="Warna Background" data-testid="fmt-bg-color">
          <Palette size={12} style={{ color: fmt.bgColor || 'currentColor' }} />
          <ChevronDown size={8} />
        </Button>
        {showBgColor && (
          <div className="absolute top-7 left-0 z-50 bg-card border rounded-lg shadow-lg p-2 flex flex-wrap gap-1 w-28">
            {BG_COLORS.map(c => (
              <button key={c.val} className={`w-5 h-5 rounded border-2 ${fmt.bgColor === c.val ? 'border-primary' : 'border-transparent'} ${!c.val ? 'bg-muted text-[8px]' : ''}`}
                style={{ backgroundColor: c.val || undefined }}
                title={c.label}
                onClick={() => { apply('bgColor', c.val); setShowBgColor(false); }}
              >{!c.val ? '−' : ''}</button>
            ))}
          </div>
        )}
      </div>
      {key && (
        <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px] text-muted-foreground ml-1"
          onClick={() => onFormat(key, {})} title="Reset format sel ini">
          Reset
        </Button>
      )}
    </div>
  );
}

// ─── Formula Bar ──────────────────────────────────────────────────────────────

function FormulaBar({ selectedCell, rows, onUpdateCell, readOnly }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState('');

  useEffect(() => {
    if (!selectedCell) return;
    setVal(String(selectedCell.rawVal ?? ''));
    setEditing(false);
  }, [selectedCell]);

  if (!selectedCell) return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/20 border-b text-xs text-muted-foreground" data-testid="formula-bar">
      <Sigma size={13} className="shrink-0" />
      <span>Pilih sel untuk melihat/edit nilai</span>
    </div>
  );

  const { rowId, colKey, rawVal } = selectedCell;
  const displayVal = String(rawVal ?? '');
  const isFormula = displayVal.startsWith('=');
  const computed = isFormula ? String(evaluateFormula(displayVal, rows, colKey)) : displayVal;

  const commit = () => {
    setEditing(false);
    onUpdateCell(rowId, colKey, val);
  };

  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-muted/10 border-b" data-testid="formula-bar">
      <Sigma size={13} className="shrink-0 text-muted-foreground" />
      <span className="text-xs text-muted-foreground font-mono shrink-0">{colKey}</span>
      <div className="w-px h-4 bg-border shrink-0" />
      {editing && !readOnly ? (
        <Input
          value={val}
          onChange={e => setVal(e.target.value)}
          onBlur={commit}
          onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditing(false); }}
          autoFocus
          className="h-6 text-xs font-mono flex-1 border-0 bg-transparent focus-visible:ring-0 p-0"
          placeholder="Masukkan nilai atau =FORMULA(kolom)..."
        />
      ) : (
        <div
          className={`flex-1 text-xs font-mono cursor-text truncate ${isFormula ? 'text-primary' : ''}`}
          onClick={() => !readOnly && setEditing(true)}
          title={isFormula ? `Formula: ${displayVal}\nHasil: ${computed}` : displayVal}
          data-testid="formula-bar-value"
        >
          {isFormula ? (
            <span className="flex items-center gap-2">
              <span className="text-primary">{displayVal}</span>
              <span className="text-muted-foreground">= {computed}</span>
            </span>
          ) : displayVal || <span className="text-muted-foreground">Kosong — klik untuk edit</span>}
        </div>
      )}
      {isFormula && (
        <Badge variant="secondary" className="text-[10px] shrink-0">Formula</Badge>
      )}
    </div>
  );
}

// ─── Grid Editor View ─────────────────────────────────────────────────────────

function GridEditorView({ document: initDoc, token, onBack, onUpdated }) {
  const [doc, setDoc]           = useState(initDoc);
  const [rows, setRows]         = useState([]);
  const [columns, setColumns]   = useState([]);
  const [formatting, setFormatting] = useState({});
  const [selectedRows, setSelectedRows] = useState(() => new Set());
  const [selectedCell, setSelectedCell] = useState(null); // { rowId, colKey, rawVal }
  const [saving, setSaving]     = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved');
  const [renaming, setRenaming] = useState(false);
  const [newName, setNewName]   = useState('');
  const [showShare, setShowShare] = useState(false);
  const [showManageCols, setShowManageCols] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const [exporting, setExporting] = useState(false);
  const saveTimerRef = useRef(null);
  const isReadOnly = !canEdit(doc?.access_level);

  useEffect(() => {
    if (initDoc) {
      setDoc(initDoc);
      const content = initDoc.content || {};
      setColumns(content.columns || []);
      setRows(content.rows || []);
      setFormatting(content.formatting || {});
      setSaveStatus('saved');
    }
  }, [initDoc]);

  // ── Save ──
  const handleSave = useCallback(async (rowsToSave, colsToSave, fmtToSave) => {
    if (isReadOnly) return;
    setSaving(true); setSaveStatus('saving');
    try {
      await apicall('PUT', `/api/workspace/documents/${doc.id}`, token, {
        content: { columns: colsToSave, rows: rowsToSave, formatting: fmtToSave },
      });
      setSaveStatus('saved');
      if (onUpdated) onUpdated();
    } catch {
      toast.error('Gagal auto-save'); setSaveStatus('pending');
    } finally { setSaving(false); }
  }, [doc, token, onUpdated, isReadOnly]);

  const queueSave = useCallback((r, c, f) => {
    setSaveStatus('pending');
    clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => handleSave(r, c, f), 2000);
  }, [handleSave]);

  const manualSave = async () => {
    clearTimeout(saveTimerRef.current);
    await handleSave(rows, columns, formatting);
    // Save version snapshot
    try {
      await apicall('POST', `/api/workspace/documents/${doc.id}/versions`, token, {
        content: { columns, rows, formatting },
      });
    } catch { /* non-critical */ }
  };

  // ── Rows ──
  const handleRowsChange = (newRows) => {
    if (isReadOnly) return;
    setRows(newRows);
    queueSave(newRows, columns, formatting);
  };
  const handleAddRow = () => {
    if (isReadOnly) return;
    const newRow = { id: `row_${Date.now()}` };
    columns.forEach(col => { newRow[col.key] = ''; });
    const newRows = [...rows, newRow];
    setRows(newRows); queueSave(newRows, columns, formatting);
  };
  const handleDeleteSelected = () => {
    if (isReadOnly || selectedRows.size === 0) return;
    if (!window.confirm(`Hapus ${selectedRows.size} baris?`)) return;
    const newRows = rows.filter(r => !selectedRows.has(r.id));
    setRows(newRows); setSelectedRows(new Set());
    queueSave(newRows, columns, formatting);
    toast.success(`${selectedRows.size} baris dihapus`);
  };

  // ── Columns ──
  const handleAddColumn = (colDef) => {
    if (isReadOnly) return;
    const newCols = [...columns, colDef];
    const newRows = rows.map(r => ({ ...r, [colDef.key]: '' }));
    setColumns(newCols); setRows(newRows);
    queueSave(newRows, newCols, formatting);
    toast.success(`Kolom "${colDef.name}" ditambahkan`);
  };
  const handleDeleteColumn = (key) => {
    if (isReadOnly) return;
    const newCols = columns.filter(c => c.key !== key);
    const newRows = rows.map(r => { const nr = { ...r }; delete nr[key]; return nr; });
    const newFmt = Object.fromEntries(Object.entries(formatting).filter(([k]) => !k.includes(`:${key}`)));
    setColumns(newCols); setRows(newRows); setFormatting(newFmt);
    queueSave(newRows, newCols, newFmt);
  };

  // ── Cell Formatting ──
  const handleFormat = (fmtKey, fmtVal) => {
    const newFmt = { ...formatting, [fmtKey]: fmtVal };
    setFormatting(newFmt);
    queueSave(rows, columns, newFmt);
  };

  // ── Cell Update (from formula bar) ──
  const handleUpdateCell = (rowId, colKey, val) => {
    const newRows = rows.map(r => r.id === rowId ? { ...r, [colKey]: val } : r);
    setRows(newRows); queueSave(newRows, columns, formatting);
  };

  // ── Rename ──
  const startRename = () => { if (canEdit(doc?.access_level)) { setNewName(doc.name); setRenaming(true); } };
  const commitRename = async () => {
    const trimmed = newName.trim();
    if (!trimmed || trimmed === doc.name) { setRenaming(false); return; }
    try {
      await apicall('PUT', `/api/workspace/documents/${doc.id}`, token, { name: trimmed });
      setDoc(prev => ({ ...prev, name: trimmed })); if (onUpdated) onUpdated();
      toast.success('Nama diperbarui');
    } catch (e) { toast.error(e.message); } finally { setRenaming(false); }
  };

  // ── Export Excel ──
  const handleExportExcel = async () => {
    setExporting(true);
    try {
      const response = await fetch(`${API}/api/workspace/documents/${doc.id}/export-excel`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error('Export gagal');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a'); a.href = url; a.download = `${doc.name.replace(/ /g,'_')}.xlsx`;
      window.document.body.appendChild(a); a.click();
      window.URL.revokeObjectURL(url); window.document.body.removeChild(a);
      toast.success('File Excel berhasil didownload');
    } catch { toast.error('Gagal export Excel'); } finally { setExporting(false); }
  };

  // ── Build DataGrid columns ──
  const gridColumns = useMemo(() => [
    ...(!isReadOnly ? [SelectColumn] : []),
    ...columns.map(col => ({
      key: col.key,
      name: col.name,
      editable: !isReadOnly,
      resizable: true,
      width: col.width || 150,
      renderCell: ({ row, column }) => {
        const rawVal = row[column.key];
        const fmtKey = `${row.id}:${column.key}`;
        const fmt = formatting[fmtKey] || {};
        const displayVal = typeof rawVal === 'string' && rawVal.startsWith('=')
          ? evaluateFormula(rawVal, rows, column.key)
          : rawVal;
        const isSelected = selectedCell?.rowId === row.id && selectedCell?.colKey === column.key;
        return (
          <div
            style={{
              fontWeight: fmt.bold ? 'bold' : 'normal',
              fontStyle: fmt.italic ? 'italic' : 'normal',
              color: fmt.color || undefined,
              backgroundColor: fmt.bgColor || undefined,
              textAlign: fmt.align || 'left',
              width: '100%', height: '100%',
              padding: '0 8px',
              display: 'flex', alignItems: 'center',
              outline: isSelected ? '2px solid hsl(var(--primary))' : 'none',
            }}
            onClick={() => setSelectedCell({ rowId: row.id, colKey: column.key, rawVal })}
          >
            {String(displayVal ?? '')}
          </div>
        );
      },
    })),
  ], [columns, formatting, selectedCell, rows, isReadOnly]);

  const saveIndicator = isReadOnly ? null : (
    <span className="text-xs flex items-center gap-1" data-testid="save-status">
      {saveStatus === 'saving'  && <><Loader2 size={11} className="animate-spin" /><span className="text-muted-foreground">Menyimpan...</span></>}
      {saveStatus === 'pending' && <><AlertCircle size={11} className="text-amber-500" /><span className="text-amber-600">Belum disimpan</span></>}
      {saveStatus === 'saved'   && <><Check size={11} className="text-emerald-500" /><span className="text-muted-foreground">Tersimpan</span></>}
    </span>
  );

  return (
    <div className="flex flex-col h-full" data-testid="grid-editor-view">
      {/* Header */}
      <div className="border-b bg-card px-4 py-3 shrink-0">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2 min-w-0">
            <Button variant="ghost" size="sm" onClick={onBack} className="shrink-0" data-testid="back-btn"><ChevronRight size={16} className="rotate-180" /></Button>
            {renaming ? (
              <Input value={newName} onChange={e => setNewName(e.target.value)} onKeyDown={e => { if (e.key==='Enter') commitRename(); if (e.key==='Escape') setRenaming(false); }} onBlur={commitRename} autoFocus className="h-7 text-sm font-semibold w-64" data-testid="rename-input" />
            ) : (
              <div className="flex items-center gap-1.5 min-w-0">
                <h2 className="text-base font-semibold truncate" data-testid="doc-title">{doc?.name}</h2>
                {canEdit(doc?.access_level) && <Button variant="ghost" size="sm" className="h-6 w-6 p-0 shrink-0" onClick={startRename} data-testid="rename-btn"><Edit3 size={12} /></Button>}
              </div>
            )}
            <AccessBadge level={doc?.access_level} />
          </div>
          <div className="flex gap-2 shrink-0">
            {isReadOnly && <span className="flex items-center gap-1 text-xs text-amber-600 border border-amber-200 bg-amber-50 px-2 py-1 rounded-md"><Lock size={12} />Hanya Lihat</span>}
            {saveIndicator}
            {canShare(doc?.access_level) && <Button variant="outline" size="sm" onClick={() => setShowShare(true)} data-testid="share-btn"><Share2 size={14} className="mr-1" />Share</Button>}
            <Button variant="outline" size="sm" onClick={handleExportExcel} disabled={exporting} data-testid="export-excel-btn">
              {exporting ? <Loader2 size={14} className="animate-spin mr-1" /> : <Download size={14} className="mr-1" />}Excel
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowVersions(true)} data-testid="version-history-btn">
              <History size={14} className="mr-1" />Versi
            </Button>
          </div>
        </div>
        {/* Edit Toolbar */}
        {!isReadOnly && (
          <div className="flex gap-2 flex-wrap">
            <Button size="sm" onClick={manualSave} disabled={saving || saveStatus==='saved'} data-testid="manual-save-btn">
              {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : <Save size={14} className="mr-1" />}
              {saving ? 'Menyimpan...' : 'Simpan'}
            </Button>
            <Button size="sm" variant="outline" onClick={handleAddRow} data-testid="add-row-btn"><Plus size={14} className="mr-1" />Baris Baru</Button>
            <Button size="sm" variant="outline" onClick={() => setShowManageCols(true)} data-testid="manage-cols-btn"><Columns size={14} className="mr-1" />Kolom</Button>
            {selectedRows.size > 0 && (
              <Button size="sm" variant="destructive" onClick={handleDeleteSelected} data-testid="delete-rows-btn"><Trash2 size={14} className="mr-1" />Hapus {selectedRows.size} Baris</Button>
            )}
          </div>
        )}
      </div>

      {/* Formula Bar */}
      <FormulaBar selectedCell={selectedCell} rows={rows} onUpdateCell={handleUpdateCell} readOnly={isReadOnly} />

      {/* Formatting Toolbar */}
      <FormattingToolbar selectedCell={selectedCell} formatting={formatting} onFormat={handleFormat} readOnly={isReadOnly} />

      {/* Grid */}
      <div className="flex-1 overflow-hidden">
        {gridColumns.length === 0 && !isReadOnly ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
            <Columns size={40} className="opacity-30" />
            <p className="text-sm">Belum ada kolom.</p>
            <Button size="sm" variant="outline" onClick={() => setShowManageCols(true)}><Plus size={14} className="mr-1" />Tambah Kolom</Button>
          </div>
        ) : (
          <DataGrid
            columns={gridColumns}
            rows={rows}
            rowKeyGetter={(row) => row.id}
            onRowsChange={handleRowsChange}
            selectedRows={selectedRows}
            onSelectedRowsChange={setSelectedRows}
            className="h-full"
            style={{
              '--rdg-background-color': 'hsl(var(--background))',
              '--rdg-header-background-color': 'hsl(var(--muted))',
              '--rdg-row-hover-background-color': 'hsl(var(--accent))',
              '--rdg-border-color': 'hsl(var(--border))',
              '--rdg-color': 'hsl(var(--foreground))',
              '--rdg-selection-color': 'hsl(var(--primary))',
              height: '100%',
            }}
            data-testid="data-grid"
          />
        )}
      </div>

      {/* Footer */}
      <div className="border-t bg-card px-4 py-2 shrink-0 flex items-center justify-between">
        <p className="text-xs text-muted-foreground">{rows.length} baris · {columns.length} kolom{selectedRows.size > 0 && ` · ${selectedRows.size} dipilih`}</p>
        {isReadOnly && <p className="text-xs text-amber-500 flex items-center gap-1"><Lock size={11} />Mode baca saja</p>}
      </div>

      {/* Dialogs */}
      <ShareDialog open={showShare} onClose={() => setShowShare(false)} document={doc} token={token} onShared={(u) => setDoc(prev => ({ ...prev, ...u }))} />
      <ManageColumnsDialog open={showManageCols} onClose={() => setShowManageCols(false)} columns={columns} onDelete={handleDeleteColumn} onAdd={handleAddColumn} />
      <VersionHistoryDrawer open={showVersions} onClose={() => setShowVersions(false)} docId={doc?.id} token={token}
        onRestored={async () => {
          const updated = await apicall('GET', `/api/workspace/documents/${doc.id}`, token);
          setDoc(updated);
          setColumns(updated.content?.columns || []);
          setRows(updated.content?.rows || []);
          setFormatting(updated.content?.formatting || {});
          setSaveStatus('saved');
        }}
      />
    </div>
  );
}

// ─── Document Card ────────────────────────────────────────────────────────────

function DocCard({ doc, onOpen, onDelete, onShare, showDelete, showShare }) {
  return (
    <Card className="hover:shadow-md transition-all cursor-pointer group border" onClick={() => onOpen(doc.id)} data-testid={`doc-card-${doc.id}`}>
      <CardContent className="p-4 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <FileSpreadsheet size={20} className="text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="font-medium text-sm truncate">{doc.name}</h3>
            <AccessBadge level={doc.access_level} />
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {!doc.is_owner && <span>oleh {doc.owner_name}</span>}
            <span className="flex items-center gap-1"><Clock size={11} />{fmtTime(doc.updated_at)}</span>
            <span>{doc.metadata?.row_count ?? 0} baris · {doc.metadata?.column_count ?? 0} kolom</span>
          </div>
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {showShare && (
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={(e) => { e.stopPropagation(); onShare(doc); }} data-testid={`share-doc-${doc.id}`}>
              <Share2 size={14} />
            </Button>
          )}
          {showDelete && (
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-destructive hover:text-destructive" onClick={(e) => { e.stopPropagation(); onDelete(doc.id, doc.name); }} data-testid={`delete-doc-${doc.id}`}>
              <Trash2 size={14} />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Main WorkspacePortal ─────────────────────────────────────────────────────

export default function WorkspacePortal({ token, user }) {
  const [documents, setDocuments] = useState({ owned: [], shared: [] });
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showNewDoc, setShowNewDoc] = useState(false);
  const [showImportExcel, setShowImportExcel] = useState(false);
  const [showImportModule, setShowImportModule] = useState(false);
  const [shareTarget, setShareTarget] = useState(null);
  const [importingExcel, setImportingExcel] = useState(false);
  const fileInputRef = useRef(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apicall('GET', '/api/workspace/documents', token);
      setDocuments(data);
    } catch { toast.error('Gagal memuat dokumen'); } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { loadDocuments(); }, [loadDocuments]);

  const handleDocOpen = async (docId) => {
    try {
      const doc = await apicall('GET', `/api/workspace/documents/${docId}`, token);
      setSelectedDoc(doc);
    } catch (e) { toast.error(e.message || 'Gagal membuka dokumen'); }
  };

  const handleDocDelete = async (docId, docName) => {
    if (!window.confirm(`Hapus "${docName}"?`)) return;
    try {
      await apicall('DELETE', `/api/workspace/documents/${docId}`, token);
      toast.success('Dokumen dihapus'); loadDocuments();
    } catch (e) { toast.error(e.message); }
  };

  // Quick Excel import (old 1-step, kept for quick action)
  const handleQuickExcelImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.match(/\.xlsx?$/i)) { toast.error('File harus .xlsx atau .xls'); return; }
    setImportingExcel(true);
    const fd = new FormData(); fd.append('file', file);
    try {
      const res = await fetch(`${API}/api/workspace/documents/import-excel`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd });
      const doc = await res.json();
      if (!res.ok) throw new Error(doc.detail || 'Import gagal');
      toast.success(`Excel berhasil diimport: "${doc.name}"`);
      loadDocuments(); setSelectedDoc(doc);
    } catch (e) { toast.error(e.message); }
    finally { setImportingExcel(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const filteredOwned  = documents.owned.filter(d => d.name.toLowerCase().includes(searchQuery.toLowerCase()));
  const filteredShared = documents.shared.filter(d => d.name.toLowerCase().includes(searchQuery.toLowerCase()));

  if (selectedDoc) {
    return (
      <GridEditorView
        document={selectedDoc}
        token={token}
        onBack={() => setSelectedDoc(null)}
        onUpdated={loadDocuments}
      />
    );
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-background via-background to-muted/20" data-testid="workspace-portal">
      <div className="border-b bg-card/50 backdrop-blur-sm shrink-0">
        <div className="p-6 pb-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold">My Workspace</h1>
              <p className="text-sm text-muted-foreground mt-1">Personal document management & spreadsheet editor</p>
            </div>
            <Button onClick={() => setShowNewDoc(true)} data-testid="new-doc-btn">
              <Plus size={16} className="mr-1" />Spreadsheet Baru
            </Button>
          </div>
          <div className="relative max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Cari dokumen..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} className="pl-9" data-testid="doc-search" />
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="text-center py-12">
              <Loader2 size={32} className="animate-spin mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground mt-2">Memuat dokumen...</p>
            </div>
          ) : (
            <>
              {/* Quick Actions */}
              <div className="grid grid-cols-3 gap-4">
                <Card className="cursor-pointer hover:bg-accent/50 hover:shadow-md transition-all border-dashed" onClick={() => setShowNewDoc(true)} data-testid="quick-new-spreadsheet">
                  <CardContent className="p-5 text-center">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mx-auto mb-2"><Plus size={20} className="text-primary" /></div>
                    <p className="text-sm font-medium">Spreadsheet Baru</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Mulai dari kosong</p>
                  </CardContent>
                </Card>

                <Card className="cursor-pointer hover:bg-accent/50 hover:shadow-md transition-all border-dashed" onClick={() => setShowImportExcel(true)} data-testid="quick-import-excel">
                  <CardContent className="p-5 text-center">
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center mx-auto mb-2">
                      {importingExcel ? <Loader2 size={20} className="text-emerald-600 animate-spin" /> : <Upload size={20} className="text-emerald-600" />}
                    </div>
                    <p className="text-sm font-medium">Import Excel</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Preview + mapping kolom</p>
                  </CardContent>
                </Card>
                <input type="file" ref={fileInputRef} onChange={handleQuickExcelImport} accept=".xlsx,.xls" className="hidden" />

                <Card className="cursor-pointer hover:bg-accent/50 hover:shadow-md transition-all border-dashed" onClick={() => setShowImportModule(true)} data-testid="quick-import-module">
                  <CardContent className="p-5 text-center">
                    <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center mx-auto mb-2"><Package size={20} className="text-blue-600" /></div>
                    <p className="text-sm font-medium">Import dari Modul</p>
                    <p className="text-xs text-muted-foreground mt-0.5">Aset, Pengadaan</p>
                  </CardContent>
                </Card>
              </div>

              {/* My Documents */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-base font-semibold flex items-center gap-2">
                    <FileSpreadsheet size={17} className="text-primary" />
                    Dokumen Saya
                    <Badge variant="secondary" className="text-xs">{filteredOwned.length}</Badge>
                  </h2>
                  <Button variant="ghost" size="sm" onClick={loadDocuments} className="h-7"><RefreshCw size={13} /></Button>
                </div>
                {filteredOwned.length === 0 ? (
                  <Card><CardContent className="p-10 text-center">
                    <FileSpreadsheet size={40} className="mx-auto text-muted-foreground/30 mb-3" />
                    <p className="text-sm text-muted-foreground">{searchQuery ? 'Tidak ada dokumen yang cocok' : 'Belum ada dokumen.'}</p>
                    {!searchQuery && <Button size="sm" variant="outline" className="mt-3" onClick={() => setShowNewDoc(true)}><Plus size={13} className="mr-1" />Buat Sekarang</Button>}
                  </CardContent></Card>
                ) : (
                  <div className="grid gap-2.5">
                    {filteredOwned.map(doc => (
                      <DocCard key={doc.id} doc={doc} onOpen={handleDocOpen} onDelete={handleDocDelete} onShare={() => setShareTarget(doc)} showDelete showShare />
                    ))}
                  </div>
                )}
              </div>

              {/* Shared with Me */}
              {filteredShared.length > 0 && (
                <div>
                  <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
                    <Users size={17} className="text-blue-600" />Dibagikan ke Saya
                    <Badge variant="secondary" className="text-xs">{filteredShared.length}</Badge>
                  </h2>
                  <div className="grid gap-2.5">
                    {filteredShared.map(doc => (
                      <DocCard key={doc.id} doc={doc} onOpen={handleDocOpen} onDelete={handleDocDelete} onShare={() => setShareTarget(doc)} showDelete={doc.is_owner} showShare={canShare(doc.access_level)} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Dialogs */}
      <Dialog open={showNewDoc} onOpenChange={(v) => !v && setShowNewDoc(false)}>
        <DialogContent className="sm:max-w-sm" data-testid="new-doc-dialog">
          <DialogHeader><DialogTitle>Spreadsheet Baru</DialogTitle></DialogHeader>
          <NewDocForm token={token} onCreated={(doc) => { loadDocuments(); setSelectedDoc(doc); setShowNewDoc(false); }} onClose={() => setShowNewDoc(false)} />
        </DialogContent>
      </Dialog>

      <ImportExcelDialog open={showImportExcel} onClose={() => setShowImportExcel(false)} token={token} onImported={(doc) => { loadDocuments(); setSelectedDoc(doc); }} />
      <ImportFromModuleDialog open={showImportModule} onClose={() => setShowImportModule(false)} token={token} onImported={(doc) => { loadDocuments(); setSelectedDoc(doc); }} />
      <ShareDialog open={!!shareTarget} onClose={() => setShareTarget(null)} document={shareTarget} token={token} onShared={() => loadDocuments()} />
    </div>
  );
}

function NewDocForm({ token, onCreated, onClose }) {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const handleCreate = async () => {
    if (!name.trim()) { toast.error('Nama dokumen wajib diisi'); return; }
    setLoading(true);
    try {
      const doc = await apicall('POST', '/api/workspace/documents', token, { name: name.trim() });
      toast.success('Spreadsheet baru dibuat!'); onCreated(doc);
    } catch (e) { toast.error(e.message); } finally { setLoading(false); }
  };
  return (
    <>
      <Input placeholder="Nama spreadsheet..." value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key==='Enter' && !loading && handleCreate()} autoFocus data-testid="new-doc-name-input" />
      <DialogFooter className="gap-2">
        <Button variant="outline" onClick={onClose}>Batal</Button>
        <Button onClick={handleCreate} disabled={loading || !name.trim()} data-testid="new-doc-submit">
          {loading ? <Loader2 size={14} className="animate-spin mr-1" /> : <Plus size={14} className="mr-1" />}Buat
        </Button>
      </DialogFooter>
    </>
  );
}
