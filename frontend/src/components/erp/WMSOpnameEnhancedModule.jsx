/**
 * WMS Opname Enhanced (Opname2) — Advanced Cycle Counting & Variance Analysis
 * P1: Enhanced stock opname with cycle planning, variance tracking, and adjustment workflows
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ClipboardCheck, Plus, RefreshCw, Eye, Play, StopCircle, CheckCircle2,
  AlertTriangle, Loader2, Search, BarChart3, TrendingUp, TrendingDown,
  X, Save, Calendar, Package, MapPin, FileText
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_COLORS = {
  planned: 'bg-blue-500/20 text-blue-300',
  in_progress: 'bg-amber-500/20 text-amber-300',
  completed: 'bg-emerald-500/20 text-emerald-300',
  cancelled: 'bg-red-500/20 text-red-300',
};

const VARIANCE_TYPE_COLORS = {
  over: 'bg-emerald-500/20 text-emerald-300',
  under: 'bg-red-500/20 text-red-300',
  match: 'bg-zinc-500/20 text-zinc-400',
};

const fmt = (n) => new Intl.NumberFormat('id-ID', { minimumFractionDigits: 2 }).format(n ?? 0);

export default function WMSOpnameEnhancedModule({ token }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);
  const [cycles, setCycles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState('all');
  const [search, setSearch] = useState('');
  const [createDialog, setCreateDialog] = useState(false);
  const [viewDialog, setViewDialog] = useState(null);
  const [stats, setStats] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (tab !== 'all') params.set('status', tab);
      const [cyclesRes, statsRes] = await Promise.all([
        fetch(`${API}/api/wms/opname2/cycles?${params}`, { headers }).then(r => r.json()),
        fetch(`${API}/api/wms/opname2/stats`, { headers }).then(r => r.json()),
      ]);
      setCycles(cyclesRes.items || []);
      setStats(statsRes);
    } catch {
      toast.error('Gagal memuat data opname cycle');
    } finally {
      setLoading(false);
    }
  }, [headers, search, tab]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
      cycle_name: fd.get('cycle_name'),
      cycle_type: fd.get('cycle_type') || 'full',
      planned_date: fd.get('planned_date') || null,
      zone_ids: fd.get('zone_ids')?.split(',').filter(Boolean) || [],
      notes: fd.get('notes') || '',
    };
    try {
      const r = await fetch(`${API}/api/wms/opname2/cycles`, { method: 'POST', headers, body: JSON.stringify(data) });
      if (!r.ok) throw new Error();
      toast.success('Cycle opname berhasil dibuat');
      setCreateDialog(false);
      load();
    } catch {
      toast.error('Gagal membuat cycle opname');
    }
  };

  const handleStart = async (id) => {
    try {
      const r = await fetch(`${API}/api/wms/opname2/cycles/${id}/start`, { method: 'POST', headers });
      if (!r.ok) throw new Error();
      toast.success('Cycle opname dimulai');
      load();
    } catch {
      toast.error('Gagal start cycle');
    }
  };

  const handleComplete = async (id) => {
    try {
      const r = await fetch(`${API}/api/wms/opname2/cycles/${id}/complete`, { method: 'POST', headers });
      if (!r.ok) throw new Error();
      toast.success('Cycle opname selesai');
      load();
    } catch {
      toast.error('Gagal complete cycle');
    }
  };

  const handleViewDetail = async (cycle) => {
    try {
      const r = await fetch(`${API}/api/wms/opname2/cycles/${cycle.id}`, { headers });
      const d = await r.json();
      setViewDialog(d);
    } catch {
      toast.error('Gagal memuat detail cycle');
    }
  };

  const filteredCycles = useMemo(() => {
    if (tab === 'all') return cycles;
    return cycles.filter(c => c.status === tab);
  }, [cycles, tab]);

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-zinc-900 via-zinc-900 to-zinc-800 text-zinc-100" data-testid="wms-opname-enhanced-module">
      {/* Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-purple-500/20 border border-purple-500/30">
                <ClipboardCheck className="w-5 h-5 text-purple-300" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold text-white">Opname Enhanced</h1>
                <p className="text-sm text-zinc-400 mt-0.5">Advanced cycle counting & variance analysis</p>
              </div>
            </div>
            <Button
              onClick={() => setCreateDialog(true)}
              className="bg-purple-600 hover:bg-purple-700 text-white"
              data-testid="create-cycle-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Cycle Baru
            </Button>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-4 gap-3 mb-4">
              <div className="bg-white/5 border border-white/10 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">Total Cycles</span>
                  <ClipboardCheck className="w-4 h-4 text-purple-400" />
                </div>
                <p className="text-2xl font-bold text-white mt-1">{stats.total_cycles || 0}</p>
              </div>
              <div className="bg-white/5 border border-white/10 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">In Progress</span>
                  <Play className="w-4 h-4 text-amber-400" />
                </div>
                <p className="text-2xl font-bold text-white mt-1">{stats.in_progress || 0}</p>
              </div>
              <div className="bg-white/5 border border-white/10 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">Completed</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-2xl font-bold text-white mt-1">{stats.completed || 0}</p>
              </div>
              <div className="bg-white/5 border border-white/10 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500">Avg Accuracy</span>
                  <BarChart3 className="w-4 h-4 text-blue-400" />
                </div>
                <p className="text-2xl font-bold text-white mt-1">{fmt(stats.avg_accuracy || 0)}%</p>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <Input
                placeholder="Cari cycle name, zone..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-white/5 border-white/10 text-white"
                data-testid="search-cycle-input"
              />
            </div>
            <Button
              variant="outline"
              onClick={load}
              disabled={loading}
              className="border-white/10 hover:bg-white/5"
              data-testid="refresh-cycle-btn"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        <Tabs value={tab} onValueChange={setTab} className="px-6">
          <TabsList className="bg-white/5 border-b border-white/10 w-full justify-start rounded-none">
            <TabsTrigger value="all" data-testid="tab-all">Semua</TabsTrigger>
            <TabsTrigger value="planned" data-testid="tab-planned">Planned</TabsTrigger>
            <TabsTrigger value="in_progress" data-testid="tab-in-progress">In Progress</TabsTrigger>
            <TabsTrigger value="completed" data-testid="tab-completed">Completed</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Cycles List */}
      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64" data-testid="loading-cycles">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          </div>
        ) : filteredCycles.length === 0 ? (
          <div className="text-center py-16" data-testid="empty-cycles">
            <ClipboardCheck className="w-16 h-16 mx-auto text-zinc-700 mb-4" />
            <p className="text-zinc-500">Belum ada cycle opname</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredCycles.map((cycle) => (
              <div
                key={cycle.id}
                className="bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-colors cursor-pointer"
                onClick={() => handleViewDetail(cycle)}
                data-testid={`cycle-card-${cycle.cycle_name}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <ClipboardCheck className="w-4 h-4 text-purple-400" />
                      <h3 className="font-semibold text-white">{cycle.cycle_name}</h3>
                    </div>
                    <p className="text-sm text-zinc-400">{cycle.cycle_type} cycle</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs ${STATUS_COLORS[cycle.status] || ''}`}>
                    {cycle.status}
                  </span>
                </div>

                <div className="space-y-2 text-sm">
                  {cycle.planned_date && (
                    <div className="flex items-center gap-2 text-zinc-400">
                      <Calendar className="w-3 h-3" />
                      <span>{new Date(cycle.planned_date).toLocaleDateString('id-ID')}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Items Counted:</span>
                    <span className="text-zinc-200">{cycle.items_counted || 0}</span>
                  </div>
                  {cycle.variance_count > 0 && (
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Variances:</span>
                      <span className="text-red-300">{cycle.variance_count}</span>
                    </div>
                  )}
                  {cycle.accuracy_pct !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Accuracy:</span>
                      <span className={`font-mono ${cycle.accuracy_pct >= 95 ? 'text-emerald-300' : 'text-amber-300'}`}>
                        {fmt(cycle.accuracy_pct)}%
                      </span>
                    </div>
                  )}
                </div>

                <div className="mt-3 pt-3 border-t border-white/10 flex gap-2">
                  {cycle.status === 'planned' && (
                    <Button
                      size="sm"
                      className="flex-1 bg-purple-600 hover:bg-purple-700 text-xs"
                      onClick={(e) => { e.stopPropagation(); handleStart(cycle.id); }}
                      data-testid={`start-btn-${cycle.cycle_name}`}
                    >
                      <Play className="w-3 h-3 mr-1" />
                      Start
                    </Button>
                  )}
                  {cycle.status === 'in_progress' && (
                    <Button
                      size="sm"
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-xs"
                      onClick={(e) => { e.stopPropagation(); handleComplete(cycle.id); }}
                      data-testid={`complete-btn-${cycle.cycle_name}`}
                    >
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Complete
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={createDialog} onOpenChange={setCreateDialog}>
        <DialogContent className="bg-zinc-900 text-white border-white/10 max-w-2xl" data-testid="create-cycle-dialog">
          <DialogHeader>
            <DialogTitle>Buat Cycle Opname Baru</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="space-y-4 py-4">
              <div>
                <Label>Cycle Name *</Label>
                <Input name="cycle_name" required className="bg-white/5 border-white/10" data-testid="input-cycle-name" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Cycle Type</Label>
                  <Select name="cycle_type" defaultValue="full">
                    <SelectTrigger className="bg-white/5 border-white/10" data-testid="input-cycle-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="full">Full Count</SelectItem>
                      <SelectItem value="zone">Zone Count</SelectItem>
                      <SelectItem value="abc">ABC Count</SelectItem>
                      <SelectItem value="spot">Spot Check</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Planned Date</Label>
                  <Input name="planned_date" type="date" className="bg-white/5 border-white/10" data-testid="input-planned-date" />
                </div>
              </div>
              <div>
                <Label>Zone IDs (comma separated)</Label>
                <Input name="zone_ids" placeholder="zone1,zone2,zone3" className="bg-white/5 border-white/10" data-testid="input-zone-ids" />
              </div>
              <div>
                <Label>Notes</Label>
                <Textarea name="notes" className="bg-white/5 border-white/10" data-testid="input-notes" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateDialog(false)} className="border-white/10">
                Batal
              </Button>
              <Button type="submit" className="bg-purple-600 hover:bg-purple-700" data-testid="submit-create-cycle">
                <Save className="w-4 h-4 mr-2" />
                Simpan
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Dialog */}
      {viewDialog && (
        <Dialog open={!!viewDialog} onOpenChange={() => setViewDialog(null)}>
          <DialogContent className="bg-zinc-900 text-white border-white/10 max-w-3xl" data-testid="view-cycle-dialog">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ClipboardCheck className="w-5 h-5 text-purple-400" />
                {viewDialog.cycle?.cycle_name}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-zinc-500">Status:</span>
                  <p className="text-white font-medium">{viewDialog.cycle?.status}</p>
                </div>
                <div>
                  <span className="text-zinc-500">Type:</span>
                  <p className="text-white font-medium">{viewDialog.cycle?.cycle_type}</p>
                </div>
                <div>
                  <span className="text-zinc-500">Items Counted:</span>
                  <p className="text-white font-medium">{viewDialog.cycle?.items_counted || 0}</p>
                </div>
                <div>
                  <span className="text-zinc-500">Accuracy:</span>
                  <p className="text-white font-medium font-mono">{fmt(viewDialog.cycle?.accuracy_pct || 0)}%</p>
                </div>
              </div>

              {viewDialog.variances && viewDialog.variances.length > 0 && (
                <div className="border-t border-white/10 pt-4">
                  <h3 className="text-sm font-medium mb-3 text-zinc-400">Variances Detected</h3>
                  <div className="space-y-2 max-h-64 overflow-auto">
                    {viewDialog.variances.map((v, i) => (
                      <div key={i} className="bg-white/5 border border-white/10 rounded p-3 text-sm">
                        <div className="flex justify-between mb-1">
                          <span className="font-medium text-white">{v.material_name}</span>
                          <span className={`px-2 py-0.5 rounded-full text-xs ${VARIANCE_TYPE_COLORS[v.variance_type] || ''}`}>
                            {v.variance_type}
                          </span>
                        </div>
                        <div className="flex justify-between text-zinc-400">
                          <span>System: {fmt(v.system_qty)}</span>
                          <span>Physical: {fmt(v.physical_qty)}</span>
                          <span className={v.variance_qty > 0 ? 'text-emerald-300' : 'text-red-300'}>
                            Diff: {fmt(v.variance_qty)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
