import { useState, useEffect, useCallback, useMemo } from 'react';
import { Package, Plus, Eye, Edit2, CheckCircle2, Clock, RefreshCw, Ban, FileText, Link2 } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { motion } from 'framer-motion';
import { PageHeader } from './moduleAtoms';

const PRODUCT_CATEGORIES = ['Rok', 'Blouse', 'Dress', 'Celana', 'Set/Setelan', 'Baju Anak', 'Hijab', 'Aksesoris', 'Lainnya'];

const STATUS_CONFIG = {
  draft:          { label: 'Draft',           color: 'bg-slate-500/15 text-slate-300 border-slate-400/30' },
  confirmed:      { label: 'Dikonfirmasi',    color: 'bg-blue-500/15 text-blue-300 border-blue-400/30' },
  material_ready: { label: 'Material Siap',   color: 'bg-cyan-500/15 text-cyan-300 border-cyan-400/30' },
  cutting:        { label: 'Cutting',         color: 'bg-violet-500/15 text-violet-300 border-violet-400/30' },
  sewing:         { label: 'Sewing',          color: 'bg-purple-500/15 text-purple-300 border-purple-400/30' },
  qc:             { label: 'QC',              color: 'bg-amber-500/15 text-amber-300 border-amber-400/30' },
  packing:        { label: 'Packing',         color: 'bg-orange-500/15 text-orange-300 border-orange-400/30' },
  completed:      { label: 'Selesai',         color: 'bg-green-500/15 text-green-300 border-green-400/30' },
  invoiced:       { label: 'Ditagih',         color: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/30' },
  cancelled:      { label: 'Dibatalkan',      color: 'bg-red-500/15 text-red-300 border-red-400/30' },
};

function StatusBadge({ status }) {
  const c = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  return <span className={`inline-flex text-[10px] font-semibold px-2 py-0.5 rounded-full border ${c.color}`}>{c.label}</span>;
}

export default function MaklonOrderModule({ token }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);

  const [orders, setOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState('all');
  const [orderDialog, setOrderDialog] = useState(null);
  const [viewDialog, setViewDialog] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ordersR, clientsR] = await Promise.all([
        fetch('/api/dewi/maklon/orders', { headers }),
        fetch('/api/dewi/maklon/clients?status=active', { headers }),
      ]);
      if (ordersR.ok) setOrders(await ordersR.json());
      if (clientsR.ok) setClients(await clientsR.json());
    } catch(e) { toast.error('Gagal memuat data order'); }
    finally { setLoading(false); }
  }, [headers]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const confirmOrder = async (order) => {
    const r = await fetch(`/api/dewi/maklon/orders/${order.id}/confirm`, { method: 'PUT', headers });
    if (r.ok) { toast.success(`Order ${order.order_code} dikonfirmasi`); fetchData(); }
    else { const e = await r.json(); toast.error(e.detail || 'Gagal konfirmasi'); }
  };

  const cancelOrder = async (order) => {
    if (!window.confirm(`Batalkan order ${order.order_code}?`)) return;
    const r = await fetch(`/api/dewi/maklon/orders/${order.id}`, { method: 'DELETE', headers });
    if (r.ok) { toast.success('Order dibatalkan'); fetchData(); }
    else toast.error('Gagal membatalkan order');
  };

  const filteredOrders = tab === 'all' ? orders : orders.filter(o => {
    if (tab === 'active') return !['completed', 'cancelled', 'invoiced'].includes(o.status);
    if (tab === 'draft') return o.status === 'draft';
    if (tab === 'production') return ['material_ready', 'cutting', 'sewing', 'qc', 'packing'].includes(o.status);
    if (tab === 'completed') return ['completed', 'invoiced'].includes(o.status);
    return true;
  });

  const stats = [
    { label: 'Total Order', value: orders.length, icon: Package, color: 'text-violet-400 bg-violet-500/10 border-violet-400/20' },
    { label: 'Draft', value: orders.filter(o => o.status === 'draft').length, icon: FileText, color: 'text-orange-400 bg-orange-500/10 border-orange-400/20' },
    { label: 'Aktif', value: orders.filter(o => !['completed','cancelled','invoiced'].includes(o.status)).length, icon: Clock, color: 'text-amber-400 bg-amber-500/10 border-amber-400/20' },
    { label: 'Selesai', value: orders.filter(o => ['completed','invoiced'].includes(o.status)).length, icon: CheckCircle2, color: 'text-green-400 bg-green-500/10 border-green-400/20' },
  ];

  return (
    <div className="p-6 space-y-6" data-testid="maklon-orders">
      <PageHeader
        title="Order Maklon"
        description="Manajemen order maklon dari klien, tracking produksi hingga selesai"
        icon={Package}
        actions={
          <div className="flex gap-2">
            <Button size="sm" onClick={fetchData} variant="outline" className="gap-2">
              <RefreshCw className="w-3.5 h-3.5" /> Refresh
            </Button>
            <Button size="sm" onClick={() => setOrderDialog({})} className="gap-1.5">
              <Plus className="w-3.5 h-3.5" /> Buat Order
            </Button>
          </div>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 * i }}>
            <GlassCard className={`p-4 border ${s.color.split(' ')[2]}`}>
              <div className={`w-8 h-8 rounded-lg border ${s.color} flex items-center justify-center mb-2`}>
                <s.icon className={`w-4 h-4 ${s.color.split(' ')[0]}`} />
              </div>
              <div className="text-2xl font-bold text-foreground">{s.value}</div>
              <div className="text-xs text-foreground/50">{s.label}</div>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="all">Semua ({orders.length})</TabsTrigger>
          <TabsTrigger value="draft">Draft ({orders.filter(o=>o.status==='draft').length})</TabsTrigger>
          <TabsTrigger value="active">Aktif ({orders.filter(o=>!['completed','cancelled','invoiced'].includes(o.status)).length})</TabsTrigger>
          <TabsTrigger value="production">Produksi ({orders.filter(o=>['material_ready','cutting','sewing','qc','packing'].includes(o.status)).length})</TabsTrigger>
          <TabsTrigger value="completed">Selesai ({orders.filter(o=>['completed','invoiced'].includes(o.status)).length})</TabsTrigger>
        </TabsList>

        <TabsContent value={tab}>
          <GlassCard className="p-5">
            <h3 className="text-sm font-semibold text-foreground/80 mb-4">Daftar Order Maklon</h3>
            {loading ? (
              <div className="text-center py-10 text-foreground/40 text-sm">Memuat...</div>
            ) : filteredOrders.length === 0 ? (
              <div className="text-center py-10 text-foreground/40 text-sm">Belum ada order</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-white/5 text-xs text-foreground/50">
                    <th className="pb-2 text-left">Order Code</th><th className="pb-2 text-left">Klien</th><th className="pb-2 text-left">Produk</th>
                    <th className="pb-2 text-center">Qty</th><th className="pb-2 text-right">Nilai Order</th><th className="pb-2 text-left">Deadline</th>
                    <th className="pb-2 text-center">Progress</th><th className="pb-2 text-left">Status</th><th className="pb-2 text-center">Aksi</th>
                  </tr></thead>
                  <tbody className="divide-y divide-white/5">
                    {filteredOrders.map(o => (
                      <tr key={o.id} className="hover:bg-white/3 transition-colors">
                        <td className="py-2.5 pr-3 font-mono text-xs text-foreground/70">{o.order_code}</td>
                        <td className="py-2.5 pr-3 text-foreground">{o.client_name}</td>
                        <td className="py-2.5 pr-3">
                          <div className="font-medium text-foreground">{o.product_name}</div>
                          <div className="text-xs text-foreground/40">{o.product_category}</div>
                        </td>
                        <td className="py-2.5 pr-3 text-center font-bold">{o.qty_ordered}</td>
                        <td className="py-2.5 pr-3 text-right text-foreground/80">Rp {(o.total_value||0).toLocaleString('id-ID')}</td>
                        <td className="py-2.5 pr-3 text-xs text-foreground/60">{o.deadline_date}</td>
                        <td className="py-2.5 pr-3">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                              <div className="h-full bg-primary" style={{width: `${o.progress_percentage||0}%`}} />
                            </div>
                            <span className="text-xs text-foreground/50">{o.progress_percentage||0}%</span>
                          </div>
                        </td>
                        <td className="py-2.5 pr-3">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <StatusBadge status={o.status} />
                            {(o.linked_wo_ids || []).length > 0 && (
                              <span className="inline-flex items-center gap-1 text-[9px] bg-blue-500/15 border border-blue-400/25 text-blue-300 px-1.5 py-0.5 rounded-full font-semibold">
                                <Link2 className="w-2.5 h-2.5" />{(o.linked_wo_ids || []).length} WO
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5">
                          <div className="flex gap-1 justify-center">
                            <Button size="icon" variant="ghost" className="w-7 h-7" onClick={() => setViewDialog(o)}><Eye className="w-3.5 h-3.5" /></Button>
                            {o.status === 'draft' && (<>
                              <Button size="icon" variant="ghost" className="w-7 h-7" onClick={() => setOrderDialog({data: o})}><Edit2 className="w-3.5 h-3.5" /></Button>
                              <Button size="sm" variant="outline" className="text-xs h-7" onClick={() => confirmOrder(o)}>Konfirmasi</Button>
                              <Button size="icon" variant="ghost" className="w-7 h-7 text-red-400" onClick={() => cancelOrder(o)}><Ban className="w-3.5 h-3.5" /></Button>
                            </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </GlassCard>
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      {orderDialog !== null && (
        <OrderDialog data={orderDialog?.data || null} clients={clients} headers={headers} onClose={() => setOrderDialog(null)} onSuccess={() => { setOrderDialog(null); fetchData(); }} />
      )}
      {viewDialog && <ViewOrderDialog order={viewDialog} onClose={() => setViewDialog(null)} />}
    </div>
  );
}

// Order Form Dialog
function OrderDialog({ data, clients, headers, onClose, onSuccess }) {
  const isEdit = !!data;
  const today = new Date().toISOString().split('T')[0];
  const [form, setForm] = useState(data || {
    order_code: '', client_id: '', product_name: '', product_category: 'Rok',
    qty_ordered: '', price_per_pcs: '', order_date: today, deadline_date: today,
    fabric_provided_by: 'client', delivery_method: 'pickup', notes: ''
  });
  const [saving, setSaving] = useState(false);
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const save = async () => {
    if (!form.order_code || !form.client_id || !form.product_name || !form.qty_ordered || !form.deadline_date) {
      toast.error('Order code, klien, produk, qty, dan deadline wajib diisi'); return;
    }
    setSaving(true);
    const url = isEdit ? `/api/dewi/maklon/orders/${data.id}` : '/api/dewi/maklon/orders';
    const method = isEdit ? 'PUT' : 'POST';
    const payload = { ...form, qty_ordered: Number(form.qty_ordered), price_per_pcs: Number(form.price_per_pcs || 0) };
    const r = await fetch(url, { method, headers, body: JSON.stringify(payload) });
    setSaving(false);
    if (r.ok) { toast.success(isEdit ? 'Order diperbarui' : 'Order dibuat'); onSuccess(); }
    else { const e = await r.json(); toast.error(e.detail || 'Gagal menyimpan'); }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{isEdit ? `Edit Order: ${data.order_code}` : 'Buat Order Maklon Baru'}</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1"><Label>Order Code *</Label><Input value={form.order_code} onChange={e => set('order_code', e.target.value)} placeholder="MKL-2024-001" /></div>
            <div className="space-y-1"><Label>Pilih Klien *</Label><Select value={form.client_id} onValueChange={v => set('client_id', v)}><SelectTrigger><SelectValue placeholder="Pilih klien..." /></SelectTrigger><SelectContent>{clients.map(c => <SelectItem key={c.id} value={c.id}>{c.name} ({c.code})</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-1 col-span-2"><Label>Nama Produk *</Label><Input value={form.product_name} onChange={e => set('product_name', e.target.value)} placeholder="Contoh: Rok Midi Rayon" /></div>
            <div className="space-y-1"><Label>Kategori</Label><Select value={form.product_category} onValueChange={v => set('product_category', v)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{PRODUCT_CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-1"><Label>Qty (pcs) *</Label><Input type="number" min="1" value={form.qty_ordered} onChange={e => set('qty_ordered', e.target.value)} placeholder="0" /></div>
            <div className="space-y-1"><Label>Harga Jasa (Rp/pcs)</Label><Input type="number" value={form.price_per_pcs} onChange={e => set('price_per_pcs', e.target.value)} placeholder="0" /></div>
            <div className="space-y-1"><Label>Tanggal Order</Label><Input type="date" value={form.order_date} onChange={e => set('order_date', e.target.value)} /></div>
            <div className="space-y-1"><Label>Deadline *</Label><Input type="date" value={form.deadline_date} onChange={e => set('deadline_date', e.target.value)} /></div>
            <div className="space-y-1"><Label>Material Disediakan</Label><Select value={form.fabric_provided_by} onValueChange={v => set('fabric_provided_by', v)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="client">Klien</SelectItem><SelectItem value="cv_dewi">CV. Dewi Aditya</SelectItem></SelectContent></Select></div>
            <div className="space-y-1"><Label>Metode Pengiriman</Label><Select value={form.delivery_method} onValueChange={v => set('delivery_method', v)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="pickup">Pickup</SelectItem><SelectItem value="delivery">Delivery</SelectItem></SelectContent></Select></div>
          </div>
          <div className="space-y-1"><Label>Catatan</Label><Textarea value={form.notes} onChange={e => set('notes', e.target.value)} rows={2} placeholder="Catatan tambahan..." /></div>
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose}>Batal</Button><Button onClick={save} disabled={saving}>{saving ? 'Menyimpan...' : (isEdit ? 'Simpan' : 'Buat Order')}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// View Order Detail Dialog
function ViewOrderDialog({ order, onClose }) {
  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Detail Order: {order.order_code}</DialogTitle></DialogHeader>
        <div className="space-y-3 py-2 text-sm">
          <InfoRow label="Order Code" value={order.order_code} />
          <InfoRow label="Klien" value={order.client_name} />
          <InfoRow label="Produk" value={order.product_name} />
          <InfoRow label="Kategori" value={order.product_category} />
          <InfoRow label="Qty" value={`${order.qty_ordered} pcs`} />
          <InfoRow label="Harga/pcs" value={`Rp ${(order.price_per_pcs||0).toLocaleString('id-ID')}`} />
          <InfoRow label="Total Nilai" value={`Rp ${(order.total_value||0).toLocaleString('id-ID')}`} />
          <InfoRow label="Tgl Order" value={order.order_date} />
          <InfoRow label="Deadline" value={order.deadline_date} />
          <InfoRow label="Progress" value={`${order.progress_percentage||0}%`} />
          <InfoRow label="Status" value={<StatusBadge status={order.status} />} />
          <InfoRow label="Material" value={order.fabric_provided_by === 'client' ? 'Disediakan Klien' : 'CV. Dewi Aditya'} />
          <InfoRow label="Pengiriman" value={order.delivery_method === 'pickup' ? 'Pickup' : 'Delivery'} />
          <InfoRow label="Catatan" value={order.notes} />
        </div>
        <DialogFooter><Button variant="outline" onClick={onClose}>Tutup</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function InfoRow({ label, value }) {
  if (!value && value !== 0) return null;
  return <div className="flex gap-3"><span className="text-foreground/50 shrink-0 w-32">{label}:</span><span className="text-foreground/80">{value}</span></div>;
}
