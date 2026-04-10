import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import * as XLSX from 'xlsx';
import axios from 'axios';
import {
  Activity, DollarSign, Clock, AlertTriangle,
  Cpu, Layout, TrendingDown, CheckCircle, XCircle, Search,
  PlayCircle, HardDrive, Database, Filter, X, Maximize,
  ChevronDown, ArrowUpDown, ArrowUp, ArrowDown, Zap,
  Shield, BarChart3, Layers, Info, ChevronLeft, ChevronRight,
  Gauge, Timer, MemoryStick, CircuitBoard,
  Bug, GitCommit, FileWarning, Crosshair, Target,
  Lightbulb, FolderSearch, Hash, Flame, Network,
  AlertOctagon, ShieldAlert, Eye, ArrowRight, ChevronUp,
  Fingerprint, Repeat, Scan, Copy, Sparkles, Download
} from 'lucide-react';

// Import components
import DashboardOverview from './components/DashboardOverview';
import TestQueueAnalysis from './components/TestQueueAnalysis';
import RiskHeatmap from './components/RiskHeatmap';
import ModelInsights from './components/ModelInsights';
import ROIAnalysis from './components/ROIAnalysis';
import InteractivePredictor from './components/InteractivePredictor';

// ─────────────────────────────────────────────────
// SANDISK SPECIFIC SYNTHETIC DATA (FALLBACK)
// ─────────────────────────────────────────────────

const MOCK_COMMITS = [
  { id: 'sd_ftl_9f2a', author: 'jdoe (Junior)', message: 'Update FTL wear-leveling algorithm for QLC NAND', churn: 'High', files: 12, insertions: 847, deletions: 291 },
  { id: 'sd_nvme_4d9', author: 'asmith (Senior)', message: 'Fix NVMe completion queue timeout bug', churn: 'Low', files: 3, insertions: 42, deletions: 18 },
  { id: 'sd_ecc_1b8d', author: 'bjones (Mid)', message: 'Refactor LDPC ECC decoder soft-read logic', churn: 'Medium', files: 7, insertions: 315, deletions: 198 },
];

const BASE_MODULES = [
  { id: 'pcie_mac', name: 'PCIe Gen4 PHY', group: 'Host IO', loc: 18000, fp: { top: '0%', left: '0%', width: '18%', height: '100%' } },
  { id: 'nvme_ctrl', name: 'NVMe Core', group: 'Host Logic', loc: 28000, fp: { top: '0%', left: '20%', width: '28%', height: '38%' } },
  { id: 'aes_crypto', name: 'AES-256 Engine', group: 'Security', loc: 9000, fp: { top: '40%', left: '20%', width: '28%', height: '20%' } },
  { id: 'dram_ctrl', name: 'DRAM Ctrl', group: 'Memory', loc: 12000, fp: { top: '62%', left: '20%', width: '28%', height: '38%' } },
  { id: 'ftl_core', name: 'Flash Translation Layer', group: 'Firmware', loc: 45000, fp: { top: '0%', left: '50%', width: '50%', height: '48%' } },
  { id: 'ecc_ldpc', name: 'LDPC ECC Engine', group: 'Data Integrity', loc: 32000, fp: { top: '50%', left: '50%', width: '50%', height: '30%' } },
  { id: 'nand_onfi', name: 'ONFI NAND PHY', group: 'Storage IO', loc: 15000, fp: { top: '82%', left: '50%', width: '50%', height: '18%' } },
];

const COMMIT_RISK_PROFILES = {
  'sd_ftl_9f2a': { ftl_core: 0.94, nand_onfi: 0.55, dram_ctrl: 0.42 },
  'sd_nvme_4d9': { nvme_ctrl: 0.82, pcie_mac: 0.68, dram_ctrl: 0.15 },
  'sd_ecc_1b8d': { ecc_ldpc: 0.89, ftl_core: 0.35, nand_onfi: 0.45 },
};

// ─────────────────────────────────────────────────
// ERROR CATEGORIES & FAILURE CLUSTERS
// ─────────────────────────────────────────────────

