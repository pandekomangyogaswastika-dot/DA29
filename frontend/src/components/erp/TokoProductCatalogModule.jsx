import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Shirt, Plus, Search, Edit2, Trash2, ImagePlus, X, Package, Loader2, Copy } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { PageHeader } from './moduleAtoms';

const CHANNELS = [
  { code: 'shopee', name: 'Shopee' },
  { code: 'tokopedia', name: 'Tokopedia' },
  { code: 'tiktok_shop', name: 'TikTok Shop' },
  { code: 'website', name: 'Website' },
];

const STATUS_FILTERS = [
  { id: 'all', label: 'Semua' },
  { id: 'active', label: 'Aktif' },
  { id: 'draft', label: 'Draft' },
  { id: 'archived', label: 'Arsip' },
];

const fmtIDR = (n) => `Rp ${Number(n || 0).toLocaleString('id-ID')}`;

const emptyForm = {
  sku_code: '',
  name: '',
  description: '',
  category: '',
  base_price: 0,
  cost_price: 0,
  channel_prices: [],
  variants: [],
  photos: [],
  stock_total: 0,
  weight_grams: 0,
  status: 'draft',
  tags: [],
};

export default function TokoProductCatalogModule({ token }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState(null); // {data} for edit; {} for create
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter !== 'all') params.set('status', filter);
      if (search) params.set('search', search);
      const r = await fetch(`/api/dewi/toko/products?${params}`, { headers });
      if (r.ok) setProducts(await r.json());
    } finally {
      setLoading(false);
    }
  }, [filter, search, headers]);

  useEffect(() => { load(); }, [load]);

  const save = async (form, id) => {
    setSaving(true);
    try {
      const body = {
        ...form,
        base_price: Number(form.base_price || 0),
        cost_price: Number(form.cost_price || 0),
        stock_total: Number(form.stock_total || 0),
        weight_grams: Number(form.weight_grams || 0),
        channel_prices: form.channel_prices.filter((cp) => cp.price > 0),
      };
      const url = id ? `/api/dewi/toko/products/${id}` : '/api/dewi/toko/products';
      const method = id ? 'PUT' : 'POST';
      const r = await fetch(url, { method, headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Gagal');
      toast.success(id ? 'Produk diperbarui' : 'Produk dibuat');
      setEditing(null);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (p) => {
    if (!window.confirm(`Hapus produk ${p.sku_code}?`)) return;
    const r = await fetch(`/api/dewi/toko/products/${p.id}`, { method: 'DELETE', headers });
    if (r.ok) { toast.success('Dihapus'); load(); } else toast.error('Gagal hapus');
  };

  return (
    <div className="p-6 space-y-6" data-testid="toko-product-catalog">
      <PageHeader
        title="Katalog Produk Toko Online"
        description="Master SKU, varian, harga per channel, foto produk."
        icon={Shirt}
        actions={
          <Button size="sm" onClick={() => setEditing({})} className="gap-1.5" data-testid="toko-product-create-btn">
            <Plus className="w-3.5 h-3.5" /> Produk Baru
          </Button>
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex gap-1.5">
          {STATUS_FILTERS.map((f) => (
            <Button key={f.id} size="sm" variant={filter === f.id ? 'default' : 'outline'} onClick={() => setFilter(f.id)} data-testid={`toko-product-filter-${f.id}`}>
              {f.label}
            </Button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-foreground/40" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Cari SKU / nama produk..."
            className="w-full rounded-lg border border-white/10 bg-white/5 pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:border-[hsl(var(--primary))]/60"
            data-testid="toko-product-search"
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 animate-pulse">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-56 rounded-xl bg-foreground/[0.05]" />)}
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-14 rounded-xl border border-dashed border-white/10">
          <Package className="w-10 h-10 mx-auto text-foreground/30 mb-2" />
          <p className="text-sm text-foreground/50">Belum ada produk. Klik "Produk Baru" untuk mulai.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" data-testid="toko-product-grid">
          {products.map((p) => (
            <GlassCard key={p.id} className="overflow-hidden flex flex-col" data-testid={`toko-product-card-${p.id}`}>
              <div className="aspect-square bg-foreground/[0.04] flex items-center justify-center relative overflow-hidden">
                {p.photos?.[0] ? (
                  <img src={p.photos[0]} alt={p.name} className="w-full h-full object-cover" />
                ) : (
                  <Shirt className="w-10 h-10 text-foreground/20" />
                )}
                <div className="absolute top-2 right-2">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase font-medium ${
                    p.status === 'active' ? 'bg-emerald-500/20 text-emerald-300'
                    : p.status === 'draft' ? 'bg-amber-500/20 text-amber-300'
                    : 'bg-foreground/20 text-foreground/60'
                  }`}>{p.status}</span>
                </div>
              </div>
              <div className="p-3 space-y-1.5 flex-1 flex flex-col">
                <div className="font-mono text-[10px] text-foreground/55 flex items-center gap-1">
                  {p.sku_code}
                </div>
                <div className="text-sm font-medium line-clamp-2">{p.name}</div>
                <div className="text-xs text-foreground/55">{p.category || '—'}</div>
                <div className="flex items-center justify-between mt-auto pt-2">
                  <div>
                    <div className="text-sm font-bold tabular-nums">{fmtIDR(p.base_price)}</div>
                    <div className="text-xs text-foreground/55">Stok {p.stock_total ?? 0}</div>
                  </div>
                  <div className="flex gap-1">
                    <Button size="icon" variant="ghost" className="w-7 h-7" onClick={() => setEditing({ data: p })} data-testid={`toko-product-edit-${p.id}`}>
                      <Edit2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="icon" variant="ghost" className="w-7 h-7 text-red-400 hover:bg-red-500/15" onClick={() => remove(p)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      )}

      {editing && <ProductEditor product={editing.data} headers={headers} token={token} onClose={() => setEditing(null)} onSave={save} saving={saving} />}
    </div>
  );
}

function ProductEditor({ product, headers, token, onClose, onSave, saving }) {
  const isEdit = Boolean(product);
  const [form, setForm] = useState(() => product ? {
    ...emptyForm,
    ...product,
    channel_prices: Array.isArray(product.channel_prices) ? product.channel_prices : [],
    variants: Array.isArray(product.variants) ? product.variants : [],
    photos: Array.isArray(product.photos) ? product.photos : [],
    tags: Array.isArray(product.tags) ? product.tags : [],
  } : { ...emptyForm });
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));

  const setChannelPrice = (code, price) => {
    const existing = form.channel_prices.find((c) => c.channel === code);
    const val = Number(price || 0);
    let next;
    if (existing) {
      next = form.channel_prices.map((c) => c.channel === code ? { ...c, price: val } : c);
    } else {
      next = [...form.channel_prices, { channel: code, price: val, active: true }];
    }
    set({ channel_prices: next });
  };
  const getChannelPrice = (code) => form.channel_prices.find((c) => c.channel === code)?.price ?? '';

  const addVariant = () => set({ variants: [...form.variants, { name: '', size: '', color: '', stock: 0 }] });
  const updateVariant = (i, patch) => set({ variants: form.variants.map((v, idx) => idx === i ? { ...v, ...patch } : v) });
  const removeVariant = (i) => set({ variants: form.variants.filter((_, idx) => idx !== i) });

  const handlePhotoUpload = async (e) => {
    if (!isEdit) {
      toast.error('Simpan produk dulu sebelum upload foto');
      if (fileRef.current) fileRef.current.value = '';
      return;
    }
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    for (const f of files) {
      if (!f.type.startsWith('image/')) { toast.error(`${f.name} bukan gambar`); continue; }
      if (f.size > 5 * 1024 * 1024) { toast.error(`${f.name} > 5MB`); continue; }
      try {
        const fd = new FormData();
        fd.append('file', f);
        const r = await fetch(`/api/dewi/toko/products/${product.id}/photos`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: fd,
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Upload gagal');
        set({ photos: [...form.photos, d.url] });
      } catch (err) { toast.error(`${f.name}: ${err.message}`); }
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
  };

  const removePhoto = async (url) => {
    if (isEdit) {
      try {
        await fetch(`/api/dewi/toko/products/${product.id}/photos/remove`, {
          method: 'POST', headers, body: JSON.stringify({ url }),
        });
      } catch (e) { /* ignore */ }
    }
    set({ photos: form.photos.filter((u) => u !== url) });
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="toko-product-editor">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shirt className="w-4 h-4 text-pink-400" /> {isEdit ? 'Edit Produk' : 'Produk Baru'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Basic */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">SKU Code *</Label>
              <Input value={form.sku_code} onChange={(e) => set({ sku_code: e.target.value.toUpperCase() })} placeholder="BLS-LINEN-001" disabled={isEdit} data-testid="toko-product-sku" />
            </div>
            <div>
              <Label className="text-xs">Kategori</Label>
              <Input value={form.category} onChange={(e) => set({ category: e.target.value })} placeholder="Blouse, Dress..." />
            </div>
          </div>
          <div>
            <Label className="text-xs">Nama Produk *</Label>
            <Input value={form.name} onChange={(e) => set({ name: e.target.value })} placeholder="Blouse Linen Premium..." data-testid="toko-product-name" />
          </div>
          <div>
            <Label className="text-xs">Deskripsi</Label>
            <Textarea value={form.description} onChange={(e) => set({ description: e.target.value })} rows={3} />
          </div>

          {/* Pricing */}
          <div className="rounded-lg border border-white/10 p-3 space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-foreground/55">Pricing</div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Base Price (Rp)</Label>
                <Input type="number" value={form.base_price} onChange={(e) => set({ base_price: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">HPP / Cost (Rp)</Label>
                <Input type="number" value={form.cost_price} onChange={(e) => set({ cost_price: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">Berat (gram)</Label>
                <Input type="number" value={form.weight_grams} onChange={(e) => set({ weight_grams: e.target.value })} />
              </div>
            </div>
            <div className="pt-2">
              <Label className="text-xs">Harga per Channel (opsional)</Label>
              <div className="grid grid-cols-2 gap-2 mt-1.5">
                {CHANNELS.map((c) => (
                  <div key={c.code} className="flex items-center gap-2">
                    <span className="text-xs text-foreground/65 w-24">{c.name}</span>
                    <Input type="number" value={getChannelPrice(c.code)} onChange={(e) => setChannelPrice(c.code, e.target.value)} placeholder="kosong = pakai base" />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Stock & Status */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Stok Total</Label>
              <Input type="number" value={form.stock_total} onChange={(e) => set({ stock_total: e.target.value })} />
            </div>
            <div>
              <Label className="text-xs">Status</Label>
              <Select value={form.status} onValueChange={(v) => set({ status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="active">Active (Publish)</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Variants */}
          <div className="rounded-lg border border-white/10 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs font-medium uppercase tracking-wider text-foreground/55">Varian (opsional)</div>
              <Button size="sm" variant="outline" onClick={addVariant} className="h-7 text-xs gap-1"><Plus className="w-3 h-3" /> Varian</Button>
            </div>
            {form.variants.length === 0 ? (
              <p className="text-xs text-foreground/45">Belum ada varian. Tambahkan varian kalau produk punya multi-size/color.</p>
            ) : (
              form.variants.map((v, i) => (
                <div key={i} className="grid grid-cols-[1fr_80px_100px_80px_30px] gap-2 items-center">
                  <Input placeholder="Nama" value={v.name} onChange={(e) => updateVariant(i, { name: e.target.value })} />
                  <Input placeholder="Size" value={v.size} onChange={(e) => updateVariant(i, { size: e.target.value })} />
                  <Input placeholder="Color" value={v.color} onChange={(e) => updateVariant(i, { color: e.target.value })} />
                  <Input type="number" placeholder="Stok" value={v.stock} onChange={(e) => updateVariant(i, { stock: Number(e.target.value || 0) })} />
                  <Button size="icon" variant="ghost" className="w-7 h-7 text-red-400" onClick={() => removeVariant(i)}><X className="w-3.5 h-3.5" /></Button>
                </div>
              ))
            )}
          </div>

          {/* Photos */}
          <div className="rounded-lg border border-white/10 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs font-medium uppercase tracking-wider text-foreground/55">Foto Produk</div>
              {isEdit ? (
                <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={uploading} className="h-7 text-xs gap-1" data-testid="toko-product-upload-photo">
                  {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ImagePlus className="w-3 h-3" />}
                  Upload
                </Button>
              ) : (
                <span className="text-[10px] text-foreground/45 italic">Simpan produk dulu</span>
              )}
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={handlePhotoUpload} className="hidden" />
            </div>
            {form.photos.length === 0 ? (
              <p className="text-xs text-foreground/45">Belum ada foto.</p>
            ) : (
              <div className="grid grid-cols-4 gap-2">
                {form.photos.map((url) => (
                  <div key={url} className="relative aspect-square rounded-lg border border-white/10 overflow-hidden bg-foreground/[0.04]">
                    <img src={url} alt="" className="w-full h-full object-cover" />
                    <button type="button" onClick={() => removePhoto(url)} className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-red-500">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Batal</Button>
          <Button onClick={() => onSave(form, product?.id)} disabled={saving || !form.sku_code || !form.name} data-testid="toko-product-save">
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />}
            {isEdit ? 'Simpan' : 'Buat'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
