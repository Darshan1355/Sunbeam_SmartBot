import React, { useState, useEffect } from 'react';
import { X, Wrench, CheckCircle2, Tag, Terminal, Layers } from 'lucide-react';
import { ToolItem } from '../types/chat';
import { fetchTools } from '../services/api';

interface ToolsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNotify: (type: 'success' | 'error' | 'info', msg: string) => void;
}

export const ToolsModal: React.FC<ToolsModalProps> = ({
  isOpen,
  onClose,
  onNotify,
}) => {
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string>('all');

  useEffect(() => {
    if (isOpen) {
      loadTools();
    }
  }, [isOpen]);

  const loadTools = async () => {
    setLoading(true);
    try {
      const data = await fetchTools();
      setTools(data);
    } catch (err: any) {
      onNotify('error', `Failed to load tools: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const categories = ['all', ...Array.from(new Set(tools.map((t) => t.category)))];
  const filtered = filterCategory === 'all' ? tools : tools.filter((t) => t.category === filterCategory);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-scale-up">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <Wrench className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Registered Agent Tools</h2>
              <p className="text-xs text-slate-400">10 LangChain @tool Decorated Callable Utilities</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category Filter Pills */}
        <div className="px-5 py-2.5 border-b border-slate-800/80 bg-slate-950/40 flex items-center gap-1.5 overflow-x-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                filterCategory === cat
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Tools List */}
        <div className="p-5 overflow-y-auto space-y-3 flex-1">
          {loading ? (
            <div className="text-center py-12 text-xs text-slate-400">Loading registered tools...</div>
          ) : (
            filtered.map((t, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/90 hover:border-slate-700/80 transition-all space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-orange-400">{t.name}</span>
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-[10px] text-slate-300 capitalize font-medium flex items-center gap-1">
                      <Tag className="w-2.5 h-2.5 text-blue-400" /> {t.category}
                    </span>
                  </div>
                  <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Available
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">{t.description}</p>

                {t.parameters && t.parameters.properties && (
                  <div className="pt-1.5 flex items-center gap-2 text-[11px] text-slate-500 font-mono">
                    <Terminal className="w-3 h-3 text-slate-400" />
                    <span>Inputs: {Object.keys(t.parameters.properties).join(', ')}</span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/40 text-center text-[11px] text-slate-500">
          Tools are selected dynamically by the LangGraph agent orchestrator.
        </div>
      </div>
    </div>
  );
};
