import { useState, useEffect, useCallback, Suspense, useMemo } from 'react';
import './App.css';
import Login from './components/erp/Login';
import PortalSelector from './components/erp/PortalSelector';
import PortalShell from './components/erp/PortalShell';
import OperatorView from './components/erp/OperatorView';
import ShopFloorTV from './components/erp/ShopFloorTV';
import { MODULE_REGISTRY, DEFAULT_MODULE } from './components/erp/moduleRegistry';
import { ThemeProvider } from './components/theme/ThemeProvider';
import { Toaster } from './components/ui/sonner';
import { TooltipProvider } from './components/ui/tooltip';
import AIChatbotWidget from './components/erp/AIChatbotWidget';
import ClientLogin from './components/client/ClientLogin';
import ClientPortalShell from './components/client/ClientPortalShell';
import { clientApi } from './components/client/clientApi';
import CreatorPortalApp from './components/creator/CreatorPortalApp';
import LiveHostPortalApp from './components/livehost/LiveHostPortalApp';
import VendorCMTPortalApp from './components/vendor-cmt/VendorCMTPortalApp';
import AbsenPage from './pages/AbsenPage';
import { configureApi } from './lib/apiFetch';
import ErrorBoundary from './components/ErrorBoundary';

// Default module untuk tiap portal
const PORTAL_DEFAULT_MODULE = {
  management: 'management-dashboard',
  production: 'production-dashboard',
  warehouse:  'warehouse-dashboard',
  finance:    'finance-dashboard',
  hr:         'hr-dashboard',
  maklon:     'maklon-dashboard',
  toko:       'toko-dashboard',
  rnd:        'rnd-dashboard',
  self:       'self-dashboard',
  collaboration: 'collaboration',  // NEW: Unified Communication + Workspace + Learning
  assets:     'asset-dashboard',
};

const VALID_PORTALS = Object.keys(PORTAL_DEFAULT_MODULE);

const ModuleSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[hsl(var(--primary))]" />
  </div>
);

// Deteksi apakah URL saat ini /operator
const isOperatorRoute = () => {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/operator');
};

// Deteksi apakah URL saat ini /tv
const isTVRoute = () => {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/tv');
};

// Deteksi apakah URL saat ini /client (Portal Klien Maklon)
const isClientRoute = () => {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/client');
};

// Deteksi apakah URL saat ini /creator (Portal Creator KOL)
const isCreatorRoute = () => {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/creator');
};

// Deteksi apakah URL saat ini /livehost (Portal LiveHost - Phase 4)
const isLiveHostRoute = () => {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/livehost');
};

// Deteksi apakah URL saat ini /absen (Portal Absen Mandiri)
const isAbsenRoute = () => {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/absen');
};

// Deteksi apakah URL saat ini /vendor-cmt (Portal Vendor CMT)
const isVendorCMTRoute = () => {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.startsWith('/vendor-cmt');
};

function ClientPortalApp() {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    const sess = clientApi.loadSession();
    if (sess) {
      setToken(sess.token);
      setUser(sess.user);
    }
    setBootstrapped(true);
  }, []);

  const handleLogin = useCallback((tokenData, userData) => {
    setToken(tokenData);
    setUser(userData);
  }, []);

  const handleLogout = useCallback(() => {
    clientApi.clearSession();
    setToken(null);
    setUser(null);
  }, []);

  if (!bootstrapped) {
    return (
      <div className="flex items-center justify-center h-screen bg-[hsl(var(--background))]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[hsl(var(--primary))]"></div>
      </div>
    );
  }

  if (!token || !user) {
    return <ClientLogin onLogin={handleLogin} />;
  }

  return <ClientPortalShell token={token} user={user} onLogout={handleLogout} />;
}

