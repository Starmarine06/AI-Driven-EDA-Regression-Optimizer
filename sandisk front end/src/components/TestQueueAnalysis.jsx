import React from 'react';
import { TrendingDown, Search, X, Filter, ArrowUpDown, ArrowUp, ArrowDown, Download } from 'lucide-react';

export default function TestQueueAnalysis({
  apiData,
  currentTests,
  filteredTests,
  selectedModule,
  setSelectedModule,
  searchQuery,
  setSearchQuery,
  sortConfig,
  handleSort,
  SortIcon
}) {
  const PAGE_SIZE = 25;
  const [page, setPage] = React.useState(1);

  // Reset to page 1 whenever filters change
  React.useEffect(() => { setPage(1); }, [filteredTests.length]);

  const totalPages = Math.ceil(filteredTests.length / PAGE_SIZE);
  const pagedTests = filteredTests.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleExportExcel = () => {
    alert('Export functionality would be implemented here');
  };

  return (
    <div className="space-y-6">
      {/* Queue Statistics */}
      {apiData?.testQueue?.queue_stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-4">
            <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider mb-1">Mean Risk Score</p>
            <p className="text-white text-xl font-bold font-[var(--font-mono)]">
              {apiData.testQueue.queue_stats.mean_risk?.toFixed(2)}
            </p>
          </div>
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-4">
            <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider mb-1">Median Risk Score</p>
            <p className="text-white text-xl font-bold font-[var(--font-mono)]">
              {apiData.testQueue.queue_stats.median_risk?.toFixed(2)}
            </p>
          </div>
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-4">
            <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider mb-1">Max Risk Score</p>
            <p className="text-red-400 text-xl font-bold font-[var(--font-mono)]">
              {apiData.testQueue.queue_stats.max_risk?.toFixed(2)}
            </p>
          </div>
          <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-4">
            <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider mb-1">Min Risk Score</p>
            <p className="text-emerald-400 text-xl font-bold font-[var(--font-mono)]">
              {apiData.testQueue.queue_stats.min_risk?.toFixed(2)}
            </p>
          </div>
        </div>
      )}

      {/* Failure Probability by Risk Quartile Chart */}
      {apiData?.testQueue?.failure_by_quartile && (
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <TrendingDown size={16} className="text-blue-400" /> Failure Probability by Risk Quartile
          </h3>
          <div className="space-y-4">
            {apiData.testQueue.failure_by_quartile.map((quartile, index) => (
              <div key={index}>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-zinc-400 font-medium">{quartile.risk_quartile}</span>
                  <span className="text-zinc-400 font-[var(--font-mono)]">
                    {quartile.mean?.toFixed(3)} avg failure prob
                  </span>
                </div>
                <div className="w-full bg-zinc-950 rounded-full h-3 border border-zinc-800/60 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full animate-bar-grow"
                    style={{ width: `${(quartile.mean || 0) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Test Priority Queue Table */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 border-b border-zinc-800/60">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <TrendingDown size={15} className="text-red-400" /> Test Priority Queue
            </h3>
            {selectedModule && (
              <span className="flex items-center gap-1.5 bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-1 rounded-full text-[10px] font-semibold animate-fade-in">
                <Filter size={10} /> {selectedModule}
                <button onClick={() => setSelectedModule(null)} className="hover:text-white transition-colors ml-0.5">
                  <X size={10} />
                </button>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportExcel}
              className="flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1.5 rounded-lg text-[10px] font-semibold hover:bg-emerald-500/20 hover:border-emerald-500/30 transition-all"
            >
              <Download size={11} /> Export XLSX
            </button>
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                placeholder="Search tests…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full sm:w-52 bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-300 focus:outline-none focus:border-red-500/60 focus:ring-1 focus:ring-red-500/30 transition-all placeholder:text-zinc-600"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors">
                  <X size={12} />
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900/90 text-zinc-500 sticky top-0 z-10 backdrop-blur-md border-b border-zinc-800/80">
              <tr>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider">#</th>
                {[
                  { key: 'commit_id', label: 'Commit ID', align: 'text-left' },
                  { key: 'modules_affected', label: 'Modules Affected', align: 'text-left' },
                  { key: 'risk_score', label: 'Risk Score', align: 'text-right' },
                  { key: 'predicted_failure_probability', label: 'Failure Prob', align: 'text-right' },
                  { key: 'code_churn_ratio', label: 'Code Churn', align: 'text-right' },
                  { key: 'regression_time_hours', label: 'Test Time (h)', align: 'text-right' },
                ].map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort({ key: col.key, direction: sortConfig.direction === 'asc' ? 'desc' : 'asc' })}
                    className={`px-4 py-3 font-semibold text-[10px] uppercase tracking-wider ${col.align} cursor-pointer select-none group hover:text-zinc-300 transition-colors`}
                  >
                    <span className="inline-flex items-center gap-1.5">
                      {col.label}
                      <SortIcon column={col.key} />
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/30">
              {filteredTests.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-zinc-600">
                    <Search size={20} className="mx-auto mb-2 opacity-30" />
                    No tests match this selection.
                  </td>
                </tr>
              ) : pagedTests.map((test, idx) => {
                const globalIdx = (page - 1) * PAGE_SIZE + idx;
                return (
                  <tr
                    key={test.commit_id || idx}
                    className="table-row-interactive group"
                    style={{ animationDelay: `${idx * 20}ms` }}
                  >
                    <td className="px-4 py-2.5 text-zinc-600 font-[var(--font-mono)] text-[10px]">
                      {String(globalIdx + 1).padStart(2, '0')}
                    </td>
                    <td className="px-4 py-2.5 font-[var(--font-mono)] text-zinc-300 text-[11px]">
                      <div className="flex items-center gap-2">
                        {globalIdx < 3 && !selectedModule && (
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.8)]" />
                        )}
                        {test.commit_id || `TEST_${idx}`}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-zinc-400 font-medium text-[11px]">
                      {test.modules_affected || 'N/A'}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <RiskBadge risk={(test.risk_score || 0) / 100} />
                    </td>
                    <td className="px-4 py-2.5 text-right font-[var(--font-mono)] font-bold text-zinc-300 text-[11px]">
                      {((test.predicted_failure_probability || 0) * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-2.5 text-right font-[var(--font-mono)] font-bold text-zinc-300 text-[11px]">
                      {(test.code_churn_ratio || 0).toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-[var(--font-mono)] font-bold text-zinc-300 text-[11px]">
                      {test.regression_time_hours || 0}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-3 flex items-center justify-between text-[10px] text-zinc-600 font-medium px-4 pb-4">
          <span>Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filteredTests.length)} of {filteredTests.length} tests</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-zinc-400 hover:text-white"
            >← Prev</button>
            <span className="text-zinc-500">{page} / {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-zinc-400 hover:text-white"
            >Next →</button>
          </div>
          <span className="flex items-center gap-1.5">
            Sorted by <span className="text-zinc-400 font-semibold">{sortConfig.key}</span>
            {sortConfig.direction === 'asc' ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
          </span>
        </div>
      </div>
    </div>
  );
}

// RiskBadge component
function RiskBadge({ risk }) {
  const riskLevel = risk > 0.7 ? 'HIGH' : risk > 0.4 ? 'MEDIUM' : 'LOW';
  const colors = {
    HIGH: 'bg-red-500/10 text-red-400 border-red-500/20',
    MEDIUM: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    LOW: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  };

  return (
    <span className={`chip-status ${colors[riskLevel]}`}>
      {(risk * 100).toFixed(1)}
    </span>
  );
}