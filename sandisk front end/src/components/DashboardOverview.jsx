import React from 'react';
import { Activity, AlertTriangle, Clock, DollarSign, TrendingDown, CheckCircle, XCircle, Gauge, Timer, Zap } from 'lucide-react';

// Assuming KpiCard is defined elsewhere in the app
// If not, you'll need to import it or define it here

export default function DashboardOverview({
  apiData,
  currentTests,
  avgRisk,
  highRiskTests,
  baselineCost,
  costSaved,
  reductionPct,
  sparkRisk,
  sparkCost,
  sparkSavings
}) {
  return (
    <div className="space-y-8">
      {/* ──── KPI CARDS ──── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Avg Failure Prob"
          value={parseFloat((avgRisk * 100).toFixed(1))}
          suffix="%"
          icon={Activity}
          iconBg="bg-zinc-800"
          iconColor="text-zinc-400"
          sparkData={sparkRisk.map(v => v * 100)}
          delay={50}
        />
        <KpiCard
          label="High-Risk Tests"
          value={highRiskTests}
          suffix={`/ ${currentTests.length}`}
          icon={AlertTriangle}
          iconBg="bg-red-500/10"
          iconColor="text-red-400"
          accentColor="text-red-400"
          sparkData={[3, 5, 4, 7, 6, 8, highRiskTests]}
          delay={100}
        />
        <KpiCard
          label="Baseline Compute"
          value={parseFloat(baselineCost.toFixed(0))}
          prefix="$"
          icon={Clock}
          iconBg="bg-zinc-800"
          iconColor="text-zinc-400"
          sparkData={sparkCost}
          delay={150}
        />
        <KpiCard
          label="Projected Savings"
          value={parseFloat(costSaved.toFixed(0))}
          prefix="+$"
          icon={DollarSign}
          iconBg="bg-emerald-500/10"
          iconColor="text-emerald-400"
          accentColor="text-emerald-400"
          sparkData={sparkSavings}
          delay={200}
        >
          <p className="text-[10px] text-emerald-500/60 mt-1 font-semibold">{reductionPct.toFixed(0)}% TTFF reduction</p>
        </KpiCard>
      </div>

      {/* ──── CHARTS AND METRICS ──── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity Chart */}
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <Activity size={16} className="text-blue-400" /> Recent Verification Activity
          </h3>
          {apiData?.overview ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
                <span className="text-zinc-400">Total Commits Analyzed</span>
                <span className="text-white font-bold font-[var(--font-mono)]">{apiData.overview.total_commits}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
                <span className="text-zinc-400">Recent Commits</span>
                <span className="text-white font-bold font-[var(--font-mono)]">{apiData.overview.recent_commits}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
                <span className="text-zinc-400">Failure Rate</span>
                <span className="text-red-400 font-bold font-[var(--font-mono)]">{apiData.overview.failure_rate?.toFixed(1)}%</span>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-500">
              <Activity size={32} className="mx-auto mb-2 opacity-30" />
              <p>Loading activity data...</p>
            </div>
          )}
        </div>

        {/* Risk Distribution */}
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <AlertTriangle size={16} className="text-amber-400" /> Risk Distribution
          </h3>
          {apiData?.overview?.risk_distribution ? (
            <div className="space-y-3">
              {Object.entries(apiData.overview.risk_distribution).map(([level, count]) => (
                <div key={level} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${
                      level === 'High' ? 'bg-red-500' :
                      level === 'Medium' ? 'bg-amber-500' : 'bg-emerald-500'
                    }`} />
                    <span className="text-zinc-400 text-sm">{level} Risk</span>
                  </div>
                  <span className="text-white font-bold font-[var(--font-mono)]">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-500">
              <AlertTriangle size={32} className="mx-auto mb-2 opacity-30" />
              <p>Loading risk data...</p>
            </div>
          )}
        </div>
      </div>

      {/* ──── TTFF ANALYSIS ──── */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-6">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Timer size={15} className="text-emerald-400" /> Compute Time-to-First-Failure (TTFF)
            </h3>
            <p className="text-xs text-zinc-500 mt-1">Standard FIFO queue vs. AI-optimized priority queue.</p>
          </div>
          <div className="mt-3 md:mt-0 px-4 py-2 bg-zinc-800/40 border border-zinc-700/40 rounded-lg text-[10px] text-zinc-400 font-medium flex items-center gap-2">
            <Gauge size={12} className="text-zinc-500" />
            SanDisk Goal: <span className="text-white font-semibold">80% bugs found in 20% runtime</span>
          </div>
        </div>

        <div className="space-y-6">
          {/* Baseline */}
          <div>
            <div className="flex justify-between text-xs mb-2">
              <span className="text-zinc-400 font-medium flex items-center gap-2">
                <XCircle size={14} className="text-zinc-600" /> Baseline Regression (Run All)
              </span>
              <span className="text-zinc-400 font-[var(--font-mono)] font-bold">
                {Math.round((currentTests.length * 60) / 60).toFixed(1)}h
              </span>
            </div>
            <div className="w-full bg-zinc-950 rounded-full h-4 border border-zinc-800/60 flex overflow-hidden p-0.5 relative">
              <div
                className="bg-gradient-to-r from-zinc-700 to-zinc-600 h-full rounded-full animate-bar-grow relative"
                style={{ width: '65%', animationDelay: '0.5s' }}
              >
                <div className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-r from-transparent to-zinc-600" />
              </div>
            </div>
          </div>

          {/* Optimized */}
          <div>
            <div className="flex justify-between text-xs mb-2">
              <span className="text-white font-semibold flex items-center gap-2">
                <CheckCircle size={14} className="text-emerald-500" /> CoreOptima AI (Smart Order)
              </span>
              <span className="text-emerald-400 font-[var(--font-mono)] font-extrabold text-base">
                {Math.round((currentTests.length * 60 * 0.08) / 60).toFixed(1)}h
              </span>
            </div>
            <div className="w-full bg-zinc-950 rounded-full h-4 border border-zinc-800/60 flex overflow-hidden p-0.5 relative">
              <div
                className="bg-gradient-to-r from-emerald-600 to-emerald-400 h-full rounded-full animate-bar-grow relative"
                style={{ width: '8%', animationDelay: '0.8s' }}
              >
                <div className="absolute inset-0 bg-white/10 animate-pulse rounded-full" />
              </div>
            </div>
          </div>

          {/* Summary stats row */}
          <div className="flex flex-wrap items-center gap-4 pt-4 border-t border-zinc-800/50">
            <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/5 border border-emerald-500/15 rounded-lg">
              <Zap size={14} className="text-emerald-400" />
              <div>
                <p className="text-[10px] text-emerald-500/70 font-semibold uppercase tracking-wider">Time Saved</p>
                <p className="text-sm font-bold text-emerald-400 font-[var(--font-mono)]">
                  {Math.round((currentTests.length * 60 * 0.92) / 60).toFixed(1)}h
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/5 border border-emerald-500/15 rounded-lg">
              <TrendingDown size={14} className="text-emerald-400" />
              <div>
                <p className="text-[10px] text-emerald-500/70 font-semibold uppercase tracking-wider">TTFF Reduction</p>
                <p className="text-sm font-bold text-emerald-400 font-[var(--font-mono)]">{reductionPct.toFixed(1)}%</p>
              </div>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/5 border border-emerald-500/15 rounded-lg">
              <DollarSign size={14} className="text-emerald-400" />
              <div>
                <p className="text-[10px] text-emerald-500/70 font-semibold uppercase tracking-wider">Cost Efficiency</p>
                <p className="text-sm font-bold text-emerald-400 font-[var(--font-mono)]">${Math.round(costSaved)}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// KpiCard component (assuming it's not imported)
function KpiCard({ label, value, prefix = '', suffix = '', icon: Icon, iconBg, iconColor, accentColor, sparkData, delay = 0, children }) {
  return (
    <div
      className={`bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-4 relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-300 ${accentColor ? 'hover:shadow-lg' : ''}`}
      style={{
        animationDelay: `${delay}ms`,
        boxShadow: accentColor ? `0 0 20px rgba(239, 68, 68, 0.05)` : undefined
      }}
    >
      {/* Glow effect for accent cards */}
      {accentColor && (
        <div className="absolute inset-0 bg-gradient-to-br from-red-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      )}

      <div className="flex items-center justify-between mb-3 relative z-10">
        <div className={`p-2 rounded-lg ${iconBg}`}>
          <Icon size={16} className={iconColor} />
        </div>
        <div className="flex items-center gap-1">
          {sparkData && sparkData.length > 1 && (
            <div className="flex items-end gap-0.5 h-4">
              {sparkData.slice(-7).map((val, i) => (
                <div
                  key={i}
                  className={`w-0.5 rounded-full transition-all duration-300 ${
                    i === sparkData.slice(-7).length - 1
                      ? accentColor || 'bg-zinc-400'
                      : 'bg-zinc-600'
                  }`}
                  style={{
                    height: `${(val / Math.max(...sparkData)) * 100}%`,
                    animationDelay: `${delay + i * 50}ms`
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="relative z-10">
        <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
        <p className={`text-2xl font-bold font-[var(--font-mono)] ${accentColor || 'text-white'}`}>
          {prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}
        </p>
        {children}
      </div>
    </div>
  );
}