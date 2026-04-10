import React from 'react';
import { DollarSign, TrendingDown, Clock, Zap } from 'lucide-react';

export default function ROIAnalysis({ apiData }) {
  const impact = apiData?.roiAnalysis;

  if (!impact) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <DollarSign size={32} className="mx-auto mb-4 text-zinc-600" />
          <p className="text-zinc-400">Loading ROI analysis...</p>
        </div>
      </div>
    );
  }

  // Calculate annual projections
  const annualCostSaved = (impact.cost_saved_usd || 0) * 250 * 20;
  const annualTimeSaved = (impact.time_saved_hours || 0) * 250 * 20;

  return (
    <div className="space-y-6">
      {/* Main ROI Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <DollarSign size={20} className="text-emerald-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Cost Saved Per Run</p>
              <p className="text-emerald-400 text-2xl font-bold font-[var(--font-mono)]">
                ${impact.cost_saved_usd?.toFixed(0) || 0}
              </p>
              <p className="text-emerald-500/60 text-xs mt-1">
                {impact.cost_saved_percent?.toFixed(1) || 0}% reduction
              </p>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Clock size={20} className="text-blue-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Time Saved Per Run</p>
              <p className="text-blue-400 text-2xl font-bold font-[var(--font-mono)]">
                {impact.time_saved_hours?.toFixed(1) || 0}h
              </p>
              <p className="text-blue-500/60 text-xs mt-1">
                {impact.time_saved_percent?.toFixed(1) || 0}% faster
              </p>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <TrendingDown size={20} className="text-purple-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Annual Cost Savings</p>
              <p className="text-purple-400 text-2xl font-bold font-[var(--font-mono)]">
                ${annualCostSaved.toLocaleString()}
              </p>
              <p className="text-purple-500/60 text-xs mt-1">
                250 commits × 20 developers
              </p>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-amber-500/10 rounded-lg">
              <Zap size={20} className="text-amber-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Annual Time Saved</p>
              <p className="text-amber-400 text-2xl font-bold font-[var(--font-mono)]">
                {Math.round(annualTimeSaved).toLocaleString()}h
              </p>
              <p className="text-amber-500/60 text-xs mt-1">
                ~{Math.round(annualTimeSaved / 2000)} dev-years
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 5-Year ROI Projection */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
          <TrendingDown size={16} className="text-green-400" /> 5-Year ROI Projection
        </h3>
        <p className="text-zinc-500 text-xs mb-6">Cumulative cost savings over time (20 developers)</p>

        <div className="space-y-4">
          {Array.from({ length: 5 }, (_, i) => i + 1).map((year) => {
            const cumulativeSavings = year * annualCostSaved;
            const percentage = (cumulativeSavings / (annualCostSaved * 5)) * 100;

            return (
              <div key={year}>
                <div className="flex justify-between text-xs mb-2">
                  <span className="text-zinc-400 font-medium">Year {year}</span>
                  <span className="text-zinc-400 font-[var(--font-mono)]">
                    ${cumulativeSavings.toLocaleString()}
                  </span>
                </div>
                <div className="w-full bg-zinc-950 rounded-full h-3 border border-zinc-800/60 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-green-600 to-green-400 rounded-full animate-bar-grow"
                    style={{
                      width: `${percentage}%`,
                      animationDelay: `${year * 200}ms`
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Savings Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Breakdown Pie Chart */}
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <DollarSign size={16} className="text-emerald-400" /> Annual Savings Breakdown
          </h3>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-zinc-800/40 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded bg-blue-500"></div>
                <span className="text-zinc-300 text-sm">Compute Costs</span>
              </div>
              <span className="text-white font-bold font-[var(--font-mono)]">
                ${(impact.cost_saved_usd * 0.6).toFixed(0)}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-zinc-800/40 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded bg-orange-500"></div>
                <span className="text-zinc-300 text-sm">Developer Time</span>
              </div>
              <span className="text-white font-bold font-[var(--font-mono)]">
                ${(impact.cost_saved_usd * 0.4).toFixed(0)}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded bg-emerald-500"></div>
                <span className="text-emerald-300 text-sm font-semibold">Total Annual</span>
              </div>
              <span className="text-emerald-400 font-bold font-[var(--font-mono)]">
                ${impact.cost_saved_usd.toFixed(0)}
              </span>
            </div>
          </div>
        </div>

        {/* Detailed Impact Metrics */}
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <Zap size={16} className="text-blue-400" /> Detailed Impact Metrics
          </h3>

          <div className="space-y-3">
            {[
              { label: 'Tests in Optimized Mode', value: impact.tests_run_in_optimized_mode || 0 },
              { label: 'Total Tests Analyzed', value: impact.total_tests || 0 },
              { label: 'Optimized Regression Time', value: `${impact.optimized_regression_hours?.toFixed(2) || 0} hours` },
              { label: 'Original Regression Time', value: `${impact.original_regression_hours?.toFixed(2) || 0} hours` },
              { label: 'Failures Caught in First Pass', value: `${impact.failure_catch_rate_percent?.toFixed(1) || 0}%` },
              { label: 'Cost per Test Hour (AWS)', value: '$0.50' },
              { label: 'Annual Developer Commits', value: '250 (per developer)' },
              { label: 'Developers Affected', value: '20' }
            ].map((metric, index) => (
              <div key={index} className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
                <span className="text-zinc-400 text-sm">{metric.label}</span>
                <span className="text-white font-bold font-[var(--font-mono)] text-sm">
                  {metric.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ROI Summary */}
      <div className="bg-gradient-to-r from-emerald-500/10 to-blue-500/10 border border-emerald-500/20 rounded-xl p-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-emerald-500/10 rounded-xl">
            <DollarSign size={24} className="text-emerald-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-white mb-2">Return on Investment Summary</h3>
            <p className="text-zinc-300 text-sm leading-relaxed">
              SanDisk Optima's AI-driven test prioritization delivers significant cost and time savings.
              By intelligently ordering regression tests based on failure risk prediction, the system reduces
              time-to-first-failure by {impact.time_saved_percent?.toFixed(1) || 0}% while maintaining comprehensive
              test coverage. The projected annual savings of ${annualCostSaved.toLocaleString()} demonstrate
              strong ROI for enterprise-scale RTL verification workflows.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}