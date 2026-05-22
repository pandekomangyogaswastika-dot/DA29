/**
 * LiveHost Management Module
 * 
 * Features:
 * - LiveHost CRUD (list, create, edit, delete)
 * - Weekly shift calendar view
 * - Shift assignment & management
 * - Clock in/out tracking
 * - Shift performance recording
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Users, Plus, Edit, Trash2, Calendar, Clock, DollarSign, TrendingUp,
  CheckCircle, XCircle, AlertCircle, RefreshCw, Search, Filter, X,
  ChevronLeft, ChevronRight, Eye, UserCheck, UserX, Loader2, Save,
  Video, BarChart3, Calendar as CalendarIcon, User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import AnalyticsTab from './AnalyticsTab';
import PaymentTab from './PaymentTab';
import { AccountBadge, getPlatformConfig } from './AccountBadge';
import { ActiveAccountBar } from './ActiveAccountBar';
import { useActiveMarketingAccount } from '@/hooks/useActiveMarketingAccount';

const API = process.env.REACT_APP_BACKEND_URL;

const fmt = (n) => new Intl.NumberFormat('id-ID').format(n || 0);
const fmtRp = (n) => `Rp ${fmt(n)}`;

// ══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ══════════════════════════════════════════════════════════════════════════════

const StatusBadge = ({ status }) => {
  const config = {
    active: { label: 'Active', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' },
    inactive: { label: 'Inactive', color: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' },
    on_leave: { label: 'On Leave', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' },
  };
  const cfg = config[status] || config.inactive;
  return <Badge className={`text-xs ${cfg.color}`}>{cfg.label}</Badge>;
};

const AttendanceBadge = ({ status }) => {
  const config = {
    scheduled: { label: 'Scheduled', color: 'bg-blue-100 text-blue-700', icon: CalendarIcon },
    on_time: { label: 'On Time', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
    late: { label: 'Late', color: 'bg-amber-100 text-amber-700', icon: AlertCircle },
    no_show: { label: 'No Show', color: 'bg-red-100 text-red-700', icon: XCircle },
    completed: { label: 'Completed', color: 'bg-violet-100 text-violet-700', icon: CheckCircle },
  };
  const cfg = config[status] || config.scheduled;
  const Icon = cfg.icon;
  return (
    <Badge className={`text-xs ${cfg.color} flex items-center gap-1`}>
      <Icon size={10} />
      {cfg.label}
    </Badge>
  );
};

const EmploymentTypeBadge = ({ type }) => {
  const config = {
    full_time: { label: 'Full Time', color: 'bg-blue-100 text-blue-700' },
    part_time: { label: 'Part Time', color: 'bg-violet-100 text-violet-700' },
    freelance: { label: 'Freelance', color: 'bg-pink-100 text-pink-700' },
    contract: { label: 'Contract', color: 'bg-amber-100 text-amber-700' },
  };
  const cfg = config[type] || config.part_time;
  return <Badge className={`text-xs ${cfg.color}`}>{cfg.label}</Badge>;
};

// ══════════════════════════════════════════════════════════════════════════════
// MAIN MODULE
// ══════════════════════════════════════════════════════════════════════════════

export default function LiveHostModule({ token }) {
  const [activeTab, setActiveTab] = useState('hosts'); // hosts | shifts | calendar
  const authH = useMemo(() => ({ Authorization: `Bearer ${token || localStorage.getItem('auth_token')}` }), [token]);

  return (
    <div className="min-h-screen bg-background p-4 md:p-6" data-testid="livehost-module">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Users size={24} className="text-primary" />
          LiveHost Management
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Kelola live host, shift scheduling, dan performance tracking
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-muted rounded-xl mb-6 overflow-x-auto">
        {[
          { id: 'hosts', label: 'Live Hosts', icon: Users },
          { id: 'shifts', label: 'Shift Management', icon: Clock },
          { id: 'calendar', label: 'Calendar View', icon: Calendar },
          { id: 'scripts', label: 'Script Library', icon: Video },
          { id: 'training', label: 'Training', icon: TrendingUp },
          { id: 'analytics', label: 'Analytics', icon: BarChart3 },
          { id: 'payment', label: 'Payment', icon: DollarSign },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 justify-center whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            data-testid={`tab-${tab.id}`}
          >
            <tab.icon size={15} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'hosts' && <LiveHostsTab authH={authH} />}
      {activeTab === 'shifts' && <ShiftsTab authH={authH} />}
      {activeTab === 'calendar' && <CalendarTab authH={authH} />}
      {activeTab === 'scripts' && <ScriptsTab authH={authH} />}
      {activeTab === 'training' && <TrainingTab authH={authH} />}
      {activeTab === 'analytics' && <AnalyticsTab authH={authH} />}
      {activeTab === 'payment' && <PaymentTab authH={authH} />}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB 1: LIVE HOSTS
// ══════════════════════════════════════════════════════════════════════════════

function LiveHostsTab({ authH }) {
  const [hosts, setHosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [accounts, setAccounts] = useState([]);

  // Shared persistent account context (localStorage)
  const { activeAccount: activeAccountCtx, setActiveAccount: setActiveAccountCtx } = useActiveMarketingAccount();
  const filterAccountId = activeAccountCtx?.id || '';
  const setFilterAccountId = (id) => {
    const acc = accounts.find(a => a.id === id);
    setActiveAccountCtx(acc || null);
  };

  const [showAddEditModal, setShowAddEditModal] = useState(false);
  const [editingHost, setEditingHost] = useState(null);

  const fetchHosts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (searchQuery) params.append('search', searchQuery);

      const res = await fetch(`${API}/api/marketing/livehost?${params}`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setHosts(data);
      }
    } catch (e) {
      toast.error('Gagal memuat data LiveHost');
    } finally {
      setLoading(false);
    }
  }, [authH, statusFilter, searchQuery]);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/marketing/accounts?status=active`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setAccounts(data);
      }
    } catch (e) {}
  }, [authH]);

  useEffect(() => {
    fetchHosts();
    fetchAccounts();
  }, [fetchHosts, fetchAccounts]);

  const handleDelete = async (host) => {
    if (!window.confirm(`Yakin ingin menghapus LiveHost "${host.name}"?`)) return;
    try {
      const res = await fetch(`${API}/api/marketing/livehost/${host.id}`, {
        method: 'DELETE',
        headers: authH,
      });
      if (res.ok) {
        toast.success('LiveHost berhasil dihapus');
        fetchHosts();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Gagal menghapus LiveHost');
      }
    } catch (e) {
      toast.error('Gagal menghapus LiveHost');
    }
  };

  // Client-side filter by account
  const displayedHosts = filterAccountId
    ? hosts.filter(h => (h.assigned_accounts || []).some(a => a.id === filterAccountId))
    : hosts;

  return (
    <div className="space-y-4">
      {/* Active Account Bar */}
      <ActiveAccountBar
        accounts={accounts}
        activeAccount={accounts.find(a => a.id === filterAccountId) || null}
        onAccountChange={(acc) => setFilterAccountId(acc ? acc.id : '')}
        hint="Filter LiveHost by akun:"
      />

      {/* Filters & Actions */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Cari nama atau email..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-9 h-9"
              data-testid="search-livehost"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[130px] h-9" data-testid="filter-status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
              <SelectItem value="on_leave">On Leave</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Button variant="outline" size="sm" onClick={fetchHosts} className="h-9" data-testid="refresh-hosts">
            <RefreshCw size={14} className="mr-1.5" />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => {
              setEditingHost(null);
              setShowAddEditModal(true);
            }}
            className="h-9"
            data-testid="add-livehost-btn"
          >
            <Plus size={14} className="mr-1.5" />
            Tambah LiveHost
          </Button>
        </div>
      </div>

      {/* LiveHost Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={28} className="animate-spin text-muted-foreground" />
        </div>
      ) : hosts.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Users size={40} className="text-muted-foreground opacity-40" />
            <p className="font-medium">Belum ada LiveHost</p>
            <p className="text-sm text-muted-foreground">Tambahkan LiveHost pertama untuk mulai scheduling</p>
            <Button size="sm" onClick={() => setShowAddEditModal(true)}>
              <Plus size={14} className="mr-1.5" />
              Tambah LiveHost
            </Button>
          </CardContent>
        </Card>
        ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="livehosts-table">
                <thead>
                  <tr className="border-b bg-muted/30">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Nama</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Email</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Employment</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Hourly Rate</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Assigned Accounts</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {displayedHosts.map(host => (
                    <tr key={host.id} className="hover:bg-muted/30 transition-colors" data-testid={`host-row-${host.id}`}>
                      <td className="px-4 py-3 font-medium">{host.name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{host.email}</td>
                      <td className="px-4 py-3">
                        <EmploymentTypeBadge type={host.employment_type} />
                      </td>
                      <td className="px-4 py-3 tabular-nums">{fmtRp(host.hourly_rate)}</td>
                      <td className="px-4 py-3">
                        {/* Assigned Accounts — tampilkan badge per akun */}
                        <div className="flex flex-wrap gap-1">
                          {(host.assigned_accounts || []).length > 0 ? (
                            host.assigned_accounts.map(a => {
                              const full = accounts.find(x => x.id === a.id);
                              return (
                                <AccountBadge
                                  key={a.id}
                                  account={full || { account_name: a.name, platform: 'unknown' }}
                                  size="xs"
                                />
                              );
                            })
                          ) : (
                            <span className="text-xs text-muted-foreground italic">Belum di-assign</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={host.status} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => {
                              setEditingHost(host);
                              setShowAddEditModal(true);
                            }}
                            data-testid={`edit-host-${host.id}`}
                          >
                            <Edit size={14} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => handleDelete(host)}
                            data-testid={`delete-host-${host.id}`}
                          >
                            <Trash2 size={14} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add/Edit Modal */}
      {showAddEditModal && (
        <AddEditHostModal
          host={editingHost}
          accounts={accounts}
          authH={authH}
          onClose={() => {
            setShowAddEditModal(false);
            setEditingHost(null);
          }}
          onSuccess={() => {
            setShowAddEditModal(false);
            setEditingHost(null);
            fetchHosts();
          }}
        />
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// ADD/EDIT HOST MODAL
// ══════════════════════════════════════════════════════════════════════════════

function AddEditHostModal({ host, accounts, authH, onClose, onSuccess }) {
  const isEdit = !!host;
  const [form, setForm] = useState({
    name: host?.name || '',
    email: host?.email || '',
    password: '',
    phone: host?.phone || '',
    employment_type: host?.employment_type || 'part_time',
    hourly_rate: host?.hourly_rate || 0,
    shift_preferences: host?.shift_preferences || [],
    language_skills: host?.language_skills || [],
    product_expertise: host?.product_expertise || [],
    assigned_account_ids: host?.assigned_account_ids || [],
    status: host?.status || 'active',
    notes: host?.notes || '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.email) {
      toast.error('Nama dan email wajib diisi');
      return;
    }
    if (!isEdit && !form.password) {
      toast.error('Password wajib diisi untuk LiveHost baru');
      return;
    }

    setSaving(true);
    try {
      const payload = { ...form };
      if (isEdit && !form.password) {
        delete payload.password;
      }

      const url = isEdit ? `${API}/api/marketing/livehost/${host.id}` : `${API}/api/marketing/livehost`;
      const method = isEdit ? 'PATCH' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { ...authH, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        toast.success(isEdit ? 'LiveHost berhasil diupdate' : 'LiveHost berhasil ditambahkan');
        onSuccess();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Gagal menyimpan LiveHost');
      }
    } catch (e) {
      toast.error('Gagal menyimpan LiveHost');
    } finally {
      setSaving(false);
    }
  };

  const toggleArrayItem = (field, value) => {
    const current = form[field] || [];
    if (current.includes(value)) {
      setForm(f => ({ ...f, [field]: current.filter(v => v !== value) }));
    } else {
      setForm(f => ({ ...f, [field]: [...current, value] }));
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User size={18} className="text-primary" />
            {isEdit ? 'Edit LiveHost' : 'Tambah LiveHost Baru'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Nama *</Label>
              <Input
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="mt-1 h-9"
                placeholder="Nama LiveHost"
                data-testid="input-name"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold">Email *</Label>
              <Input
                type="email"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                className="mt-1 h-9"
                placeholder="email@example.com"
                data-testid="input-email"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Password {!isEdit && '*'}</Label>
              <Input
                type="password"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                className="mt-1 h-9"
                placeholder={isEdit ? 'Kosongkan jika tidak diubah' : 'Password login'}
                data-testid="input-password"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold">Phone</Label>
              <Input
                value={form.phone}
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                className="mt-1 h-9"
                placeholder="08xxx"
                data-testid="input-phone"
              />
            </div>
          </div>

          {/* Employment & Rate */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Employment Type</Label>
              <Select value={form.employment_type} onValueChange={v => setForm(f => ({ ...f, employment_type: v }))}>
                <SelectTrigger className="mt-1 h-9" data-testid="select-employment">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full_time">Full Time</SelectItem>
                  <SelectItem value="part_time">Part Time</SelectItem>
                  <SelectItem value="freelance">Freelance</SelectItem>
                  <SelectItem value="contract">Contract</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold">Hourly Rate (Rp)</Label>
              <Input
                type="number"
                min="0"
                step="1000"
                value={form.hourly_rate}
                onChange={e => setForm(f => ({ ...f, hourly_rate: Number(e.target.value) }))}
                className="mt-1 h-9"
                data-testid="input-hourly-rate"
              />
            </div>
          </div>

          {/* Shift Preferences */}
          <div>
            <Label className="text-xs font-semibold mb-2 block">Shift Preferences</Label>
            <div className="flex flex-wrap gap-2">
              {['morning', 'afternoon', 'evening', 'night'].map(shift => (
                <button
                  key={shift}
                  type="button"
                  onClick={() => toggleArrayItem('shift_preferences', shift)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    (form.shift_preferences || []).includes(shift)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                  data-testid={`shift-${shift}`}
                >
                  {shift.charAt(0).toUpperCase() + shift.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Language Skills */}
          <div>
            <Label className="text-xs font-semibold mb-2 block">Language Skills</Label>
            <div className="flex flex-wrap gap-2">
              {['indonesia', 'english', 'mandarin'].map(lang => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => toggleArrayItem('language_skills', lang)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    (form.language_skills || []).includes(lang)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                  data-testid={`lang-${lang}`}
                >
                  {lang.charAt(0).toUpperCase() + lang.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Product Expertise */}
          <div>
            <Label className="text-xs font-semibold mb-2 block">Product Expertise</Label>
            <div className="flex flex-wrap gap-2">
              {['fashion', 'electronics', 'food', 'beauty', 'health', 'home'].map(prod => (
                <button
                  key={prod}
                  type="button"
                  onClick={() => toggleArrayItem('product_expertise', prod)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    (form.product_expertise || []).includes(prod)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                  data-testid={`product-${prod}`}
                >
                  {prod.charAt(0).toUpperCase() + prod.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Assigned Accounts */}
          <div>
            <Label className="text-xs font-semibold mb-2 block">Assigned Platform Accounts</Label>
            <div className="max-h-32 overflow-y-auto border rounded-lg p-2 space-y-1">
              {accounts.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-2">Belum ada platform account</p>
              ) : (
                accounts.map(acc => (
                  <label key={acc.id} className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(form.assigned_account_ids || []).includes(acc.id)}
                      onChange={() => toggleArrayItem('assigned_account_ids', acc.id)}
                      className="rounded"
                      data-testid={`account-${acc.id}`}
                    />
                    <span className="text-xs flex-1">{acc.account_name}</span>
                    <Badge variant="outline" className="text-xs">{acc.platform}</Badge>
                  </label>
                ))
              )}
            </div>
          </div>

          {/* Status (only for edit) */}
          {isEdit && (
            <div>
              <Label className="text-xs font-semibold">Status</Label>
              <Select value={form.status} onValueChange={v => setForm(f => ({ ...f, status: v }))}>
                <SelectTrigger className="mt-1 h-9" data-testid="select-status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="on_leave">On Leave</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Notes */}
          <div>
            <Label className="text-xs font-semibold">Notes</Label>
            <Textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="mt-1 text-sm"
              rows={3}
              placeholder="Catatan tambahan..."
              data-testid="input-notes"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Batal
            </Button>
            <Button type="submit" disabled={saving} data-testid="submit-host">
              {saving ? (
                <>
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                  Menyimpan...
                </>
              ) : (
                <>
                  <Save size={14} className="mr-1.5" />
                  {isEdit ? 'Update' : 'Simpan'}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB 2: SHIFTS (LIST VIEW)
// ══════════════════════════════════════════════════════════════════════════════

function ShiftsTab({ authH }) {
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({ page: 1, total: 0, limit: 50 });
  const [filters, setFilters] = useState({
    host_id: 'all',
    account_id: '',
    date_from: '',
    date_to: '',
    attendance_status: 'all',
  });
  const [hosts, setHosts] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [showAddShiftModal, setShowAddShiftModal] = useState(false);
  const [showPerformanceModal, setShowPerformanceModal] = useState(false);
  const [selectedShift, setSelectedShift] = useState(null);

  const fetchShifts = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, limit: 50 });
      Object.entries(filters).forEach(([key, val]) => {
        if (val && val !== 'all') params.append(key, val);
      });

      const res = await fetch(`${API}/api/marketing/livehost/shifts?${params}`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setShifts(data.shifts || []);
        setPagination(data.pagination || { page: 1, total: 0, limit: 50 });
      }
    } catch (e) {
      toast.error('Gagal memuat data shift');
    } finally {
      setLoading(false);
    }
  }, [authH, filters]);

  const fetchHosts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/marketing/livehost?status=active`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setHosts(data);
      }
    } catch (e) {}
  }, [authH]);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/marketing/accounts?status=active`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setAccounts(data);
      }
    } catch (e) {}
  }, [authH]);

  useEffect(() => {
    fetchShifts();
    fetchHosts();
    fetchAccounts();
  }, [fetchShifts, fetchHosts, fetchAccounts]);

  const handleClockAction = async (shift, action) => {
    try {
      const res = await fetch(`${API}/api/marketing/livehost/clock`, {
        method: 'POST',
        headers: { ...authH, 'Content-Type': 'application/json' },
        body: JSON.stringify({ shift_id: shift.id, action }),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        fetchShifts(pagination.page);
      } else {
        const err = await res.json();
        toast.error(err.detail || `Gagal ${action}`);
      }
    } catch (e) {
      toast.error(`Gagal ${action}`);
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters & Actions */}
      <div className="flex flex-col sm:flex-row gap-3 items-end justify-between">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full">
          <div>
            <Label className="text-xs mb-1">LiveHost</Label>
            <Select value={filters.host_id} onValueChange={v => setFilters(f => ({ ...f, host_id: v }))}>
              <SelectTrigger className="h-9" data-testid="filter-host">
                <SelectValue placeholder="Semua Host" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Host</SelectItem>
                {hosts.map(h => (
                  <SelectItem key={h.id} value={h.id}>{h.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs mb-1">Dari Tanggal</Label>
            <Input
              type="date"
              value={filters.date_from}
              onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))}
              className="h-9"
              data-testid="filter-date-from"
            />
          </div>
          <div>
            <Label className="text-xs mb-1">Sampai Tanggal</Label>
            <Input
              type="date"
              value={filters.date_to}
              onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))}
              className="h-9"
              data-testid="filter-date-to"
            />
          </div>
          <div>
            <Label className="text-xs mb-1">Status</Label>
            <Select value={filters.attendance_status} onValueChange={v => setFilters(f => ({ ...f, attendance_status: v }))}>
              <SelectTrigger className="h-9" data-testid="filter-attendance">
                <SelectValue placeholder="Semua Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Status</SelectItem>
                <SelectItem value="scheduled">Scheduled</SelectItem>
                <SelectItem value="on_time">On Time</SelectItem>
                <SelectItem value="late">Late</SelectItem>
                <SelectItem value="no_show">No Show</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex gap-2 w-full sm:w-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchShifts(pagination.page)}
            className="h-9"
            data-testid="refresh-shifts"
          >
            <RefreshCw size={14} className="mr-1.5" />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => setShowAddShiftModal(true)}
            className="h-9"
            data-testid="add-shift-btn"
          >
            <Plus size={14} className="mr-1.5" />
            Tambah Shift
          </Button>
        </div>
      </div>

      {/* Shifts Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={28} className="animate-spin text-muted-foreground" />
        </div>
      ) : shifts.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Clock size={40} className="text-muted-foreground opacity-40" />
            <p className="font-medium">Belum ada shift</p>
            <Button size="sm" onClick={() => setShowAddShiftModal(true)}>
              <Plus size={14} className="mr-1.5" />
              Tambah Shift
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="shifts-table">
                  <thead>
                    <tr className="border-b bg-muted/30">
                      <th className="px-4 py-3 text-left text-xs font-semibold">Tanggal</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold">LiveHost</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold">Shift</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold">Waktu</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold">Performance</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {shifts.map(shift => (
                      <tr key={shift.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3 font-medium">{shift.date}</td>
                        <td className="px-4 py-3">{shift.host_name}</td>
                        <td className="px-4 py-3 capitalize">{shift.shift_type}</td>
                        <td className="px-4 py-3 text-xs tabular-nums">
                          {shift.shift_start_time} - {shift.shift_end_time}
                        </td>
                        <td className="px-4 py-3">
                          <AttendanceBadge status={shift.attendance_status} />
                        </td>
                        <td className="px-4 py-3">
                          {shift.revenue > 0 ? (
                            <div className="text-xs">
                              <div className="font-medium">{fmtRp(shift.revenue)}</div>
                              <div className="text-muted-foreground">{shift.orders} orders</div>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            {shift.attendance_status === 'scheduled' && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs"
                                onClick={() => handleClockAction(shift, 'clock_in')}
                                data-testid={`clock-in-${shift.id}`}
                              >
                                <UserCheck size={12} className="mr-1" />
                                Clock In
                              </Button>
                            )}
                            {(shift.attendance_status === 'on_time' || shift.attendance_status === 'late') && !shift.clock_out_time && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs"
                                onClick={() => handleClockAction(shift, 'clock_out')}
                                data-testid={`clock-out-${shift.id}`}
                              >
                                <UserX size={12} className="mr-1" />
                                Clock Out
                              </Button>
                            )}
                            {shift.attendance_status === 'completed' && shift.revenue === 0 && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs"
                                onClick={() => {
                                  setSelectedShift(shift);
                                  setShowPerformanceModal(true);
                                }}
                                data-testid={`record-performance-${shift.id}`}
                              >
                                <BarChart3 size={12} className="mr-1" />
                                Record
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {shifts.length} of {pagination.total} shifts
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fetchShifts(pagination.page - 1)}
                  disabled={!pagination.has_prev}
                >
                  <ChevronLeft size={14} />
                </Button>
                <span className="text-sm">
                  Page {pagination.page} of {pagination.total_pages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fetchShifts(pagination.page + 1)}
                  disabled={!pagination.has_next}
                >
                  <ChevronRight size={14} />
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      {showAddShiftModal && (
        <AddShiftModal
          hosts={hosts}
          accounts={accounts}
          authH={authH}
          onClose={() => setShowAddShiftModal(false)}
          onSuccess={() => {
            setShowAddShiftModal(false);
            fetchShifts(pagination.page);
          }}
        />
      )}

      {showPerformanceModal && selectedShift && (
        <RecordPerformanceModal
          shift={selectedShift}
          authH={authH}
          onClose={() => {
            setShowPerformanceModal(false);
            setSelectedShift(null);
          }}
          onSuccess={() => {
            setShowPerformanceModal(false);
            setSelectedShift(null);
            fetchShifts(pagination.page);
          }}
        />
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// ADD SHIFT MODAL
// ══════════════════════════════════════════════════════════════════════════════

function AddShiftModal({ hosts, accounts, authH, onClose, onSuccess }) {
  const [form, setForm] = useState({
    host_id: '',
    account_id: '',
    date: new Date().toISOString().split('T')[0],
    shift_type: 'morning',
    shift_start_time: '09:00',
    shift_end_time: '13:00',
    notes: '',
  });
  const [saving, setSaving] = useState(false);

  // Filter akun sesuai assigned_accounts dari host yang dipilih
  const selectedHost = hosts.find(h => h.id === form.host_id);
  const hostAssignedIds = (selectedHost?.assigned_accounts || []).map(a => a.id);
  const availableAccounts = hostAssignedIds.length > 0
    ? accounts.filter(a => hostAssignedIds.includes(a.id))
    : accounts;

  // Auto-clear account jika tidak tersedia setelah host berganti
  useEffect(() => {
    if (form.account_id && availableAccounts.length > 0 &&
        !availableAccounts.find(a => a.id === form.account_id)) {
      setForm(f => ({ ...f, account_id: '' }));
    }
  }, [form.host_id]); // eslint-disable-line

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.host_id || !form.account_id || !form.date) {
      toast.error('LiveHost, account, dan tanggal wajib diisi');
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API}/api/marketing/livehost/shifts`, {
        method: 'POST',
        headers: { ...authH, 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        toast.success('Shift berhasil dibuat');
        onSuccess();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Gagal membuat shift');
      }
    } catch (e) {
      toast.error('Gagal membuat shift');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock size={18} className="text-primary" />
            Tambah Shift Baru
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label className="text-xs font-semibold">LiveHost *</Label>
            <Select value={form.host_id} onValueChange={v => setForm(f => ({ ...f, host_id: v }))}>
              <SelectTrigger className="mt-1 h-9" data-testid="select-host">
                <SelectValue placeholder="Pilih LiveHost" />
              </SelectTrigger>
              <SelectContent>
                {hosts.map(h => (
                  <SelectItem key={h.id} value={h.id}>{h.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs font-semibold">Platform Account *</Label>
            <Select
              value={form.account_id}
              onValueChange={v => setForm(f => ({ ...f, account_id: v }))}
            >
              <SelectTrigger className="mt-1 h-9" data-testid="select-account">
                <SelectValue placeholder="Pilih Account" />
              </SelectTrigger>
              <SelectContent>
                {availableAccounts.map(a => {
                  const cfg = getPlatformConfig(a.platform);
                  return (
                    <SelectItem key={a.id} value={a.id}>
                      {cfg.icon} {a.account_name} ({cfg.label})
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            {form.host_id && hostAssignedIds.length === 0 && (
              <p className="text-[10px] text-amber-500 mt-1">
                Host belum di-assign ke akun manapun. Edit host untuk menambah assignment.
              </p>
            )}
            {form.account_id && availableAccounts.find(a => a.id === form.account_id) && (() => {
              const acc = availableAccounts.find(a => a.id === form.account_id);
              const cfg = getPlatformConfig(acc.platform);
              return (
                <div className={`mt-1.5 flex items-center gap-1.5 px-2 py-1 rounded border text-[10px] font-medium ${cfg.bg} ${cfg.border} ${cfg.text}`}>
                  {cfg.icon} Shift untuk: {acc.account_name}
                </div>
              );
            })()}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Tanggal *</Label>
              <Input
                type="date"
                value={form.date}
                onChange={e => setForm(f => ({ ...f, date: e.target.value }))}
                className="mt-1 h-9"
                data-testid="input-date"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold">Shift Type</Label>
              <Select value={form.shift_type} onValueChange={v => setForm(f => ({ ...f, shift_type: v }))}>
                <SelectTrigger className="mt-1 h-9" data-testid="select-shift-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="morning">Morning</SelectItem>
                  <SelectItem value="afternoon">Afternoon</SelectItem>
                  <SelectItem value="evening">Evening</SelectItem>
                  <SelectItem value="night">Night</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Start Time</Label>
              <Input
                type="time"
                value={form.shift_start_time}
                onChange={e => setForm(f => ({ ...f, shift_start_time: e.target.value }))}
                className="mt-1 h-9"
                data-testid="input-start-time"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold">End Time</Label>
              <Input
                type="time"
                value={form.shift_end_time}
                onChange={e => setForm(f => ({ ...f, shift_end_time: e.target.value }))}
                className="mt-1 h-9"
                data-testid="input-end-time"
              />
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold">Notes</Label>
            <Textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="mt-1 text-sm"
              rows={2}
              placeholder="Catatan shift..."
              data-testid="input-shift-notes"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Batal
            </Button>
            <Button type="submit" disabled={saving} data-testid="submit-shift">
              {saving ? (
                <>
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                  Menyimpan...
                </>
              ) : (
                <>
                  <Save size={14} className="mr-1.5" />
                  Simpan
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// RECORD PERFORMANCE MODAL
// ══════════════════════════════════════════════════════════════════════════════

function RecordPerformanceModal({ shift, authH, onClose, onSuccess }) {
  const [form, setForm] = useState({
    shift_id: shift.id,
    platform: shift.platform || 'shopee',
    viewers: 0,
    peak_viewers: 0,
    revenue: 0,
    orders: 0,
    items_promoted: [],
    script_adherence_score: null,
    challenges_faced: '',
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [itemInput, setItemInput] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    setSaving(true);
    try {
      const res = await fetch(`${API}/api/marketing/livehost/shifts/${shift.id}/performance`, {
        method: 'POST',
        headers: { ...authH, 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        toast.success('Performance berhasil dicatat');
        onSuccess();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Gagal mencatat performance');
      }
    } catch (e) {
      toast.error('Gagal mencatat performance');
    } finally {
      setSaving(false);
    }
  };

  const addItem = () => {
    if (itemInput.trim()) {
      setForm(f => ({ ...f, items_promoted: [...f.items_promoted, itemInput.trim()] }));
      setItemInput('');
    }
  };

  const removeItem = (index) => {
    setForm(f => ({ ...f, items_promoted: f.items_promoted.filter((_, i) => i !== index) }));
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 size={18} className="text-primary" />
            Record Shift Performance
          </DialogTitle>
          <p className="text-sm text-muted-foreground">
            {shift.host_name} - {shift.date} ({shift.shift_start_time}-{shift.shift_end_time})
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label className="text-xs font-semibold">Platform</Label>
            <Select value={form.platform} onValueChange={v => setForm(f => ({ ...f, platform: v }))}>
              <SelectTrigger className="mt-1 h-9" data-testid="select-platform">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="shopee">Shopee</SelectItem>
                <SelectItem value="tiktokshop">TikTokShop</SelectItem>
                <SelectItem value="tokopedia">Tokopedia</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Viewers</Label>
              <Input
                type="number"
                min="0"
                value={form.viewers}
                onChange={e => setForm(f => ({ ...f, viewers: Number(e.target.value) }))}
                className="mt-1 h-9"
                data-testid="input-viewers"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold">Peak Viewers</Label>
              <Input
                type="number"
                min="0"
                value={form.peak_viewers}
                onChange={e => setForm(f => ({ ...f, peak_viewers: Number(e.target.value) }))}
                className="mt-1 h-9"
                data-testid="input-peak-viewers"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Revenue (Rp)</Label>
              <Input
                type="number"
                min="0"
                step="1000"
                value={form.revenue}
                onChange={e => setForm(f => ({ ...f, revenue: Number(e.target.value) }))}
                className="mt-1 h-9"
                data-testid="input-revenue"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold">Orders</Label>
              <Input
                type="number"
                min="0"
                value={form.orders}
                onChange={e => setForm(f => ({ ...f, orders: Number(e.target.value) }))}
                className="mt-1 h-9"
                data-testid="input-orders"
              />
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold">Items Promoted</Label>
            <div className="mt-1 flex gap-2">
              <Input
                value={itemInput}
                onChange={e => setItemInput(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && (e.preventDefault(), addItem())}
                placeholder="Nama produk"
                className="h-9"
                data-testid="input-item"
              />
              <Button type="button" size="sm" onClick={addItem} className="h-9">
                <Plus size={14} />
              </Button>
            </div>
            {form.items_promoted.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {form.items_promoted.map((item, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {item}
                    <button
                      type="button"
                      onClick={() => removeItem(i)}
                      className="ml-1 hover:text-red-600"
                    >
                      <X size={10} />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div>
            <Label className="text-xs font-semibold">Script Adherence Score (0-100)</Label>
            <Input
              type="number"
              min="0"
              max="100"
              value={form.script_adherence_score || ''}
              onChange={e => setForm(f => ({ ...f, script_adherence_score: e.target.value ? Number(e.target.value) : null }))}
              className="mt-1 h-9"
              placeholder="Optional"
              data-testid="input-script-score"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold">Challenges Faced</Label>
            <Textarea
              value={form.challenges_faced}
              onChange={e => setForm(f => ({ ...f, challenges_faced: e.target.value }))}
              className="mt-1 text-sm"
              rows={2}
              placeholder="Kendala yang dihadapi saat live..."
              data-testid="input-challenges"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold">Notes</Label>
            <Textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              className="mt-1 text-sm"
              rows={2}
              placeholder="Catatan tambahan..."
              data-testid="input-performance-notes"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Batal
            </Button>
            <Button type="submit" disabled={saving} data-testid="submit-performance">
              {saving ? (
                <>
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                  Menyimpan...
                </>
              ) : (
                <>
                  <Save size={14} className="mr-1.5" />
                  Simpan
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB 3: CALENDAR VIEW (PLACEHOLDER - will be implemented in next iteration)
// ══════════════════════════════════════════════════════════════════════════════

function CalendarTab({ authH }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
        <Calendar size={48} className="text-muted-foreground opacity-40" />
        <p className="font-medium">Calendar View - Coming Soon</p>
        <p className="text-sm text-muted-foreground text-center max-w-md">
          Weekly/monthly calendar view untuk visualisasi shift akan diimplementasi di iterasi berikutnya
        </p>
      </CardContent>
    </Card>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB 4: SCRIPT LIBRARY
// ══════════════════════════════════════════════════════════════════════════════

function ScriptsTab({ authH }) {
  const [scripts, setScripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingScript, setEditingScript] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [categoryFilter, setCategoryFilter] = useState('all');

  const fetchScripts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (categoryFilter !== 'all') params.append('category', categoryFilter);

      const res = await fetch(`${API}/api/marketing/livehost/scripts?${params}`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setScripts(data);
      }
    } catch (e) {
      toast.error('Gagal memuat scripts');
    } finally {
      setLoading(false);
    }
  }, [authH, categoryFilter]);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/marketing/accounts?status=active`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setAccounts(data);
      }
    } catch (e) {}
  }, [authH]);

  useEffect(() => {
    fetchScripts();
    fetchAccounts();
  }, [fetchScripts, fetchAccounts]);

  const handleDelete = async (script) => {
    if (!window.confirm(`Yakin ingin menghapus script "${script.title}"?`)) return;
    try {
      const res = await fetch(`${API}/api/marketing/livehost/scripts/${script.id}`, {
        method: 'DELETE',
        headers: authH,
      });
      if (res.ok) {
        toast.success('Script berhasil dihapus');
        fetchScripts();
      }
    } catch (e) {
      toast.error('Gagal menghapus script');
    }
  };

  return (
    <div className="space-y-4">
      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[160px] h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="opening">Opening</SelectItem>
              <SelectItem value="demo">Demo/Product</SelectItem>
              <SelectItem value="promo">Promo</SelectItem>
              <SelectItem value="closing">Closing</SelectItem>
              <SelectItem value="faq">FAQ</SelectItem>
              <SelectItem value="objection_handling">Objection Handling</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={fetchScripts} className="h-9">
            <RefreshCw size={14} className="mr-1.5" />
            Refresh
          </Button>
        </div>
        <Button
          size="sm"
          onClick={() => {
            setEditingScript(null);
            setShowModal(true);
          }}
          className="h-9"
        >
          <Plus size={14} className="mr-1.5" />
          Add Script
        </Button>
      </div>

      {/* Scripts Grid */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={28} className="animate-spin text-muted-foreground" />
        </div>
      ) : scripts.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <Video size={40} className="text-muted-foreground opacity-40" />
            <p className="font-medium">Belum ada script</p>
            <Button size="sm" onClick={() => setShowModal(true)}>
              <Plus size={14} className="mr-1.5" />
              Add Script
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scripts.map(script => (
            <Card key={script.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-semibold line-clamp-2">{script.title}</CardTitle>
                    <div className="flex items-center gap-2 mt-1.5">
                      <Badge variant="outline" className="text-xs capitalize">{script.category.replace('_', ' ')}</Badge>
                      <Badge variant="secondary" className="text-xs">{script.language}</Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      onClick={() => {
                        setEditingScript(script);
                        setShowModal(true);
                      }}
                    >
                      <Edit size={12} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-red-600"
                      onClick={() => handleDelete(script)}
                    >
                      <Trash2 size={12} />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-xs text-muted-foreground line-clamp-4 mb-2">{script.script_text}</p>
                <div className="text-xs text-muted-foreground">
                  <strong>Scope:</strong> {script.account_name || 'Global (All Accounts)'}
                </div>
                {script.products_applicable && script.products_applicable.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {script.products_applicable.slice(0, 3).map(prod => (
                      <Badge key={prod} variant="secondary" className="text-xs">{prod}</Badge>
                    ))}
                    {script.products_applicable.length > 3 && (
                      <Badge variant="secondary" className="text-xs">+{script.products_applicable.length - 3}</Badge>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <ScriptModal
          script={editingScript}
          accounts={accounts}
          authH={authH}
          onClose={() => {
            setShowModal(false);
            setEditingScript(null);
          }}
          onSuccess={() => {
            setShowModal(false);
            setEditingScript(null);
            fetchScripts();
          }}
        />
      )}
    </div>
  );
}

function ScriptModal({ script, accounts, authH, onClose, onSuccess }) {
  const isEdit = !!script;
  const [form, setForm] = useState({
    title: script?.title || '',
    category: script?.category || 'opening',
    account_id: script?.account_id || '',
    script_text: script?.script_text || '',
    language: script?.language || 'indonesia',
    products_applicable: script?.products_applicable || [],
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title || !form.script_text) {
      toast.error('Title dan script text wajib diisi');
      return;
    }

    setSaving(true);
    try {
      const url = isEdit ? `${API}/api/marketing/livehost/scripts/${script.id}` : `${API}/api/marketing/livehost/scripts`;
      const method = isEdit ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { ...authH, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, account_id: form.account_id || null }),
      });

      if (res.ok) {
        toast.success(isEdit ? 'Script berhasil diupdate' : 'Script berhasil dibuat');
        onSuccess();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Gagal menyimpan script');
      }
    } catch (e) {
      toast.error('Gagal menyimpan script');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Script' : 'Add Script'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label className="text-xs font-semibold">Title *</Label>
            <Input
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="mt-1 h-9"
              placeholder="e.g., Opening Script - Fashion Live"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Category</Label>
              <Select value={form.category} onValueChange={v => setForm(f => ({ ...f, category: v }))}>
                <SelectTrigger className="mt-1 h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="opening">Opening</SelectItem>
                  <SelectItem value="demo">Demo/Product</SelectItem>
                  <SelectItem value="promo">Promo</SelectItem>
                  <SelectItem value="closing">Closing</SelectItem>
                  <SelectItem value="faq">FAQ</SelectItem>
                  <SelectItem value="objection_handling">Objection Handling</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold">Language</Label>
              <Select value={form.language} onValueChange={v => setForm(f => ({ ...f, language: v }))}>
                <SelectTrigger className="mt-1 h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="indonesia">Indonesia</SelectItem>
                  <SelectItem value="english">English</SelectItem>
                  <SelectItem value="mandarin">Mandarin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold">Account (Optional)</Label>
            <Select value={form.account_id || 'global'} onValueChange={v => setForm(f => ({ ...f, account_id: v === 'global' ? '' : v }))}>
              <SelectTrigger className="mt-1 h-9">
                <SelectValue placeholder="Global (All Accounts)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="global">Global (All Accounts)</SelectItem>
                {accounts.map(acc => (
                  <SelectItem key={acc.id} value={acc.id}>
                    {acc.account_name} ({acc.platform})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs font-semibold">Script Text *</Label>
            <Textarea
              value={form.script_text}
              onChange={e => setForm(f => ({ ...f, script_text: e.target.value }))}
              className="mt-1 text-sm"
              rows={6}
              placeholder="Tulis script lengkap di sini..."
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Batal
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? (
                <>
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                  Menyimpan...
                </>
              ) : (
                <>
                  <Save size={14} className="mr-1.5" />
                  {isEdit ? 'Update' : 'Simpan'}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// TAB 5: TRAINING MANAGEMENT
// ══════════════════════════════════════════════════════════════════════════════

function TrainingTab({ authH }) {
  const [trainings, setTrainings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingTraining, setEditingTraining] = useState(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedTraining, setSelectedTraining] = useState(null);

  const fetchTrainings = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/marketing/livehost/training`, { headers: authH });
      if (res.ok) {
        const data = await res.json();
        setTrainings(data);
      }
    } catch (e) {
      toast.error('Gagal memuat training');
    } finally {
      setLoading(false);
    }
  }, [authH]);

  useEffect(() => {
    fetchTrainings();
  }, [fetchTrainings]);

  const handleDelete = async (training) => {
    if (!window.confirm(`Yakin ingin menghapus training "${training.title}"?`)) return;
    try {
      const res = await fetch(`${API}/api/marketing/livehost/training/${training.id}`, {
        method: 'DELETE',
        headers: authH,
      });
      if (res.ok) {
        toast.success('Training berhasil dihapus');
        fetchTrainings();
      }
    } catch (e) {
      toast.error('Gagal menghapus training');
    }
  };

  return (
    <div className="space-y-4">
      {/* Actions */}
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={fetchTrainings} className="h-9">
          <RefreshCw size={14} className="mr-1.5" />
          Refresh
        </Button>
        <Button
          size="sm"
          onClick={() => {
            setEditingTraining(null);
            setShowModal(true);
          }}
          className="h-9"
        >
          <Plus size={14} className="mr-1.5" />
          Add Training
        </Button>
      </div>

      {/* Training Grid */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 size={28} className="animate-spin text-muted-foreground" />
        </div>
      ) : trainings.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 gap-3">
            <TrendingUp size={40} className="text-muted-foreground opacity-40" />
            <p className="font-medium">Belum ada training</p>
            <Button size="sm" onClick={() => setShowModal(true)}>
              <Plus size={14} className="mr-1.5" />
              Add Training
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {trainings.map(training => (
            <Card key={training.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-semibold line-clamp-2">{training.title}</CardTitle>
                    <div className="flex items-center gap-2 mt-1.5">
                      <Badge variant="outline" className="text-xs capitalize">{training.category.replace('_', ' ')}</Badge>
                      {training.is_required && (
                        <Badge variant="destructive" className="text-xs">Required</Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      onClick={() => {
                        setEditingTraining(training);
                        setShowModal(true);
                      }}
                    >
                      <Edit size={12} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-red-600"
                      onClick={() => handleDelete(training)}
                    >
                      <Trash2 size={12} />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0 space-y-2">
                <p className="text-xs text-muted-foreground line-clamp-3">{training.description}</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">Type:</span>{' '}
                    <span className="font-medium capitalize">{training.content_type}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Duration:</span>{' '}
                    <span className="font-medium">{training.duration_minutes} min</span>
                  </div>
                  {training.passing_score && (
                    <div>
                      <span className="text-muted-foreground">Pass Score:</span>{' '}
                      <span className="font-medium">{training.passing_score}%</span>
                    </div>
                  )}
                  {training.expiry_months && (
                    <div>
                      <span className="text-muted-foreground">Expiry:</span>{' '}
                      <span className="font-medium">{training.expiry_months} months</span>
                    </div>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full h-8 mt-2"
                  onClick={() => {
                    setSelectedTraining(training);
                    setShowAssignModal(true);
                  }}
                >
                  <UserCheck size={12} className="mr-1.5" />
                  Assign to Hosts
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Modals */}
      {showModal && (
        <TrainingModal
          training={editingTraining}
          authH={authH}
          onClose={() => {
            setShowModal(false);
            setEditingTraining(null);
          }}
          onSuccess={() => {
            setShowModal(false);
            setEditingTraining(null);
            fetchTrainings();
          }}
        />
      )}

      {showAssignModal && selectedTraining && (
        <AssignTrainingModal
          training={selectedTraining}
          authH={authH}
          onClose={() => {
            setShowAssignModal(false);
            setSelectedTraining(null);
          }}
          onSuccess={() => {
            setShowAssignModal(false);
            setSelectedTraining(null);
            toast.success('Training berhasil di-assign');
          }}
        />
      )}
    </div>
  );
}

function TrainingModal({ training, authH, onClose, onSuccess }) {
  const isEdit = !!training;
  const [form, setForm] = useState({
    title: training?.title || '',
    category: training?.category || 'product_knowledge',
    description: training?.description || '',
    content_type: training?.content_type || 'video',
    duration_minutes: training?.duration_minutes || 0,
    is_required: training?.is_required ?? true,
    expiry_months: training?.expiry_months || null,
    passing_score: training?.passing_score || null,
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title || !form.description) {
      toast.error('Title dan description wajib diisi');
      return;
    }

    setSaving(true);
    try {
      const url = isEdit ? `${API}/api/marketing/livehost/training/${training.id}` : `${API}/api/marketing/livehost/training`;
      const method = isEdit ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { ...authH, 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        toast.success(isEdit ? 'Training berhasil diupdate' : 'Training berhasil dibuat');
        onSuccess();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Gagal menyimpan training');
      }
    } catch (e) {
      toast.error('Gagal menyimpan training');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Training' : 'Add Training'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label className="text-xs font-semibold">Title *</Label>
            <Input
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="mt-1 h-9"
              placeholder="e.g., Product Knowledge 101"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold">Category</Label>
            <Select value={form.category} onValueChange={v => setForm(f => ({ ...f, category: v }))}>
              <SelectTrigger className="mt-1 h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="product_knowledge">Product Knowledge</SelectItem>
                <SelectItem value="platform_rules">Platform Rules</SelectItem>
                <SelectItem value="engagement">Engagement Techniques</SelectItem>
                <SelectItem value="sales_techniques">Sales Techniques</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs font-semibold">Description *</Label>
            <Textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="mt-1 text-sm"
              rows={3}
              placeholder="Deskripsi training..."
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Content Type</Label>
              <Select value={form.content_type} onValueChange={v => setForm(f => ({ ...f, content_type: v }))}>
                <SelectTrigger className="mt-1 h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="video">Video</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="quiz">Quiz</SelectItem>
                  <SelectItem value="external_link">External Link</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-semibold">Duration (minutes)</Label>
              <Input
                type="number"
                min="0"
                value={form.duration_minutes}
                onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))}
                className="mt-1 h-9"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold">Passing Score (%) - Optional</Label>
              <Input
                type="number"
                min="0"
                max="100"
                value={form.passing_score || ''}
                onChange={e => setForm(f => ({ ...f, passing_score: e.target.value ? Number(e.target.value) : null }))}
                className="mt-1 h-9"
                placeholder="For quiz only"
              />
            </div>
            <div>
              <Label className="text-xs font-semibold">Expiry (months) - Optional</Label>
              <Input
                type="number"
                min="0"
                value={form.expiry_months || ''}
                onChange={e => setForm(f => ({ ...f, expiry_months: e.target.value ? Number(e.target.value) : null }))}
                className="mt-1 h-9"
                placeholder="Re-certification"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.is_required}
              onChange={e => setForm(f => ({ ...f, is_required: e.target.checked }))}
              className="rounded"
            />
            <Label className="text-xs font-medium cursor-pointer">Required Training</Label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Batal
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? (
                <>
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                  Menyimpan...
                </>
              ) : (
                <>
                  <Save size={14} className="mr-1.5" />
                  {isEdit ? 'Update' : 'Simpan'}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function AssignTrainingModal({ training, authH, onClose, onSuccess }) {
  const [hosts, setHosts] = useState([]);
  const [selectedHostIds, setSelectedHostIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchHosts = async () => {
      try {
        const res = await fetch(`${API}/api/marketing/livehost?status=active`, { headers: authH });
        if (res.ok) {
          const data = await res.json();
          setHosts(data);
        }
      } catch (e) {
        toast.error('Gagal memuat LiveHost');
      } finally {
        setLoading(false);
      }
    };
    fetchHosts();
  }, [authH]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (selectedHostIds.length === 0) {
      toast.error('Pilih minimal 1 LiveHost');
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API}/api/marketing/livehost/training/assign`, {
        method: 'POST',
        headers: { ...authH, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          training_id: training.id,
          host_ids: selectedHostIds,
        }),
      });

      if (res.ok) {
        onSuccess();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Gagal assign training');
      }
    } catch (e) {
      toast.error('Gagal assign training');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Assign Training: {training.title}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Pilih LiveHost yang akan di-assign training ini:
          </p>

          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 size={24} className="animate-spin" />
            </div>
          ) : (
            <div className="max-h-64 overflow-y-auto border rounded-lg p-2 space-y-1">
              {hosts.map(host => (
                <label key={host.id} className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedHostIds.includes(host.id)}
                    onChange={e => {
                      if (e.target.checked) {
                        setSelectedHostIds([...selectedHostIds, host.id]);
                      } else {
                        setSelectedHostIds(selectedHostIds.filter(id => id !== host.id));
                      }
                    }}
                    className="rounded"
                  />
                  <span className="text-sm flex-1">{host.name}</span>
                  <EmploymentTypeBadge type={host.employment_type} />
                </label>
              ))}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Batal
            </Button>
            <Button type="submit" disabled={saving || loading}>
              {saving ? (
                <>
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                  Assigning...
                </>
              ) : (
                <>
                  <UserCheck size={14} className="mr-1.5" />
                  Assign ({selectedHostIds.length})
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
