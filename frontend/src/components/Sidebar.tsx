import { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Settings, BarChart2, Upload, FileText, PieChart, LogOut, Sparkles, Palette, HelpCircle, ChevronUp, Wallet } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../lib/utils';
import { useAuth } from '../context/AuthContext';

const getSidebarItems = (t: any) => [
  { name: t('Dashboard'), icon: BarChart2, path: '/dashboard' },
  { name: t('Transactions'), icon: FileText, path: '/transactions' },
  { name: t('Budgeting') || 'Budgeting', icon: Wallet, path: '/budgeting' },
  { name: t('Financial Report') || 'Reports', icon: PieChart, path: '/reports' },
  { name: t('Upload'), icon: Upload, path: '/upload' },
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { t } = useTranslation();
  const location = useLocation();
  const { user, logout } = useAuth();
  const sidebarItems = getSidebarItems(t);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <>
      {/* Overlay for mobile */}
      <div 
        className={cn(
          "fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      <aside className={cn(
        "flex flex-col h-screen w-64 bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xl fixed left-0 top-0 z-50 border-r border-slate-200 dark:border-slate-800 transition-transform duration-300",
        isOpen ? "translate-x-0" : "-translate-x-full",
        "md:translate-x-0"
      )}>
        <div className="flex items-center gap-3 p-6 border-b border-slate-200 dark:border-slate-800">
          <div className="p-2 bg-blue-600 rounded-lg">
            <PieChart className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">financeApp</h1>
        </div>
        
        <nav className="flex-1 p-4 overflow-y-auto">
          <ul className="space-y-2">
            {sidebarItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <li key={item.name}>
                  <Link
                    to={item.path}
                    onClick={() => onClose?.()} // Close sidebar on mobile when link clicked
                    className={cn(
                      "flex items-center space-x-3 p-3 rounded-lg transition-all duration-200 group",
                      isActive 
                        ? "bg-blue-600 text-white shadow-md" 
                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white"
                    )}
                  >
                    <item.icon className={cn("h-5 w-5", isActive ? "text-white" : "text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white")} />
                    <span className="font-medium">{item.name}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800">
          <div className="relative" ref={userMenuRef}>
            {isUserMenuOpen && (
              <div className="absolute bottom-full left-0 w-full mb-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-2">
                <div className="p-4 border-b border-slate-200 dark:border-slate-800">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">
                    {user?.email?.split('@')[0] || 'User'}
                  </p>
                  <p className="text-xs text-slate-400 truncate">
                    {user?.email}
                  </p>
                </div>
                
                <div className="p-2 space-y-1">
                  <button className="flex items-center space-x-3 p-2 w-full rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white transition-colors text-sm">
                    <Sparkles className="h-4 w-4" />
                    <span>Upgrade plan</span>
                  </button>
                  <Link 
                    to="/personalization" 
                    onClick={() => onClose?.()}
                    className="flex items-center space-x-3 p-2 w-full rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white transition-colors text-sm"
                  >
                    <Palette className="h-4 w-4" />
                    <span>{t('Personalization')}</span>
                  </Link>
                  <Link 
                    to="/settings" 
                    onClick={() => onClose?.()}
                    className="flex items-center space-x-3 p-2 w-full rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white transition-colors text-sm"
                  >
                    <Settings className="h-4 w-4" />
                    <span>{t('Settings')}</span>
                  </Link>
                </div>

                <div className="h-px bg-slate-200 dark:bg-slate-800 my-1 mx-2"></div>

                <div className="p-2 space-y-1">
                  <button className="flex items-center space-x-3 p-2 w-full rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white transition-colors text-sm">
                    <HelpCircle className="h-4 w-4" />
                    <span>Help</span>
                  </button>
                  <button
                    onClick={() => {
                      logout();
                      onClose?.();
                    }}
                    className="flex items-center space-x-3 p-2 w-full rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white transition-colors text-sm"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>{t('Logout')}</span>
                  </button>
                </div>
              </div>
            )}

            <button 
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center space-x-3 p-3 w-full rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-all duration-200 border border-transparent dark:hover:border-slate-700 group"
            >
              <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-sm shrink-0">
                <span className="text-sm font-bold">
                  {user?.email?.charAt(0).toUpperCase() || 'U'}
                </span>
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                  {user?.email?.split('@')[0] || 'User'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">Free Plan</p>
              </div>
              <ChevronUp className={cn("h-4 w-4 text-slate-400 transition-transform duration-200", isUserMenuOpen && "rotate-180")} />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