const ERROR_CATEGORIES = [
  { id: 'timeout', label: 'Timeout / Hang', icon: 'Clock', color: '#f59e0b', bgClass: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  { id: 'assertion', label: 'Assertion Failure', icon: 'AlertOctagon', color: '#ef4444', bgClass: 'bg-red-500/10 text-red-400 border-red-500/20' },
  { id: 'protocol', label: 'Protocol Violation', icon: 'ShieldAlert', color: '#a855f7', bgClass: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
  { id: 'data_integrity', label: 'Data Mismatch', icon: 'Database', color: '#3b82f6', bgClass: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  { id: 'resource', label: 'Resource Exhaustion', icon: 'Flame', color: '#f97316', bgClass: 'bg-orange-500/10 text-orange-400 border-orange-500/20' },
];

// Signature generation: deterministic hash from category + signal + module
function generateSignature(category, signal, testId) {
  const mod = testId.split('_').slice(1, -1).join('_');
  const raw = `${category}::${signal}::${mod}`;
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    hash = ((hash << 5) - hash + raw.charCodeAt(i)) | 0;
  }
  return 'SIG-' + Math.abs(hash).toString(16).toUpperCase().padStart(8, '0');
}

// Per-commit failure cluster data with unique signatures and recurrence tracking
const COMMIT_FAILURE_CLUSTERS = {
  'sd_ftl_9f2a': [
    { id: 'F001', testId: 'TB_FTL_CORE_001', category: 'assertion', severity: 'critical', signal: 'ftl_map_table_update', message: 'L2P mapping corrupted after wear-leveling pass on block 0x3FA2', affectedTests: 8, relatedChange: 'ftl_wl_engine.sv:142 — new block rotation logic', signature: generateSignature('assertion', 'ftl_map_table_update', 'TB_FTL_CORE_001'), recurrences: 5, firstSeen: 'REG-2024-1187', lastSeen: 'REG-2024-1203' },
    { id: 'F002', testId: 'TB_FTL_CORE_003', category: 'data_integrity', severity: 'critical', signal: 'nand_write_verify', message: 'Write-verify mismatch on QLC page 3 after GC compaction', affectedTests: 6, relatedChange: 'ftl_gc_compact.sv:89 — modified page packing order', signature: generateSignature('data_integrity', 'nand_write_verify', 'TB_FTL_CORE_003'), recurrences: 3, firstSeen: 'REG-2024-1195', lastSeen: 'REG-2024-1203' },
    { id: 'F003', testId: 'TB_NAND_ONFI_002', category: 'timeout', severity: 'high', signal: 'onfi_ready_busy_n', message: 'NAND tR timeout exceeded 200µs during multi-plane read', affectedTests: 4, relatedChange: 'ftl_wl_engine.sv:210 — new timing constraint', signature: generateSignature('timeout', 'onfi_ready_busy_n', 'TB_NAND_ONFI_002'), recurrences: 2, firstSeen: 'REG-2024-1200', lastSeen: 'REG-2024-1203' },
    { id: 'F004', testId: 'TB_DRAM_CTRL_001', category: 'resource', severity: 'medium', signal: 'dram_cmd_queue_full', message: 'DRAM command queue overflow under sustained FTL writeback', affectedTests: 3, relatedChange: 'ftl_writeback.sv:55 — increased burst length', signature: generateSignature('resource', 'dram_cmd_queue_full', 'TB_DRAM_CTRL_001'), recurrences: 7, firstSeen: 'REG-2024-1150', lastSeen: 'REG-2024-1203' },
    { id: 'F005', testId: 'TB_FTL_CORE_005', category: 'assertion', severity: 'high', signal: 'ftl_trim_bitmap', message: 'Trim bitmap inconsistency after concurrent UNMAP + write', affectedTests: 5, relatedChange: 'ftl_wl_engine.sv:142 — new block rotation logic', signature: generateSignature('assertion', 'ftl_trim_bitmap', 'TB_FTL_CORE_005'), recurrences: 1, firstSeen: 'REG-2024-1203', lastSeen: 'REG-2024-1203' },
    { id: 'F006', testId: 'TB_NAND_ONFI_004', category: 'protocol', severity: 'low', signal: 'onfi_crc_check', message: 'Optional CRC field not populated on status read', affectedTests: 1, relatedChange: 'nand_onfi_phy.sv:78 — status register mask', signature: generateSignature('protocol', 'onfi_crc_check', 'TB_NAND_ONFI_004'), recurrences: 12, firstSeen: 'REG-2024-1089', lastSeen: 'REG-2024-1203' },
  ],
  'sd_nvme_4d9': [
    { id: 'F007', testId: 'TB_NVME_CTRL_001', category: 'timeout', severity: 'critical', signal: 'cq_doorbell_timeout', message: 'Completion queue doorbell write timed out after 500ms', affectedTests: 7, relatedChange: 'nvme_cq_arbiter.sv:34 — doorbell interrupt path fix', signature: generateSignature('timeout', 'cq_doorbell_timeout', 'TB_NVME_CTRL_001'), recurrences: 4, firstSeen: 'REG-2024-1191', lastSeen: 'REG-2024-1203' },
    { id: 'F008', testId: 'TB_PCIE_MAC_002', category: 'protocol', severity: 'high', signal: 'pcie_tlp_malformed', message: 'Malformed TLP header detected on Gen4 x4 link', affectedTests: 4, relatedChange: 'nvme_cq_arbiter.sv:34 — changed TLP routing', signature: generateSignature('protocol', 'pcie_tlp_malformed', 'TB_PCIE_MAC_002'), recurrences: 1, firstSeen: 'REG-2024-1203', lastSeen: 'REG-2024-1203' },
    { id: 'F009', testId: 'TB_NVME_CTRL_003', category: 'assertion', severity: 'medium', signal: 'nvme_sq_head_ptr', message: 'SQ head pointer wraparound assertion on queue depth 1024', affectedTests: 3, relatedChange: 'nvme_sq_engine.sv:112 — pointer width change', signature: generateSignature('assertion', 'nvme_sq_head_ptr', 'TB_NVME_CTRL_003'), recurrences: 6, firstSeen: 'REG-2024-1165', lastSeen: 'REG-2024-1203' },
    { id: 'F010', testId: 'TB_PCIE_MAC_004', category: 'data_integrity', severity: 'low', signal: 'pcie_ecrc_mismatch', message: 'ECRC mismatch on completion with relaxed ordering', affectedTests: 2, relatedChange: 'pcie_mac_layer.sv:201 — ECRC generation update', signature: generateSignature('data_integrity', 'pcie_ecrc_mismatch', 'TB_PCIE_MAC_004'), recurrences: 9, firstSeen: 'REG-2024-1102', lastSeen: 'REG-2024-1203' },
  ],
  'sd_ecc_1b8d': [
    { id: 'F011', testId: 'TB_ECC_LDPC_001', category: 'assertion', severity: 'critical', signal: 'ldpc_syndrome_zero', message: 'Decoder converged to wrong codeword — syndrome zero but data corrupted', affectedTests: 9, relatedChange: 'ecc_ldpc_decoder.sv:67 — soft-read LLR quantization change', signature: generateSignature('assertion', 'ldpc_syndrome_zero', 'TB_ECC_LDPC_001'), recurrences: 2, firstSeen: 'REG-2024-1199', lastSeen: 'REG-2024-1203' },
    { id: 'F012', testId: 'TB_ECC_LDPC_003', category: 'data_integrity', severity: 'critical', signal: 'ecc_uncorrectable', message: 'Uncorrectable error rate spiked 3× on 3D QLC read-retry path', affectedTests: 7, relatedChange: 'ecc_ldpc_decoder.sv:115 — retry threshold adjustment', signature: generateSignature('data_integrity', 'ecc_uncorrectable', 'TB_ECC_LDPC_003'), recurrences: 3, firstSeen: 'REG-2024-1195', lastSeen: 'REG-2024-1203' },
    { id: 'F013', testId: 'TB_FTL_CORE_002', category: 'timeout', severity: 'high', signal: 'ecc_decode_latency', message: 'ECC decode latency exceeded 40µs SLA for sequential read', affectedTests: 5, relatedChange: 'ecc_ldpc_decoder.sv:67 — iteration count change', signature: generateSignature('timeout', 'ecc_decode_latency', 'TB_FTL_CORE_002'), recurrences: 8, firstSeen: 'REG-2024-1140', lastSeen: 'REG-2024-1203' },
    { id: 'F014', testId: 'TB_NAND_ONFI_001', category: 'protocol', severity: 'medium', signal: 'onfi_read_retry_seq', message: 'Read-retry feature address sequence violated ONFI 4.2 spec', affectedTests: 3, relatedChange: 'nand_read_retry.sv:45 — feature address table update', signature: generateSignature('protocol', 'onfi_read_retry_seq', 'TB_NAND_ONFI_001'), recurrences: 1, firstSeen: 'REG-2024-1203', lastSeen: 'REG-2024-1203' },
    { id: 'F015', testId: 'TB_ECC_LDPC_005', category: 'resource', severity: 'medium', signal: 'ldpc_buffer_overflow', message: 'Decoder input buffer overflow on back-to-back multiplane reads', affectedTests: 4, relatedChange: 'ecc_ldpc_decoder.sv:180 — buffer depth reduction', signature: generateSignature('resource', 'ldpc_buffer_overflow', 'TB_ECC_LDPC_005'), recurrences: 5, firstSeen: 'REG-2024-1178', lastSeen: 'REG-2024-1203' },
  ],
};

// Recent design/testbench changes per commit
const RECENT_CHANGES = {
  'sd_ftl_9f2a': [
    { file: 'ftl_wl_engine.sv', lines: '142-210', type: 'Design', description: 'New block rotation and wear-leveling algorithm for QLC endurance', riskScore: 0.92 },
    { file: 'ftl_gc_compact.sv', lines: '78-95', type: 'Design', description: 'Modified garbage collection page packing for 4-plane QLC', riskScore: 0.78 },
    { file: 'ftl_writeback.sv', lines: '50-62', type: 'Design', description: 'Increased DRAM writeback burst length from 8 to 16', riskScore: 0.45 },
    { file: 'tb_ftl_wl_test.sv', lines: '1-300', type: 'Testbench', description: 'New wear-leveling stress test stimulus', riskScore: 0.30 },
  ],
  'sd_nvme_4d9': [
    { file: 'nvme_cq_arbiter.sv', lines: '28-52', type: 'Design', description: 'Fixed completion queue doorbell interrupt acknowledgement path', riskScore: 0.85 },
    { file: 'nvme_sq_engine.sv', lines: '108-120', type: 'Design', description: 'Changed SQ head pointer register width from 10 to 11 bits', riskScore: 0.60 },
    { file: 'pcie_mac_layer.sv', lines: '195-210', type: 'Design', description: 'Updated ECRC generation for relaxed ordering completions', riskScore: 0.35 },
  ],
  'sd_ecc_1b8d': [
    { file: 'ecc_ldpc_decoder.sv', lines: '60-180', type: 'Design', description: 'Refactored soft-read LLR quantization and iteration control', riskScore: 0.91 },
    { file: 'nand_read_retry.sv', lines: '40-55', type: 'Design', description: 'Updated ONFI 4.2 read-retry feature address sequence', riskScore: 0.55 },
    { file: 'tb_ecc_stress.sv', lines: '1-450', type: 'Testbench', description: 'New multi-corner ECC decode stress patterns', riskScore: 0.25 },
  ],
};

const SEVERITY_ORDER = { critical: 4, high: 3, medium: 2, low: 1 };
const SEVERITY_COLORS = {
  critical: { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-500' },
  high: { bg: 'bg-orange-500/15', text: 'text-orange-400', border: 'border-orange-500/30', dot: 'bg-orange-500' },
  medium: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-400' },
  low: { bg: 'bg-zinc-500/15', text: 'text-zinc-400', border: 'border-zinc-500/30', dot: 'bg-zinc-500' },
};

// Seeded random for deterministic test generation
function seededRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

// ─────────────────────────────────────────────────
// ANIMATED NUMBER HOOK
// ─────────────────────────────────────────────────

function useAnimatedNumber(target, duration = 600) {
  const [value, setValue] = useState(0);
  const frameRef = useRef(null);
  const startRef = useRef(null);
  const fromRef = useRef(0);

  useEffect(() => {
    fromRef.current = value;
    startRef.current = performance.now();

    const animate = (now) => {
      const elapsed = now - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(fromRef.current + (target - fromRef.current) * eased);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration]);

  return value;
}

// ─────────────────────────────────────────────────
// HELPER COMPONENTS
// ─────────────────────────────────────────────────

const Card = ({ children, className = '', delay = 0 }) => (
  <div
    className={`glass-card p-5 md:p-6 animate-fade-in-up ${className}`}
    style={{ animationDelay: `${delay}ms` }}
  >
    {children}
  </div>
);

const RiskBadge = ({ risk }) => {
  let colorClasses = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  let dotColor = 'bg-emerald-400';
  if (risk > 0.7) { colorClasses = 'bg-red-500/10 text-red-400 border-red-500/20'; dotColor = 'bg-red-400'; }
  else if (risk > 0.4) { colorClasses = 'bg-amber-500/10 text-amber-400 border-amber-500/20'; dotColor = 'bg-amber-400'; }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold font-[var(--font-mono)] border ${colorClasses} transition-all duration-300`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor} ${risk > 0.7 ? 'animate-pulse' : ''}`} />
      {(risk * 100).toFixed(1)}%
    </span>
  );
};

const MiniSparkline = ({ data, color = '#dc2626', height = 32 }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 80;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={w} height={height} className="opacity-40 group-hover:opacity-70 transition-opacity duration-300">
      <defs>
        <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} strokeLinecap="round" strokeLinejoin="round" />
      <polygon
        fill={`url(#grad-${color.replace('#', '')})`}
        points={`0,${height} ${points} ${w},${height}`}
      />
    </svg>
  );
};

