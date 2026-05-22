/**
 * Communication Hub Portal — CV. Dewi Aditya ERP
 * Internal company chat: channels (group) + direct messages, real-time via WebSocket.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import {
  Hash, Lock, Plus, Send, Paperclip, Smile, Search,
  Users, X, MessageSquare, Circle, ChevronDown, ChevronRight,
  Phone, Settings, Wifi, WifiOff, Reply, MoreHorizontal, RefreshCw,
  Pencil, Trash2, Check, MoreVertical, Pin, PinOff, Bell, BellOff,
  Archive, ArchiveRestore, Download,
  // Session 28 — Thread Conversations
  MessageCircle, MessagesSquare, ArrowLeft,
} from 'lucide-react';

import LinkPreviewCard, { parseDeepLinks, renderContentWithLinks } from './collaboration/shared/LinkPreview';

const API = process.env.REACT_APP_BACKEND_URL || '';

function apicall(method, path, token, body) {
  const opts = {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  return fetch(`${API}${path}`, opts).then(r => r.json());
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now - d) / 86400000);
  if (diffDays === 0) return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  if (diffDays === 1) return 'Kemarin';
  return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' });
}

function initials(name) {
  if (!name) return '?';
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

function avatarColor(id) {
  const colors = [
    'bg-violet-500','bg-blue-500','bg-emerald-500','bg-amber-500',
    'bg-rose-500','bg-cyan-500','bg-indigo-500','bg-pink-500',
  ];
  let h = 0;
  for (let i = 0; i < (id||'').length; i++) h = (h * 31 + id.charCodeAt(i)) & 0xffff;
  return colors[h % colors.length];
}

// ── CreateChannelDialog ──────────────────────────────────────────────────────
function CreateChannelDialog({ open, onClose, token, onCreated }) {
  const [form, setForm] = useState({ name: '', description: '', type: 'public' });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!form.name.trim()) { toast.error('Nama channel wajib diisi'); return; }
    setLoading(true);
    try {
      const data = await apicall('POST', '/api/comm/channels', token, form);
      if (data.id) { toast.success(`Channel #${data.name} dibuat`); onCreated(data); onClose(); }
      else toast.error(data.detail || 'Gagal membuat channel');
    } catch { toast.error('Gagal membuat channel'); }
    finally { setLoading(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Buat Channel Baru</DialogTitle></DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Nama Channel</label>
            <Input placeholder="e.g. umum, produksi, keuangan" value={form.name}
              onChange={e => setForm(p => ({...p, name: e.target.value}))}
              data-testid="channel-name-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Deskripsi (opsional)</label>
            <Input placeholder="Deskripsi singkat..." value={form.description}
              onChange={e => setForm(p => ({...p, description: e.target.value}))} />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Tipe</label>
            <Select value={form.type} onValueChange={v => setForm(p => ({...p, type: v}))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="public">Publik (semua anggota)</SelectItem>
                <SelectItem value="private">Privat (anggota pilihan)</SelectItem>
                <SelectItem value="department">Departemen</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Batal</Button>
          <Button onClick={submit} disabled={loading} data-testid="create-channel-submit">
            {loading ? 'Membuat...' : 'Buat Channel'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── NewDMDialog ──────────────────────────────────────────────────────────────
function NewDMDialog({ open, onClose, token, currentUserId, onStartDM }) {
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (!open) return;
    apicall('GET', '/api/auth/users?limit=100', token)
      .then(d => setUsers(Array.isArray(d) ? d.filter(u => u.id !== currentUserId) : []))
      .catch(() => {});
  }, [open, token, currentUserId]);

  const filtered = users.filter(u =>
    u.name?.toLowerCase().includes(search.toLowerCase()) ||
    u.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader><DialogTitle>Pesan Langsung</DialogTitle></DialogHeader>
        <Input placeholder="Cari pengguna..." value={search}
          onChange={e => setSearch(e.target.value)} className="mb-2" />
        <ScrollArea className="h-56">
          <div className="space-y-1">
            {filtered.map(u => (
              <button key={u.id}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted/60 text-left transition-colors"
                onClick={() => { onStartDM(u); onClose(); }}>
                <div className={`w-8 h-8 rounded-full ${avatarColor(u.id)} flex items-center justify-center text-xs font-bold text-white shrink-0`}>
                  {initials(u.name)}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{u.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                </div>
              </button>
            ))}
            {filtered.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">Tidak ada pengguna ditemukan</p>}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

// ─── Markdown renderer ────────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return null;
  // Split into lines first to handle list items
  const lines = text.split('\n');
  const elements = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc list-inside my-0.5 space-y-0">
          {listItems.map((item, i) => <li key={i} className="text-sm">{renderInline(item)}</li>)}
        </ul>
      );
      listItems = [];
    }
  };

  const renderInline = (str) => {
    // Process inline markdown: bold, italic, code, strikethrough
    const parts = [];
    const regex = /(\*\*(.+?)\*\*|_(.+?)_|`(.+?)`|~~(.+?)~~)/g;
    let last = 0;
    let m;
    while ((m = regex.exec(str)) !== null) {
      if (m.index > last) parts.push(str.slice(last, m.index));
      if (m[2] !== undefined) parts.push(<strong key={m.index}>{m[2]}</strong>);
      else if (m[3] !== undefined) parts.push(<em key={m.index}>{m[3]}</em>);
      else if (m[4] !== undefined) parts.push(<code key={m.index} className="bg-muted px-1 rounded text-xs font-mono">{m[4]}</code>);
      else if (m[5] !== undefined) parts.push(<del key={m.index}>{m[5]}</del>);
      last = m.index + m[0].length;
    }
    if (last < str.length) parts.push(str.slice(last));
    return parts.length > 0 ? parts : str;
  };

  lines.forEach((line, idx) => {
    const listMatch = line.match(/^[-*]\s+(.*)/);
    if (listMatch) {
      listItems.push(listMatch[1]);
    } else {
      flushList();
      if (line === '') {
        elements.push(<br key={`br-${idx}`} />);
      } else {
        elements.push(<span key={`line-${idx}`} className="block">{renderInline(line)}</span>);
      }
    }
  });
  flushList();
  return <>{elements}</>;
}

const EMOJI_LIST = ['👍','❤️','😂','😮','😢','🔥','✅','👏','🙏','💯'];
function MessageItem({ msg, currentUserId, token, onNavigate, onReact, onReply, onEdit, onDelete, onPin, onUnpin, isAdmin, onLightbox, onOpenThread, isInThread }) {
  const isMine = msg.sender_id === currentUserId;
  const [showReactions, setShowReactions] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(msg.content || '');
  const editable = isMine && (msg.message_type === 'text' || !msg.message_type) && !msg.attachments;
  const deletable = isMine || isAdmin;
  const pinnable = !msg.pinned && onPin;
  const unpinnable = msg.pinned && onUnpin;
  const isSystem = msg.sender_id === 'system' || msg.message_type === 'system_procurement';

  const submitEdit = async () => {
    const trimmed = editText.trim();
    if (!trimmed) { toast.error('Pesan tidak boleh kosong'); return; }
    if (trimmed === (msg.content || '')) { setEditing(false); return; }
    const ok = await onEdit(msg.id, trimmed);
    if (ok) setEditing(false);
  };

  return (
    <div
      className={`group flex gap-3 px-4 py-1.5 hover:bg-muted/30 transition-colors rounded-lg ${
        isMine ? 'flex-row-reverse' : ''
      }`}
      data-testid="message-item"
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full ${avatarColor(msg.sender_id)} flex items-center justify-center text-xs font-bold text-white shrink-0 mt-1`}>
        {isSystem ? 'S' : initials(msg.sender_name)}
      </div>

      {/* Content */}
      <div className={`flex-1 min-w-0 ${isMine ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Header */}
        <div className={`flex items-baseline gap-2 mb-0.5 ${isMine ? 'flex-row-reverse' : ''}`}>
          <span className="text-xs font-semibold">{isMine ? 'Saya' : (isSystem ? 'System' : msg.sender_name)}</span>
          <span className="text-[10px] text-muted-foreground">{formatTime(msg.created_at)}</span>
          {msg.edited && <span className="text-[10px] text-muted-foreground italic">(diedit)</span>}
        </div>

        {/* Reply preview */}
        {msg.reply_to_preview && (
          <div className="text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded mb-1 border-l-2 border-primary/50 max-w-xs truncate">
            {msg.reply_to_preview}
          </div>
        )}

        {/* Bubble */}
        <div className={`relative rounded-2xl px-3 py-2 text-sm max-w-[75%] break-words ${
          isSystem
            ? 'bg-amber-500/10 border border-amber-500/30 text-foreground'
            : isMine
              ? 'bg-[hsl(var(--primary)/0.15)] text-foreground rounded-tr-sm'
              : 'bg-muted/60 text-foreground rounded-tl-sm'
        }`}>
          {editing ? (
            <div className="space-y-2 min-w-[240px]">
              <Textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={3}
                className="text-sm"
                autoFocus
                data-testid="message-edit-input"
              />
              <div className="flex gap-2 justify-end">
                <Button size="sm" variant="ghost" onClick={() => { setEditing(false); setEditText(msg.content || ''); }} data-testid="message-edit-cancel">
                  <X size={14} className="mr-1" /> Batal
                </Button>
                <Button size="sm" onClick={submitEdit} data-testid="message-edit-save">
                  <Check size={14} className="mr-1" /> Simpan
                </Button>
              </div>
            </div>
          ) : msg.attachments && msg.attachments.length > 0 ? (
            <div className="space-y-2">
              {msg.attachments.map((att, idx) => {
                const isImage = att.content_type?.startsWith('image/');
                return (
                  <div key={idx}>
                    {isImage ? (
                      <button
                        className="block text-left"
                        onClick={() => onLightbox({ url: `${API}${att.file_url}`, name: att.file_name })}
                      >
                        <img
                          src={`${API}${att.file_url}`}
                          alt={att.file_name}
                          className="rounded-lg max-w-full max-h-64 object-cover border cursor-zoom-in hover:opacity-90 transition-opacity"
                        />
                        <span className="text-xs text-muted-foreground mt-1 block">{att.file_name}</span>
                      </button>
                    ) : (
                      <a href={`${API}${att.file_url}`} target="_blank" rel="noreferrer"
                        className="flex items-center gap-2 text-primary hover:underline">
                        <Paperclip size={14} />
                        <span className="truncate max-w-[200px]">{att.file_name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({Math.round(att.file_size / 1024)} KB)
                        </span>
                      </a>
                    )}
                  </div>
                );
              })}
              {msg.content && msg.content !== `📎 ${msg.attachments[0].file_name}` && (
                <span className="whitespace-pre-wrap text-sm">{renderMarkdown(msg.content)}</span>
              )}
            </div>
          ) : msg.message_type === 'file' ? (
            <a href={`${API}${msg.file_url}`} target="_blank" rel="noreferrer"
              className="flex items-center gap-2 text-primary hover:underline">
              <Paperclip size={14} />
              <span className="truncate max-w-[200px]">{msg.file_name || 'Lampiran'}</span>
            </a>
          ) : (
            <span className="whitespace-pre-wrap text-sm leading-relaxed">{renderMarkdown(msg.content)}</span>
          )}

          {/* Phase 3.7: Deep Link Preview Cards */}
          {!editing && msg.content && (() => {
            const links = parseDeepLinks(msg.content);
            if (!links.length) return null;
            return (
              <div className="mt-1 space-y-1">
                {links.map((link, idx) => (
                  <LinkPreviewCard
                    key={idx}
                    link={link}
                    onNavigate={onNavigate}
                    token={token}
                  />
                ))}
              </div>
            );
          })()}

          {/* Action toolbar on hover (reactions + reply + more menu) */}
          {!editing && !isSystem && (
            <div className={`absolute -top-8 ${isMine ? 'right-0' : 'left-0'} hidden group-hover:flex bg-card border rounded-full shadow-lg px-2 py-1 gap-1 z-10`}>
              {EMOJI_LIST.slice(0, 5).map(e => (
                <button key={e} className="text-base hover:scale-125 transition-transform"
                  onClick={() => onReact(msg.id, e)}>{e}</button>
              ))}
              <button className="text-muted-foreground hover:text-foreground ml-1"
                onClick={() => onReply(msg)} data-testid="message-reply-btn"><Reply size={14} /></button>

              {!isInThread && onOpenThread && (
                <button
                  className="text-muted-foreground hover:text-foreground"
                  onClick={() => onOpenThread(msg)}
                  data-testid="message-thread-btn"
                  title="Buka thread"
                >
                  <MessagesSquare size={14} />
                </button>
              )}

              {(editable || deletable || pinnable || unpinnable) && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      className="text-muted-foreground hover:text-foreground"
                      data-testid="message-more-btn"
                      aria-label="More actions"
                    >
                      <MoreVertical size={14} />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align={isMine ? 'end' : 'start'} className="w-44">
                    {editable && (
                      <DropdownMenuItem
                        onClick={() => { setEditing(true); setEditText(msg.content || ''); }}
                        data-testid="message-edit-action"
                      >
                        <Pencil size={14} className="mr-2" /> Edit pesan
                      </DropdownMenuItem>
                    )}
                    {pinnable && (
                      <DropdownMenuItem onClick={() => onPin(msg.id)} data-testid="message-pin-action">
                        <Pin size={14} className="mr-2" /> Pin pesan
                      </DropdownMenuItem>
                    )}
                    {unpinnable && (
                      <DropdownMenuItem onClick={() => onUnpin(msg.id)} data-testid="message-unpin-action">
                        <PinOff size={14} className="mr-2" /> Unpin pesan
                      </DropdownMenuItem>
                    )}
                    {(editable || pinnable || unpinnable) && deletable && <DropdownMenuSeparator />}
                    {deletable && (
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => onDelete(msg)}
                        data-testid="message-delete-action"
                      >
                        <Trash2 size={14} className="mr-2" /> Hapus pesan
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          )}
        </div>

        {/* Reactions */}
        {msg.reactions && Object.keys(msg.reactions).length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {Object.entries(msg.reactions).map(([emoji, users]) => (
              <button key={emoji}
                className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                  users.includes(currentUserId)
                    ? 'bg-primary/15 border-primary/40 text-primary'
                    : 'bg-muted/50 border-border hover:bg-muted'
                }`}
                onClick={() => onReact(msg.id, emoji)}>
                {emoji} {users.length}
              </button>
            ))}
          </div>
        )}

        {/* Thread reply count badge (Session 28) */}
        {!isInThread && (msg.thread_reply_count || 0) > 0 && onOpenThread && (
          <button
            onClick={() => onOpenThread(msg)}
            data-testid={`message-thread-badge-${msg.id}`}
            className="mt-1.5 inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/10 transition-colors group/thread"
          >
            <MessagesSquare size={12} />
            <span className="font-semibold">{msg.thread_reply_count}</span>
            <span className="text-foreground/60">
              {msg.thread_reply_count === 1 ? 'balasan' : 'balasan'}
            </span>
            {msg.thread_last_reply_by && (
              <span className="text-muted-foreground hidden sm:inline">
                · Terakhir oleh {msg.thread_last_reply_by}
              </span>
            )}
            <ChevronRight size={11} className="text-muted-foreground group-hover/thread:translate-x-0.5 transition-transform" />
          </button>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// THREAD PANEL (Session 28) — Slack-style nested reply drawer
// ═══════════════════════════════════════════════════════════════════════════════
function ThreadPanel({
  token, rootMessage, currentUserId, isAdmin,
  onClose, onReact, onEdit, onDelete, onPin, onUnpin, onLightbox,
  onThreadReplyAdded, onRootCountUpdated,
}) {
  const [thread, setThread] = useState(null);
  const [loading, setLoading] = useState(true);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const endRef = useRef(null);

  const loadThread = useCallback(async () => {
    if (!rootMessage?.id) return;
    setLoading(true);
    try {
      const data = await apicall('GET', `/api/comm/messages/${rootMessage.id}/thread`, token);
      setThread(data);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'auto' }), 50);
    } catch (e) {
      toast.error('Gagal memuat thread');
    } finally {
      setLoading(false);
    }
  }, [rootMessage?.id, token]);

  useEffect(() => { loadThread(); }, [loadThread]);

  // External handler called from main component on WS thread_reply for this root
  useEffect(() => {
    if (!rootMessage) return;
    const handler = (ev) => {
      if (ev.detail?.root_id !== rootMessage.id) return;
      const reply = ev.detail?.reply;
      if (!reply) return;
      setThread(prev => {
        if (!prev) return prev;
        if (prev.replies.find(r => r.id === reply.id)) return prev;
        return { ...prev, replies: [...prev.replies, reply], reply_count: (prev.reply_count || 0) + 1 };
      });
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 30);
    };
    window.addEventListener('thread:newReply', handler);
    return () => window.removeEventListener('thread:newReply', handler);
  }, [rootMessage]);

  const submit = async () => {
    const text = inputText.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      const r = await apicall('POST', `/api/comm/messages/${rootMessage.id}/thread/reply`, token, {
        content: text,
      });
      if (r?.id) {
        setThread(prev => prev ? {
          ...prev,
          replies: prev.replies.find(x => x.id === r.id) ? prev.replies : [...prev.replies, r],
          reply_count: (prev.reply_count || 0) + 1,
        } : prev);
        setInputText('');
        onThreadReplyAdded?.(r);
        onRootCountUpdated?.(rootMessage.id, (thread?.reply_count || 0) + 1, r.sender_name);
        setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 30);
      }
    } catch (e) {
      toast.error('Gagal kirim reply');
    } finally {
      setSending(false);
    }
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  if (!rootMessage) return null;

  return (
    <div
      data-testid="thread-panel"
      className="fixed inset-y-0 right-0 z-40 w-full sm:w-[420px] bg-card border-l shadow-2xl flex flex-col"
      role="complementary"
      aria-label="Thread panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={onClose}
            data-testid="thread-panel-close"
            className="p-1.5 -ml-1.5 rounded hover:bg-muted text-muted-foreground"
            aria-label="Tutup thread"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h3 className="text-sm font-semibold flex items-center gap-1.5">
              <MessagesSquare size={14} className="text-primary" /> Thread
            </h3>
            <p className="text-[11px] text-muted-foreground">
              {thread?.reply_count || 0} balasan
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded hover:bg-muted text-muted-foreground sm:hidden"
          aria-label="Tutup"
        >
          <X size={16} />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto py-3" data-testid="thread-panel-body">
        {loading && (
          <div className="text-center py-8 text-sm text-muted-foreground" data-testid="thread-loading">
            Memuat thread...
          </div>
        )}
        {!loading && thread && (
          <>
            {/* Root message */}
            <div className="border-b pb-3 mb-2">
              <MessageItem
                msg={thread.root}
                currentUserId={currentUserId}
                token={token}
                onReact={onReact}
                onReply={() => {}}
                onEdit={onEdit}
                onDelete={onDelete}
                onPin={onPin}
                onUnpin={onUnpin}
                isAdmin={isAdmin}
                onLightbox={onLightbox}
                onOpenThread={null}
                isInThread={true}
              />
            </div>
            {/* Divider with count */}
            <div className="flex items-center gap-2 px-4 mb-1 text-[11px] text-muted-foreground">
              <span className="font-medium">{thread.reply_count} balasan</span>
              <div className="flex-1 h-px bg-border" />
            </div>
            {/* Replies */}
            {thread.replies.map(r => (
              <MessageItem
                key={r.id}
                msg={r}
                currentUserId={currentUserId}
                token={token}
                onReact={onReact}
                onReply={() => {}}
                onEdit={onEdit}
                onDelete={onDelete}
                onPin={null}
                onUnpin={null}
                isAdmin={isAdmin}
                onLightbox={onLightbox}
                onOpenThread={null}
                isInThread={true}
              />
            ))}
            {thread.replies.length === 0 && (
              <div className="text-center py-6 text-sm text-muted-foreground" data-testid="thread-empty-replies">
                Belum ada balasan. Mulai diskusi di bawah.
              </div>
            )}
            <div ref={endRef} />
          </>
        )}
      </div>

      {/* Reply input */}
      <div className="border-t px-3 py-2 shrink-0">
        <div className="flex items-end gap-2">
          <Textarea
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={onKey}
            placeholder="Balas di thread..."
            data-testid="thread-input"
            rows={1}
            className="resize-none min-h-9 max-h-32 text-sm"
            disabled={sending}
          />
          <Button
            onClick={submit}
            disabled={sending || !inputText.trim()}
            data-testid="thread-send-button"
            size="sm"
            className="h-9 shrink-0"
          >
            <Send size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
}