function App() {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPortal, setSelectedPortal] = useState(null);
  const [currentModule, setCurrentModule] = useState('management-dashboard');
  const [operatorRoute, setOperatorRoute] = useState(isOperatorRoute());
  const [tvRoute, setTVRoute] = useState(isTVRoute());
  const [clientRoute, setClientRoute] = useState(isClientRoute());
  const [creatorRoute, setCreatorRoute] = useState(isCreatorRoute());
  const [liveHostRoute, setLiveHostRoute] = useState(isLiveHostRoute());
  const [absenRoute, setAbsenRoute] = useState(isAbsenRoute());
  const [vendorCMTRoute, setVendorCMTRoute] = useState(isVendorCMTRoute());

  // Sync operatorRoute on popstate / navigation
  useEffect(() => {
    const onPop = () => {
      setOperatorRoute(isOperatorRoute());
      setTVRoute(isTVRoute());
      setClientRoute(isClientRoute());
      setCreatorRoute(isCreatorRoute());
      setLiveHostRoute(isLiveHostRoute());
      setAbsenRoute(isAbsenRoute());
      setVendorCMTRoute(isVendorCMTRoute());
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  // Restore session
  useEffect(() => {
    const savedToken = localStorage.getItem('erp_token');
    const savedUser = localStorage.getItem('erp_user');
    const savedPortal = localStorage.getItem('erp_portal');
    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        const parsed = JSON.parse(savedUser);
        setUser(parsed);
        if (savedPortal && VALID_PORTALS.includes(savedPortal)) {
          setSelectedPortal(savedPortal);
          setCurrentModule(PORTAL_DEFAULT_MODULE[savedPortal]);
        }
      } catch (e) {
        localStorage.removeItem('erp_token');
        localStorage.removeItem('erp_user');
        localStorage.removeItem('erp_portal');
      }
    }
    setLoading(false);
  }, []);

  // Configure apiFetch wrapper with 401 auto-logout handler (runs once on mount)
  useEffect(() => {
    configureApi({
      onUnauthorized: () => {
        // Clear session storage and trigger re-render to Login
        localStorage.removeItem('erp_token');
        localStorage.removeItem('erp_user');
        localStorage.removeItem('erp_portal');
        setToken(null);
        setUser(null);
        setSelectedPortal(null);
      },
    });
  }, []);

  const handleLogin = useCallback((tokenData, userData) => {
    setToken(tokenData);
    setUser(userData);
    localStorage.setItem('erp_token', tokenData);
    localStorage.setItem('erp_user', JSON.stringify(userData));
    // Role operator → redirect ke Operator View
    if ((userData.role || '').toLowerCase() === 'operator') {
      window.history.pushState({}, '', '/operator');
      setOperatorRoute(true);
    } else {
      setSelectedPortal(null);
      setCurrentModule('management-dashboard');
    }
  }, []);

  const handleLogout = useCallback(() => {
    setToken(null);
    setUser(null);
    setSelectedPortal(null);
    setCurrentModule('management-dashboard');
    localStorage.removeItem('erp_token');
    localStorage.removeItem('erp_user');
    localStorage.removeItem('erp_portal');
    if (isOperatorRoute()) {
      window.history.pushState({}, '', '/');
      setOperatorRoute(false);
    }
  }, []);

  const handleSelectPortal = useCallback((portalId) => {
    if (!VALID_PORTALS.includes(portalId)) return;
    setSelectedPortal(portalId);
    setCurrentModule(PORTAL_DEFAULT_MODULE[portalId]);
    localStorage.setItem('erp_portal', portalId);
  }, []);

  // Hybrid-nav support: switch portal dari pill-nav tanpa balik ke selector
  const handlePortalChange = useCallback((portalId) => {
    if (!VALID_PORTALS.includes(portalId)) return;
    setSelectedPortal(portalId);
    setCurrentModule(PORTAL_DEFAULT_MODULE[portalId]);
    localStorage.setItem('erp_portal', portalId);
  }, []);

  const handleBackToPortals = useCallback(() => {
    setSelectedPortal(null);
    setCurrentModule('management-dashboard');
    localStorage.removeItem('erp_portal');
  }, []);

  const [navParams, setNavParams] = useState({});

  const handleNavigate = useCallback((moduleId, params = {}) => {
    setCurrentModule(moduleId);
    setNavParams(params || {});
  }, []);

  // ── Memoize headers to prevent infinite re-render in child components ──
  // MUST be before any conditional returns (Rules of Hooks)
  const headers = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[hsl(var(--background))]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[hsl(var(--primary))]"></div>
      </div>
    );
  }

  // TV Mode (Phase 18C) — public, no auth required
  if (tvRoute) {
    return <ShopFloorTV />;
  }

  // Absen Mandiri Portal — dedicated attendance page
  if (absenRoute) {
    return <AbsenPage />;
  }

  // Vendor CMT Portal — separate app for CMT vendors
  if (vendorCMTRoute) {
    return <VendorCMTPortalApp />;
  }

  // Client Portal (Phase 4) — separate app, separate auth, separate token storage
  if (clientRoute) {
    return <ClientPortalApp />;
  }

  // Creator Portal (Phase 5) — separate app for KOL creators
  if (creatorRoute) {
    return <CreatorPortalApp />;
  }

  // LiveHost Portal (Phase 4 / Session 28) — separate app for live streaming hosts
  if (liveHostRoute) {
    return <LiveHostPortalApp />;
  }

  if (!token || !user) return <Login onLogin={handleLogin} />;

  // Operator View (mobile) on /operator URL OR if user role is operator
  if (operatorRoute || (user.role || '').toLowerCase() === 'operator') {
    return <OperatorView user={user} token={token} onLogout={handleLogout} />;
  }

  if (!selectedPortal) {
    return <PortalSelector user={user} onSelectPortal={handleSelectPortal} onLogout={handleLogout} />;
  }

  const userPerms = user?.permissions || [];
  const hasPerm = (key) => {
    const role = (user?.role || '').toLowerCase();
    if (['superadmin', 'admin', 'owner'].includes(role)) return true;
    return userPerms.includes(key) || userPerms.includes(key.split('.')[0] + '.*') || userPerms.includes('*');
  };

  const ModuleComponent = MODULE_REGISTRY[currentModule] || DEFAULT_MODULE;

  // Special handling for Portal Kolaborasi - render full screen without PortalShell wrapper
  if (selectedPortal === 'collaboration') {
    return (
      <>
        <Suspense fallback={<ModuleSpinner />}>
          <ModuleComponent
            token={token}
            user={user}
            headers={headers}
            userRole={user?.role}
            hasPerm={hasPerm}
            onNavigate={handleNavigate}
            onLogout={handleLogout}
            onBack={handleBackToPortals}
            moduleId={currentModule}
            deepLinkParams={navParams}
          />
        </Suspense>
        {/* Global AI Chatbot Widget */}
        <AIChatbotWidget headers={headers} user={user} />
      </>
    );
  }

  // Standard portal rendering with PortalShell
  return (
    <>
      <PortalShell
        portal={selectedPortal}
        user={user}
        token={token}
        onBack={handleBackToPortals}
        onLogout={handleLogout}
        onPortalChange={handlePortalChange}
        currentModule={currentModule}
        onModuleChange={setCurrentModule}
      >
        <Suspense fallback={<ModuleSpinner />}>
          <ModuleComponent
            token={token}
            user={user}
            headers={headers}
            userRole={user?.role}
            hasPerm={hasPerm}
            onNavigate={handleNavigate}
            moduleId={currentModule}
            deepLinkParams={navParams}
          />
        </Suspense>
      </PortalShell>
      {/* Global AI Chatbot Widget — available on all portals */}
      <AIChatbotWidget headers={headers} user={user} />
    </>
  );
}

export default function AppWithTheme() {
  return (
    <ErrorBoundary level="root">
      <ThemeProvider defaultTheme="system">
        <TooltipProvider delayDuration={250}>
          {/* Ambient decorative layers — pointer-events none, behind everything */}
          <div className="starfield" aria-hidden="true" />
          <div className="noise-overlay fixed inset-0 pointer-events-none" aria-hidden="true" />
          <App />
          <Toaster position="top-right" richColors closeButton />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