const KpiCard = ({ label, value, suffix = '', prefix = '', icon: Icon, iconBg, iconColor, accentColor, sparkData, delay = 0, children }) => {
  const animatedVal = useAnimatedNumber(parseFloat(value) || 0);
  const displayVal = typeof value === 'number'
    ? (Number.isInteger(value) ? Math.round(animatedVal) : animatedVal.toFixed(1))
    : value;

  return (
    <Card className="group relative overflow-hidden hover:scale-[1.02] transition-transform duration-300" delay={delay}>
      <div className="flex items-start justify-between relative z-10">
        <div>
          <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">{label}</p>
          <h3 className={`text-3xl font-extrabold tracking-tight mt-1 ${accentColor || 'text-white'}`}>
            <span className="number-ticker">{prefix}{typeof value === 'number' ? displayVal.toLocaleString() : value}</span>
            {suffix && <span className="text-sm font-medium text-zinc-500 ml-1">{suffix}</span>}
          </h3>
          {children}
        </div>
        <div className={`p-2.5 rounded-xl ${iconBg || 'bg-zinc-800'} ${iconColor || 'text-zinc-400'} transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3`}>
          <Icon size={20} />
        </div>
      </div>
      {sparkData && (
        <div className="absolute bottom-0 right-0">
          <MiniSparkline data={sparkData} color={accentColor === 'text-red-400' ? '#ef4444' : accentColor === 'text-emerald-400' ? '#10b981' : '#71717a'} />
        </div>
      )}
    </Card>
  );
};

