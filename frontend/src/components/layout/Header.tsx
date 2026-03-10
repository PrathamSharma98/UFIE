import React, { useCallback, useRef, useEffect, useState } from 'react';
import { Droplets, Bot, BarChart3, AlertTriangle, Menu, Map, X } from 'lucide-react';

type TabId = 'map' | 'analytics' | 'alerts';

interface HeaderProps {
  onToggleAI: () => void;
  onToggleSidebar: () => void;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'map', label: 'Map View', icon: Map },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
];

export default function Header({ onToggleAI, onToggleSidebar, activeTab, onTabChange }: HeaderProps) {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const [indicatorStyle, setIndicatorStyle] = useState<React.CSSProperties>({});

  // Update the sliding indicator position when activeTab changes
  useEffect(() => {
    const idx = tabs.findIndex((t) => t.id === activeTab);
    const el = tabRefs.current[idx];
    if (el) {
      setIndicatorStyle({
        left: el.offsetLeft,
        width: el.offsetWidth,
      });
    }
  }, [activeTab]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const currentIdx = tabs.findIndex((t) => t.id === activeTab);
      let nextIdx = currentIdx;

      if (e.key === 'ArrowRight') {
        e.preventDefault();
        nextIdx = (currentIdx + 1) % tabs.length;
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        nextIdx = (currentIdx - 1 + tabs.length) % tabs.length;
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        return; // already active
      } else {
        return;
      }

      onTabChange(tabs[nextIdx].id);
      tabRefs.current[nextIdx]?.focus();
    },
    [activeTab, onTabChange]
  );

  return (
    <header className="h-14 bg-slate-900/95 backdrop-blur-xl border-b border-slate-700/50 flex items-center justify-between px-4 z-40 relative select-none">
      {/* Left: brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 hover:bg-slate-700/60 rounded-lg lg:hidden"
          aria-label="Toggle sidebar"
        >
          <Menu size={20} className="text-slate-400" />
        </button>
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Droplets size={19} className="text-white" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-sm font-extrabold gradient-text tracking-tight leading-none">UFIE</h1>
            <p className="text-[10px] text-slate-500 leading-none mt-0.5">Urban Flood Intelligence</p>
          </div>
        </div>
      </div>

      {/* Center: tab nav */}
      <nav
        className="relative flex items-center bg-slate-800/60 rounded-xl p-1 gap-0.5"
        role="tablist"
        aria-label="Main navigation"
        onKeyDown={handleKeyDown}
      >
        {/* Sliding indicator */}
        <div
          className="absolute top-1 h-[calc(100%-8px)] bg-gradient-to-r from-blue-600/30 to-cyan-600/20 rounded-lg border border-blue-500/30 transition-all duration-300 ease-out pointer-events-none"
          style={indicatorStyle}
        />

        {tabs.map((tab, i) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              ref={(el) => { tabRefs.current[i] = el; }}
              role="tab"
              aria-selected={isActive}
              tabIndex={isActive ? 0 : -1}
              onClick={() => onTabChange(tab.id)}
              className={`relative z-[1] flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-900 ${
                isActive
                  ? 'text-blue-300'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <tab.icon size={14} />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Right: AI button */}
      <button
        onClick={onToggleAI}
        className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl text-xs font-semibold text-white shadow-lg shadow-blue-600/25 hover:shadow-blue-500/35 active:scale-[0.97] transition-all duration-200"
      >
        <Bot size={15} />
        <span className="hidden sm:inline">AI Copilot</span>
      </button>
    </header>
  );
}
