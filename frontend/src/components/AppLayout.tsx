import { ReactNode, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import {
  LayoutDashboard,
  Package,
  Upload,
  Languages,
  Search,
  Sparkles,
  Download,
  Menu,
  X,
  ChevronLeft,
  ChevronDown,
  LogOut,
  Boxes,
  Layers,
  Bookmark,
  LayoutTemplate,
  Settings2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const dashboardItem: NavItem = {
  label: 'Dashboard',
  href: '/',
  icon: LayoutDashboard,
};

const navSections: NavSection[] = [
  {
    label: 'Raw Data',
    items: [
      { label: 'Import', href: '/imports', icon: Upload },
      { label: 'Translation', href: '/translations', icon: Languages },
      { label: 'Keywords', href: '/keywords', icon: Search },
      { label: 'Saved Terms', href: '/keywords/saved-terms', icon: Bookmark },
    ],
  },
  {
    label: 'Listings',
    items: [
      { label: 'Listings', href: '/groups', icon: Layers },
      { label: 'Title Templates', href: '/templates', icon: LayoutTemplate },
    ],
  },
  {
    label: 'Content',
    items: [
      { label: 'Generated titles', href: '/content/generated-titles', icon: Sparkles },
    ],
  },
  {
    label: 'Products',
    items: [
      { label: 'Products', href: '/variants', icon: Boxes },
      { label: 'Parents', href: '/products', icon: Package },
    ],
  },
  {
    label: 'Bible',
    items: [
      { label: 'Exports', href: '/exports', icon: Download },
    ],
  },
  {
    label: 'Settings',
    items: [
      { label: 'Settings', href: '/settings', icon: Settings2 },
    ],
  },
];

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, role, signOut, isAdmin } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    navSections.forEach((section) => {
      initial[section.label] = true;
    });
    return initial;
  });

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  const toggleSection = (label: string) => {
    setOpenSections((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  useEffect(() => {
    navSections.forEach((section) => {
      if (section.items.some((item) => isActive(item.href))) {
        setOpenSections((prev) => ({ ...prev, [section.label]: true }));
      }
    });
  }, [location.pathname]);

  const handleSignOut = async () => {
    await signOut();
    navigate('/auth');
  };

  const getUserInitials = () => {
    const source = user?.full_name || user?.email || '';
    return source.substring(0, 2).toUpperCase();
  };

  const NavLink = ({
    item,
    sectionLabel,
    onClick,
  }: {
    item: NavItem;
    sectionLabel?: string;
    onClick?: () => void;
  }) => {
    const active = isActive(item.href);
    return (
      <Link
        to={item.href}
        onClick={onClick}
        title={collapsed ? `${sectionLabel ? sectionLabel + ' – ' : ''}${item.label}` : item.label}
        className={cn(
          'group flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm font-medium transition-all duration-150',
          active
            ? 'bg-primary/10 text-primary'
            : 'text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground'
        )}
      >
        <div
          className={cn(
            'flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-md transition-all duration-150',
            active
              ? 'bg-primary/15 text-primary'
              : 'text-muted-foreground group-hover:text-foreground group-hover:bg-muted/60'
          )}
        >
          <item.icon className="w-4 h-4" />
        </div>
        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden whitespace-nowrap"
            >
              {item.label}
            </motion.span>
          )}
        </AnimatePresence>
        {active && !collapsed && (
          <motion.div
            layoutId="activeIndicator"
            className="ml-auto w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0"
          />
        )}
      </Link>
    );
  };

  const UserMenu = ({ showLabel = true }: { showLabel?: boolean }) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            'flex items-center gap-2.5 w-full rounded-lg px-2 py-1.5 transition-colors hover:bg-sidebar-accent/60 text-left',
            !showLabel && 'justify-center p-1.5'
          )}
        >
          <Avatar className="h-7 w-7 flex-shrink-0 ring-2 ring-primary/20">
            <AvatarFallback className="text-[11px] font-semibold bg-primary/15 text-primary">
              {getUserInitials()}
            </AvatarFallback>
          </Avatar>
          {showLabel && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate text-foreground leading-tight">
                {user?.full_name || user?.email}
              </p>
              <p className="text-[10px] text-muted-foreground truncate leading-tight capitalize">
                {isAdmin ? 'Admin' : role || 'User'}
              </p>
            </div>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-medium">{user?.email}</p>
            <p className="text-xs text-muted-foreground capitalize">{role || 'user'}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleSignOut} className="text-destructive focus:text-destructive gap-2">
          <LogOut className="w-4 h-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  return (
    <div className="min-h-screen flex w-full bg-background">
      {/* Desktop Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 68 : 236 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="hidden lg:flex flex-col border-r border-border bg-sidebar fixed h-full z-30 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center h-14 px-3 border-b border-sidebar-border flex-shrink-0">
          <AnimatePresence initial={false}>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex items-center gap-2.5 flex-1 min-w-0"
              >
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm flex-shrink-0">
                  <Sparkles className="w-3.5 h-3.5 text-primary-foreground" />
                </div>
                <div className="min-w-0">
                  <span className="font-display font-bold text-foreground text-sm tracking-tight">Traxe</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          {collapsed && (
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm mx-auto">
              <Sparkles className="w-3.5 h-3.5 text-primary-foreground" />
            </div>
          )}
          {!collapsed && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 flex-shrink-0 text-muted-foreground hover:text-foreground"
              onClick={() => setCollapsed(!collapsed)}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto overflow-x-hidden">
          {/* Dashboard */}
          <NavLink item={dashboardItem} />

          {/* Sections */}
          {navSections.map((section) => (
            <div key={section.label} className="pt-3">
              {collapsed ? (
                <>
                  {/* Collapsed: tiny separator dot */}
                  <div className="flex justify-center py-1 mb-0.5">
                    <div className="w-4 h-px bg-border" />
                  </div>
                  <div className="space-y-0.5">
                    {section.items.map((item) => (
                      <NavLink key={item.href} item={item} sectionLabel={section.label} />
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => toggleSection(section.label)}
                    className="flex w-full items-center justify-between px-2.5 py-1 mb-0.5 group"
                  >
                    <span className="text-[10px] font-semibold tracking-widest text-muted-foreground/60 uppercase group-hover:text-muted-foreground transition-colors">
                      {section.label}
                    </span>
                    <ChevronDown
                      className={cn(
                        'w-3 h-3 text-muted-foreground/50 transition-transform duration-200',
                        !openSections[section.label] && '-rotate-90'
                      )}
                    />
                  </button>
                  <AnimatePresence initial={false}>
                    {openSections[section.label] && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="space-y-0.5 overflow-hidden"
                      >
                        {section.items.map((item) => (
                          <NavLink key={item.href} item={item} />
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </>
              )}
            </div>
          ))}

          {/* Collapse toggle at bottom of nav when collapsed */}
          {collapsed && (
            <div className="pt-3 flex justify-center">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                onClick={() => setCollapsed(false)}
              >
                <ChevronLeft className="w-4 h-4 rotate-180" />
              </Button>
            </div>
          )}
        </nav>

        {/* User */}
        <div className="border-t border-sidebar-border p-2 flex-shrink-0">
          <UserMenu showLabel={!collapsed} />
        </div>
      </motion.aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-card/95 backdrop-blur border-b border-border z-40 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-primary-foreground" />
          </div>
          <span className="font-display font-bold text-foreground text-sm tracking-tight">Traxe</span>
        </div>
        <div className="flex items-center gap-1">
          <UserMenu showLabel={false} />
          <Button
            variant="ghost"
            size="sm"
            className="h-9 w-9 p-0"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="lg:hidden fixed inset-0 bg-foreground/20 backdrop-blur-sm z-40"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="lg:hidden fixed right-0 top-0 bottom-0 w-72 bg-sidebar border-l border-sidebar-border z-50 flex flex-col"
            >
              <div className="flex items-center justify-between h-14 px-4 border-b border-sidebar-border flex-shrink-0">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shadow-sm">
                    <Sparkles className="w-3.5 h-3.5 text-primary-foreground" />
                  </div>
                  <span className="font-display font-bold text-sm tracking-tight">Traxe</span>
                </div>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => setMobileOpen(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>

              <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
                <Link
                  to={dashboardItem.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    'group flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm font-medium transition-all',
                    isActive(dashboardItem.href)
                      ? 'bg-primary/10 text-primary'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground'
                  )}
                >
                  <div className={cn(
                    'flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-md',
                    isActive(dashboardItem.href)
                      ? 'bg-primary/15 text-primary'
                      : 'text-muted-foreground'
                  )}>
                    <dashboardItem.icon className="w-4 h-4" />
                  </div>
                  <span>{dashboardItem.label}</span>
                </Link>

                {navSections.map((section) => (
                  <div key={section.label} className="pt-3">
                    <button
                      type="button"
                      onClick={() => toggleSection(section.label)}
                      className="flex w-full items-center justify-between px-2.5 py-1 mb-0.5 group"
                    >
                      <span className="text-[10px] font-semibold tracking-widest text-muted-foreground/60 uppercase group-hover:text-muted-foreground transition-colors">
                        {section.label}
                      </span>
                      <ChevronDown
                        className={cn(
                          'w-3 h-3 text-muted-foreground/50 transition-transform duration-200',
                          !openSections[section.label] && '-rotate-90'
                        )}
                      />
                    </button>
                    <AnimatePresence initial={false}>
                      {openSections[section.label] && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.18 }}
                          className="space-y-0.5 overflow-hidden"
                        >
                          {section.items.map((item) => (
                            <Link
                              key={item.href}
                              to={item.href}
                              onClick={() => setMobileOpen(false)}
                              className={cn(
                                'group flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm font-medium transition-all',
                                isActive(item.href)
                                  ? 'bg-primary/10 text-primary'
                                  : 'text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-foreground'
                              )}
                            >
                              <div className={cn(
                                'flex-shrink-0 flex items-center justify-center w-7 h-7 rounded-md',
                                isActive(item.href)
                                  ? 'bg-primary/15 text-primary'
                                  : 'text-muted-foreground'
                              )}>
                                <item.icon className="w-4 h-4" />
                              </div>
                              <span>{item.label}</span>
                              {isActive(item.href) && (
                                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                              )}
                            </Link>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </nav>

              <div className="border-t border-sidebar-border p-3 flex-shrink-0">
                <UserMenu showLabel />
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main
        className={cn(
          'flex-1 pt-14 lg:pt-0 transition-all duration-200',
          collapsed ? 'lg:pl-[68px]' : 'lg:pl-[236px]'
        )}
      >
        {children}
      </main>
    </div>
  );
}
