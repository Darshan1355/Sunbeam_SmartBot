import React, { useState, useEffect } from 'react';
import { X, Database, RefreshCw, Search, CheckCircle2, AlertCircle, FileText, HardDrive } from 'lucide-react';
import { KnowledgeStats } from '../types/chat';
import { fetchKnowledgeStats, updateKnowledgeBase, searchKnowledgeBase } from '../services/api';

interface KnowledgeBaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNotify: (type: 'success' | 'error' | 'info', msg: string) => void;
}

export const KnowledgeBaseModal: React.FC<KnowledgeBaseModalProps> = ({
  isOpen,
  onClose,
  onNotify,
}) => {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadStats();
    }
  }, [isOpen]);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await fetchKnowledgeStats();
      setStats(data);
    } catch (err: any) {
      onNotify('error', `Failed to load stats: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (force: boolean) => {
    setUpdating(true);
    try {
      const res = await updateKnowledgeBase(force);
      onNotify('success', `Knowledge base updated! ${res.new_chunks_added} chunks added, ${res.duplicates_skipped} duplicates skipped.`);
      await loadStats();
    } catch (err: any) {
      onNotify('error', `Update failed: ${err.message}`);
    } finally {
      setUpdating(false);
    }
  };

  const handleTestSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await searchKnowledgeBase(searchQuery.trim(), 3);
      setSearchResults(res.results || []);
    } catch (err: any) {
      onNotify('error', `Search error: ${err.message}`);
    } finally {
      setSearching(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-scale-up">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-orange-500/10 text-orange-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Knowledge Base Dashboard</h2>
              <p className="text-xs text-slate-400">ChromaDB Vector Store & Source Documents</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-5 flex-1">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <p className="text-[11px] text-slate-400 font-medium">Collection</p>
              <p className="text-sm font-bold text-slate-100 font-mono mt-0.5">{stats?.collection_name || 'langchain'}</p>
            </div>
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <p className="text-[11px] text-slate-400 font-medium">Total Chunks</p>
              <p className="text-sm font-bold text-orange-400 font-mono mt-0.5">{stats?.total_documents ?? 15}</p>
            </div>
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <p className="text-[11px] text-slate-400 font-medium">Embedding Dim</p>
              <p className="text-sm font-bold text-slate-100 font-mono mt-0.5">{stats?.dimension ?? 384}</p>
            </div>
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <p className="text-[11px] text-slate-400 font-medium">Status</p>
              <p className="text-xs font-semibold text-emerald-400 flex items-center gap-1 mt-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
              </p>
            </div>
          </div>

          {/* Sources Breakdown */}
          <div>
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-orange-400" /> Indexed Data Sources
            </h3>
            <div className="space-y-1.5">
              {stats?.sources_breakdown && Object.keys(stats.sources_breakdown).length > 0 ? (
                Object.entries(stats.sources_breakdown).map(([src, count], idx) => (
                  <div key={idx} className="flex items-center justify-between p-2.5 bg-slate-950/40 border border-slate-800/80 rounded-xl text-xs">
                    <span className="font-mono text-slate-300">{src}</span>
                    <span className="px-2 py-0.5 bg-slate-800 text-orange-400 font-mono rounded text-[11px] font-semibold">
                      {count} chunks
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-slate-500 py-2">No source breakdown available.</div>
              )}
            </div>
          </div>

          {/* Search Testing Interface */}
          <div>
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Search className="w-3.5 h-3.5 text-blue-400" /> Vector Search Testing
            </h3>
            <form onSubmit={handleTestSearch} className="flex gap-2">
              <input
                type="text"
                placeholder="Test query (e.g., Core Java fees, Hinjawadi hostel, AI internship)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-orange-500"
              />
              <button
                type="submit"
                disabled={searching || !searchQuery.trim()}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5"
              >
                {searching ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                <span>Test</span>
              </button>
            </form>

            {searchResults.length > 0 && (
              <div className="mt-3 space-y-2 max-h-48 overflow-y-auto">
                {searchResults.map((res, i) => (
                  <div key={i} className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl text-xs space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="font-mono text-orange-400">{res.source}</span>
                      <span className="text-emerald-400 font-mono">Score: {res.relevance_score}</span>
                    </div>
                    <p className="text-slate-300 line-clamp-2">{res.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between">
          <p className="text-[11px] text-slate-500">Persistent ChromaDB storage</p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleUpdate(false)}
              disabled={updating}
              className="px-3.5 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${updating ? 'animate-spin' : ''}`} />
              <span>{updating ? 'Updating...' : 'Incremental Update'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
