import React from 'react';
import { Lightbulb, TrendingUp, BarChart3 } from 'lucide-react';

export default function ModelInsights({ apiData }) {
  const metadata = apiData?.modelInsights;

  if (!metadata) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Lightbulb size={32} className="mx-auto mb-4 text-zinc-600" />
          <p className="text-zinc-400">Loading model insights...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Model Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <BarChart3 size={20} className="text-blue-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider">Model Type</p>
              <p className="text-white text-lg font-bold">XGBoost</p>
            </div>
          </div>
          <p className="text-zinc-600 text-xs">Classifier with {metadata.n_estimators || 'N/A'} estimators</p>
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <TrendingUp size={20} className="text-emerald-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider">ROC-AUC Score</p>
              <p className="text-emerald-400 text-2xl font-bold font-[var(--font-mono)]">
                {metadata.roc_auc_score?.toFixed(4) || 'N/A'}
              </p>
            </div>
          </div>
          <p className="text-zinc-600 text-xs">Area under ROC curve</p>
        </div>

        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-amber-500/10 rounded-lg">
              <Lightbulb size={20} className="text-amber-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs font-medium uppercase tracking-wider">F1 Score</p>
              <p className="text-amber-400 text-2xl font-bold font-[var(--font-mono)]">
                {metadata.f1_score?.toFixed(4) || 'N/A'}
              </p>
            </div>
          </div>
          <p className="text-zinc-600 text-xs">Harmonic mean of precision and recall</p>
        </div>
      </div>

      {/* Training Configuration */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
          <Lightbulb size={16} className="text-purple-400" /> Training Configuration
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
              <span className="text-zinc-400 text-sm">Training Samples</span>
              <span className="text-white font-bold font-[var(--font-mono)]">{metadata.training_samples || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
              <span className="text-zinc-400 text-sm">Test Samples</span>
              <span className="text-white font-bold font-[var(--font-mono)]">{metadata.test_samples || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
              <span className="text-zinc-400 text-sm">Algorithm</span>
              <span className="text-white font-bold font-[var(--font-mono)]">{metadata.model_type || 'N/A'}</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
              <span className="text-zinc-400 text-sm">Estimators</span>
              <span className="text-white font-bold font-[var(--font-mono)]">{metadata.n_estimators || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
              <span className="text-zinc-400 text-sm">Max Depth</span>
              <span className="text-white font-bold font-[var(--font-mono)]">{metadata.max_depth || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-zinc-800/40 rounded-lg">
              <span className="text-zinc-400 text-sm">Trained</span>
              <span className="text-white font-bold font-[var(--font-mono)] text-xs">{metadata.timestamp || 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Importance */}
      {metadata.feature_importance && (
        <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
          <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
            <BarChart3 size={16} className="text-blue-400" /> Feature Importance Ranking
          </h3>
          <p className="text-zinc-500 text-xs mb-6">Top features contributing to failure prediction</p>

          <div className="space-y-3">
            {metadata.feature_importance
              .sort((a, b) => b.importance - a.importance)
              .slice(0, 15)
              .map((feature, index) => (
                <div key={feature.feature}>
                  <div className="flex justify-between text-xs mb-2">
                    <span className="text-zinc-400 font-medium">{feature.feature}</span>
                    <span className="text-zinc-400 font-[var(--font-mono)]">
                      {feature.importance.toFixed(4)}
                    </span>
                  </div>
                  <div className="w-full bg-zinc-950 rounded-full h-2 border border-zinc-800/60 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full animate-bar-grow"
                      style={{
                        width: `${(feature.importance / Math.max(...metadata.feature_importance.map(f => f.importance))) * 100}%`,
                        animationDelay: `${index * 50}ms`
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>

          {/* Feature Descriptions */}
          <div className="mt-6 p-4 bg-zinc-800/40 rounded-lg">
            <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider mb-3">Feature Descriptions</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-zinc-400">
              <div>
                <span className="font-semibold text-zinc-300">code_churn_ratio:</span> Amount of code changed
              </div>
              <div>
                <span className="font-semibold text-zinc-300">author_experience_years:</span> Developer experience level
              </div>
              <div>
                <span className="font-semibold text-zinc-300">risk_score:</span> Engineered composite risk metric
              </div>
              <div>
                <span className="font-semibold text-zinc-300">lines_added/deleted:</span> Code modification volume
              </div>
              <div>
                <span className="font-semibold text-zinc-300">modules_affected_count:</span> Number of impacted modules
              </div>
              <div>
                <span className="font-semibold text-zinc-300">historical_bug_frequency:</span> Past bugs in modules
              </div>
              <div>
                <span className="font-semibold text-zinc-300">is_hotspot_module:</span> Critical module flag
              </div>
              <div>
                <span className="font-semibold text-zinc-300">regression_time_hours:</span> Expected test duration
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Model Status */}
      <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 rounded-lg">
            <Lightbulb size={20} className="text-emerald-400" />
          </div>
          <div>
            <p className="text-emerald-400 font-bold">Model Status: Production Ready</p>
            <p className="text-emerald-400/80 text-sm mt-1">
              XGBoost classifier trained on RTL verification data with {metadata.roc_auc_score?.toFixed(3) || 'N/A'} ROC-AUC performance.
              Currently active in SanDisk Optima regression pipeline.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}