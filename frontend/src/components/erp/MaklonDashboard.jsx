import { useState, useEffect, useMemo } from 'react';
import { Factory, Users, Package, TrendingUp, Clock, CheckCircle2, DollarSign, AlertTriangle, RefreshCw } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { PageHeader } from './moduleAtoms';
import { fetchMaklonOrders, posToLegacyOrders } from '@/lib/maklonOrderAdapter';

export default function MaklonDashboard({ token, onNavigate }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);

  const [summary, setSummary] = useState({});
  const [recentOrders, setRecentOrders] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sumR, ordersR] = await Promise.all([
        fetch('/api/dewi/maklon/summary', { headers }),
        fetch('/api/dewi/maklon/pos', { headers }),
      ]);
      if (sumR.ok) setSummary(await sumR.json());
      if (ordersR.ok) {
        const orderList = posToLegacyOrders(await ordersR.json());
        setRecentOrders(orderList.slice(0, 10));
      }
    } catch (e) {
      toast.error('Gagal memuat data dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [fetchData]);

  const stats = [
    { label: 'Total Klien',        value: summary.total_clients || 0,     icon: Users,         color: 'text-blue-400 bg-blue-500/10 border-blue-400/20' },
    { label: 'Klien Aktif',        value: summary.active_clients || 0,    icon: CheckCircle2,  color: 'text-green-400 bg-green-500/10 border-green-400/20' },
    { label: 'Order Aktif',        value: summary.active_orders || 0,     icon: Clock,         color: 'text-amber-400 bg-amber-500/10 border-amber-400/20' },
    { label: 'Order Selesai',      value: summary.completed_orders || 0,  icon: Package,       color: 'text-violet-400 bg-violet-500/10 border-violet-400/20' },
    { label: 'Draft',              value: summary.draft_orders || 0,      icon: AlertTriangle, color: 'text-orange-400 bg-orange-500/10 border-orange-400/20' },
    { label: 'Dikonfirmasi',       value: summary.confirmed_orders || 0,  icon: CheckCircle2,  color: 'text-cyan-400 bg-cyan-500/10 border-cyan-400/20' },
    { label: 'Sedang Produksi',    value: summary.in_production || 0,     icon: Factory,       color: 'text-pink-400 bg-pink-500/10 border-pink-400/20' },
    { label: 'Total Revenue',      value: `Rp ${(summary.total_revenue || 0).toLocaleString('id-ID')}`, icon: DollarSign, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-400/20' },
  ];

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

  const StatusBadge = ({ status }) => {
    const c = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
    return <span className={`inline-flex text-[10px] font-semibold px-2 py-0.5 rounded-full border ${c.color}`}>{c.label}</span>;
  };

  return (
    <div className="p-6 space-y-6" data-testid="maklon-dashboard">
      <PageHeader
        title="Dashboard Maklon"
        description="Ringkasan order maklon, klien aktif, dan performa produksi jasa maklon"
        icon={Factory}
        actions={
          <Button size="sm" onClick={fetchData} variant="outline" className="gap-2">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </Button>
        }
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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

      {/* Quick Actions */}
      <GlassCard className="p-5">
        <h3 className="text-sm font-semibold text-foreground/80 mb-3">Quick Actions</h3>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => onNavigate && onNavigate('maklon-clients')} className="gap-1.5">
            <Users className="w-3.5 h-3.5" /> Kelola Klien
          </Button>
          <Button size="sm" onClick={() => onNavigate && onNavigate('maklon-po')} variant="outline" className="gap-1.5">
            <Package className="w-3.5 h-3.5" /> Kelola Order
          </Button>
        </div>
      </GlassCard>

      {/* Recent Orders */}
      <GlassCard className="p-5">
        <h3 className="text-sm font-semibold text-foreground/80 mb-4">Order Terbaru</h3>
        {loading ? (
          <div className="text-center py-10 text-foreground/40 text-sm">Memuat...</div>
        ) : recentOrders.length === 0 ? (
          <div className="text-center py-10 text-foreground/40 text-sm">Belum ada order maklon</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5 text-xs text-foreground/50">
                  <th className="pb-2 text-left">Order Code</th>
                  <th className="pb-2 text-left">Klien</th>
                  <th className="pb-2 text-left">Produk</th>
                  <th className="pb-2 text-center">Qty</th>
                  <th className="pb-2 text-right">Nilai Order</th>
                  <th className="pb-2 text-left">Deadline</th>
                  <th className="pb-2 text-center">Progress</th>
                  <th className="pb-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {recentOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-white/3 transition-colors">
                    <td className="py-2.5 pr-3 font-mono text-xs text-foreground/70">{order.order_code}</td>
                    <td className="py-2.5 pr-3 text-foreground">{order.client_name}</td>
                    <td className="py-2.5 pr-3">
                      <div className="font-medium text-foreground">{order.product_name}</div>
                      <div className="text-xs text-foreground/40">{order.product_category}</div>
                    </td>
                    <td className="py-2.5 pr-3 text-center font-bold">{order.qty_ordered}</td>
                    <td className="py-2.5 pr-3 text-right text-foreground/80">Rp {(order.total_value || 0).toLocaleString('id-ID')}</td>
                    <td className="py-2.5 pr-3 text-xs text-foreground/60">{order.deadline_date}</td>
                    <td className="py-2.5 pr-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div className="h-full bg-primary" style={{ width: `${order.progress_percentage || 0}%` }} />
                        </div>
                        <span className="text-xs text-foreground/50">{order.progress_percentage || 0}%</span>
                      </div>
                    </td>
                    <td className="py-2.5 pr-3"><StatusBadge status={order.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
