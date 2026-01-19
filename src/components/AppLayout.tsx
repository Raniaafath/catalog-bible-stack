import { ReactNode, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import {
  LayoutDashboard,
  Upload,
  Languages,
  Search,
  Sparkles,
  Download,
  Menu,
  X,
  ChevronLeft,
  LogOut,
  User,
  Shield,
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
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: LayoutDashboard },
  { label: 'Imports', href: '/imports', icon: Upload },
  { label: 'Translations', href: '/translations', icon: Languages },
  { label: 'Keywords', href: '/keywords', icon: Search },
  { label: 'Content', href: '/content', icon: Sparkles },
  { label: 'Exports', href: '/exports', icon: Download },
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

  const isActive = (href: string) => {
    if (href === '/') return location.pathname === '/';
    return location.pathname.startsWith(href);
  };

  const handleSignOut = async () => {
    await signOut();
    navigate('/auth');
  };

  const getUserInitials = () => {
    const email = user?.email || '';
    return email.substring(0, 2).toUpperCase();
  };

  const UserMenu = ({ showLabel = true }: { showLabel?: boolean }) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className={cn("gap-2", showLabel ? "w-full justify-start px-3" : "h-10 w-10 p-0")}>
          <Avatar className="h-7 w-7">
            <AvatarImage src={user?.user_metadata?.avatar_url} />
            <AvatarFallback className="text-xs bg-primary text-primary-foreground">
              {getUserInitials()}
            </AvatarFallback>
          </Avatar>
          {showLabel && (
            <div className="flex-1 text-left overflow-hidden">
              <p className="text-sm font-medium truncate">{user?.email}</p>
              <div className="flex items-center gap-1">
                {isAdmin ? (
                  <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">
                    <Shield className="w-2.5 h-2.5 mr-0.5" />
                    Admin
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                    <User className="w-2.5 h-2.5 mr-0.5" />
                    User
                  </Badge>
                )}
              </div>
            </div>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium">{user?.email}</p>
            <p className="text-xs text-muted-foreground capitalize">{role || 'user'} role</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleSignOut} className="text-destructive focus:text-destructive">
          <LogOut className="w-4 h-4 mr-2" />
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
        animate={{ width: collapsed ? 72 : 240 }}
        transition={{ duration: 0.2 }}
        className="hidden lg:flex flex-col border-r border-border bg-sidebar fixed h-full z-30"
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-sidebar-border">
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-primary-foreground" />
                </div>
                <span className="font-display font-semibold text-foreground">Pipeline</span>
              </motion.div>
            )}
          </AnimatePresence>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => setCollapsed(!collapsed)}
          >
            <ChevronLeft
              className={cn(
                'w-4 h-4 transition-transform duration-200',
                collapsed && 'rotate-180'
              )}
            />
          </Button>
        </div>

        <nav className="flex-1 py-4 px-2 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive(item.href)
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="overflow-hidden whitespace-nowrap"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          ))}
        </nav>

        {/* User Section */}
        <div className="border-t border-sidebar-border p-2">
          <UserMenu showLabel={!collapsed} />
        </div>
      </motion.aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-card border-b border-border z-40 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-display font-semibold text-foreground">Pipeline</span>
        </div>
        <div className="flex items-center gap-2">
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
              className="lg:hidden fixed right-0 top-0 bottom-0 w-72 bg-sidebar border-l border-sidebar-border z-50"
            >
              <div className="flex items-center justify-between h-14 px-4 border-b border-sidebar-border">
                <span className="font-display font-semibold text-foreground">Menu</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-9 w-9 p-0"
                  onClick={() => setMobileOpen(false)}
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
              <nav className="py-4 px-2 space-y-1">
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    to={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      isActive(item.href)
                        ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                    )}
                  >
                    <item.icon className="w-5 h-5 flex-shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                ))}
              </nav>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main
        className={cn(
          'flex-1 pt-14 lg:pt-0 transition-all duration-200',
          collapsed ? 'lg:pl-[72px]' : 'lg:pl-[240px]'
        )}
      >
        {children}
      </main>
    </div>
  );
}
