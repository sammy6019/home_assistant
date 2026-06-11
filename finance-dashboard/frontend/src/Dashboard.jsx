import React, { useState, useEffect, useRef } from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import './Dashboard.css';

ChartJS.register(ArcElement, Tooltip, Legend);

const API = process.env.REACT_APP_API_URL || '/api';
const fmt$ = (n) => n == null ? '—' : `$${Number(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const fmtPct = (n) => n == null ? '—' : `${n>=0?'+':''}${Number(n).toFixed(2)}%`;
const CHART_COLORS = ['#CE1126','#002B5C','#8B0000','#1a3a6b','#e05070','#3a5a9b','#f09090','#7090c0','#d04060','#506090'];

// ── Root ──────────────────────────────────────────────────────────────────────
const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [apiHealth, setApiHealth] = useState(false);
  const [overview, setOverview]   = useState(null);
  const [schwab,   setSchwab]     = useState(null);
  const [coinbase, setCoinbase]   = useState(null);
  const [robinhood,setRobinhood]  = useState(null);

  useEffect(() => {
    checkHealth();
    loadAll();
    const t = setInterval(checkHealth, 30000);
    return () => clearInterval(t);
  }, []);

  const checkHealth = async () => {
    try { await fetch(`${API}/health`); setApiHealth(true); }
    catch { setApiHealth(false); }
  };

  const loadAll = async () => {
    const [ov, sw, cb, rh] = await Promise.all([
      fetch(`${API}/portfolio/overview`).then(r=>r.json()).catch(()=>null),
      fetch(`${API}/portfolio/schwab`).then(r=>r.json()).catch(()=>null),
      fetch(`${API}/portfolio/coinbase`).then(r=>r.json()).catch(()=>null),
      fetch(`${API}/portfolio/robinhood`).then(r=>r.json()).catch(()=>null),
    ]);
    if (ov) setOverview(ov);
    if (sw?.positions?.length) setSchwab(sw);
    if (cb?.positions?.length) setCoinbase(cb);
    if (rh?.positions?.length) setRobinhood(rh);
  };

  const onUpload = (account, data) => {
    if (account === 'schwab')    { setSchwab(data);    }
    if (account === 'coinbase')  { setCoinbase(data);  }
    if (account === 'robinhood') { setRobinhood(data); }
    if (data !== null) {
      fetch(`${API}/portfolio/overview`).then(r=>r.json()).then(setOverview).catch(()=>{});
    } else {
      setOverview(null);
    }
  };

  const tabs = [
    { id:'overview',  label:'🌐 Overview' },
    { id:'schwab',    label:'📈 Schwab' },
    { id:'coinbase',  label:'₿ Coinbase' },
    { id:'robinhood', label:'🪶 Robinhood' },
    { id:'report',    label:'🤖 AI Report' },
  ];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-title">
          <h1>📊 Finance Dashboard</h1>
          <span className={`api-badge ${apiHealth?'ok':'err'}`}>{apiHealth?'● API online':'● API offline'}</span>
        </div>
        {overview && overview.total_value > 0 && (
          <div className="header-stats">
            <StatChip label="Total Value"   value={fmt$(overview.total_value)} />
            <StatChip label="Today"         value={fmtPct(overview.total_day_pct)} sub={fmt$(overview.total_day_change)} color={overview.total_day_change>=0?'pos':'neg'} />
            <StatChip label="All-Time Gain" value={fmtPct(overview.total_gain_pct)} sub={fmt$(overview.total_gain_dollar)} color={overview.total_gain_dollar>=0?'pos':'neg'} />
            <StatChip label="Cash"          value={fmt$(overview.total_cash)} />
          </div>
        )}
      </header>

      <div className="tabs-bar">
        {tabs.map(t=>(
          <button key={t.id} className={`tab ${activeTab===t.id?'active':''}`} onClick={()=>setActiveTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab==='overview'  && <OverviewTab  overview={overview} />}
        {activeTab==='schwab'    && <AccountTab account="schwab"    data={schwab}    onUpload={onUpload} label="Schwab"    hint="Accounts → Positions → Export" />}
        {activeTab==='coinbase'  && <AccountTab account="coinbase"  data={coinbase}  onUpload={onUpload} label="Coinbase"  hint="Assets → Statements → Generate Report → CSV" />}
        {activeTab==='robinhood' && <AccountTab account="robinhood" data={robinhood} onUpload={onUpload} label="Robinhood" hint="Account → History → Export" />}
        {activeTab==='report'    && <ReportTab />}
      </div>
    </div>
  );
};

// ── Shared sub-components ────────────────────────────────────────────────────
const StatChip = ({ label, value, sub, color }) => (
  <div className={`stat-chip ${color||''}`}>
    <span className="chip-label">{label}</span>
    <span className="chip-value">{value}</span>
    {sub && <span className="chip-sub">{sub}</span>}
  </div>
);

const SortTh = ({ col, label, sortConfig, onSort }) => (
  <th onClick={()=>onSort(col)} style={{cursor:'pointer',whiteSpace:'nowrap'}}>
    {label} {sortConfig.key===col?(sortConfig.dir==='asc'?'↑':'↓'):'↕'}
  </th>
);

// ── Score badge ───────────────────────────────────────────────────────────────
const ScoreBadge = ({ rating, score, ratingClass }) => (
  <span className={`score-badge ${ratingClass}`}>
    {score != null ? `${score}` : '—'} <span className="score-rating">{rating}</span>
  </span>
);

// ── Score detail panel (expands below a row) ──────────────────────────────────
const ScorePanel = ({ ta }) => {
  if (!ta) return null;
  if (ta.error) return <div className="ta-panel ta-error">⚠ {ta.error}</div>;

  const Bar = ({ score, max, label }) => (
    <div className="ta-bar-row">
      <span className="ta-bar-label">{label}</span>
      <div className="ta-bar-track">
        <div className="ta-bar-fill" style={{width:`${Math.min(100,(score/max)*100)}%`}}/>
      </div>
      <span className="ta-bar-score">{score}/{max}</span>
    </div>
  );

  const Row = ({ icon, explanation, score, max }) => (
    <div className="ta-row">
      <span className="ta-icon">{icon}</span>
      <span className="ta-expl">{explanation}</span>
      <Bar score={score} max={max} label="" />
    </div>
  );

  const t = ta.technical;
  const f = ta.fundamental;

  return (
    <div className="ta-panel">
      <div className="ta-header">
        <ScoreBadge rating={ta.rating} score={ta.composite_score} ratingClass={ta.rating_class} />
        <span className="ta-subtitle">
          Technical {t?.score?.toFixed(0)}/100 (60%)
          {f && ` · Fundamental ${f.score?.toFixed(0)}/100 (40%)`}
        </span>
      </div>

      <div className="ta-sections">
        <div className="ta-section">
          <div className="ta-section-title">📈 Technical</div>
          {t?.rsi   && <Row icon="〰" explanation={t.rsi.explanation}   score={t.rsi.score}   max={t.rsi.max} />}
          {t?.ma50  && <Row icon="📊" explanation={t.ma50.explanation}  score={t.ma50.score}  max={t.ma50.max} />}
          {t?.ma200 && <Row icon="📉" explanation={t.ma200.explanation} score={t.ma200.score} max={t.ma200.max} />}
        </div>

        {f && (
          <div className="ta-section">
            <div className="ta-section-title">🏦 Fundamental {f.sector !== 'N/A' ? `· ${f.sector}` : ''}</div>
            <Row icon="💰" explanation={f.pe.explanation}              score={f.pe.score}              max={f.pe.max} />
            <Row icon="📈" explanation={f.earnings_growth.explanation} score={f.earnings_growth.score} max={f.earnings_growth.max} />
            <Row icon="💵" explanation={f.dividend_yield.explanation}  score={f.dividend_yield.score}  max={f.dividend_yield.max} />
          </div>
        )}
      </div>
    </div>
  );
};

// ── Positions table ───────────────────────────────────────────────────────────
const PositionsTable = ({ positions }) => {
  const [sort,       setSort]       = useState({key:'market_value',dir:'desc'});
  const [taData,     setTaData]     = useState({});   // {symbol: ta_result}
  const [loading,    setLoading]    = useState({});   // {symbol: bool}
  const [expanded,   setExpanded]   = useState(null); // symbol currently showing panel

  const handleSort = (key) => setSort(prev=>({key, dir:prev.key===key&&prev.dir==='asc'?'desc':'asc'}));

  const fetchTA = async (symbol, assetClass='stock') => {
    if (loading[symbol]) return;
    setLoading(p=>({...p,[symbol]:true}));
    try {
      const res = await fetch(`${API}/ta/${symbol}?asset_class=${assetClass}`);
      const d   = await res.json();
      setTaData(p=>({...p,[symbol]:d}));
      setExpanded(symbol);
    } catch(e) {
      setTaData(p=>({...p,[symbol]:{error:e.message}}));
    } finally {
      setLoading(p=>({...p,[symbol]:false}));
    }
  };

  const toggleExpand = (symbol, assetClass) => {
    if (expanded === symbol) { setExpanded(null); return; }
    if (taData[symbol])       { setExpanded(symbol); return; }
    fetchTA(symbol, assetClass);
  };

  const sorted = [...positions].sort((a,b)=>{
    const mult = sort.dir==='asc'?1:-1;
    const av = a[sort.key], bv = b[sort.key];
    return typeof av==='string' ? av.localeCompare(bv)*mult : (av-bv)*mult;
  });
  const th = (col,lbl) => <SortTh key={col} col={col} label={lbl} sortConfig={sort} onSort={handleSort}/>;

  return (
    <div className="table-scroll">
      <table className="holdings-table">
        <thead><tr>
          {th('symbol','Ticker')}
          {th('security_type','Type')}
          {th('price','Price')}
          {th('quantity','Qty')}
          {th('market_value','Mkt Value')}
          {th('pct_of_account','% Acct')}
          {th('cost_basis','Cost Basis')}
          {th('gain_loss_dollar','Gain/Loss $')}
          {th('gain_loss_pct','Gain/Loss %')}
          {th('day_change_dollar','Day Chg $')}
          {th('day_change_pct','Day Chg %')}
          <th>Score</th>
        </tr></thead>
        <tbody>
          {sorted.map(p=>{
            const ta  = taData[p.symbol];
            const exp = expanded === p.symbol;
            return (
              <React.Fragment key={`${p.symbol}-${p.account||''}`}>
                <tr className={exp ? 'row-expanded' : ''}>
                  <td><strong>{p.symbol}</strong>{p.account&&<span className="acct-badge">{p.account}</span>}<br/><small className="desc">{p.description}</small></td>
                  <td>{p.security_type||'—'}</td>
                  <td>{fmt$(p.price)}</td>
                  <td>{p.quantity}</td>
                  <td>{fmt$(p.market_value)}</td>
                  <td>{p.pct_of_account!=null ? p.pct_of_account.toFixed(2)+'%' : '—'}</td>
                  <td>{p.cost_basis?fmt$(p.cost_basis):'—'}</td>
                  <td className={p.gain_loss_dollar>=0?'pos':'neg'}>{fmt$(p.gain_loss_dollar)}</td>
                  <td className={p.gain_loss_pct>=0?'pos':'neg'}>{fmtPct(p.gain_loss_pct)}</td>
                  <td className={p.day_change_dollar>=0?'pos':'neg'}>{fmt$(p.day_change_dollar)}</td>
                  <td className={p.day_change_pct>=0?'pos':'neg'}>{fmtPct(p.day_change_pct)}</td>
                  <td>
                    {ta && !ta.error
                      ? <button className="btn-score-toggle" onClick={()=>setExpanded(exp?null:p.symbol)}>
                          <ScoreBadge rating={ta.rating} score={ta.composite_score} ratingClass={ta.rating_class}/>
                        </button>
                      : <button
                          className="btn-analyze"
                          onClick={()=>toggleExpand(p.symbol, p.asset_class||'stock')}
                          disabled={loading[p.symbol]}
                        >
                          {loading[p.symbol] ? '⏳' : '📊'}
                        </button>
                    }
                  </td>
                </tr>
                {exp && (
                  <tr className="ta-row-expanded">
                    <td colSpan={12}><ScorePanel ta={ta} /></td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const Alerts = ({ alerts }) => {
  if (!alerts?.length) return null;
  return (
    <div className="holdings-alerts">
      <h3>⚡ Movers Today (&gt;5%)</h3>
      <div className="alerts-row">
        {alerts.map(p=>(
          <div key={p.symbol} className={`alert-chip ${p.day_change_pct>=0?'pos':'neg'}`}>
            <strong>{p.symbol}</strong> {fmtPct(p.day_change_pct)}
          </div>
        ))}
      </div>
    </div>
  );
};

const MiniDoughnut = ({ data, labels, title }) => {
  const valid = data.filter(v=>v>0);
  if (!valid.length) return null;
  const chartData = {
    labels,
    datasets:[{ data, backgroundColor:CHART_COLORS, borderWidth:2, borderColor:'#fff' }]
  };
  return (
    <div className="holdings-chart-box">
      <h3>{title}</h3>
      <div style={{maxWidth:260,margin:'0 auto'}}>
        <Doughnut data={chartData} options={{plugins:{legend:{position:'bottom',labels:{font:{size:11}}}},cutout:'58%'}}/>
      </div>
    </div>
  );
};

// ── Overview Tab ──────────────────────────────────────────────────────────────
const OverviewTab = ({ overview }) => {
  if (!overview || overview.total_value === 0) {
    return (
      <div className="empty-state">
        <p>No data yet — upload CSVs in the Schwab, Coinbase, and Robinhood tabs.</p>
      </div>
    );
  }

  const alloc = overview.allocation || {};
  const breakdown = overview.account_breakdown || {};

  return (
    <div className="overview-tab">
      {/* Charts row */}
      <div className="overview-charts">
        <MiniDoughnut
          title="Asset Allocation"
          labels={Object.keys(alloc).filter(k=>alloc[k]>0)}
          data={Object.keys(alloc).filter(k=>alloc[k]>0).map(k=>alloc[k])}
        />
        <MiniDoughnut
          title="By Account"
          labels={Object.keys(breakdown).filter(k=>breakdown[k]>0)}
          data={Object.keys(breakdown).filter(k=>breakdown[k]>0).map(k=>breakdown[k])}
        />
      </div>

      {/* Top 10 */}
      {overview.top10?.length > 0 && (
        <div className="holdings-table-box" style={{marginTop:20}}>
          <h3>Top 10 Holdings (all accounts)</h3>
          <PositionsTable positions={overview.top10} />
        </div>
      )}
    </div>
  );
};

// ── Account Tab (Schwab / Coinbase / Robinhood) ───────────────────────────────
const AccountTab = ({ account, data, onUpload, label, hint }) => {
  const fileRef = useRef(null);
  const [loading,  setLoading]  = useState(false);
  const [status,   setStatus]   = useState(null);

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true); setStatus(null);
    onUpload(account, null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res  = await fetch(`${API}/portfolio/upload/${account}`, {method:'POST',body:form});
      const json = await res.json();
      if (res.ok) {
        setStatus({ok:true, msg:`Loaded ${json.positions} positions — total ${fmt$(json.total_value)}`});
        // Re-fetch this account's full data
        const full = await fetch(`${API}/portfolio/${account}`).then(r=>r.json());
        onUpload(account, full);
      } else {
        setStatus({ok:false, msg:json.detail||'Upload failed'});
      }
    } catch(err) {
      setStatus({ok:false, msg:err.message});
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value='';
    }
  };

  const top7 = data
    ? [...data.positions].sort((a,b)=>b.market_value-a.market_value).slice(0,7)
    : [];
  const otherVal = data && data.positions.length > 7
    ? data.total_value - data.cash - top7.reduce((s,p)=>s+p.market_value,0)
    : 0;
  const chartLabels = [...top7.map(p=>p.symbol), otherVal>0?'Other':null].filter(Boolean);
  const chartData   = [...top7.map(p=>p.market_value), otherVal>0?otherVal:null].filter(v=>v!=null&&v>0);

  return (
    <div className="account-tab">
      {/* Upload bar */}
      <div className="holdings-upload-bar">
        <div>
          <strong>{label} CSV</strong>
          <span className="upload-hint"> — {hint}</span>
        </div>
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          {status && <span className={`upload-status ${status.ok?'ok':'err'}`}>{status.msg}</span>}
          <input ref={fileRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleFile}/>
          <button className="btn-upload" onClick={()=>fileRef.current?.click()} disabled={loading}>
            {loading?'⏳ Parsing...':`📂 Upload ${label} CSV`}
          </button>
        </div>
      </div>

      {!data && (
        <div className="empty-state">
          <p>No {label} data yet. Export your positions CSV and upload it above.</p>
        </div>
      )}

      {data && (
        <>
          {/* Summary */}
          <div className="holdings-summary-grid">
            <div className="h-stat"><span className="h-stat-label">Total Value</span><span className="h-stat-value">{fmt$(data.total_value)}</span></div>
            <div className="h-stat"><span className="h-stat-label">Cash</span><span className="h-stat-value">{fmt$(data.cash)}</span></div>
            <div className={`h-stat ${data.total_day_change>=0?'pos':'neg'}`}>
              <span className="h-stat-label">Today</span>
              <span className="h-stat-value">{fmtPct(data.total_day_pct)}</span>
              <span className="h-stat-sub">{fmt$(data.total_day_change)}</span>
            </div>
            <div className={`h-stat ${data.total_gain_dollar>=0?'pos':'neg'}`}>
              <span className="h-stat-label">Total Gain</span>
              <span className="h-stat-value">{fmtPct(data.total_gain_pct)}</span>
              <span className="h-stat-sub">{fmt$(data.total_gain_dollar)}</span>
            </div>
            <div className="h-stat">
              <span className="h-stat-label">Positions</span>
              <span className="h-stat-value">{data.position_count}</span>
              <span className="h-stat-sub">{data.uploaded_at?new Date(data.uploaded_at).toLocaleDateString():'—'}</span>
            </div>
          </div>

          <Alerts alerts={data.alerts} />

          <div className="holdings-body">
            <MiniDoughnut title="Holdings Breakdown" labels={chartLabels} data={chartData} />
            <div className="holdings-table-box">
              <h3>All Positions</h3>
              <PositionsTable positions={data.positions} />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ── AI Analyst Report Tab ────────────────────────────────────────────────────
const ReportTab = () => {
  const [report,   setReport]   = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);

  const fetchReport = async (force=false) => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/report${force?'?force=true':''}`);
      const d   = await res.json();
      if (d.error && !d.report) { setError(d.error); setReport(null); }
      else setReport(d);
    } catch(e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchReport(); }, []);

  // Parse markdown-style sections into structured blocks
  const parseSections = (text) => {
    if (!text) return [];
    return text.split(/\n(?=## )/).map(block => {
      const lines   = block.trim().split('\n');
      const heading = lines[0].replace(/^## /, '').trim();
      const body    = lines.slice(1).join('\n').trim();
      return { heading, body };
    }).filter(s => s.heading);
  };

  const sections = report?.report ? parseSections(report.report) : [];

  const sectionIcon = (heading) => {
    if (heading.includes('Buy'))       return 'buy';
    if (heading.includes('Overbought') || heading.includes('Alert')) return 'alert';
    if (heading.includes('Rebalanc'))  return 'rebalance';
    if (heading.includes('Dividend'))  return 'dividend';
    if (heading.includes('Tax'))       return 'tax';
    return 'default';
  };

  return (
    <div className="report-tab">
      <div className="report-toolbar">
        <div>
          <strong>AI Analyst Report</strong>
          {report?.generated_at && (
            <span className="report-age"> — generated {new Date(report.generated_at).toLocaleString()}</span>
          )}
          {report?.model && <span className="report-model"> via {report.model}</span>}
        </div>
        <div style={{display:'flex',gap:10}}>
          <button className="btn-upload" onClick={()=>fetchReport(false)} disabled={loading}>
            {loading ? '⏳ Generating…' : '📋 Load Report'}
          </button>
          <button className="btn-regenerate" onClick={()=>fetchReport(true)} disabled={loading} title="Force regenerate">
            🔄 Regenerate
          </button>
        </div>
      </div>

      {error && <div className="report-error">⚠️ {error}</div>}

      {loading && (
        <div className="report-loading">
          <div className="report-spinner" />
          <p>Analysing your portfolio with {report?.model || 'Ollama'}…<br/>
          <small>This runs RSI, moving averages, and fundamentals on your holdings — usually takes 30–60 seconds.</small></p>
        </div>
      )}

      {!loading && report?.summary && (
        <div className="report-summary-row">
          <div className="rs-chip"><span className="rs-label">Portfolio Value</span><span className="rs-val">{fmt$(report.summary.total_value)}</span></div>
          <div className={`rs-chip ${report.summary.total_gl>=0?'pos':'neg'}`}>
            <span className="rs-label">Total Gain/Loss</span>
            <span className="rs-val">{fmtPct(report.summary.total_gl_pct)}</span>
            <span className="rs-sub">{fmt$(report.summary.total_gl)}</span>
          </div>
          <div className="rs-chip"><span className="rs-label">Positions</span><span className="rs-val">{report.summary.position_count}</span></div>
          {report.summary.overbought?.length > 0 && (
            <div className="rs-chip warn"><span className="rs-label">Overbought</span><span className="rs-val">{report.summary.overbought.map(p=>p.symbol).join(', ')}</span></div>
          )}
          {report.summary.oversold?.length > 0 && (
            <div className="rs-chip good"><span className="rs-label">Oversold</span><span className="rs-val">{report.summary.oversold.map(p=>p.symbol).join(', ')}</span></div>
          )}
        </div>
      )}

      {!loading && sections.length > 0 && (
        <div className="report-sections">
          {sections.map((s,i) => (
            <div key={i} className={`report-section report-section--${sectionIcon(s.heading)}`}>
              <h3 className="report-section-heading">{s.heading}</h3>
              <div className="report-section-body">
                {s.body.split('\n').filter(l=>l.trim()).map((line,j) => (
                  <p key={j} className={line.startsWith('-')||line.startsWith('•') ? 'report-li' : 'report-p'}>
                    {line.replace(/^\s*[-•]\s*/,'')}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && !report && (
        <div className="empty-state"><p>Click "Load Report" to generate your AI analysis.</p></div>
      )}
    </div>
  );
};

export default Dashboard;