const Tooltip = ({ children, content, position = 'top' }) => {
  const posStyles = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div className="tooltip-container">
      {children}
      <div className={`tooltip-content ${posStyles[position]} whitespace-nowrap`}>
        <div className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-medium px-3 py-2 rounded-lg shadow-xl">
          {content}
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────────

export default function App() {
  const [selectedCommit, setSelectedCommit] = useState(MOCK_COMMITS[0].id);
  const [costPerHour, setCostPerHour] = useState(45);
  const [selectedModule, setSelectedModule] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sortConfig, setSortConfig] = useState({ key: 'risk', direction: 'desc' });
  const [hoveredModule, setHoveredModule] = useState(null);
  const [isDispatching, setIsDispatching] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Navigation state
  const [activeView, setActiveView] = useState('overview');

  // Predictor state
  const [predictorInputs, setPredictorInputs] = useState({
    code_churn_ratio: 0.5,
    files_modified: 10,
    author_experience_years: 5,
    historical_bug_frequency: 15,
    modules_affected_count: 3
  });
  const [predictorResult, setPredictorResult] = useState(null);
  const [predictorLoading, setPredictorLoading] = useState(false);

  // API data state
  const [apiData, setApiData] = useState({
    overview: null,
    testQueue: null,
    heatmap: null,
    modelInsights: null,
    roiAnalysis: null,
    loading: true,
    error: null
  });

  const fetchData = useCallback(async () => {
    setApiData(prev => ({ ...prev, loading: true, error: null }));
    try {
      const healthCheck = await axios.get('http://127.0.0.1:5000/api/health', { timeout: 5000 });
      console.log('API Health:', healthCheck.data);

      const [overviewRes, testQueueRes, heatmapRes, modelRes, roiRes] = await Promise.all([
        axios.get('http://127.0.0.1:5000/api/overview', { timeout: 10000 }),
        axios.get('http://127.0.0.1:5000/api/test-queue', { timeout: 10000 }),
        axios.get('http://127.0.0.1:5000/api/heatmap', { timeout: 10000 }),
        axios.get('http://127.0.0.1:5000/api/model-insights', { timeout: 10000 }),
        axios.get('http://127.0.0.1:5000/api/roi-analysis', { timeout: 10000 })
      ]);

      setApiData({
        overview: overviewRes.data,
        testQueue: testQueueRes.data,
        heatmap: heatmapRes.data,
        modelInsights: modelRes.data,
        roiAnalysis: roiRes.data,
        loading: false,
        error: null
      });
    } catch (error) {
      console.error('API fetch error:', error.message);
      setApiData(prev => ({
        ...prev,
        loading: false,
        error: `Failed to connect to backend API (${error.message}). Using mock data for demonstration.`
      }));
    }
  }, []);

  // Fetch on mount
  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => { setMounted(true); }, []);

  const activeCommit = MOCK_COMMITS.find(c => c.id === selectedCommit);

  // Generate modules with active risk profile (use API data if available)
  const activeModules = useMemo(() => {
    // Primary source of module information is the backend API, which reads
    // the CSV files located under rtl_verification_system/data (optimized_test_queue.csv).
    // The `/api/heatmap` endpoint does the heavy lifting – grouping by module,
    // computing average risk, failure probability and commit counts – and
    // returns the resulting list of modules.  If the API is up, we always use
    // that data here.  (The previous mock fallback was only meant for an offline demo.)
    if (apiData.heatmap && apiData.heatmap.modules) {
      return apiData.heatmap.modules.map(mod => ({
        id: mod.module,
        name: mod.module.replace('_', ' '),
        risk: mod.avg_risk_score / 100, // Convert to 0-1 scale
        avgFailureProb: mod.avg_failure_prob,
        commitCount: mod.commit_count,
        layout: mod.layout
      }));
    }

    // If API hasn't returned yet or is unreachable, return an empty list so
    // the UI simply renders no modules rather than stale mock values.
    return [];
  }, [selectedCommit, apiData.heatmap]);

  // Generate tests (use API data if available)
  const currentTests = useMemo(() => {
    if (apiData.testQueue && apiData.testQueue.test_queue) {
      // Use real API data
      return apiData.testQueue.test_queue.map((test, index) => ({
        id: test.commit_id || `TEST_${index}`,
        moduleId: test.modules_affected.split(',')[0].trim(), // Take first module
        moduleName: test.modules_affected.split(',')[0].trim(),
        runtime: (test.regression_time_hours || 1) * 60, // Convert hours to minutes
        passRate: 1 - (test.predicted_failure_probability || 0),
        risk: (test.risk_score || 0) / 100, // Convert to 0-1 scale
        failureProb: test.predicted_failure_probability || 0
      }));
    } else {
      // Fallback to mock data
      const tests = [];
      const rng = seededRandom(selectedCommit.charCodeAt(3) * 137);
      activeModules.forEach(mod => {
        const numTests = Math.floor(mod.loc / 3000) + 2;
        for (let i = 0; i < numTests; i++) {
          let testRisk = mod.risk + (rng() * 0.3 - 0.15);
          testRisk = Math.max(0.01, Math.min(0.99, testRisk));
          tests.push({
            id: `TB_${mod.id.toUpperCase()}_${String(i + 1).padStart(3, '0')}`,
            moduleId: mod.id,
            moduleName: mod.name,
            runtime: Math.floor(rng() * 90) + 10,
            passRate: 1 - (testRisk * 0.4),
            risk: testRisk,
          });
        }
      });
      return tests.sort((a, b) => b.risk - a.risk);
    }
  }, [activeModules, selectedCommit, apiData.testQueue]);

  // Filter & sort tests
  const filteredTests = useMemo(() => {
    let result = currentTests;
    if (selectedModule) result = result.filter(t => t.moduleId === selectedModule);
    if (searchQuery) result = result.filter(t => t.id.toLowerCase().includes(searchQuery.toLowerCase()) || t.moduleName.toLowerCase().includes(searchQuery.toLowerCase()));

    const { key, direction } = sortConfig;
    result = [...result].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];
      if (typeof aVal === 'string') return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      return direction === 'asc' ? aVal - bVal : bVal - aVal;
    });
    return result;
  }, [currentTests, selectedModule, searchQuery, sortConfig]);

  // Derived metrics (use API data when available)
  const avgRisk = useMemo(() => {
    if (apiData.overview) {
      return apiData.overview.kpis?.model_accuracy || 0.85; // Use model accuracy as proxy
    }
    return currentTests.reduce((acc, t) => acc + t.risk, 0) / currentTests.length;
  }, [currentTests, apiData.overview]);

  const highRiskTests = useMemo(() => {
    if (apiData.testQueue) {
      return apiData.testQueue.test_queue?.filter(t => t.risk_score > 66).length || 0;
    }
    return currentTests.filter(t => t.risk > 0.7).length;
  }, [currentTests, apiData.testQueue]);

  const totalRuntimeMins = useMemo(() => {
    if (apiData.testQueue) {
      return apiData.testQueue.test_queue?.reduce((acc, t) => acc + (t.regression_time_hours * 60), 0) || 0;
    }
    return currentTests.reduce((acc, t) => acc + t.runtime, 0);
  }, [currentTests, apiData.testQueue]);

  const totalRuntimeHours = totalRuntimeMins / 60;
  const baselineCost = totalRuntimeHours * costPerHour;
  const baselineTTFF = totalRuntimeMins * 0.65;
  const optimizedTTFF = totalRuntimeMins * 0.08;
  const timeSavedMins = baselineTTFF - optimizedTTFF;
  const costSaved = (timeSavedMins / 60) * costPerHour;
  const reductionPct = baselineTTFF > 0 ? ((baselineTTFF - optimizedTTFF) / baselineTTFF * 100) : 0;

  // Sparkline data (use API data when available)
  const sparkRisk = useMemo(() => {
    if (apiData.overview) {
      return [0.32, 0.35, 0.41, 0.38, 0.44, 0.42, apiData.overview.kpis?.model_accuracy || 0.85];
    }
    return [0.32, 0.35, 0.41, 0.38, 0.44, 0.42, avgRisk];
  }, [avgRisk, apiData.overview]);

  const sparkCost = useMemo(() => {
    if (apiData.overview) {
      return [820, 780, 910, 870, 950, 920, apiData.overview.kpis?.cost_savings || baselineCost];
    }
    return [820, 780, 910, 870, 950, 920, baselineCost];
  }, [baselineCost, apiData.overview]);

  const sparkSavings = useMemo(() => {
    if (apiData.overview) {
      return [380, 420, 460, 510, 490, 550, apiData.overview.kpis?.cost_savings || costSaved];
    }
    return [380, 420, 460, 510, 490, 550, costSaved];
  }, [costSaved, apiData.overview]);

  // ─── FAILURE INTELLIGENCE ───
  const activeFailures = useMemo(() => COMMIT_FAILURE_CLUSTERS[selectedCommit] || [], [selectedCommit]);
  const activeChanges = useMemo(() => RECENT_CHANGES[selectedCommit] || [], [selectedCommit]);

  // Error clustering: group failures by category
  const errorClusters = useMemo(() => {
    const clusters = {};
    ERROR_CATEGORIES.forEach(cat => { clusters[cat.id] = { ...cat, failures: [], totalAffected: 0 }; });
    activeFailures.forEach(f => {
      if (clusters[f.category]) {
        clusters[f.category].failures.push(f);
        clusters[f.category].totalAffected += f.affectedTests;
      }
    });
    return Object.values(clusters).filter(c => c.failures.length > 0).sort((a, b) => b.totalAffected - a.totalAffected);
  }, [activeFailures]);

  // Impact analysis: which modules are most affected
  const moduleImpact = useMemo(() => {
    const impact = {};
    activeFailures.forEach(f => {
      // Extract module from testId
      const parts = f.testId.split('_');
      const modKey = parts.slice(1, -1).join('_').toLowerCase();
      const mod = activeModules.find(m => m.id === modKey);
      if (!impact[modKey]) impact[modKey] = { moduleId: modKey, moduleName: mod?.name || modKey, failureCount: 0, totalAffected: 0, severities: [], categories: new Set() };
      impact[modKey].failureCount++;
      impact[modKey].totalAffected += f.affectedTests;
      impact[modKey].severities.push(f.severity);
      impact[modKey].categories.add(f.category);
    });
    return Object.values(impact).sort((a, b) => b.totalAffected - a.totalAffected);
  }, [activeFailures, activeModules]);

  // Prioritized failures: composite score = severity × affectedTests × recency
  const prioritizedFailures = useMemo(() => {
    return activeFailures.map(f => {
      const sevWeight = SEVERITY_ORDER[f.severity] || 1;
      const impactScore = f.affectedTests / 10;
      const changeCorrelation = activeChanges.some(c => f.relatedChange.includes(c.file)) ? 1.5 : 1.0;
      const debugPriority = (sevWeight * 0.4 + impactScore * 0.35 + changeCorrelation * 0.25) * 100;
      return { ...f, debugPriority: Math.min(99.9, debugPriority) };
    }).sort((a, b) => b.debugPriority - a.debugPriority);
  }, [activeFailures, activeChanges]);

  // Debug suggestions: top files to investigate
  const debugSuggestions = useMemo(() => {
    const fileMap = {};
    prioritizedFailures.forEach(f => {
      const file = f.relatedChange.split(':')[0];
      if (!fileMap[file]) fileMap[file] = { file, failures: [], maxPriority: 0, reasons: [] };
      fileMap[file].failures.push(f.id);
      fileMap[file].maxPriority = Math.max(fileMap[file].maxPriority, f.debugPriority);
      const reason = `${f.severity} ${ERROR_CATEGORIES.find(c => c.id === f.category)?.label || f.category} — ${f.affectedTests} tests affected`;
      if (!fileMap[file].reasons.includes(reason)) fileMap[file].reasons.push(reason);
    });
    return Object.values(fileMap).sort((a, b) => b.maxPriority - a.maxPriority);
  }, [prioritizedFailures]);

  // ─── UNIQUE SIGNATURE ANALYSIS ───
  const uniqueSignatures = useMemo(() => {
    const sigMap = {};
    activeFailures.forEach(f => {
      if (!sigMap[f.signature]) {
        sigMap[f.signature] = {
          signature: f.signature,
          category: f.category,
          signal: f.signal,
          severity: f.severity,
          recurrences: f.recurrences,
          firstSeen: f.firstSeen,
          lastSeen: f.lastSeen,
          isNew: f.recurrences === 1,
          failures: [],
          totalAffectedTests: 0,
          testIds: new Set(),
        };
      }
      sigMap[f.signature].failures.push(f);
      sigMap[f.signature].totalAffectedTests += f.affectedTests;
      sigMap[f.signature].testIds.add(f.testId);
      // Take worst severity
      if (SEVERITY_ORDER[f.severity] > SEVERITY_ORDER[sigMap[f.signature].severity]) {
        sigMap[f.signature].severity = f.severity;
      }
    });
    return Object.values(sigMap).sort((a, b) => {
      // Sort: new first, then by recurrences desc, then by affected tests desc
      if (a.isNew !== b.isNew) return a.isNew ? -1 : 1;
      if (b.recurrences !== a.recurrences) return b.recurrences - a.recurrences;
      return b.totalAffectedTests - a.totalAffectedTests;
    });
  }, [activeFailures]);

  const totalUniqueErrors = uniqueSignatures.length;
  const newErrors = uniqueSignatures.filter(s => s.isNew).length;
  const recurringErrors = uniqueSignatures.filter(s => !s.isNew).length;
  const maxRecurrence = Math.max(...uniqueSignatures.map(s => s.recurrences), 1);

  // Expanded failure detail
  const [expandedFailure, setExpandedFailure] = useState(null);

  // Sort handler
  const handleSort = useCallback((key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  }, []);

  // Dispatch simulation
  const handleDispatch = useCallback(() => {
    setIsDispatching(true);
    setTimeout(() => setIsDispatching(false), 3000);
  }, []);

  // Handle predictor submission — calls FastAPI prediction server on port 8000
  const handlePredict = useCallback(async () => {
    setPredictorLoading(true);
    try {
      // Send only the 5 user inputs — FastAPI derives the rest
      const payload = {
        code_churn_ratio: predictorInputs.code_churn_ratio,
        files_modified: predictorInputs.files_modified,
        author_experience_years: predictorInputs.author_experience_years,
        historical_bug_frequency: predictorInputs.historical_bug_frequency,
        modules_affected_count: predictorInputs.modules_affected_count,
      };

      console.group('%c[RTL Predictor] FastAPI Request', 'color:#60a5fa;font-weight:bold');
      console.log('Endpoint : POST http://127.0.0.1:8000/predict');
      console.table(payload);
      console.groupEnd();

      const response = await axios.post('http://127.0.0.1:8000/predict', payload, { timeout: 10000 });

      console.group('%c[RTL Predictor] FastAPI Response', 'color:#34d399;font-weight:bold');
      console.log('Risk Score         :', response.data.risk_score);
      console.log('Failure Probability:', response.data.failure_probability);
      console.log('Risk Level         :', response.data.risk_level);
      console.log('Model              :', response.data.prediction_source, '@', response.data.model_timestamp);
      if (response.data.feature_vector) {
        console.log('Feature Vector Used:');
        console.table(response.data.feature_vector);
      }
      console.groupEnd();

      setPredictorResult(response.data);
    } catch (error) {
      console.error('[RTL Predictor] Error:', error.message);
      const { code_churn_ratio: c, author_experience_years: exp,
        historical_bug_frequency: bugs, modules_affected_count: mods } = predictorInputs;
      const riskScore = ((1 - exp / 20) * 0.2 + c * 0.3 + (bugs / (mods + 1)) * 0.3) * 100;
      setPredictorResult({
        risk_score: Math.max(0, Math.min(100, riskScore)),
        failure_probability: Math.max(0.05, Math.min(0.95, riskScore / 100 * 0.5 + 0.1)),
        risk_level: riskScore > 70 ? 'HIGH' : riskScore > 40 ? 'MEDIUM' : 'LOW',
        recommendation: 'Offline — start FastAPI server: python prediction_server.py',
        prediction_source: 'offline_formula',
      });
    } finally {
      setPredictorLoading(false);
    }
  }, [predictorInputs]);

  // ─── EXCEL EXPORT ───
  const handleExportExcel = useCallback(() => {
    const wb = XLSX.utils.book_new();

    // Sheet 1: Test Priority Queue
    const testRows = filteredTests.map((t, i) => ({
      '#': i + 1,
      'Test ID': t.id,
      'Target Module': t.moduleName,
      'Module ID': t.moduleId,
      'Runtime (min)': t.runtime,
      'Pass Rate': `${(t.passRate * 100).toFixed(1)}%`,
      'AI Risk Score': `${(t.risk * 100).toFixed(1)}%`,
      'Risk Level': t.risk > 0.7 ? 'HIGH' : t.risk > 0.4 ? 'MEDIUM' : 'LOW',
    }));
    const ws1 = XLSX.utils.json_to_sheet(testRows);
    ws1['!cols'] = [{ wch: 4 }, { wch: 22 }, { wch: 22 }, { wch: 14 }, { wch: 14 }, { wch: 12 }, { wch: 14 }, { wch: 12 }];
    XLSX.utils.book_append_sheet(wb, ws1, 'Test Priority Queue');

    // Sheet 2: Failure Intelligence
    const failRows = prioritizedFailures.map((f, i) => ({
      'Priority': `P${i + 1}`,
      'Failure ID': f.id,
      'Signature': f.signature,
      'Category': ERROR_CATEGORIES.find(c => c.id === f.category)?.label || f.category,
      'Severity': f.severity,
      'Signal': f.signal,
      'Error Message': f.message,
      'Recurrences': f.recurrences,
      'First Seen': f.firstSeen,
      'Last Seen': f.lastSeen,
      'Tests Affected': f.affectedTests,
      'Debug Priority Score': f.debugPriority.toFixed(1),
      'Related Change': f.relatedChange,
      'Source Test': f.testId,
    }));
    const ws2 = XLSX.utils.json_to_sheet(failRows);
    ws2['!cols'] = [{ wch: 8 }, { wch: 10 }, { wch: 16 }, { wch: 20 }, { wch: 10 }, { wch: 22 }, { wch: 60 }, { wch: 12 }, { wch: 16 }, { wch: 16 }, { wch: 14 }, { wch: 18 }, { wch: 45 }, { wch: 22 }];
    XLSX.utils.book_append_sheet(wb, ws2, 'Failure Intelligence');

    // Sheet 3: Unique Signatures
    const sigRows = uniqueSignatures.map(s => ({
      'Signature': s.signature,
      'Category': ERROR_CATEGORIES.find(c => c.id === s.category)?.label || s.category,
      'Signal': s.signal,
      'Severity': s.severity,
      'Recurrences': s.recurrences,
      'Tests Impacted': s.totalAffectedTests,
      'Unique Tests': s.testIds.size,
      'Status': s.isNew ? 'NEW' : 'RECURRING',
      'First Seen': s.firstSeen,
      'Last Seen': s.lastSeen,
    }));
    const ws3 = XLSX.utils.json_to_sheet(sigRows);
    ws3['!cols'] = [{ wch: 16 }, { wch: 20 }, { wch: 22 }, { wch: 10 }, { wch: 12 }, { wch: 14 }, { wch: 12 }, { wch: 12 }, { wch: 16 }, { wch: 16 }];
    XLSX.utils.book_append_sheet(wb, ws3, 'Unique Signatures');

    // Sheet 4: Module Impact
    const modRows = activeModules.map(m => {
      const impact = moduleImpact.find(mi => mi.moduleId === m.id);
      return {
        'Module ID': m.id,
        'Module Name': m.name,
        'Group': m.group,
        'Lines of Code': m.loc,
        'Risk Score': `${(m.risk * 100).toFixed(1)}%`,
        'Risk Level': m.risk > 0.7 ? 'HIGH' : m.risk > 0.4 ? 'MEDIUM' : 'LOW',
        'Failures': impact?.failureCount || 0,
        'Tests Affected': impact?.totalAffected || 0,
        'Error Types': impact?.categories?.size || 0,
      };
    });
    const ws4 = XLSX.utils.json_to_sheet(modRows);
    ws4['!cols'] = [{ wch: 14 }, { wch: 24 }, { wch: 14 }, { wch: 14 }, { wch: 12 }, { wch: 12 }, { wch: 10 }, { wch: 14 }, { wch: 12 }];
    XLSX.utils.book_append_sheet(wb, ws4, 'Module Impact');

    // Download
    const commitLabel = selectedCommit.replace(/[^a-zA-Z0-9]/g, '_');
    XLSX.writeFile(wb, `SanDisk_Optima_${commitLabel}_${new Date().toISOString().slice(0, 10)}.xlsx`);
  }, [filteredTests, prioritizedFailures, uniqueSignatures, activeModules, moduleImpact, selectedCommit]);

  const SortIcon = ({ column }) => {
    if (sortConfig.key !== column) return <ArrowUpDown size={12} className="opacity-30 group-hover:opacity-60 transition-opacity" />;
    return sortConfig.direction === 'asc'
      ? <ArrowUp size={12} className="text-red-400" />
      : <ArrowDown size={12} className="text-red-400" />;
  };

  const rangeProgress = ((costPerHour - 10) / (200 - 10)) * 100;

  return (
    <div className={`min-h-screen bg-zinc-950 text-zinc-300 flex flex-col md:flex-row selection:bg-red-500/30 ${mounted ? 'opacity-100' : 'opacity-0'} transition-opacity duration-500`}>

      {/* ──── SIDEBAR ──── */}
      <aside className={`${sidebarCollapsed ? 'w-full md:w-20' : 'w-full md:w-80'} bg-zinc-950 border-r border-zinc-800/60 flex flex-col relative z-20 transition-all duration-500 ease-out`}>
        <div className="p-5 flex-1 flex flex-col overflow-hidden">

          {/* Logo */}
          <div className={`flex items-center gap-3 mb-8 animate-slide-in-left ${sidebarCollapsed ? 'justify-center' : ''}`}>
            <div className="p-2.5 bg-gradient-to-br from-red-600 to-red-700 rounded-xl text-white shadow-[0_0_20px_rgba(220,38,38,0.4)] flex-shrink-0 transition-transform duration-300 hover:scale-105">
              <HardDrive size={22} />
            </div>
            {!sidebarCollapsed && (
              <div className="overflow-hidden">
                <h1 className="text-lg font-extrabold tracking-tight text-white leading-tight">SanDisk Optima</h1>
                <p className="text-[10px] text-zinc-500 font-semibold tracking-[0.2em] uppercase">AI RTL Verification</p>
              </div>
            )}
          </div>

          {/* Collapse toggle */}
          <button
            onClick={() => setSidebarCollapsed(v => !v)}
            className="hidden md:flex absolute top-5 right-0 translate-x-1/2 w-6 h-6 bg-zinc-800 border border-zinc-700 rounded-full items-center justify-center text-zinc-400 hover:text-white hover:bg-zinc-700 transition-all z-30 shadow-md"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
          </button>

          {!sidebarCollapsed && (
            <div className="space-y-7 flex-1 animate-fade-in">

              {/* Pipeline Context */}
              <div>
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                  <Layers size={12} /> Pipeline Context
                </h3>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-400 font-medium">Target Commit</label>
                  <select
                    value={selectedCommit}
                    onChange={(e) => { setSelectedCommit(e.target.value); setSelectedModule(null); }}
                    className="custom-select w-full bg-zinc-900 border border-zinc-700/50 rounded-xl p-3 text-sm text-white focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none transition-all appearance-none cursor-pointer hover:border-zinc-600"
                  >
                    {MOCK_COMMITS.map(c => (
                      <option key={c.id} value={c.id}>{c.id.split('_').pop()} — {c.author}</option>
                    ))}
                  </select>
                </div>

                <div className="mt-3 p-4 bg-zinc-900/60 border border-zinc-800/80 rounded-xl space-y-3">
                  <div>
                    <p className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider mb-1">Commit Message</p>
                    <p className="text-sm font-medium text-zinc-200 leading-relaxed">{activeCommit.message}</p>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-3 border-t border-zinc-800/60">
                    <div className="text-center">
                      <p className="text-[10px] text-zinc-500 font-medium">Files</p>
                      <p className="text-sm font-bold text-zinc-200 font-[var(--font-mono)]">{activeCommit.files}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-emerald-500 font-medium">+Lines</p>
                      <p className="text-sm font-bold text-emerald-400 font-[var(--font-mono)]">{activeCommit.insertions}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-[10px] text-red-500 font-medium">-Lines</p>
                      <p className="text-sm font-bold text-red-400 font-[var(--font-mono)]">{activeCommit.deletions}</p>
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-3 border-t border-zinc-800/60">
                    <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Churn Level</span>
                    <span className={`chip-status ${activeCommit.churn === 'High' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                      activeCommit.churn === 'Medium' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${activeCommit.churn === 'High' ? 'bg-red-400 animate-pulse' :
                        activeCommit.churn === 'Medium' ? 'bg-amber-400' :
                          'bg-emerald-400'
                        }`} />
                      {activeCommit.churn}
                    </span>
                  </div>
                </div>
              </div>

              {/* Farm Parameters */}
              <div>
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                  <Cpu size={12} /> Farm Parameters
                </h3>
                <div className="space-y-3">
                  <label className="text-xs text-zinc-400 font-medium flex justify-between items-center">
                    Compute Cost
                    <span className="text-white font-[var(--font-mono)] font-bold bg-zinc-800 px-3 py-1.5 rounded-lg text-sm border border-zinc-700/80 shadow-inner">
                      ${costPerHour}/hr
                    </span>
                  </label>
                  <input
                    type="range"
                    min="10" max="200" step="5"
                    value={costPerHour}
                    onChange={(e) => setCostPerHour(Number(e.target.value))}
                    className="w-full cursor-pointer"
                    style={{ '--range-progress': `${rangeProgress}%` }}
                  />
                  <div className="flex justify-between text-[10px] text-zinc-600 font-[var(--font-mono)]">
                    <span>$10</span>
                    <span>$200</span>
                  </div>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="p-4 bg-zinc-900/40 border border-zinc-800/60 rounded-xl">
                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
                  <BarChart3 size={12} /> Session Stats
                </h3>
                <div className="space-y-2.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-zinc-500">Total Tests</span>
                    <span className="text-white font-bold font-[var(--font-mono)]">{currentTests.length}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-zinc-500">Total Runtime</span>
                    <span className="text-white font-bold font-[var(--font-mono)]">{(totalRuntimeMins / 60).toFixed(1)}h</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-zinc-500">Coverage</span>
                    <span className="text-emerald-400 font-bold font-[var(--font-mono)]">7/7 IPs</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Dispatch Button */}
          {!sidebarCollapsed && (
            <div className="mt-auto pt-5">
              <button
                onClick={handleDispatch}
                disabled={isDispatching}
                className={`btn-dispatch w-full text-white font-bold py-3.5 rounded-xl flex items-center justify-center gap-2.5 transition-all active:scale-[0.97] shadow-lg ${isDispatching
                  ? 'bg-zinc-700 cursor-wait shadow-none'
                  : 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 shadow-red-600/25 hover:shadow-red-500/40'
                  }`}
              >
                {isDispatching ? (
                  <>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                    Dispatching…
                  </>
                ) : (
                  <>
                    <Zap size={16} />
                    Dispatch AI Regression
                  </>
                )}
              </button>
              <p className="text-[10px] text-zinc-600 text-center mt-2.5 font-medium">
                Estimated: {Math.round(optimizedTTFF)}min to first failure
              </p>
            </div>
          )}
        </div>
      </aside>

      {/* ──── MAIN CONTENT ──── */}
      <main className="flex-1 p-5 lg:p-8 overflow-y-auto relative">
        {/* Ambient glow */}
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-red-500/[0.03] blur-[150px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-emerald-500/[0.02] blur-[120px] rounded-full pointer-events-none" />

        {/* Header */}
        <header className="mb-8 relative z-10 animate-fade-in-up">
          <div className="flex items-center justify-between gap-3 mb-1">
            <div className="flex items-center gap-3">
              <div className="w-1 h-8 bg-gradient-to-b from-red-500 to-red-700 rounded-full" />
              <div>
                <h2 className="text-2xl font-extrabold text-white tracking-tight">RTL Verification Dashboard</h2>
                <p className="text-zinc-500 text-sm">AI-Driven Test Prioritization System</p>
              </div>
            </div>
            <button
              onClick={fetchData}
              disabled={apiData.loading}
              title="Re-fetch all data from the latest CSV files"
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800/60 border border-zinc-700/60 text-zinc-400 hover:text-white hover:bg-zinc-700/60 hover:border-zinc-600 transition-all text-xs font-semibold disabled:opacity-40 disabled:cursor-wait"
            >
              <svg className={`w-3.5 h-3.5 ${apiData.loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {apiData.loading ? 'Refreshing…' : 'Refresh Data'}
            </button>
          </div>
        </header>

        {/* Navigation Tabs */}
        <nav className="mb-8 relative z-10">
          <div className="flex flex-wrap gap-1 bg-zinc-900/40 border border-zinc-800/60 rounded-xl p-1">
            {[
              { id: 'overview', label: 'Dashboard Overview', icon: BarChart3 },
              { id: 'test-queue', label: 'Test Queue Analysis', icon: TrendingDown },
              { id: 'heatmap', label: 'Risk Heatmap', icon: Flame },
              { id: 'model-insights', label: 'Model Insights', icon: Lightbulb },
              { id: 'roi-analysis', label: 'ROI Analysis', icon: DollarSign },
              { id: 'predictor', label: 'Interactive Predictor', icon: Target }
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeView === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveView(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive
                    ? 'bg-red-500/10 text-red-400 border border-red-500/20 shadow-lg shadow-red-500/10'
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'
                    }`}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </nav>

        {/* Loading/Error States */}
        {apiData.loading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-2 border-red-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-zinc-400">Loading data from backend...</p>
            </div>
          </div>
        )}

        {apiData.error && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-8">
            <div className="flex items-center gap-3">
              <AlertTriangle className="text-amber-400" size={20} />
              <div>
                <p className="text-amber-400 font-medium">Backend Connection Issue</p>
                <p className="text-amber-400/80 text-sm">{apiData.error}</p>
                <p className="text-zinc-500 text-xs mt-1">Using mock data for demonstration</p>
              </div>
            </div>
          </div>
        )}

        {/* View Content */}
        {activeView === 'overview' && <DashboardOverview apiData={apiData} currentTests={currentTests} avgRisk={avgRisk} highRiskTests={highRiskTests} baselineCost={baselineCost} costSaved={costSaved} reductionPct={reductionPct} sparkRisk={sparkRisk} sparkCost={sparkCost} sparkSavings={sparkSavings} />}
        {activeView === 'test-queue' && <TestQueueAnalysis apiData={apiData} currentTests={currentTests} filteredTests={filteredTests} selectedModule={selectedModule} setSelectedModule={setSelectedModule} searchQuery={searchQuery} setSearchQuery={setSearchQuery} sortConfig={sortConfig} handleSort={handleSort} SortIcon={SortIcon} />}
        {activeView === 'heatmap' && <RiskHeatmap activeModules={activeModules} selectedModule={selectedModule} setSelectedModule={setSelectedModule} hoveredModule={hoveredModule} setHoveredModule={setHoveredModule} apiData={apiData} />}
        {activeView === 'model-insights' && <ModelInsights apiData={apiData} />}
        {activeView === 'roi-analysis' && <ROIAnalysis apiData={apiData} />}
        {activeView === 'predictor' && <InteractivePredictor predictorInputs={predictorInputs} setPredictorInputs={setPredictorInputs} predictorResult={predictorResult} predictorLoading={predictorLoading} handlePredict={handlePredict} />}

        {/* Footer */}
        <footer className="mt-8 pb-4 text-center text-[10px] text-zinc-700 font-medium relative z-10">
          SanDisk Optima v2.0 — CoreOptima AI Engine — Confidential & Proprietary
        </footer>
      </main>
    </div>
  );
}
