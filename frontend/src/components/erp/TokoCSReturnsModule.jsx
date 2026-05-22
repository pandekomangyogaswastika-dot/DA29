import { useState, useEffect, useCallback, useMemo } from 'react';
import { MessageSquare, RotateCcw, Plus, Edit2, Trash2, RefreshCw, Search, Star, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
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

const RETURN_TYPE_LABELS = { expedition_return: 'Retur Ekspedisi', customer_refund: 'Refund Customer' };
const RETURN_STATUS_COLORS = {
  new: 'bg-blue-500/15 text-blue-300 border-blue-400/25',
  investigating: 'bg-amber-500/15 text-amber-300 border-amber-400/25',
  decision_made: 'bg-purple-500/15 text-purple-300 border-purple-400/25',
  resolved: 'bg-green-500/15 text-green-300 border-green-400/25',
  closed: 'bg-foreground/10 text-foreground/50 border-foreground/15',
};
const DECISION_LABELS = { reship: 'Kirim Ulang', refund: 'Refund', reject: 'Tolak', pending: 'Belum Diputuskan' };
const DECISION_COLORS = {
  reship: 'bg-blue-500/15 text-blue-300',
  refund: 'bg-amber-500/15 text-amber-300',
  reject: 'bg-red-500/15 text-red-300',
  pending: 'bg-foreground/10 text-foreground/50',
};
const CHANNEL_OPTIONS = ['shopee', 'tokopedia', 'tiktok_shop', 'website'];
const fmtDate = (d) => d ? new Date(d).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' }) : '-';

export default function TokoCSReturnsModule({ token, defaultTab = 'cs' }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [returnsSummary, setReturnsSummary] = useState(null);

  // Returns
  const [returns, setReturns] = useState([]);
  const [returnsLoading, setReturnsLoading] = useState(false);
  const [returnSearch, setReturnSearch] = useState('');
  const [returnTypeFilter, setReturnTypeFilter] = useState('all');
  const [returnStatusFilter, setReturnStatusFilter] = useState('all');
  const [returnDialog, setReturnDialog] = useState(null);
  const [savingReturn, setSavingReturn] = useState(false);
  const [decisionDialog, setDecisionDialog] = useState(null);
  const [decision, setDecision] = useState({ decision: 'reship', decision_notes: '', tracking_number: '' });

  // Reviews (CS)
  const [reviews, setReviews] = useState([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [reviewDialog, setReviewDialog] = useState(null);
  const [responseText, setResponseText] = useState('');
  const [respondingId, setRespondingId] = useState(null);
  const [ratingFilter, setRatingFilter] = useState('all');
  const [reviewStatusFilter, setReviewStatusFilter] = useState('all');

  const emptyReturn = { order_number: '', return_type: 'customer_refund', customer_name: '', channel_code: 'shopee', reason: '', evidence_notes: '', estimated_value: 0 };
  const emptyReview = { channel_code: 'shopee', order_ref: '', customer_name: '', rating: 5, review_text: '', sku_code: '' };

  const loadReturns = useCallback(async () => {
    setReturnsLoading(true);
    try {
      const params = new URLSearchParams();
      if (returnTypeFilter !== 'all') params.set('return_type', returnTypeFilter);
      if (returnStatusFilter !== 'all') params.set('status', returnStatusFilter);
      if (returnSearch) params.set('search', returnSearch);
      const [rReturns, rSummary] = await Promise.all([
        fetch(`/api/dewi/toko/returns?${params}`, { headers }),
        fetch('/api/dewi/toko/returns/summary', { headers }),
      ]);
      if (rReturns.ok) setReturns(await rReturns.json());
      if (rSummary.ok) setReturnsSummary(await rSummary.json());
    } finally { setReturnsLoading(false); }
  }, [headers, returnTypeFilter, returnStatusFilter, returnSearch]);

  const loadReviews = useCallback(async () => {
    setReviewsLoading(true);
    try {
      const params = new URLSearchParams();
      if (reviewStatusFilter !== 'all') params.set('status', reviewStatusFilter);
      if (ratingFilter !== 'all') params.set('max_rating', ratingFilter);
      const r = await fetch(`/api/dewi/toko/reviews?${params}`, { headers });
      if (r.ok) setReviews(await r.json());
    } finally { setReviewsLoading(false); }
  }, [headers, reviewStatusFilter, ratingFilter]);

  useEffect(() => { if (activeTab === 'returns') loadReturns(); }, [activeTab, loadReturns]);
  useEffect(() => { loadReturns(); }, [loadReturns]);
  useEffect(() => { if (activeTab === 'cs') loadReviews(); }, [activeTab, loadReviews]);

  const saveReturn = async () => {
    if (!returnDialog?.customer_name || !returnDialog?.reason) { toast.error('Nama dan alasan wajib diisi'); return; }
    setSavingReturn(true);
    try {
      const { id, ...body } = { ...returnDialog, estimated_value: Number(returnDialog.estimated_value) };
      const url = id ? `/api/dewi/toko/returns/${id}` : '/api/dewi/toko/returns';
      const r = await fetch(url, { method: id ? 'PUT' : 'POST', headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Gagal');
      toast.success(id ? 'Return diperbarui' : `${d.return_code} dibuat`);
      setReturnDialog(null);
      loadReturns();
    } catch (e) { toast.error(e.message); }
    finally { setSavingReturn(false); }
  };

  const makeDecision = async () => {
    if (!decision.decision_notes.trim()) { toast.error('Catatan keputusan wajib diisi'); return; }
    const r = await fetch(`/api/dewi/toko/returns/${decisionDialog.id}/decision`, {
      method: 'POST', headers, body: JSON.stringify(decision),
    });
    const d = await r.json();
    if (!r.ok) { toast.error(d.detail || 'Gagal'); return; }
    toast.success(`Keputusan: ${DECISION_LABELS[decision.decision]}`);
    setDecisionDialog(null);
    loadReturns();
  };

  const deleteReturn = async (ret) => {
    if (!window.confirm(`Hapus kasus return ${ret.return_code}?`)) return;
    const r = await fetch(`/api/dewi/toko/returns/${ret.id}`, { method: 'DELETE', headers });
    const d = await r.json();
    if (!r.ok) { toast.error(d.detail || 'Gagal'); return; }
    toast.success('Dihapus');
    loadReturns();
  };

  const respondReview = async (reviewId) => {
    if (!responseText.trim()) { toast.error('Isi teks respons'); return; }
    setRespondingId(reviewId);
    try {
      const r = await fetch(`/api/dewi/toko/reviews/${reviewId}/respond`, {
        method: 'PUT', headers, body: JSON.stringify({ response_text: responseText }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Gagal');
      toast.success('Respons disimpan');
      setReviewDialog(null);
      setResponseText('');
      loadReviews();
    } catch (e) { toast.error(e.message); }
    finally { setRespondingId(null); }
  };

  const flagReview = async (reviewId) => {
    const r = await fetch(`/api/dewi/toko/reviews/${reviewId}/flag`, { method: 'PUT', headers });
    const d = await r.json();
    if (!r.ok) { toast.error(d.detail || 'Gagal'); return; }
    toast.success('Review diflag');
    loadReviews();
  };

  const deleteReview = async (rev) => {
    if (!window.confirm('Hapus review ini?')) return;
    const r = await fetch(`/api/dewi/toko/reviews/${rev.id}`, { method: 'DELETE', headers });
    if (r.ok) { toast.success('Dihapus'); loadReviews(); } else toast.error('Gagal');
  };

  const addReview = async () => {
    if (!reviewDialog?.review_text) { toast.error('Isi teks review'); return; }
    const r = await fetch('/api/dewi/toko/reviews', { method: 'POST', headers, body: JSON.stringify(reviewDialog) });
    const d = await r.json();
    if (!r.ok) { toast.error(d.detail || 'Gagal'); return; }
    toast.success('Review dicatat');
    setReviewDialog(null);
    loadReviews();
  };

  const StarRating = ({ rating }) => (
    <span className="flex gap-0.5">
      {[1,2,3,4,5].map(i => (
        <Star key={i} className={`w-3 h-3 ${i <= rating ? 'fill-amber-400 text-amber-400' : 'text-foreground/20'}`} />
      ))}
    </span>
  );

  return (
    <div className="p-6 space-y-6" data-testid="toko-cs-module">
      <PageHeader
        title="Customer Service"
        description="Kelola ulasan pelanggan, kasus return, dan keputusan refund"
        icon={MessageSquare}
      />

      {/* Summary Cards */}
      {returnsSummary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <GlassCard className="p-3 text-center">
            <div className="text-2xl font-bold text-blue-400">{returnsSummary.new_returns}</div>
            <div className="text-xs text-foreground/55">Return Baru</div>
          </GlassCard>
          <GlassCard className="p-3 text-center">
            <div className="text-2xl font-bold text-amber-400">{returnsSummary.investigating}</div>
            <div className="text-xs text-foreground/55">Investigasi</div>
          </GlassCard>
          <GlassCard className="p-3 text-center">
            <div className="text-2xl font-bold text-green-400">{returnsSummary.resolved}</div>
            <div className="text-xs text-foreground/55">Selesai</div>
          </GlassCard>
          <GlassCard className="p-3 text-center">
            <div className="text-2xl font-bold text-red-400">{returnsSummary.low_reviews}</div>
            <div className="text-xs text-foreground/55">Ulasan Buruk</div>
          </GlassCard>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="cs" data-testid="tab-cs">Ulasan & CS</TabsTrigger>
          <TabsTrigger value="returns" data-testid="tab-returns">Return & Refund</TabsTrigger>
        </TabsList>

        {/* CS / REVIEWS TAB */}
        <TabsContent value="cs" className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <div className="flex gap-1">
              {['all', '3', '2', '1'].map(r => (
                <button key={r} onClick={() => setRatingFilter(r)}
                  className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                    ratingFilter === r ? 'bg-red-500/15 border-red-400/30 text-red-300' : 'border-foreground/15 text-foreground/60'
                  }`}>
                  {r === 'all' ? 'Semua Rating' : `≤${r}⭐`}
                </button>
              ))}
            </div>
            <Select value={reviewStatusFilter} onValueChange={setReviewStatusFilter}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Status</SelectItem>
                <SelectItem value="unread">Belum Dibaca</SelectItem>
                <SelectItem value="responded">Sudah Direspons</SelectItem>
                <SelectItem value="flagged">Diflag</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" onClick={() => setReviewDialog({ ...emptyReview })} className="gap-1 ml-auto" data-testid="btn-add-review">
              <Plus className="w-3.5 h-3.5" /> Catat Review
            </Button>
          </div>

          {reviewsLoading ? (
            <div className="text-center py-8 text-foreground/40">Memuat...</div>
          ) : reviews.length === 0 ? (
            <GlassCard className="p-10 text-center">
              <MessageSquare className="w-10 h-10 mx-auto mb-3 text-foreground/25" />
              <p className="text-foreground/50 text-sm">Belum ada ulasan pelanggan</p>
            </GlassCard>
          ) : (
            <div className="space-y-2">
              {reviews.map(rev => (
                <GlassCard key={rev.id} className="p-4" data-testid={`review-row-${rev.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <StarRating rating={rev.rating} />
                        <span className="text-sm font-medium">{rev.customer_name || 'Anonim'}</span>
                        <span className="text-xs text-foreground/40 capitalize">{rev.channel_code}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded border ${
                          rev.status === 'unread' ? 'bg-blue-500/15 text-blue-300 border-blue-400/25' :
                          rev.status === 'flagged' ? 'bg-red-500/15 text-red-300 border-red-400/25' : 'bg-green-500/15 text-green-300 border-green-400/25'
                        }`}>{rev.status}</span>
                      </div>
                      <p className="text-sm text-foreground/70 mt-1.5">{rev.review_text}</p>
                      {rev.response_text && (
                        <div className="mt-2 p-2 rounded-lg bg-primary/5 border border-primary/15">
                          <p className="text-xs text-primary/80"><span className="font-medium">Respons:</span> {rev.response_text}</p>
                        </div>
                      )}
                      <div className="text-xs text-foreground/35 mt-1">{fmtDate(rev.created_at)}</div>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {rev.status !== 'responded' && (
                        <Button size="sm" variant="outline" className="text-xs h-7" onClick={() => { setReviewDialog({ ...rev, _action: 'respond' }); setResponseText(''); }}
                          data-testid={`btn-respond-${rev.id}`}>
                          Respons
                        </Button>
                      )}
                      {rev.status === 'unread' && (
                        <Button size="sm" variant="ghost" className="text-xs h-7 text-amber-400" onClick={() => flagReview(rev.id)} data-testid={`btn-flag-${rev.id}`}>
                          <AlertTriangle className="w-3.5 h-3.5" />
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" className="text-xs h-7 text-red-400" onClick={() => deleteReview(rev)} data-testid={`btn-delete-review-${rev.id}`}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </TabsContent>

        {/* RETURNS TAB */}
        <TabsContent value="returns" className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <div className="relative flex-1 min-w-40">
              <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-foreground/40" />
              <Input placeholder="Cari nama / kode return..." value={returnSearch} onChange={e => setReturnSearch(e.target.value)} className="pl-8" />
            </div>
            <Select value={returnTypeFilter} onValueChange={setReturnTypeFilter}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Tipe</SelectItem>
                <SelectItem value="expedition_return">Retur Ekspedisi</SelectItem>
                <SelectItem value="customer_refund">Refund Customer</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" onClick={() => setReturnDialog({ ...emptyReturn })} className="gap-1" data-testid="btn-add-return">
              <Plus className="w-3.5 h-3.5" /> Kasus Baru
            </Button>
          </div>

          {returnsLoading ? (
            <div className="text-center py-8 text-foreground/40">Memuat...</div>
          ) : returns.length === 0 ? (
            <GlassCard className="p-10 text-center">
              <RotateCcw className="w-10 h-10 mx-auto mb-3 text-foreground/25" />
              <p className="text-foreground/50 text-sm">Belum ada kasus return/refund</p>
            </GlassCard>
          ) : (
            <div className="space-y-2">
              {returns.map(ret => (
                <GlassCard key={ret.id} className="p-4" data-testid={`return-row-${ret.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs text-foreground/50">{ret.return_code}</span>
                        <span className="font-medium text-sm">{ret.customer_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${RETURN_STATUS_COLORS[ret.status]}`}>{ret.status}</span>
                        <span className="text-xs text-foreground/50">{RETURN_TYPE_LABELS[ret.return_type]}</span>
                        {ret.decision !== 'pending' && (
                          <span className={`text-xs px-2 py-0.5 rounded ${DECISION_COLORS[ret.decision]}`}>{DECISION_LABELS[ret.decision]}</span>
                        )}
                      </div>
                      <p className="text-sm text-foreground/65 mt-1">{ret.reason}</p>
                      {ret.order_number && <div className="text-xs text-foreground/40 mt-0.5">Order: {ret.order_number}</div>}
                      <div className="text-xs text-foreground/35 mt-0.5">{fmtDate(ret.created_at)}</div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {['new', 'investigating'].includes(ret.status) && (
                        <Button size="sm" className="text-xs h-7" onClick={() => { setDecisionDialog(ret); setDecision({ decision: 'reship', decision_notes: '', tracking_number: '' }); }}
                          data-testid={`btn-decision-${ret.id}`}>
                          Putuskan
                        </Button>
                      )}
                      <Button size="sm" variant="ghost" className="text-xs h-7 text-red-400" onClick={() => deleteReturn(ret)} data-testid={`btn-delete-return-${ret.id}`}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </GlassCard>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Add Review Dialog */}
      {reviewDialog && !reviewDialog._action && (
        <Dialog open={!!reviewDialog} onOpenChange={() => setReviewDialog(null)}>
          <DialogContent className="max-w-md" data-testid="dialog-add-review">
            <DialogHeader><DialogTitle>Catat Review</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Channel</Label>
                  <Select value={reviewDialog.channel_code} onValueChange={v => setReviewDialog(d => ({ ...d, channel_code: v }))}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>{CHANNEL_OPTIONS.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Rating</Label>
                  <Select value={String(reviewDialog.rating)} onValueChange={v => setReviewDialog(d => ({ ...d, rating: Number(v) }))}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>{[1,2,3,4,5].map(n => <SelectItem key={n} value={String(n)}>{n} ⭐</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Nama Customer</Label>
                  <Input className="mt-1" value={reviewDialog.customer_name} onChange={e => setReviewDialog(d => ({ ...d, customer_name: e.target.value }))} data-testid="input-review-name" />
                </div>
                <div>
                  <Label className="text-xs">SKU Produk</Label>
                  <Input className="mt-1 uppercase" value={reviewDialog.sku_code} onChange={e => setReviewDialog(d => ({ ...d, sku_code: e.target.value.toUpperCase() }))} />
                </div>
              </div>
              <div>
                <Label className="text-xs">Teks Review *</Label>
                <Textarea className="mt-1" rows={3} value={reviewDialog.review_text} onChange={e => setReviewDialog(d => ({ ...d, review_text: e.target.value }))} data-testid="input-review-text" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setReviewDialog(null)}>Batal</Button>
              <Button onClick={addReview} data-testid="btn-save-review">Simpan</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Respond Review Dialog */}
      {reviewDialog?._action === 'respond' && (
        <Dialog open={!!reviewDialog} onOpenChange={() => setReviewDialog(null)}>
          <DialogContent className="max-w-md" data-testid="dialog-respond-review">
            <DialogHeader><DialogTitle>Respons Review</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div className="p-3 rounded-lg bg-foreground/5 border border-foreground/10">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium">{reviewDialog.customer_name || 'Anonim'}</span>
                  <span className="text-xs text-foreground/40">{[1,2,3,4,5].map(i => i <= reviewDialog.rating ? '⭐' : '').join('')}</span>
                </div>
                <p className="text-sm text-foreground/60">{reviewDialog.review_text}</p>
              </div>
              <div>
                <Label className="text-xs">Template Respons</Label>
                <div className="flex flex-wrap gap-1 mt-1 mb-2">
                  {[
                    'Terima kasih atas ulasannya! Kami akan terus meningkatkan kualitas.',
                    'Mohon maaf atas pengalaman yang kurang baik. Tim kami akan segera membantu.',
                    'Terima kasih sudah berbelanja. Semoga puas dengan produk kami!',
                  ].map((t, i) => (
                    <button key={i} className="text-xs px-2 py-1 rounded border border-foreground/15 hover:border-primary/30 text-foreground/60" onClick={() => setResponseText(t)}>
                      Template {i+1}
                    </button>
                  ))}
                </div>
                <Textarea className="mt-1" rows={3} placeholder="Tulis respons Anda..." value={responseText} onChange={e => setResponseText(e.target.value)} data-testid="input-response-text" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setReviewDialog(null)}>Batal</Button>
              <Button onClick={() => respondReview(reviewDialog.id)} disabled={!!respondingId || !responseText.trim()} data-testid="btn-send-response">
                {respondingId ? 'Mengirim...' : 'Kirim Respons'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Return New/Edit Dialog */}
      {returnDialog && (
        <Dialog open={!!returnDialog} onOpenChange={() => setReturnDialog(null)}>
          <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="dialog-return">
            <DialogHeader><DialogTitle>{returnDialog.id ? 'Edit Return' : 'Kasus Return Baru'}</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Tipe Return</Label>
                  <Select value={returnDialog.return_type} onValueChange={v => setReturnDialog(d => ({ ...d, return_type: v }))}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="expedition_return">Retur Ekspedisi</SelectItem>
                      <SelectItem value="customer_refund">Refund Customer</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Channel</Label>
                  <Select value={returnDialog.channel_code} onValueChange={v => setReturnDialog(d => ({ ...d, channel_code: v }))}>
                    <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>{CHANNEL_OPTIONS.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs">Nama Customer *</Label>
                  <Input className="mt-1" value={returnDialog.customer_name} onChange={e => setReturnDialog(d => ({ ...d, customer_name: e.target.value }))} data-testid="input-return-customer" />
                </div>
                <div>
                  <Label className="text-xs">No. Order</Label>
                  <Input className="mt-1" placeholder="ORD-..." value={returnDialog.order_number} onChange={e => setReturnDialog(d => ({ ...d, order_number: e.target.value }))} />
                </div>
              </div>
              <div>
                <Label className="text-xs">Alasan Return *</Label>
                <Textarea className="mt-1" rows={2} value={returnDialog.reason} onChange={e => setReturnDialog(d => ({ ...d, reason: e.target.value }))} data-testid="input-return-reason" />
              </div>
              <div>
                <Label className="text-xs">Catatan Bukti (foto, video)</Label>
                <Textarea className="mt-1" rows={2} value={returnDialog.evidence_notes} onChange={e => setReturnDialog(d => ({ ...d, evidence_notes: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">Estimasi Nilai (Rp)</Label>
                <Input type="number" className="mt-1" min={0} value={returnDialog.estimated_value} onChange={e => setReturnDialog(d => ({ ...d, estimated_value: e.target.value }))} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setReturnDialog(null)}>Batal</Button>
              <Button onClick={saveReturn} disabled={savingReturn} data-testid="btn-save-return">
                {savingReturn ? 'Menyimpan...' : 'Simpan'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Decision Dialog */}
      {decisionDialog && (
        <Dialog open={!!decisionDialog} onOpenChange={() => setDecisionDialog(null)}>
          <DialogContent className="max-w-md" data-testid="dialog-decision">
            <DialogHeader><DialogTitle>Putuskan Kasus Return</DialogTitle></DialogHeader>
            <div className="space-y-3 py-2">
              <div className="p-3 rounded-lg bg-foreground/5 border border-foreground/10 text-sm">
                <div className="font-medium">{decisionDialog.customer_name}</div>
                <div className="text-foreground/60 text-xs mt-0.5">{decisionDialog.reason}</div>
              </div>
              <div>
                <Label className="text-xs">Keputusan</Label>
                <Select value={decision.decision} onValueChange={v => setDecision(d => ({ ...d, decision: v }))}>
                  <SelectTrigger className="mt-1" data-testid="select-decision"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="reship">Kirim Ulang</SelectItem>
                    <SelectItem value="refund">Refund</SelectItem>
                    <SelectItem value="reject">Tolak</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {decision.decision === 'reship' && (
                <div>
                  <Label className="text-xs">No. Resi Pengiriman Ulang</Label>
                  <Input className="mt-1" value={decision.tracking_number} onChange={e => setDecision(d => ({ ...d, tracking_number: e.target.value }))} />
                </div>
              )}
              <div>
                <Label className="text-xs">Catatan Keputusan *</Label>
                <Textarea className="mt-1" rows={2} value={decision.decision_notes} onChange={e => setDecision(d => ({ ...d, decision_notes: e.target.value }))} data-testid="input-decision-notes" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDecisionDialog(null)}>Batal</Button>
              <Button onClick={makeDecision} disabled={!decision.decision_notes.trim()} data-testid="btn-confirm-decision">
                Konfirmasi
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
