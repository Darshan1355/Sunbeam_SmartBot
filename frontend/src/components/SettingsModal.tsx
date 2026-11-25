import React, { useState, useEffect } from 'react';
import { X, Settings, Moon, Sun, Trash2, Cpu, Info, ShieldCheck } from 'lucide-react';
import { fetchConfig } from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onClearAllChats: () => void;
  onNotify: (type: 'success' | 'error' | 'info', msg: string) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onClearAllChats,
  onNotify,
}) => {
  const [config, setConfig] = useState<any>(null);
  const [isDark, setIsDark] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  const loadConfig = async () => {
    try {
      const data = await fetchConfig();
      setConfig(data);
    } catch (e: any) {
      onNotify('error', 'Could not load server config');
    }
  };

  const toggleTheme = () => {
    setIsDark(!isDark);
    if (!isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    onNotify('info', `Switched to ${!isDark ? 'Dark' : 'Light'} mode`);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-scale-up">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-slate-800 text-slate-300">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Settings & Preferences</h2>
              <p className="text-xs text-slate-400">Configure client behavior and view system info</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-5">
          {/* Theme setting */}
          <div className="flex items-center justify-between p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl">
            <div className="flex items-center gap-3">
              {isDark ? <Moon className="w-4 h-4 text-orange-400" /> : <Sun className="w-4 h-4 text-amber-400" />}
              <div>
                <p className="text-xs font-semibold text-slate-200">Appearance</p>
                <p className="text-[11px] text-slate-400">Currently using Dark theme</p>
              </div>
            </div>
            <button
              onClick={toggleTheme}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors"
            >
              Toggle {isDark ? 'Light' : 'Dark'}
            </button>
          </div>

          {/* Model info */}
          <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-orange-400" />
              <p className="text-xs font-semibold text-slate-200">Active AI Model</p>
            </div>
            <div className="p-2.5 bg-slate-900 border border-slate-800/80 rounded-lg flex items-center justify-between font-mono text-xs">
              <span className="text-orange-300">{config?.groq_model || 'openai/gpt-oss-120b'}</span>
              <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-emerald-400">Groq API</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Low-latency inference orchestrated through LangGraph with strict anti-hallucination guardrails.
            </p>
          </div>

          {/* Chat options */}
          <div className="flex items-center justify-between p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl">
            <div>
              <p className="text-xs font-semibold text-slate-200">Auto-Scroll</p>
              <p className="text-[11px] text-slate-400">Automatically scroll to newest token</p>
            </div>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="w-4 h-4 accent-orange-500 rounded"
            />
          </div>

          {/* Danger zone: Clear all */}
          <div className="p-3.5 bg-rose-950/20 border border-rose-900/40 rounded-xl flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-rose-200">Clear All Conversations</p>
              <p className="text-[11px] text-rose-300/70">Permanently delete all chat threads</p>
            </div>
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to delete all conversations?')) {
                  onClearAllChats();
                  onClose();
                }
              }}
              className="px-3 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-900 text-xs font-medium text-rose-100 transition-colors flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear All</span>
            </button>
          </div>
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between text-[11px] text-slate-500">
          <span>Sunbeam SmartBot v1.0.0</span>
          <span className="flex items-center gap-1 text-emerald-400 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" /> Secure • No keys exposed
          </span>
        </div>
      </div>
    </div>
  );
};
