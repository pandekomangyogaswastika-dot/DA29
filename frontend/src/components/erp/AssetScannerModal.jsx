/**
 * AssetScannerModal — Scan Barcode/QR Asset untuk WMS & Inventory
 * 
 * Fitur:
 * - Scan barcode/QR code asset
 * - Manual input asset number
 * - Update lokasi asset setelah scan
 * - Record scan history
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { Camera, Keyboard, X, AlertTriangle, Loader2, MapPin, Package } from 'lucide-react';
import { Html5Qrcode } from 'html5-qrcode';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';

const SCANNER_ELEMENT_ID = 'asset-qr-reader';

export default function AssetScannerModal({ token, onScanned, onClose }) {
  const scannerRef = useRef(null);
  const [cameraState, setCameraState] = useState('idle');
  const [cameraError, setCameraError] = useState('');
  const [tab, setTab] = useState('camera');
  const [manual, setManual] = useState('');
  const [location, setLocation] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState('');

  const stopCamera = useCallback(async () => {
    try {
      if (scannerRef.current) {
        const inst = scannerRef.current;
        scannerRef.current = null;
        if (inst.isScanning) {
          try { await inst.stop(); } catch (_) { /* noop */ }
        }
        try { await inst.clear(); } catch (_) { /* noop */ }
      }
    } catch (_) { /* noop */ }
  }, []);

  const resolveAsset = useCallback(async (assetNumber) => {
    const cleaned = String(assetNumber || '').trim().toUpperCase();
    if (!cleaned) throw new Error('Nomor aset kosong');
    
    const res = await fetch(
      `/api/assets/scan-by-number/${encodeURIComponent(cleaned)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    
    if (res.status === 404) throw new Error(`Aset "${cleaned}" tidak ditemukan`);
    if (!res.ok) {
      let detail = '';
      try { detail = (await res.json()).detail || ''; } catch (_) { /* noop */ }
      throw new Error(detail || `Gagal mengambil aset (HTTP ${res.status})`);
    }
    return await res.json();
  }, [token]);

  const recordScan = useCallback(async (asset, newLocation) => {
    try {
      const res = await fetch(`/api/assets/${asset.id}/scan`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scan_type: 'location_check',
          location: newLocation || '',
          notes: `Scanned via ${tab === 'camera' ? 'camera' : 'manual input'}`,
        }),
      });
      
      if (!res.ok) throw new Error('Gagal record scan');
      return await res.json();
    } catch (e) {
      console.error('Record scan error:', e);
      throw e;
    }
  }, [token, tab]);

  const handleDetected = useCallback(async (payload, source) => {
    setLookupError('');
    setLookupLoading(true);
    try {
      // Parse payload (bisa JSON dari QR atau plain text dari barcode)
      let assetNumber = payload;
      try {
        const parsed = JSON.parse(payload);
        if (parsed.type === 'asset' && parsed.asset_number) {
          assetNumber = parsed.asset_number;
        }
      } catch (_) {
        // Plain text, use as-is
      }
      
      const asset = await resolveAsset(assetNumber);
      
      // Record scan
      await recordScan(asset, location);
      
      // Stop camera
      await stopCamera();
      
      toast.success(`Asset ${asset.asset_number} berhasil di-scan!`);
      
      if (onScanned) onScanned(asset, { payload, source, location });
    } catch (e) {
      setLookupError(e.message || 'Gagal mengambil asset');
      toast.error(e.message || 'Gagal scan asset');
    } finally {
      setLookupLoading(false);
    }
  }, [resolveAsset, recordScan, location, onScanned, stopCamera]);

  const startCamera = useCallback(async () => {
    setCameraError('');
    setCameraState('starting');
    try {
      const el = document.getElementById(SCANNER_ELEMENT_ID);
      if (!el) {
        setCameraState('unsupported');
        setCameraError('Scanner tidak bisa diinisialisasi');
        return;
      }

      if (scannerRef.current) {
        await stopCamera();
      }

      let cameras = [];
      try {
        cameras = await Html5Qrcode.getCameras();
      } catch (err) {
        setCameraState('blocked');
        setCameraError('Kamera diblokir atau tidak ada izin');
        return;
      }

      if (!cameras || cameras.length === 0) {
        setCameraState('unsupported');
        setCameraError('Tidak ada kamera tersedia');
        return;
      }

      const backCam = cameras.find(c => c.label?.toLowerCase().includes('back')) || cameras[0];
      const scanner = new Html5Qrcode(SCANNER_ELEMENT_ID);
      scannerRef.current = scanner;

      await scanner.start(
        backCam.id,
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          handleDetected(decodedText, 'camera');
        },
        (err) => { /* silent */ }
      );

      setCameraState('scanning');
    } catch (err) {
      setCameraState('blocked');
      setCameraError(err.message || 'Gagal start kamera');
    }
  }, [handleDetected, stopCamera]);

  useEffect(() => {
    if (tab === 'camera') {
      startCamera();
    } else {
      stopCamera();
    }
    return () => { stopCamera(); };
  }, [tab, startCamera, stopCamera]);

  const handleManualSubmit = () => {
    if (!manual.trim()) {
      toast.error('Nomor aset wajib diisi');
      return;
    }
    handleDetected(manual, 'manual');
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package size={16} />
            Scan Asset
          </DialogTitle>
        </DialogHeader>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full">
            <TabsTrigger value="camera" className="flex-1">
              <Camera size={14} className="mr-1" /> Kamera
            </TabsTrigger>
            <TabsTrigger value="manual" className="flex-1">
              <Keyboard size={14} className="mr-1" /> Manual
            </TabsTrigger>
          </TabsList>

          {/* Camera Tab */}
          <TabsContent value="camera" className="mt-3 space-y-3">
            <div className="bg-muted/40 rounded-lg p-3">
              <label className="text-xs font-medium text-muted-foreground">Lokasi (opsional)</label>
              <Input
                placeholder="Rak A-12, Gudang Utama..."
                value={location}
                onChange={e => setLocation(e.target.value)}
                className="mt-1"
              />
            </div>

            <div
              id={SCANNER_ELEMENT_ID}
              className="w-full aspect-square rounded-xl overflow-hidden bg-muted/20 border-2 border-dashed border-border"
            />

            {cameraState === 'scanning' && (
              <div className="text-center">
                <div className="flex items-center justify-center gap-2 text-sm text-emerald-600">
                  <div className="animate-pulse w-2 h-2 bg-emerald-500 rounded-full" />
                  Scanning... Arahkan kamera ke barcode/QR
                </div>
              </div>
            )}

            {cameraState === 'starting' && (
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 size={14} className="animate-spin" />
                Memulai kamera...
              </div>
            )}

            {(cameraState === 'blocked' || cameraState === 'unsupported') && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-sm">
                <div className="flex items-start gap-2">
                  <AlertTriangle size={16} className="text-amber-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-600">Kamera tidak tersedia</p>
                    <p className="text-xs text-muted-foreground mt-1">{cameraError}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Silakan gunakan tab Manual atau izinkan akses kamera.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {lookupError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm">
                <p className="text-red-600">{lookupError}</p>
              </div>
            )}
          </TabsContent>

          {/* Manual Tab */}
          <TabsContent value="manual" className="mt-3 space-y-3">
            <div className="bg-muted/40 rounded-lg p-3 space-y-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Nomor Asset *</label>
                <Input
                  placeholder="AST-IT-2026-0001"
                  value={manual}
                  onChange={e => setManual(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleManualSubmit()}
                  className="mt-1"
                  data-testid="manual-asset-input"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Lokasi (opsional)</label>
                <Input
                  placeholder="Rak A-12, Gudang Utama..."
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>

            <Button
              className="w-full"
              onClick={handleManualSubmit}
              disabled={lookupLoading}
              data-testid="submit-manual-scan"
            >
              {lookupLoading ? (
                <>
                  <Loader2 size={14} className="mr-1 animate-spin" />
                  Memproses...
                </>
              ) : (
                <>
                  <MapPin size={14} className="mr-1" />
                  Scan Asset
                </>
              )}
            </Button>

            {lookupError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm">
                <p className="text-red-600">{lookupError}</p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Tutup</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
