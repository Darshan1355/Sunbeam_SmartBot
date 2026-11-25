import React from 'react';
import { Menu, Trash2, Database, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  title: string;
  onToggleSidebar: () => void;
  onClearHistory: () => void;
  onOpenKnowledgeBase: () => void;
  knowledgeStatus?: string;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  onToggleSidebar,
  onClearHistory,
  onOpenKnowledgeBase,
  knowledgeStatus = 'healthy',
}) => {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-4 flex items-center justify-between z-20 shrink-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        <h2 className="text-sm font-semibold text-slate-200 truncate max-w-[200px] sm:max-w-md">
          {title}
        </h2>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onOpenKnowledgeBase}
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-300 transition-colors"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Knowledge Base: Online</span>
        </button>

        <button
          onClick={onClearHistory}
          title="Clear current conversation messages"
          className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
