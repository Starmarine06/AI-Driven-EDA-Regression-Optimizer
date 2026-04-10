import React from 'react';
import { Target, Zap, Copy, AlertTriangle } from 'lucide-react';

function SliderRow({ label, hint, value, min, max, step, onChange, color, accentColor, format }) {
  const display = format ? format(value) : value;
  return (
    <div>
      <label className="text-xs font-semibold text-zinc-300 flex justify-between mb-1.5">
        <span>{label}</span>
        <span className={`font-[var(--font-mono)] ${color}`}>{display}</span>
      </label>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={onChange}
        className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer"
        style={{ accentColor: accentColor || '#3b82f6' }}
      />
      <p className="text-[10px] text-zinc-500 mt-1">{hint}</p>
    </div>
  );
}

export default function InteractivePredictor({
  predictorInputs,
  setPredictorInputs,
  predictorResult,
  predictorLoading,
  handlePredict
}) {
  const set = (key, val) => setPredictorInputs(prev => ({ ...prev, [key]: val }));

  // Compute all 13 model features live (mirrors api_server.py + train_model.py)
  const { code_churn_ratio: c, files_modified: f, author_experience_years: exp,
    historical_bug_frequency: bugs, modules_affected_count: mods } = predictorInputs;
  const derived = {
    lines_added: Math.round(c * f * 15),
    lines_deleted: Math.round(c * f * 8),
    regression_time_hours: Math.max(0.5, f * 0.3).toFixed(1),
    code_churn_normalized: (c * f).toFixed(3),
    bug_density: (bugs / (mods + 1)).toFixed(4),
  };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

      {/* ── Input Card ─────────────────────────────────────── */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
          <Target size={15} className="text-blue-400" /> Failure Predictor
        </h3>
        <p className="text-xs text-zinc-500 mb-5">
          Uses the latest XGBoost model on every prediction.
        </p>

        <div className="space-y-5">

          <SliderRow
            label="Code Churn Ratio"
            hint="Changed lines ÷ total codebase size (0.0 – 1.0)"
            value={predictorInputs.code_churn_ratio}
            min={0} max={1} step={0.05}
            onChange={e => set('code_churn_ratio', parseFloat(e.target.value))}
            color="text-blue-400" accentColor="#3b82f6"
            format={v => v.toFixed(2)}
          />

          <SliderRow
            label="Files Modified"
            hint="Number of source files touched by this commit"
            value={predictorInputs.files_modified}
            min={1} max={100} step={1}
            onChange={e => set('files_modified', parseInt(e.target.value))}
            color="text-emerald-400" accentColor="#10b981"
          />

          <SliderRow
            label="Author Experience (Years)"
            hint="Years of RTL / embedded development experience"
            value={predictorInputs.author_experience_years}
            min={0} max={20} step={1}
            onChange={e => set('author_experience_years', parseInt(e.target.value))}
            color="text-purple-400" accentColor="#a855f7"
          />

          <SliderRow
            label="Historical Bug Frequency"
            hint="Number of past bugs found in the affected modules (0–60)"
            value={predictorInputs.historical_bug_frequency}
            min={0} max={60} step={1}
            onChange={e => set('historical_bug_frequency', parseInt(e.target.value))}
            color="text-amber-400" accentColor="#f59e0b"
          />

          <SliderRow
            label="Modules Affected"
            hint="Number of distinct RTL modules touched by this commit"
            value={predictorInputs.modules_affected_count}
            min={1} max={15} step={1}
            onChange={e => set('modules_affected_count', parseInt(e.target.value))}
            color="text-orange-400" accentColor="#f97316"
          />

          {/* ── Derived Features Panel ── */}
          <div className="mt-2 p-3 bg-zinc-950/60 border border-zinc-800/40 rounded-lg">
            <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Auto-computed model features</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {Object.entries(derived).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center">
                  <span className="text-[9px] text-zinc-500 font-[var(--font-mono)]">{k}</span>
                  <span className="text-[9px] text-zinc-300 font-[var(--font-mono)] font-bold">{v}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Predict Button */}
          <button
            onClick={handlePredict}
            disabled={predictorLoading}
            className={`w-full py-3 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition-all active:scale-95 mt-2 ${predictorLoading
              ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:from-blue-500 hover:to-blue-400 shadow-lg shadow-blue-600/25'
              }`}
          >
            {predictorLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Predicting…
              </>
            ) : (
              <><Zap size={16} /> Run Prediction</>
            )}
          </button>
        </div>
      </div>

      {/* ── Result Card ─────────────────────────────────────── */}
      <div className="bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-6">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
          <Target size={15} className="text-red-400" /> Prediction Result
        </h3>

        {predictorResult ? (
          <div className="space-y-4">
            {/* Risk Score Bar */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold text-zinc-300">Failure Risk Score</span>
                <span className={`text-2xl font-bold font-[var(--font-mono)] ${predictorResult.risk_level === 'HIGH' ? 'text-red-400' :
                  predictorResult.risk_level === 'MEDIUM' ? 'text-amber-400' : 'text-emerald-400'
                  }`}>
                  {predictorResult.risk_score.toFixed(1)}
                </span>
              </div>
              <div className="w-full bg-zinc-950 rounded-full h-3 border border-zinc-800/60 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${predictorResult.risk_level === 'HIGH' ? 'bg-gradient-to-r from-red-600 to-red-500' :
                    predictorResult.risk_level === 'MEDIUM' ? 'bg-gradient-to-r from-amber-600 to-amber-500' :
                      'bg-gradient-to-r from-emerald-600 to-emerald-500'
                    }`}
                  style={{ width: `${predictorResult.risk_score}%` }}
                />
              </div>
            </div>

            {/* Risk Level */}
            <div className="flex items-center gap-3">
              <div className={`p-3 rounded-lg ${predictorResult.risk_level === 'HIGH' ? 'bg-red-500/10' :
                predictorResult.risk_level === 'MEDIUM' ? 'bg-amber-500/10' : 'bg-emerald-500/10'
                }`}>
                <AlertTriangle size={20} className={
                  predictorResult.risk_level === 'HIGH' ? 'text-red-400' :
                    predictorResult.risk_level === 'MEDIUM' ? 'text-amber-400' : 'text-emerald-400'
                } />
              </div>
              <div>
                <p className="text-xs font-bold text-zinc-300">Risk Level</p>
                <p className={`text-sm font-extrabold ${predictorResult.risk_level === 'HIGH' ? 'text-red-400' :
                  predictorResult.risk_level === 'MEDIUM' ? 'text-amber-400' : 'text-emerald-400'
                  }`}>{predictorResult.risk_level}</p>
              </div>
            </div>

            {/* Failure Probability */}
            <div className="p-3 bg-zinc-900/40 border border-zinc-800/60 rounded-lg">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-semibold text-zinc-300">Failure Probability</span>
                <span className="text-lg font-bold font-[var(--font-mono)] text-white">
                  {(predictorResult.failure_probability * 100).toFixed(1)}%
                </span>
              </div>
              <p className="text-[10px] text-zinc-500">Likelihood this commit introduces a test failure</p>
            </div>

            {/* Recommendation */}
            <div className={`p-3 rounded-lg border ${predictorResult.risk_level === 'HIGH' ? 'bg-red-500/5 border-red-500/20' :
              predictorResult.risk_level === 'MEDIUM' ? 'bg-amber-500/5 border-amber-500/20' :
                'bg-emerald-500/5 border-emerald-500/20'
              }`}>
              <p className="text-[10px] font-semibold text-zinc-300 uppercase tracking-wider mb-1">Recommendation</p>
              <p className={`text-xs leading-relaxed ${predictorResult.risk_level === 'HIGH' ? 'text-red-300' :
                predictorResult.risk_level === 'MEDIUM' ? 'text-amber-300' : 'text-emerald-300'
                }`}>{predictorResult.recommendation}</p>
            </div>

            {/* Source + timestamp */}
            <div className="flex justify-between items-center text-[10px] text-zinc-600 font-[var(--font-mono)]">
              <span>Model: {predictorResult.prediction_source}</span>
              {predictorResult.model_timestamp && predictorResult.model_timestamp !== 'N/A' && (
                <span>Trained: {predictorResult.model_timestamp}</span>
              )}
            </div>

            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(predictorResult, null, 2));
                alert('Result copied to clipboard!');
              }}
              className="w-full py-2 rounded-lg bg-zinc-800 text-zinc-300 text-xs font-semibold hover:bg-zinc-700 transition-all flex items-center justify-center gap-2"
            >
              <Copy size={12} /> Copy Result
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-14 h-14 rounded-full bg-zinc-800/50 flex items-center justify-center mb-3">
              <Zap size={22} className="text-zinc-600" />
            </div>
            <p className="text-sm text-zinc-400">Adjust sliders and click</p>
            <p className="text-xs text-zinc-600 mt-1">"Run Prediction" to analyse risk</p>
          </div>
        )}
      </div>
    </div>
  );
}