// ── Main Component ───────────────────────────────────────────────────────────
export default function CommunicationHubPortal({ token, user, isEmbedded = false, initialChannelId = null }) {
  const [channels, setChannels] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeView, setActiveView] = useState(null); // {type: 'channel'|'dm', id, name, otherUserId?}
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState(new Set());
  const [unreadCounts, setUnreadCounts] = useState({ channels: {}, dms: {} });
  const [typingUsers, setTypingUsers] = useState({});
  const [showCreateChannel, setShowCreateChannel] = useState(false);
  const [showNewDM, setShowNewDM] = useState(false);
  const [replyTo, setReplyTo] = useState(null);
  // Session 28 — Thread Conversations
  const [threadRoot, setThreadRoot] = useState(null); // currently open thread root msg
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [channelsExpanded, setChannelsExpanded] = useState(true);
  const [dmsExpanded, setDmsExpanded] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);

  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const typingTimerRef = useRef({});
  const cancelledRef = useRef(false);
  const fileInputRef = useRef(null);

  const [uploadingFile, setUploadingFile] = useState(false);
  const [mentionState, setMentionState] = useState({ active: false, query: '', start: 0 });
  const [channelMembers, setChannelMembers] = useState([]);
  const mentionRef = useRef(null);

  // Pinned messages
  const [pinnedMessages, setPinnedMessages] = useState([]);
  const [showPinned, setShowPinned] = useState(false);

  // Image Lightbox
  const [lightboxImg, setLightboxImg] = useState(null); // { url, name }

  // Archived channels
  const [archivedChannels, setArchivedChannels] = useState([]);
  const [showArchived, setShowArchived] = useState(false);

  // Browser notification permission
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const currentUserId = user?.id || '';
  const isAdmin = ['admin','superadmin'].includes(user?.role);

  // Load channel members when active channel changes (for @mention)
  useEffect(() => {
    if (activeView?.type === 'channel') {
      apicall('GET', `/api/comm/channels/${activeView.id}/members`, token)
        .then(data => { if (data?.members) setChannelMembers(data.members); })
        .catch(() => {});
      // Load pinned messages
      apicall('GET', `/api/comm/channels/${activeView.id}/pinned`, token)
        .then(data => { if (Array.isArray(data)) setPinnedMessages(data); })
        .catch(() => {});
    } else {
      setPinnedMessages([]);
      setShowPinned(false);
    }
  }, [activeView, token]);

  // ── Load initial data ───────────────────────────────────────────────────────
  const loadChannels = useCallback(async () => {
    try {
      const data = await apicall('GET', '/api/comm/channels', token);
      if (Array.isArray(data)) setChannels(data);
    } catch {}
  }, [token]);

  const loadArchivedChannels = useCallback(async () => {
    try {
      const data = await apicall('GET', '/api/comm/channels?include_archived=true', token);
      if (Array.isArray(data)) setArchivedChannels(data);
    } catch {}
  }, [token]);

  const loadConversations = useCallback(async () => {
    try {
      const data = await apicall('GET', '/api/comm/conversations', token);
      if (Array.isArray(data)) setConversations(data);
    } catch {}
  }, [token]);

  useEffect(() => {
    loadChannels();
    loadConversations();
  }, [loadChannels, loadConversations]);

  // Auto-select initial channel when embedded (for Study Groups)
  useEffect(() => {
    if (isEmbedded && initialChannelId && channels.length > 0) {
      const channel = channels.find(ch => ch.id === initialChannelId);
      if (channel && !activeView) {
        setActiveView({ type: 'channel', id: channel.id, name: channel.name, description: channel.description });
      }
    }
  }, [isEmbedded, initialChannelId, channels, activeView]);

  // ── WebSocket ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    cancelledRef.current = false;

    const connect = () => {
      if (cancelledRef.current) return;
      const base = (process.env.REACT_APP_BACKEND_URL || '')
        .replace(/^https:/i, 'wss:').replace(/^http:/i, 'ws:');
      const url = `${base}/api/comm/ws?token=${encodeURIComponent(token)}`;
      let ws;
      try { ws = new WebSocket(url); } catch { return; }
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelledRef.current) { ws.close(); return; }
        setWsConnected(true);
      };

      ws.onmessage = (e) => {
        try {
          const payload = JSON.parse(e.data);
          if (payload.type === 'new_message') {
            const { message, channel_id, conv_id, scope } = payload.data;
            // Browser / in-app notification for messages not from self
            if (message.sender_id !== currentUserId) {
              const isActiveChannel =
                activeView?.type === 'channel' && activeView?.id === channel_id ||
                activeView?.type === 'dm' && conv_id;
              const title = message.sender_name || 'Pesan baru';
              const body  = message.content?.slice(0, 80) || '📎 Lampiran';
              if (document.hidden) {
                // Browser notification (tab tidak aktif)
                if ('Notification' in window && Notification.permission === 'granted') {
                  try { new Notification(title, { body, icon: '/logo192.png', tag: message.id }); } catch {}
                }
              } else if (!isActiveChannel) {
                // In-app toast (tab aktif tapi channel lain)
                toast(`💬 ${title}`, { description: body, duration: 4000 });
              }
            }
            // If active view matches, append message
            setActiveView(av => {
              if (av) {
                const match =
                  (av.type === 'channel' && channel_id && av.id === channel_id) ||
                  (av.type === 'dm' && conv_id);
                if (match) {
                  setMessages(prev => {
                    if (prev.find(m => m.id === message.id)) return prev;
                    return [...prev, message];
                  });
                  setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
                  // Mark as read
                  const refId = av.type === 'channel' ? channel_id : conv_id;
                  apicall('POST', `/api/comm/read/${refId}`, token).catch(() => {});
                }
              }
              return av;
            });
            // Update unread counts
            if (scope === 'channel') {
              loadChannels();
            } else {
              loadConversations();
            }
          } else if (payload.type === 'reaction_update') {
            const { msg_id, reactions } = payload.data;
            setMessages(prev => prev.map(m => m.id === msg_id ? { ...m, reactions } : m));
          } else if (payload.type === 'message_edited') {
            const { msg_id, message } = payload.data;
            setMessages(prev => prev.map(m => m.id === msg_id ? { ...m, ...(message || {}) } : m));
          } else if (payload.type === 'message_deleted') {
            const { msg_id } = payload.data;
            setMessages(prev => prev.filter(m => m.id !== msg_id));
            setPinnedMessages(prev => prev.filter(m => m.id !== msg_id));
          } else if (payload.type === 'message_pinned') {
            const { msg_id } = payload.data;
            // Reload pinned list when a message is pinned
            setActiveView(av => {
              if (av?.type === 'channel') {
                apicall('GET', `/api/comm/channels/${av.id}/pinned`, token)
                  .then(data => { if (Array.isArray(data)) setPinnedMessages(data); })
                  .catch(() => {});
                // Update messages list: mark as pinned
                setMessages(prev => prev.map(m => m.id === msg_id ? { ...m, pinned: true } : m));
              }
              return av;
            });
            toast('📌 Pesan di-pin', { duration: 2000 });
          } else if (payload.type === 'message_unpinned') {
            const { msg_id } = payload.data;
            setPinnedMessages(prev => prev.filter(m => m.id !== msg_id));
            setMessages(prev => prev.map(m => m.id === msg_id ? { ...m, pinned: false } : m));
            toast('Pesan di-unpin', { duration: 2000 });
          } else if (payload.type === 'thread_reply') {
            // Session 28 — incoming thread reply broadcast
            const { reply, root_id, reply_count } = payload.data || {};
            if (!reply || !root_id) return;
            // 1. Update root message reply_count in main feed
            setMessages(prev => prev.map(m => m.id === root_id ? {
              ...m,
              thread_reply_count: reply_count ?? ((m.thread_reply_count || 0) + 1),
              thread_last_reply_at: reply.created_at,
              thread_last_reply_by: reply.sender_name,
            } : m));
            // 2. Dispatch to open thread panel (if any)
            window.dispatchEvent(new CustomEvent('thread:newReply', {
              detail: { root_id, reply, reply_count }
            }));
          } else if (payload.type === 'presence') {
            const { user_id, online } = payload.data;
            setOnlineUsers(prev => {
              const next = new Set(prev);
              if (online) next.add(user_id); else next.delete(user_id);
              return next;
            });
            setConversations(prev => prev.map(c =>
              c.other_user?.id === user_id ? { ...c, is_online: online } : c
            ));
          } else if (payload.type === 'typing') {
            const { user_id, user_name, channel_id: cid } = payload.data;
            const key = cid || 'dm';
            setTypingUsers(prev => ({ ...prev, [key]: { user_id, user_name, ts: Date.now() } }));
            clearTimeout(typingTimerRef.current[key]);
            typingTimerRef.current[key] = setTimeout(() => {
              setTypingUsers(prev => { const n = {...prev}; delete n[key]; return n; });
            }, 3000);
          } else if (payload.type === 'channel_added') {
            loadChannels();
          }
        } catch {}
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (!cancelledRef.current) {
          reconnectRef.current = setTimeout(connect, 3000);
        }
      };
      ws.onerror = () => setWsConnected(false);
    };

    connect();
    return () => {
      cancelledRef.current = true;
      clearTimeout(reconnectRef.current);
      try { wsRef.current?.close(); } catch {}
    };
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Load messages on view change ────────────────────────────────────────────
  useEffect(() => {
    if (!activeView) return;
    setLoadingMsgs(true);
    setMessages([]);
    const path = activeView.type === 'channel'
      ? `/api/comm/channels/${activeView.id}/messages?limit=50`
      : `/api/comm/conversations/${activeView.otherUserId}/messages?limit=50`;
    apicall('GET', path, token)
      .then(data => {
        if (Array.isArray(data)) setMessages(data);
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'instant' }), 50);
      })
      .catch(() => {})
      .finally(() => setLoadingMsgs(false));
    // Mark as read
    apicall('POST', `/api/comm/read/${activeView.id}`, token).catch(() => {});
  }, [activeView?.id, activeView?.type]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── File upload ────────────────────────────────────────────────────────────
  const handleFileUpload = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file || !activeView) return;
    
    // Validate
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Ukuran file maksimal 10 MB');
      return;
    }
    
    if (activeView.type !== 'channel') {
      toast.error('File attachment hanya support untuk channel saat ini');
      return;
    }
    
    setUploadingFile(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`${API}/api/comm/channels/${activeView.id}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });
      
      if (!res.ok) throw new Error('Upload gagal');
      
      const uploadData = await res.json();
      
      // Send message dengan attachment
      const body = {
        content: `📎 ${uploadData.file_name}`,
        attachments: [{
          file_url: uploadData.file_url,
          file_name: uploadData.file_name,
          file_size: uploadData.file_size,
          content_type: uploadData.content_type,
        }],
      };
      
      const msg = await apicall('POST', `/api/comm/channels/${activeView.id}/messages`, token, body);
      if (msg.id) {
        setMessages(prev => prev.find(m => m.id === msg.id) ? prev : [...prev, msg]);
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
        toast.success(`File ${uploadData.file_name} berhasil dikirim`);
      }
    } catch (err) {
      toast.error('Gagal upload file');
    } finally {
      setUploadingFile(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, [activeView, token]);

  // ── Send message ────────────────────────────────────────────────────────────
  const sendMessage = useCallback(async () => {
    const content = inputText.trim();
    if (!content || !activeView) return;
    setInputText('');
    setReplyTo(null);
    const body = {
      content,
      reply_to_id: replyTo?.id || null,
      reply_to_preview: replyTo ? `${replyTo.sender_name}: ${replyTo.content?.slice(0, 80)}` : null,
    };
    const path = activeView.type === 'channel'
      ? `/api/comm/channels/${activeView.id}/messages`
      : `/api/comm/conversations/${activeView.otherUserId}/messages`;
    try {
      const msg = await apicall('POST', path, token, body);
      if (msg.id) {
        setMessages(prev => prev.find(m => m.id === msg.id) ? prev : [...prev, msg]);
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
      }
    } catch { toast.error('Gagal mengirim pesan'); }
  }, [inputText, activeView, token, replyTo]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    // Typing indicator
    if (activeView?.type === 'channel' && wsRef.current?.readyState === WebSocket.OPEN) {
      try { wsRef.current.send(JSON.stringify({ type: 'typing', channel_id: activeView.id })); } catch {}
    }
  };

  // ── Reactions ────────────────────────────────────────────────────────────────
  const handleReact = useCallback(async (msgId, emoji) => {
    try {
      const data = await apicall('POST', `/api/comm/messages/${msgId}/reaction`, token, { emoji });
      if (data.reactions !== undefined) {
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, reactions: data.reactions } : m));
      }
    } catch {}
  }, [token]);

  // ── Edit / Delete message ──────────────────────────────────────────────────
  const handleEditMessage = useCallback(async (msgId, newContent) => {
    try {
      const data = await apicall('PATCH', `/api/comm/messages/${msgId}`, token, { content: newContent });
      if (data?.id) {
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, ...data } : m));
        toast.success('Pesan diperbarui');
        return true;
      }
      toast.error(data?.detail || 'Gagal mengedit pesan');
      return false;
    } catch {
      toast.error('Gagal mengedit pesan');
      return false;
    }
  }, [token]);

  const handleDeleteMessage = useCallback(async (msg) => {
    if (!window.confirm('Hapus pesan ini secara permanen?')) return;
    try {
      const data = await apicall('DELETE', `/api/comm/messages/${msg.id}`, token);
      if (data?.ok) {
        setMessages(prev => prev.filter(m => m.id !== msg.id));
        setPinnedMessages(prev => prev.filter(m => m.id !== msg.id));
        toast.success('Pesan dihapus');
      } else {
        toast.error(data?.detail || 'Gagal menghapus pesan');
      }
    } catch {
      toast.error('Gagal menghapus pesan');
    }
  }, [token]);

  const handlePinMessage = useCallback(async (msgId) => {
    try {
      const data = await apicall('POST', `/api/comm/messages/${msgId}/pin`, token);
      if (data?.ok) {
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, pinned: true } : m));
        // Reload pinned list
        if (activeView?.type === 'channel') {
          apicall('GET', `/api/comm/channels/${activeView.id}/pinned`, token)
            .then(d => { if (Array.isArray(d)) setPinnedMessages(d); })
            .catch(() => {});
        }
        toast.success('📌 Pesan di-pin');
      } else {
        toast.error(data?.detail || 'Gagal pin pesan');
      }
    } catch { toast.error('Gagal pin pesan'); }
  }, [token, activeView]);

  const handleUnpinMessage = useCallback(async (msgId) => {
    try {
      const data = await apicall('DELETE', `/api/comm/messages/${msgId}/pin`, token);
      if (data?.ok) {
        setPinnedMessages(prev => prev.filter(m => m.id !== msgId));
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, pinned: false } : m));
        toast.success('Pesan di-unpin');
      } else {
        toast.error(data?.detail || 'Gagal unpin pesan');
      }
    } catch { toast.error('Gagal unpin pesan'); }
  }, [token]);

  const handleArchiveChannel = useCallback(async (channelId) => {
    if (!window.confirm('Arsipkan channel ini? Channel tidak akan muncul di daftar utama.')) return;
    try {
      const data = await apicall('PATCH', `/api/comm/channels/${channelId}/archive`, token);
      if (data?.ok) {
        setChannels(prev => prev.filter(c => c.id !== channelId));
        if (activeView?.id === channelId) setActiveView(null);
        loadArchivedChannels();
        toast.success('Channel diarsipkan');
      }
    } catch { toast.error('Gagal arsipkan channel'); }
  }, [token, activeView, loadArchivedChannels]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleUnarchiveChannel = useCallback(async (channelId) => {
    try {
      const data = await apicall('PATCH', `/api/comm/channels/${channelId}/unarchive`, token);
      if (data?.ok) {
        setArchivedChannels(prev => prev.filter(c => c.id !== channelId));
        loadChannels();
        toast.success('Channel dipulihkan dari arsip');
      }
    } catch { toast.error('Gagal unarchive channel'); }
  }, [token, loadChannels]);

  // ─── Formatting helpers (Rich Text Toolbar) ─────────────────────────────────
  const applyFormat = useCallback((type) => {
    const el = inputRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end   = el.selectionEnd;
    const sel   = inputText.slice(start, end);
    let newText  = inputText;
    let newCursor = end;
    if (type === 'bold') {
      const wrapped = `**${sel || 'teks'}**`;
      newText = inputText.slice(0, start) + wrapped + inputText.slice(end);
      newCursor = start + (sel ? wrapped.length : 2);
    } else if (type === 'italic') {
      const wrapped = `_${sel || 'teks'}_`;
      newText = inputText.slice(0, start) + wrapped + inputText.slice(end);
      newCursor = start + (sel ? wrapped.length : 1);
    } else if (type === 'code') {
      const wrapped = `\`${sel || 'kode'}\``;
      newText = inputText.slice(0, start) + wrapped + inputText.slice(end);
      newCursor = start + (sel ? wrapped.length : 1);
    } else if (type === 'list') {
      const prefix = (inputText.endsWith('\n') || inputText === '') ? '- ' : '\n- ';
      newText = inputText.slice(0, end) + prefix + inputText.slice(end);
      newCursor = end + prefix.length;
    } else if (type === 'strike') {
      const wrapped = `~~${sel || 'teks'}~~`;
      newText = inputText.slice(0, start) + wrapped + inputText.slice(end);
      newCursor = start + (sel ? wrapped.length : 2);
    }
    setInputText(newText);
    requestAnimationFrame(() => { el.focus(); el.setSelectionRange(newCursor, newCursor); });
  }, [inputText]);
  const selectChannel = useCallback((ch) => {
    setActiveView({ type: 'channel', id: ch.id, name: ch.name, description: ch.description });
  }, []);

  const selectDM = useCallback((conv) => {
    const other = conv.other_user;
    setActiveView({ type: 'dm', id: conv.id, name: other?.name || 'DM', otherUserId: other?.id });
  }, []);

  const startDM = useCallback((otherUser) => {
    const existing = conversations.find(c => c.other_user?.id === otherUser.id);
    if (existing) { selectDM(existing); return; }
    // Open new DM immediately
    setActiveView({ type: 'dm', id: `new-${otherUser.id}`, name: otherUser.name, otherUserId: otherUser.id });
    // Load conversation messages (will create conv automatically)
    setLoadingMsgs(true);
    apicall('GET', `/api/comm/conversations/${otherUser.id}/messages?limit=50`, token)
      .then(data => {
        if (Array.isArray(data)) setMessages(data);
        loadConversations();
      })
      .catch(() => {})
      .finally(() => setLoadingMsgs(false));
  }, [conversations, token, selectDM, loadConversations]);

  const typingKey = activeView?.type === 'channel' ? activeView?.id : 'dm';
  const typingUser = typingUsers[typingKey];

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className={`flex ${isEmbedded ? 'h-full' : 'h-[calc(100vh-130px)]'} bg-[hsl(var(--background))] rounded-xl border overflow-hidden`} data-testid="comm-hub-portal">

      {/* Sidebar - Hidden when embedded */}
      {!sidebarCollapsed && !isEmbedded && (
        <aside className="w-72 border-r bg-[hsl(var(--card))] flex flex-col shrink-0">
          {/* Sidebar header */}
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare size={16} className="text-primary" />
              <span className="font-semibold text-sm">Communication Hub</span>
            </div>
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-red-500'}`}
                title={wsConnected ? 'Terhubung' : 'Terputus'} />
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-6 w-6"
                    onClick={() => { loadChannels(); loadConversations(); }}>
                    <RefreshCw size={12} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Perbarui</TooltipContent>
              </Tooltip>
            </div>
          </div>

          <ScrollArea className="flex-1">
            {/* Channels section */}
            <div className="px-2 py-2">
              <button className="flex items-center gap-1 w-full px-2 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
                onClick={() => setChannelsExpanded(p => !p)}>
                {channelsExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                Channels
                <span className="ml-auto"><Badge variant="secondary" className="text-[10px] px-1.5 h-4">{channels.length}</Badge></span>
              </button>
              {channelsExpanded && (
                <div className="mt-1 space-y-0.5">
                  {channels.map(ch => {
                    const unread = ch.unread_count || 0;
                    const active = activeView?.id === ch.id && activeView?.type === 'channel';
                    const canArchive = isAdmin || ch.created_by === currentUserId;
                    return (
                      <div key={ch.id} className="relative group/ch">
                        <button
                          className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                            active ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted/60 text-foreground'
                          }`}
                          onClick={() => selectChannel(ch)}
                          data-testid={`channel-item-${ch.id}`}>
                          <Hash size={14} className="shrink-0 text-muted-foreground" />
                          <span className="truncate flex-1 text-left">{ch.name}</span>
                          {unread > 0 && (
                            <Badge className="ml-auto text-[10px] px-1.5 h-4 bg-primary text-primary-foreground">{unread}</Badge>
                          )}
                        </button>
                        {canArchive && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <button className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground opacity-0 group-hover/ch:opacity-100 transition-opacity p-0.5 rounded">
                                <MoreHorizontal size={12} />
                              </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-40">
                              <DropdownMenuItem
                                onClick={() => handleArchiveChannel(ch.id)}
                                className="text-amber-600 focus:text-amber-600"
                                data-testid={`archive-channel-${ch.id}`}
                              >
                                <Archive size={12} className="mr-2" /> Arsipkan Channel
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </div>
                    );
                  })}
                  <button
                    className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                    onClick={() => setShowCreateChannel(true)}
                    data-testid="create-channel-btn">
                    <Plus size={14} />
                    <span>Buat Channel</span>
                  </button>

                  {/* Archived Channels */}
                  <button
                    className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                    onClick={() => {
                      setShowArchived(p => !p);
                      if (!showArchived) loadArchivedChannels();
                    }}
                    data-testid="archived-channels-toggle"
                  >
                    {showArchived ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    <Archive size={12} className="text-muted-foreground" />
                    <span>Channel Diarsipkan ({archivedChannels.length})</span>
                  </button>
                  {showArchived && archivedChannels.map(ch => (
                    <div key={ch.id} className="relative group/arch">
                      <button
                        className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-muted-foreground/60 hover:bg-muted/40 transition-colors"
                        onClick={() => selectChannel(ch)}
                      >
                        <Hash size={14} className="shrink-0" />
                        <span className="truncate flex-1 text-left line-through">{ch.name}</span>
                        <Archive size={10} className="shrink-0" />
                      </button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground opacity-0 group-hover/arch:opacity-100 transition-opacity p-0.5 rounded">
                            <MoreHorizontal size={12} />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44">
                          <DropdownMenuItem onClick={() => handleUnarchiveChannel(ch.id)} data-testid={`unarchive-channel-${ch.id}`}>
                            <ArchiveRestore size={12} className="mr-2" /> Pulihkan Channel
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Separator className="mx-2" />

            {/* Direct Messages section */}
            <div className="px-2 py-2">
              <button className="flex items-center gap-1 w-full px-2 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
                onClick={() => setDmsExpanded(p => !p)}>
                {dmsExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                Pesan Langsung
                <span className="ml-auto"><Badge variant="secondary" className="text-[10px] px-1.5 h-4">{conversations.length}</Badge></span>
              </button>
              {dmsExpanded && (
                <div className="mt-1 space-y-0.5">
                  {conversations.map(conv => {
                    const other = conv.other_user || {};
                    const unread = conv.unread_count || 0;
                    const isOnline = conv.is_online || onlineUsers.has(other.id);
                    const active = activeView?.id === conv.id && activeView?.type === 'dm';
                    return (
                      <button key={conv.id}
                        className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                          active ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted/60 text-foreground'
                        }`}
                        onClick={() => selectDM(conv)}
                        data-testid={`dm-item-${conv.id}`}>
                        <div className="relative shrink-0">
                          <div className={`w-6 h-6 rounded-full ${avatarColor(other.id)} flex items-center justify-center text-[10px] font-bold text-white`}>
                            {initials(other.name)}
                          </div>
                          <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-card ${
                            isOnline ? 'bg-emerald-500' : 'bg-muted-foreground/40'
                          }`} />
                        </div>
                        <span className="truncate flex-1 text-left text-sm">{other.name}</span>
                        {unread > 0 && (
                          <Badge className="ml-auto text-[10px] px-1.5 h-4 bg-primary text-primary-foreground">{unread}</Badge>
                        )}
                      </button>
                    );
                  })}
                  <button
                    className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                    onClick={() => setShowNewDM(true)}
                    data-testid="new-dm-btn">
                    <Plus size={14} />
                    <span>Pesan Baru</span>
                  </button>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Current user */}
          <div className="px-3 py-2 border-t flex items-center gap-2">
            <div className="relative">
              <div className={`w-7 h-7 rounded-full ${avatarColor(currentUserId)} flex items-center justify-center text-[10px] font-bold text-white`}>
                {initials(user?.name)}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-card bg-emerald-500" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium truncate">{user?.name}</p>
              <p className="text-[10px] text-muted-foreground">Online</p>
            </div>
          </div>
        </aside>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 bg-[hsl(var(--background))]">
        {activeView ? (
          <>
            {/* Channel/DM header */}
            <div className="px-4 py-3 border-b bg-[hsl(var(--card))] flex items-center gap-3 shrink-0">
              {/* Sidebar toggle - hidden when embedded */}
              {!isEmbedded && (
                <button className="text-muted-foreground hover:text-foreground"
                  onClick={() => setSidebarCollapsed(p => !p)}>
                  {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronDown size={18} />}
                </button>
              )}
              {activeView.type === 'channel' ? (
                <Hash size={16} className="text-muted-foreground" />
              ) : (
                <MessageSquare size={16} className="text-muted-foreground" />
              )}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-sm">{activeView.name}</h3>
                {activeView.description && (
                  <p className="text-xs text-muted-foreground truncate">{activeView.description}</p>
                )}
              </div>
              {/* Pinned messages button (channel only) */}
              {activeView.type === 'channel' && pinnedMessages.length > 0 && (
                <button
                  className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border transition-colors ${showPinned ? 'bg-amber-500/10 border-amber-500/40 text-amber-600' : 'border-border text-muted-foreground hover:border-primary/50 hover:text-foreground'}`}
                  onClick={() => setShowPinned(p => !p)}
                  data-testid="pinned-messages-btn"
                  title="Pesan di-pin"
                >
                  <Pin size={12} />
                  <span>{pinnedMessages.length} pin</span>
                </button>
              )}
              {!wsConnected && (
                <Badge variant="destructive" className="text-[10px] flex items-center gap-1">
                  <WifiOff size={10} /> Terputus
                </Badge>
              )}
            </div>

            {/* Pinned messages panel */}
            {showPinned && pinnedMessages.length > 0 && (
              <div className="border-b bg-amber-500/5 px-4 py-2 space-y-1.5 max-h-40 overflow-y-auto" data-testid="pinned-messages-panel">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-amber-600 flex items-center gap-1.5">
                    <Pin size={12} /> {pinnedMessages.length} Pesan Di-Pin
                  </span>
                  <button onClick={() => setShowPinned(false)} className="text-muted-foreground hover:text-foreground">
                    <X size={14} />
                  </button>
                </div>
                {pinnedMessages.map(pm => (
                  <div key={pm.id} className="flex items-start gap-2 text-xs bg-card rounded-lg px-3 py-2 border">
                    <Pin size={11} className="text-amber-500 shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <span className="font-medium text-foreground">{pm.sender_name}</span>
                      <span className="text-muted-foreground ml-2 truncate block">{pm.content || '📎 Lampiran'}</span>
                    </div>
                    {isAdmin && (
                      <button onClick={() => handleUnpinMessage(pm.id)} className="text-muted-foreground hover:text-destructive shrink-0" title="Unpin">
                        <X size={12} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Messages */}
            <ScrollArea className="flex-1">
              <div className="py-4 space-y-1" data-testid="message-thread">
                {loadingMsgs ? (
                  <div className="flex justify-center py-8">
                    <div className="animate-spin h-6 w-6 rounded-full border-2 border-primary border-t-transparent" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="text-center py-12">
                    <MessageSquare size={32} className="mx-auto text-muted-foreground/40 mb-2" />
                    <p className="text-sm text-muted-foreground">Belum ada pesan. Mulai percakapan!</p>
                  </div>
                ) : (
                  messages.map(msg => (
                    <MessageItem
                      key={msg.id}
                      msg={msg}
                      currentUserId={currentUserId}
                      isAdmin={isAdmin}
                      token={token}
                      onNavigate={(type, id) => {}}
                      onReact={handleReact}
                      onReply={setReplyTo}
                      onEdit={handleEditMessage}
                      onDelete={handleDeleteMessage}
                      onPin={activeView?.type === 'channel' ? handlePinMessage : null}
                      onUnpin={activeView?.type === 'channel' ? handleUnpinMessage : null}
                      onLightbox={setLightboxImg}
                      onOpenThread={setThreadRoot}
                    />
                  ))
                )}
                {typingUser && (
                  <div className="px-4 py-1 flex items-center gap-2">
                    <div className="flex gap-0.5">
                      {[0,1,2].map(i => <div key={i} className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50 animate-bounce" style={{animationDelay: `${i*0.15}s`}} />)}
                    </div>
                    <span className="text-xs text-muted-foreground">{typingUser.user_name} sedang mengetik...</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Reply preview */}
            {replyTo && (
              <div className="mx-4 mb-0 px-3 py-2 bg-muted/50 rounded-t-lg border-l-4 border-primary/60 flex items-center gap-2">
                <Reply size={14} className="text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-medium">{replyTo.sender_name}</span>
                  <p className="text-xs text-muted-foreground truncate">{replyTo.content}</p>
                </div>
                <button onClick={() => setReplyTo(null)} className="text-muted-foreground hover:text-foreground">
                  <X size={14} />
                </button>
              </div>
            )}

            {/* Composer */}
            <div className={`px-4 py-3 bg-[hsl(var(--card))] border-t shrink-0 ${replyTo ? 'rounded-b-none' : ''}`}>
              <div className="flex items-end gap-2 bg-muted/40 rounded-xl border px-3 py-2 relative">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                  accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.zip"
                />
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 shrink-0"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingFile || !activeView || activeView.type !== 'channel'}
                  title="Upload file (channel only)"
                  data-testid="upload-file-btn">
                  <Paperclip size={16} className={uploadingFile ? 'animate-pulse' : ''} />
                </Button>

                {/* ── Rich Text Formatting Toolbar ──────────────────── */}
                <div className="flex items-center gap-0.5 border-r pr-2 mr-1">
                  {[
                    { type: 'bold',   label: 'B',  title: 'Bold (**teks**)' },
                    { type: 'italic', label: 'I',  title: 'Italic (_teks_)', italic: true },
                    { type: 'code',   label: '<>', title: 'Code (`kode`)' },
                    { type: 'strike', label: 'S',  title: 'Strikethrough (~~teks~~)', strike: true },
                    { type: 'list',   label: '≡',  title: 'Bullet list' },
                  ].map(btn => (
                    <button
                      key={btn.type}
                      className="w-6 h-6 flex items-center justify-center text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                      title={btn.title}
                      onMouseDown={e => { e.preventDefault(); applyFormat(btn.type); }}
                    >
                      <span className={`font-${btn.type === 'bold' ? 'bold' : 'normal'} ${btn.italic ? 'italic' : ''} ${btn.strike ? 'line-through' : ''}`}>
                        {btn.label}
                      </span>
                    </button>
                  ))}
                </div>
                <textarea
                  ref={inputRef}
                  className="flex-1 bg-transparent resize-none outline-none text-sm min-h-[36px] max-h-32 placeholder:text-muted-foreground"
                  placeholder={`Pesan ke ${activeView.type === 'channel' ? '#' + activeView.name : activeView.name}... (@ untuk mention)`}
                  value={inputText}
                  onChange={e => {
                    const val = e.target.value;
                    setInputText(val);
                    // Detect @mention
                    const cursor = e.target.selectionStart;
                    const textBefore = val.slice(0, cursor);
                    const atMatch = textBefore.match(/@([\w\s]*)$/);
                    if (atMatch) {
                      setMentionState({ active: true, query: atMatch[1], start: textBefore.lastIndexOf('@') });
                    } else {
                      setMentionState({ active: false, query: '', start: 0 });
                    }
                  }}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  data-testid="message-input"
                />
                {/* @Mention Autocomplete Popup */}
                {mentionState.active && channelMembers.length > 0 && (() => {
                  const filtered = channelMembers.filter(m =>
                    !m.is_self && m.name.toLowerCase().includes(mentionState.query.toLowerCase())
                  ).slice(0, 6);
                  if (!filtered.length) return null;
                  return (
                    <div ref={mentionRef} className="absolute bottom-full mb-1 left-0 right-0 bg-card border rounded-lg shadow-lg z-50 overflow-hidden" style={{maxHeight: '200px', overflowY: 'auto'}}>
                      <div className="px-3 py-1.5 bg-muted/50 text-xs text-muted-foreground font-semibold">@ Mention</div>
                      {filtered.map(m => (
                        <div
                          key={m.id}
                          className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-accent transition-colors"
                          onMouseDown={e => {
                            e.preventDefault();
                            // Replace the @query with @name
                            const before = inputText.slice(0, mentionState.start);
                            const after = inputText.slice(mentionState.start + 1 + mentionState.query.length);
                            setInputText(before + '@' + m.name + ' ' + after);
                            setMentionState({ active: false, query: '', start: 0 });
                            setTimeout(() => inputRef.current?.focus(), 0);
                          }}
                        >
                          <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold flex-shrink-0">
                            {m.name[0]?.toUpperCase()}
                          </div>
                          <div>
                            <p className="text-xs font-medium">{m.name}</p>
                            <p className="text-[10px] text-muted-foreground">{m.position || m.role || ''}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
                <Button size="sm" className="rounded-lg h-8 px-3 shrink-0"
                  onClick={sendMessage}
                  disabled={!inputText.trim()}
                  data-testid="send-message-btn">
                  <Send size={14} />
                </Button>
              </div>
              <p className="text-[10px] text-muted-foreground mt-1 ml-1">
                {uploadingFile ? '⏳ Uploading file...' : 'Enter kirim · Shift+Enter baris baru · 📎 Max 10MB'}
              </p>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center p-8">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <MessageSquare size={28} className="text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-lg mb-1">Communication Hub</h3>
              <p className="text-sm text-muted-foreground max-w-xs">
                {isEmbedded 
                  ? 'Pilih channel atau kontak dari sidebar "Communication" untuk mulai diskusi.'
                  : 'Pilih channel atau kontak dari sidebar untuk mulai berkomunikasi.'}
              </p>
            </div>
            {!isEmbedded && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setShowCreateChannel(true)}
                  data-testid="empty-create-channel">
                  <Hash size={14} className="mr-1" /> Buat Channel
                </Button>
                <Button variant="outline" size="sm" onClick={() => setShowNewDM(true)}
                  data-testid="empty-new-dm">
                  <MessageSquare size={14} className="mr-1" /> Pesan Langsung
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      <CreateChannelDialog
        open={showCreateChannel}
        onClose={() => setShowCreateChannel(false)}
        token={token}
        onCreated={(ch) => { setChannels(prev => [ch, ...prev]); selectChannel(ch); }}
      />
      <NewDMDialog
        open={showNewDM}
        onClose={() => setShowNewDM(false)}
        token={token}
        currentUserId={currentUserId}
        onStartDM={startDM}
      />

      {/* ── Image Lightbox Modal ─────────────────────────────────────── */}
      {lightboxImg && (
        <div
          className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-4"
          onClick={() => setLightboxImg(null)}
          data-testid="image-lightbox"
        >
          <div className="relative max-w-[90vw] max-h-[90vh]" onClick={e => e.stopPropagation()}>
            <img
              src={lightboxImg.url}
              alt={lightboxImg.name}
              className="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
            />
            <div className="absolute top-2 right-2 flex gap-2">
              <a
                href={lightboxImg.url}
                download={lightboxImg.name}
                target="_blank"
                rel="noreferrer"
                className="bg-black/50 hover:bg-black/70 text-white rounded-full p-1.5 transition-colors"
                onClick={e => e.stopPropagation()}
                title="Download"
              >
                <Download size={16} />
              </a>
              <button
                className="bg-black/50 hover:bg-black/70 text-white rounded-full p-1.5 transition-colors"
                onClick={() => setLightboxImg(null)}
                title="Tutup"
              >
                <X size={16} />
              </button>
            </div>
            {lightboxImg.name && (
              <p className="absolute bottom-2 left-0 right-0 text-center text-white/70 text-xs px-4 truncate">
                {lightboxImg.name}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Session 28 — Thread Panel */}
      {threadRoot && (
        <ThreadPanel
          token={token}
          rootMessage={threadRoot}
          currentUserId={currentUserId}
          isAdmin={isAdmin}
          onClose={() => setThreadRoot(null)}
          onReact={handleReact}
          onEdit={handleEditMessage}
          onDelete={handleDeleteMessage}
          onPin={null}
          onUnpin={null}
          onLightbox={setLightboxImg}
          onRootCountUpdated={(rootId, count, lastReplyBy) => {
            setMessages(prev => prev.map(m => m.id === rootId ? {
              ...m,
              thread_reply_count: count,
              thread_last_reply_at: new Date().toISOString(),
              thread_last_reply_by: lastReplyBy,
            } : m));
          }}
        />
      )}
    </div>
  );
}
