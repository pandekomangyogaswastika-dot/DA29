import { useState, useEffect, useCallback, useMemo } from 'react';
import { Star, Plus, Edit2, Trash2, RefreshCw, Package, Users, TrendingUp, Search, Send } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { PageHeader } from './moduleAtoms';

const API_BASE = process.env.REACT_APP_BACKEND_URL;

const CATEGORY_LABELS = { power_partner: 'Power Partner', potential: 'Potential', viral_maker: 'Viral Maker', active: 'Aktif', passive: 'Pasif' };
const CATEGORY_COLORS = {
  power_partner: 'bg-amber-500/15 text-amber-300 border-amber-400/25',
  potential: 'bg-blue-500/15 text-blue-300 border-blue-400/25',
  viral_maker: 'bg-pink-500/15 text-pink-300 border-pink-400/25',
  active: 'bg-green-500/15 text-green-300 border-green-400/25',
  passive: 'bg-foreground/10 text-foreground/50 border-foreground/15',
};
const DEAL_TYPE_LABELS = { live_stream: 'Live Stream', tiktok_video: 'TikTok Video', feed_post: 'Feed Post', story: 'Story', review: 'Review' };
const DEAL_STATUS_COLORS = {
  draft: 'bg-amber-500/15 text-amber-300 border-amber-400/25',
  active: 'bg-green-500/15 text-green-300 border-green-400/25',
  completed: 'bg-blue-500/15 text-blue-300 border-blue-400/25',
  cancelled: 'bg-red-500/15 text-red-300 border-red-400/25',
};
const SAMPLE_STATUS_COLORS = {
  draft: 'bg-foreground/10 text-foreground/50 border-foreground/15',
  shipped: 'bg-blue-500/15 text-blue-300 border-blue-400/25',
  received: 'bg-amber-500/15 text-amber-300 border-amber-400/25',
  feedback: 'bg-purple-500/15 text-purple-300 border-purple-400/25',
  done: 'bg-green-500/15 text-green-300 border-green-400/25',
  cancelled: 'bg-red-500/15 text-red-300 border-red-400/25',
};

const CHANNEL_TYPES = ['tiktok_shop', 'shopee', 'tokopedia', 'instagram', 'youtube', 'other'];
const DEAL_TYPES = ['live_stream', 'tiktok_video', 'feed_post', 'story', 'review'];
const SAMPLE_STATUSES = ['draft', 'shipped', 'received', 'feedback', 'done', 'cancelled'];
const CATEGORIES = Object.keys(CATEGORY_LABELS);
const fmtDate = (d) => d ? new Date(d).toLocaleDateString('id-ID', { dateStyle: 'medium' }) : '-';

