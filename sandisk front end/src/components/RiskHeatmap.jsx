import React from 'react';
import { CircuitBoard, X, Database, AlertTriangle, Search } from 'lucide-react';

export default function RiskHeatmap({
  activeModules,
  selectedModule,
  setSelectedModule,
  hoveredModule,
  setHoveredModule,
  apiData
}) {
  // Mock activeFailures for demo - in real app this would come from props or context
  const activeFailures = [];

  // interactive filters/search
  const [searchText, setSearchText] = React.useState('');

  const filteredModules = React.useMemo(() => {
    if (!searchText) return activeModules;
    return activeModules.filter(mod =>
      (mod.name || mod.module).toLowerCase().includes(searchText.toLowerCase())
    );
  }, [activeModules, searchText]);

  return (
    <div className="space-y-6">
      {/* Module Risk Heatmap */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <CircuitBoard size={15} className="text-red-400" /> RTL Module Risk Heatmap
          </h3>
          {selectedModule && (
            <button
              onClick={() => setSelectedModule(null)}
              className="text-[10px] uppercase font-bold tracking-wider flex items-center gap-1 text-zinc-400 hover:text-white bg-zinc-800 px-2 py-1 rounded-md transition-all border border-zinc-700 hover:border-zinc-600 hover:bg-zinc-700"
            >
              Clear <X size={10} />
            </button>
          )}
        </div>
        <p className="text-[10px] text-zinc-600 mb-2 font-[var(--font-mono)] tracking-wider">
          RISK-WEIGHTED RTL SUBSYSTEM VIEW — CLICK MODULES FOR DETAILS
        </p>

        {/* search */}
        <div className="flex items-center gap-2 mb-4">
          <Search size={14} className="text-zinc-400" />
          <input
            type="text"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="Search modules..."
            className="bg-zinc-800/30 text-zinc-200 placeholder-zinc-500 rounded px-2 py-1 text-xs w-48"
          />
        </div>

        {/* SoC Floorplan Layout */}
        <div className="relative w-full max-w-4xl mx-auto">
          {/* SoC Die Background */}
          <div className="relative bg-gradient-to-br from-zinc-800 to-zinc-900 border-2 border-zinc-700 rounded-2xl p-8 shadow-2xl">
            {/* Module Grid */}
            <div className="grid grid-cols-6 gap-2 h-96">
              {filteredModules.map((mod) => {
                const riskPct = (mod.risk || mod.avg_risk_score / 100) * 100;
                const failureCount = (activeFailures || []).filter(f => {
                  const parts = f.testId.split('_');
                  const modKey = parts.slice(1, -1).join('_').toLowerCase();
                  return modKey === (mod.id || mod.module);
                }).length;

                // Continuous heat gradient
                const heatColor = riskPct > 70
                  ? `rgba(239, 68, 68, ${0.15 + (mod.risk || mod.avg_risk_score / 100) * 0.5})`
                  : riskPct > 40
                    ? `rgba(245, 158, 11, ${0.1 + (mod.risk || mod.avg_risk_score / 100) * 0.35})`
                    : `rgba(16, 185, 129, ${0.05 + (mod.risk || mod.avg_risk_score / 100) * 0.2})`;

                const borderHeat = riskPct > 70
                  ? `rgba(239, 68, 68, ${selectedModule === (mod.id || mod.module) || hoveredModule === (mod.id || mod.module) ? 0.9 : 0.5})`
                  : riskPct > 40
                    ? `rgba(245, 158, 11, ${selectedModule === (mod.id || mod.module) || hoveredModule === (mod.id || mod.module) ? 0.8 : 0.35})`
                    : `rgba(16, 185, 129, ${selectedModule === (mod.id || mod.module) || hoveredModule === (mod.id || mod.module) ? 0.6 : 0.2})`;

                const textHeat = riskPct > 70 ? '#fca5a5' : riskPct > 40 ? '#fcd34d' : 'rgba(110,231,183,0.8)';

                return (
                  <button
                    key={mod.id || mod.module}
                    onClick={() => setSelectedModule(selectedModule === (mod.id || mod.module) ? null : (mod.id || mod.module))}
                    onMouseEnter={() => setHoveredModule(mod.id || mod.module)}
                    onMouseLeave={() => setHoveredModule(null)}
                    className="relative rounded-lg border p-2 text-left transition-all duration-300 ease-out outline-none overflow-hidden group"
                    style={{
                      background: heatColor,
                      borderColor: borderHeat,
                      opacity: selectedModule && selectedModule !== (mod.id || mod.module) ? 0.2 : 1,
                      filter: selectedModule && selectedModule !== (mod.id || mod.module) ? 'grayscale(0.8)' : 'none',
                      transform: selectedModule === (mod.id || mod.module) ? 'scale(1.03)' : hoveredModule === (mod.id || mod.module) ? 'scale(1.01)' : 'scale(1)',
                      boxShadow: selectedModule === (mod.id || mod.module)
                        ? `0 0 15px rgba(0,0,0,0.5), inset 0 0 15px ${riskPct > 70 ? 'rgba(220,38,38,0.15)' : 'transparent'}`
                        : riskPct > 70 ? 'inset 0 0 20px rgba(220,38,38,0.1)' : 'none',
                    }}
                  >
                    {/* Pulse overlay for critical */}
                    {riskPct > 70 && (
                      <div className="absolute inset-0 rounded-lg border border-red-500/30" style={{ animation: 'pulseGlow 2s ease-in-out infinite' }} />
                    )}

                    {/* Top row: group + risk pill */}
                    <div className="flex items-center justify-between mb-1 relative z-10">
                      <span className="text-[7px] uppercase tracking-[0.15em] font-[var(--font-mono)] font-bold opacity-50" style={{ color: textHeat }}>
                        {mod.group || 'Unknown'}
                      </span>
                      <span
                        className="text-[8px] font-[var(--font-mono)] font-bold px-1.5 py-0.5 rounded bg-black/50 border border-white/10"
                        style={{ color: textHeat }}
                      >
                        {riskPct.toFixed(0)}%
                      </span>
                    </div>

                    {/* Module name */}
                    <p className="text-[10px] font-bold tracking-tight leading-tight relative z-10" style={{ color: textHeat }}>
                      {mod.name || mod.module}
                    </p>

                    {/* Bottom: LOC + failures */}
                    <div className="flex items-center justify-between mt-1.5 relative z-10">
                      <span className="text-[7px] font-[var(--font-mono)] opacity-40" style={{ color: textHeat }}>
                        {Math.round((mod.loc || 10000) / 1000)}K LOC
                      </span>
                      {failureCount > 0 && (
                        <span className="text-[7px] font-[var(--font-mono)] font-bold bg-red-500/20 text-red-400 border border-red-500/30 px-1 py-0.5 rounded">
                          {failureCount} fail{failureCount > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>

                    {/* Heat bar at bottom */}
                    <div className="absolute bottom-0 left-0 right-0 h-1 overflow-hidden rounded-b-lg">
                      <div
                        className="h-full rounded-b-lg animate-bar-grow"
                        style={{
                          width: `${riskPct}%`,
                          background: riskPct > 70 ? '#ef4444' : riskPct > 40 ? '#f59e0b' : '#10b981',
                          animationDelay: '0.3s',
                        }}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-3 pt-2 border-t border-zinc-800/50 mt-2">
            <span className="text-[8px] text-zinc-600 font-semibold uppercase tracking-wider">Risk</span>
            <div className="flex items-center gap-1">
              <div className="w-3 h-2 rounded-sm bg-emerald-500/40" />
              <span className="text-[7px] text-zinc-600">Low</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-2 rounded-sm bg-amber-500/50" />
              <span className="text-[7px] text-zinc-600">Med</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-2 rounded-sm bg-red-500/60" />
              <span className="text-[7px] text-zinc-600">High</span>
            </div>
          </div>
        </div>

        {/* Hovered module detail */}
        {hoveredModule && (
          <div className="mt-3 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-xs animate-fade-in">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-white">{activeModules.find(m => (m.id || m.module) === hoveredModule)?.name || hoveredModule}</span>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold font-[var(--font-mono)] border ${(() => {
                const risk = activeModules.find(m => (m.id || m.module) === hoveredModule)?.risk || 0;
                return risk > 0.7 ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                  risk > 0.4 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                    'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
              })()
                }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${(() => {
                  const risk = activeModules.find(m => (m.id || m.module) === hoveredModule)?.risk || 0;
                  return risk > 0.7 ? 'bg-red-400' : risk > 0.4 ? 'bg-amber-400' : 'bg-emerald-400';
                })()
                  } ${(() => {
                    const risk = activeModules.find(m => (m.id || m.module) === hoveredModule)?.risk || 0;
                    return risk > 0.7 ? 'animate-pulse' : '';
                  })()}`} />
                {(() => {
                  const risk = activeModules.find(m => (m.id || m.module) === hoveredModule)?.risk || 0;
                  return (risk * 100).toFixed(1);
                })()}%
              </span>
            </div>
            <p className="text-zinc-500 mt-1 font-[var(--font-mono)] text-[10px]">
              {(activeModules.find(m => (m.id || m.module) === hoveredModule)?.loc || 0).toLocaleString()} Lines of Code
            </p>
          </div>
        )}
      </div>

      {/* Module Details Table */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Database size={15} className="text-blue-400" /> Module Risk Details
          </h3>
          <div className="text-[10px] text-zinc-500 font-medium">
            {filteredModules.length} of {activeModules.length} modules shown
          </div>
        </div>

        <div className="overflow-auto border border-zinc-800/60 rounded-xl bg-zinc-950/80">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-900/90 text-zinc-500 sticky top-0 z-10 backdrop-blur-md border-b border-zinc-800/80">
              <tr>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider">Module</th>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider">Group</th>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider text-center">Risk Score</th>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider text-center">Lines of Code</th>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider text-center">Avg Failure Prob</th>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider text-center">Commit Count</th>
                <th className="px-4 py-3 font-semibold text-[10px] uppercase tracking-wider">Risk Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/30">
              {filteredModules
                .sort((a, b) => (b.risk || b.avg_risk_score / 100) - (a.risk || a.avg_risk_score / 100))
                .map((mod) => {
                  const riskScore = mod.risk || mod.avg_risk_score / 100;
                  const riskLevel = riskScore > 0.7 ? 'HIGH' : riskScore > 0.4 ? 'MEDIUM' : 'LOW';
                  const riskColors = {
                    HIGH: 'bg-red-500/10 text-red-400 border-red-500/20',
                    MEDIUM: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
                    LOW: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  };

                  return (
                    <tr key={mod.id || mod.module} className="table-row-interactive group">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full ${riskScore > 0.7 ? 'bg-red-400 animate-pulse' : riskScore > 0.4 ? 'bg-amber-400' : 'bg-emerald-400'
                            }`} />
                          <span className="font-bold text-zinc-200 text-[11px]">{mod.name || mod.module}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="text-zinc-400 font-medium text-[11px]">{mod.group || 'Unknown'}</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="font-[var(--font-mono)] font-bold text-zinc-200 text-[11px]">{(riskScore * 100).toFixed(1)}%</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="font-[var(--font-mono)] text-zinc-400 text-[11px]">{(mod.loc || 0).toLocaleString()}</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="font-[var(--font-mono)] text-zinc-400 text-[11px]">{((mod.avgFailureProb || mod.failure_probability || 0) * 100).toFixed(2)}%</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="font-[var(--font-mono)] text-zinc-400 text-[11px]">{mod.commitCount || mod.commit_count || 0}</span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`chip-status ${riskColors[riskLevel]}`}>
                          {riskLevel}
                        </span>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
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