export default function TokoKOLModule({ token, defaultTab = 'kol' }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [summary, setSummary] = useState(null);

  // Creators
  const [creators, setCreators] = useState([]);
  const [creatorsLoading, setCreatorsLoading] = useState(false);
  const [creatorSearch, setCreatorSearch] = useState('');
  const [creatorCategoryFilter, setCreatorCategoryFilter] = useState('all');
  const [creatorDialog, setCreatorDialog] = useState(null);
  const [savingCreator, setSavingCreator] = useState(false);

  // Deals
  const [deals, setDeals] = useState([]);
  const [dealsLoading, setDealsLoading] = useState(false);
  const [dealDialog, setDealDialog] = useState(null);
  const [savingDeal, setSavingDeal] = useState(false);

  // Samples
  const [samples, setSamples] = useState([]);
  const [samplesLoading, setSamplesLoading] = useState(false);
  const [sampleDialog, setSampleDialog] = useState(null);
  const [savingSample, setSavingSample] = useState(false);

  const emptyCreator = { name: '', phone: '', address: '', city: '', channel_type: 'tiktok_shop', category: 'active', username: '', followers: '', notes: '', status: 'active' };
  const emptyDeal = { creator_id: '', products: [], deal_type: 'tiktok_video', commission_pct: 0, notes: '', start_date: '', end_date: '', status: 'draft' };
  const emptySample = { creator_id: '', deal_id: '', sku_code: '', product_name: '', qty: 1, notes: '' };

  const loadCreators = useCallback(async () => {
    setCreatorsLoading(true);
    try {
      const params = new URLSearchParams();
      if (creatorCategoryFilter !== 'all') params.set('category', creatorCategoryFilter);
      if (creatorSearch) params.set('search', creatorSearch);
      const [rC, rS] = await Promise.all([
        fetch(`${API_BASE}/api/dewi/kol/creators?${params}`, { headers }),
        fetch(`${API_BASE}/api/dewi/kol/summary`, { headers }),
      ]);
      if (rC.ok) setCreators(await rC.json());
      if (rS.ok) setSummary(await rS.json());
    } finally { setCreatorsLoading(false); }
  }, [headers, creatorCategoryFilter, creatorSearch]);

  const loadDeals = useCallback(async () => {
    setDealsLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/dewi/kol/deals`, { headers });
      if (r.ok) setDeals(await r.json());
    } finally { setDealsLoading(false); }
  }, [headers]);

  const loadSamples = useCallback(async () => {
    setSamplesLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/dewi/kol/samples`, { headers });
      if (r.ok) setSamples(await r.json());
    } finally { setSamplesLoading(false); }
  }, [headers]);

  useEffect(() => { loadCreators(); }, [loadCreators]);
  useEffect(() => { if (activeTab === 'deals') loadDeals(); }, [activeTab, loadDeals]);
  useEffect(() => { if (activeTab === 'samples') loadSamples(); }, [activeTab, loadSamples]);

  const saveCreator = async () => {
    if (!creatorDialog?.name?.trim()) { toast.error('Nama wajib diisi'); return; }
    setSavingCreator(true);
    try {
      const { id, ...body } = { ...creatorDialog, followers: creatorDialog.followers ? Number(creatorDialog.followers) : null };
      const url = id ? `${API_BASE}/api/dewi/kol/creators/${id}` : `${API_BASE}/api/dewi/kol/creators`;
      const r = await fetch(url, { method: id ? 'PUT' : 'POST', headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Gagal');
      toast.success(id ? 'Kreator diperbarui' : 'Kreator ditambahkan');
      setCreatorDialog(null);
      loadCreators();
    } catch (e) { toast.error(e.message); }
    finally { setSavingCreator(false); }
  };

  const deleteCreator = async (c) => {
    if (!window.confirm(`Hapus kreator ${c.name}?`)) return;
    const r = await fetch(`${API_BASE}/api/dewi/kol/creators/${c.id}`, { method: 'DELETE', headers });
    const d = await r.json();
    if (!r.ok) { toast.error(d.detail || 'Gagal'); return; }
    toast.success('Dihapus');
    loadCreators();
  };

  const saveDeal = async () => {
    if (!dealDialog?.creator_id) { toast.error('Pilih kreator'); return; }
    setSavingDeal(true);
    try {
      const { id, ...body } = { ...dealDialog, commission_pct: Number(dealDialog.commission_pct) };
      const url = id ? `${API_BASE}/api/dewi/kol/deals/${id}` : `${API_BASE}/api/dewi/kol/deals`;
      const r = await fetch(url, { method: id ? 'PUT' : 'POST', headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Gagal');
      toast.success(id ? 'Deal diperbarui' : `Deal ${d.deal_code} dibuat`);
      setDealDialog(null);
      loadDeals();
    } catch (e) { toast.error(e.message); }
    finally { setSavingDeal(false); }
  };

  const deleteDeal = async (d) => {
    if (!window.confirm(`Hapus deal ${d.deal_code}?`)) return;
    const r = await fetch(`${API_BASE}/api/dewi/kol/deals/${d.id}`, { method: 'DELETE', headers });
    const res = await r.json();
    if (!r.ok) { toast.error(res.detail || 'Gagal'); return; }
    toast.success('Dihapus');
    loadDeals();
  };

  const saveSample = async () => {
    if (!sampleDialog?.creator_id || !sampleDialog?.sku_code) { toast.error('Kreator dan SKU wajib diisi'); return; }
    setSavingSample(true);
    try {
      const { id, ...body } = { ...sampleDialog, qty: Number(sampleDialog.qty), sku_code: sampleDialog.sku_code.toUpperCase() };
      const url = id ? `${API_BASE}/api/dewi/kol/samples/${id}` : `${API_BASE}/api/dewi/kol/samples`;
      const r = await fetch(url, { method: id ? 'PUT' : 'POST', headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Gagal');
      toast.success(id ? 'Sample diperbarui' : `${d.sample_code} dibuat`);
      setSampleDialog(null);
      loadSamples();
    } catch (e) { toast.error(e.message); }
    finally { setSavingSample(false); }
  };

  const deleteSample = async (s) => {
    if (!window.confirm(`Hapus sample ${s.sample_code}?`)) return;
    const r = await fetch(`${API_BASE}/api/dewi/kol/samples/${s.id}`, { method: 'DELETE', headers });
    const d = await r.json();
    if (!r.ok) { toast.error(d.detail || 'Gagal'); return; }
    toast.success('Dihapus');
    loadSamples();
  };

  return (
    <div className="p-6 space-y-6" data-testid="toko-kol-module">
      <PageHeader
        title="KOL & Kreator"
        description="Database kreator/KOL, deal kampanye, dan tracking sample produk"
        icon={Star}
      />

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-3 gap-3">
          <GlassCard className="p-3 text-center">
            <div className="text-2xl font-bold text-amber-400">{summary.total_creators}</div>
            <div className="text-xs text-foreground/55">Kreator Aktif</div>
          </GlassCard>
          <GlassCard className="p-3 text-center">
            <div className="text-2xl font-bold text-green-400">{summary.total_deals_active}</div>
            <div className="text-xs text-foreground/55">Deal Aktif</div>
          </GlassCard>
          <GlassCard className="p-3 text-center">
            <div className="text-2xl font-bold text-blue-400">{summary.pending_samples}</div>
            <div className="text-xs text-foreground/55">Sample Pending</div>
          </GlassCard>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="kol" data-testid="tab-kol">Database KOL</TabsTrigger>
          <TabsTrigger value="deals" data-testid="tab-deals">Deal & Kampanye</TabsTrigger>
          <TabsTrigger value="samples" data-testid="tab-samples">Sample Tracking</TabsTrigger>
        </TabsList>

        {/* KOL Tab */}
        <TabsContent value="kol" className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <div className="relative flex-1 min-w-40">
              <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-foreground/40" />
              <Input placeholder="Cari nama / username / kota..." value={creatorSearch} onChange={e => setCreatorSearch(e.target.value)} className="pl-8" />
            </div>
            {['all', ...CATEGORIES].map(cat => (
              <button key={cat} onClick={() => setCreatorCategoryFilter(cat)}
                className={`px-3 py-1 rounded-full text-xs border transition-colors hidden sm:block ${
                  creatorCategoryFilter === cat ? 'bg-primary/15 border-primary/30 text-primary' : 'border-foreground/15 text-foreground/60 hover:border-foreground/30'
                }`}>
                {cat === 'all' ? 'Semua' : CATEGORY_LABELS[cat]}
              </button>
            ))}
            <Button size="sm" onClick={() => setCreatorDialog({ ...emptyCreator })} className="gap-1" data-testid="btn-add-creator">
              <Plus className="w-3.5 h-3.5" /> Tambah
            </Button>
          </div>
          {creatorsLoading ? (
            <div className="text-center py-8 text-foreground/40">Memuat...</div>
          ) : creators.length === 0 ? (
            <GlassCard className="p-10 text-center">
              <Users className="w-10 h-10 mx-auto mb-3 text-foreground/25" />
              <p className="text-foreground/50 text-sm">Belum ada kreator/KOL</p>
              <Button size="sm" className="mt-3" onClick={() => setCreatorDialog({ ...emptyCreator })}>+ Tambah Kreator</Button>
            </GlassCard>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {creators.map(c => (
                <GlassCard key={c.id} className="p-4" data-testid={`creator-card-${c.id}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-semibold text-sm">{c.name}</div>
                      {c.username && <div className="text-xs text-foreground/50">@{c.username}</div>}
                      <div className="flex gap-1.5 mt-1.5 flex-wrap">
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${CATEGORY_COLORS[c.category]}`}>{CATEGORY_LABELS[c.category]}</span>
                        <span className="text-xs text-foreground/40 capitalize">{c.channel_type}</span>
                      </div>
                      {c.followers && <div className="text-xs text-foreground/50 mt-1">{Number(c.followers).toLocaleString('id-ID')} followers</div>}
                      {c.city && <div className="text-xs text-foreground/40">{c.city}</div>}
                    </div>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setCreatorDialog({ ...c })} data-testid={`btn-edit-creator-${c.id}`}>
                        <Edit2 className="w-3 h-3" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7 text-red-400" onClick={() => deleteCreator(c)} data-testid={`btn-delete-creator-${c.id}`}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Deals Tab */}
        <TabsContent value="deals" className="space-y-4">
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setDealDialog({ ...emptyDeal, products: [] })} className="gap-1" data-testid="btn-add-deal">
              <Plus className="w-3.5 h-3.5" /> Deal Baru
            </Button>
          </div>
          {dealsLoading ? (
            <div className="text-center py-8 text-foreground/40">Memuat...</div>
          ) : deals.length === 0 ? (
            <GlassCard className="p-10 text-center">
              <TrendingUp className="w-10 h-10 mx-auto mb-3 text-foreground/25" />
              <p className="text-foreground/50 text-sm">Belum ada deal</p>
            </GlassCard>
          ) : (
            <div className="space-y-2">
              {deals.map(d => (
                <GlassCard key={d.id} className="p-4" data-testid={`deal-row-${d.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs text-foreground/50">{d.deal_code}</span>
                        <span className="font-semibold text-sm">{d.creator_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${DEAL_STATUS_COLORS[d.status]}`}>{d.status}</span>
                      </div>
                      <div className="text-xs text-foreground/50 mt-1">
                        {DEAL_TYPE_LABELS[d.deal_type]} &bull; Komisi: {d.commission_pct}%
                        {d.start_date && <span className="ml-2">{fmtDate(d.start_date)} &rarr; {fmtDate(d.end_date)}</span>}
                      </div>
                      {d.products?.length > 0 && (
                        <div className="text-xs text-foreground/40 mt-0.5">
                          {d.products.map(p => p.sku_code).join(', ')}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setDealDialog({ ...d, products: d.products || [] })} data-testid={`btn-edit-deal-${d.id}`}>
                        <Edit2 className="w-3 h-3" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7 text-red-400" onClick={() => deleteDeal(d)} data-testid={`btn-delete-deal-${d.id}`}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Samples Tab */}
        <TabsContent value="samples" className="space-y-4">
          <div className="flex justify-end">
            <Button size="sm" onClick={() => setSampleDialog({ ...emptySample })} className="gap-1" data-testid="btn-add-sample">
              <Plus className="w-3.5 h-3.5" /> Request Sample
            </Button>
          </div>
          {samplesLoading ? (
            <div className="text-center py-8 text-foreground/40">Memuat...</div>
          ) : samples.length === 0 ? (
            <GlassCard className="p-10 text-center">
              <Package className="w-10 h-10 mx-auto mb-3 text-foreground/25" />
              <p className="text-foreground/50 text-sm">Belum ada sample tracking</p>
            </GlassCard>
          ) : (
            <div className="space-y-2">
              {samples.map(s => (
                <GlassCard key={s.id} className="p-4" data-testid={`sample-row-${s.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs">{s.sample_code}</span>
                        <span className="font-medium text-sm">{s.creator_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${SAMPLE_STATUS_COLORS[s.status]}`}>{s.status}</span>
                      </div>
                      <div className="text-xs text-foreground/50 mt-1">
                        SKU: <span className="font-mono">{s.sku_code}</span> &bull; Qty: {s.qty}
                        {s.tracking_number && <span className="ml-2 font-mono text-primary">{s.tracking_number}</span>}
                      </div>
                      {s.feedback_notes && <div className="text-xs text-foreground/40 mt-0.5 italic">{s.feedback_notes}</div>}
                    </div>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setSampleDialog({ ...s })} data-testid={`btn-edit-sample-${s.id}`}>
                        <Edit2 className="w-3 h-3" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7 text-red-400" onClick={() => deleteSample(s)} data-testid={`btn-delete-sample-${s.id}`}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Creator Dialog */}
      {creatorDialog && (
        <Dialog open={!!creatorDialog} onOpenChange={() => setCreatorDialog(null)}>
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="dialog-creator">
            <DialogHeader><DialogTitle>{creatorDialog.id ? 'Edit Kreator' : 'Tambah Kreator'}</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <Label className="text-xs">Nama *</Label>
                  <Input className="mt-1" value={creatorDialog.name} onChange={e => setCreatorDialog(d => ({ ...d, name: e.target.value }))} data-testid="input-creator-name" />
                </div>
                <div>
                  <Label className="text-xs">Username</Label>
                  <Input className="mt-1" placeholder="@username" value={creatorDialog.username} onChange={e => setCreatorDialog(d => ({ ...d, username: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">No. HP</Label>
                  <Input className="mt-1" value={creatorDialog.phone} onChange={e => setCreatorDialog(d => ({ ...d, phone: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Channel Utama</Label>
                  <Select value={creatorDialog.channel_type} onValueChange={v => setCreatorDialog(d => ({ ...d, channel_type: v }))}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>{CHANNEL_TYPES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Kategori</Label>
                  <Select value={creatorDialog.category} onValueChange={v => setCreatorDialog(d => ({ ...d, category: v }))}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{CATEGORY_LABELS[c]}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Kota</Label>
                  <Input className="mt-1" value={creatorDialog.city} onChange={e => setCreatorDialog(d => ({ ...d, city: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Followers</Label>
                  <Input type="number" className="mt-1" min={0} value={creatorDialog.followers} onChange={e => setCreatorDialog(d => ({ ...d, followers: e.target.value }))} />
                </div>
                <div className="col-span-2">
                  <Label className="text-xs">Catatan</Label>
                  <Textarea className="mt-1" rows={2} value={creatorDialog.notes} onChange={e => setCreatorDialog(d => ({ ...d, notes: e.target.value }))} />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreatorDialog(null)}>Batal</Button>
              <Button onClick={saveCreator} disabled={savingCreator || !creatorDialog.name} data-testid="btn-save-creator">
                {savingCreator ? 'Menyimpan...' : 'Simpan'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Deal Dialog */}
      {dealDialog && (
        <Dialog open={!!dealDialog} onOpenChange={() => setDealDialog(null)}>
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="dialog-deal">
            <DialogHeader><DialogTitle>{dealDialog.id ? 'Edit Deal' : 'Deal Baru'}</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div>
                <Label className="text-xs">Kreator *</Label>
                <Select value={dealDialog.creator_id} onValueChange={v => setDealDialog(d => ({ ...d, creator_id: v }))}>
                  <SelectTrigger className="mt-1" data-testid="select-deal-creator"><SelectValue placeholder="Pilih kreator" /></SelectTrigger>
                  <SelectContent>{creators.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Tipe Deal</Label>
                  <Select value={dealDialog.deal_type} onValueChange={v => setDealDialog(d => ({ ...d, deal_type: v }))}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>{DEAL_TYPES.map(t => <SelectItem key={t} value={t}>{DEAL_TYPE_LABELS[t]}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Komisi %</Label>
                  <Input type="number" className="mt-1" min={0} max={100} value={dealDialog.commission_pct} onChange={e => setDealDialog(d => ({ ...d, commission_pct: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Tanggal Mulai</Label>
                  <Input type="date" className="mt-1" value={dealDialog.start_date} onChange={e => setDealDialog(d => ({ ...d, start_date: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs">Tanggal Selesai</Label>
                  <Input type="date" className="mt-1" value={dealDialog.end_date} onChange={e => setDealDialog(d => ({ ...d, end_date: e.target.value }))} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="text-xs">Produk</Label>
                  <Button size="sm" variant="outline" className="text-xs h-6" onClick={() => setDealDialog(d => ({ ...d, products: [...(d.products || []), { sku_code: '', product_name: '' }] }))}>+ Produk</Button>
                </div>
                {(dealDialog.products || []).map((p, idx) => (
                  <div key={idx} className="flex gap-2 mb-1.5">
                    <Input placeholder="SKU" className="w-28" value={p.sku_code} onChange={e => {
                      const products = [...dealDialog.products]; products[idx].sku_code = e.target.value.toUpperCase();
                      setDealDialog(d => ({ ...d, products }));
                    }} />
                    <Input placeholder="Nama produk" className="flex-1" value={p.product_name} onChange={e => {
                      const products = [...dealDialog.products]; products[idx].product_name = e.target.value;
                      setDealDialog(d => ({ ...d, products }));
                    }} />
                    <Button size="icon" variant="ghost" className="h-9 w-9" onClick={() => setDealDialog(d => ({ ...d, products: d.products.filter((_, i) => i !== idx) }))}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                ))}
              </div>
              <div>
                <Label className="text-xs">Catatan</Label>
                <Textarea rows={2} className="mt-1" value={dealDialog.notes} onChange={e => setDealDialog(d => ({ ...d, notes: e.target.value }))} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDealDialog(null)}>Batal</Button>
              <Button onClick={saveDeal} disabled={savingDeal || !dealDialog.creator_id} data-testid="btn-save-deal">
                {savingDeal ? 'Menyimpan...' : 'Simpan'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Sample Dialog */}
      {sampleDialog && (
        <Dialog open={!!sampleDialog} onOpenChange={() => setSampleDialog(null)}>
          <DialogContent className="max-w-md max-h-[85vh] overflow-y-auto" data-testid="dialog-sample">
            <DialogHeader><DialogTitle>{sampleDialog.id ? 'Update Sample' : 'Request Sample'}</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              {!sampleDialog.id && (
                <>
                  <div>
                    <Label className="text-xs">Kreator *</Label>
                    <Select value={sampleDialog.creator_id} onValueChange={v => setSampleDialog(d => ({ ...d, creator_id: v }))}>
                      <SelectTrigger className="mt-1" data-testid="select-sample-creator"><SelectValue placeholder="Pilih kreator" /></SelectTrigger>
                      <SelectContent>{creators.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">SKU *</Label>
                      <Input className="mt-1 uppercase" placeholder="BLS-001" value={sampleDialog.sku_code} onChange={e => setSampleDialog(d => ({ ...d, sku_code: e.target.value.toUpperCase() }))} data-testid="input-sample-sku" />
                    </div>
                    <div>
                      <Label className="text-xs">Qty</Label>
                      <Input type="number" className="mt-1" min={1} value={sampleDialog.qty} onChange={e => setSampleDialog(d => ({ ...d, qty: e.target.value }))} />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">Nama Produk</Label>
                    <Input className="mt-1" value={sampleDialog.product_name} onChange={e => setSampleDialog(d => ({ ...d, product_name: e.target.value }))} />
                  </div>
                </>
              )}
              {sampleDialog.id && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">Status</Label>
                      <Select value={sampleDialog.status} onValueChange={v => setSampleDialog(d => ({ ...d, status: v }))}>
                        <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                        <SelectContent>{SAMPLE_STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-xs">Kurir</Label>
                      <Input className="mt-1" placeholder="JNE / J&T" value={sampleDialog.courier || ''} onChange={e => setSampleDialog(d => ({ ...d, courier: e.target.value }))} />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">No. Resi</Label>
                    <Input className="mt-1" value={sampleDialog.tracking_number || ''} onChange={e => setSampleDialog(d => ({ ...d, tracking_number: e.target.value }))} />
                  </div>
                  <div>
                    <Label className="text-xs">Feedback Kreator</Label>
                    <Textarea rows={2} className="mt-1" value={sampleDialog.feedback_notes || ''} onChange={e => setSampleDialog(d => ({ ...d, feedback_notes: e.target.value }))} />
                  </div>
                </>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSampleDialog(null)}>Batal</Button>
              <Button onClick={saveSample} disabled={savingSample} data-testid="btn-save-sample">
                {savingSample ? 'Menyimpan...' : 'Simpan'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
