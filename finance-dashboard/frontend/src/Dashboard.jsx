import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const Dashboard = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [topCryptos, setTopCryptos] = useState([]);
  const [topStocks, setTopStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [cryptoLoading, setCryptoLoading] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [assetType, setAssetType] = useState('stock');
  const [apiHealth, setApiHealth] = useState(false);
  const [ollama, setOllama] = useState(null);
  const [activeTab, setActiveTab] = useState('top-cryptos');

  const API_BASE = process.env.REACT_APP_API_URL || '/api';

  useEffect(() => {
    checkHealth();
    // Only fetch on initial load, not auto-refresh to save API tokens
    fetchTopCryptos();
    fetchTopStocks();
    
    // Only health check every 30s, not data refresh
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const response = await fetch(`${API_BASE}/health`);
      const data = await response.json();
      setApiHealth(true);
      setOllama(data.ollama_available);
    } catch (error) {
      setApiHealth(false);
      setOllama(false);
    }
  };

  const fetchTopCryptos = async () => {
    setCryptoLoading(true);
    try {
      const response = await fetch(`${API_BASE}/crypto/top-rated?include_ai=false`);
      if (response.ok) {
        const data = await response.json();
        setTopCryptos(data.top_cryptos || []);
      }
    } catch (error) {
      console.error('Error fetching top cryptos:', error);
    } finally {
      setCryptoLoading(false);
    }
  };

  const fetchTopStocks = async () => {
    setCryptoLoading(true);
    try {
      const response = await fetch(`${API_BASE}/stocks/top-rated?include_ai=false`);
      if (response.ok) {
        const data = await response.json();
        setTopStocks(data.top_stocks || []);
      }
    } catch (error) {
      console.error('Error fetching top stocks:', error);
    } finally {
      setCryptoLoading(false);
    }
  };

  const fetchAsset = async (symbol, type) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, type })
      });
      if (!response.ok) throw new Error('Failed to fetch');
      const result = await response.json();
      const existing = portfolio.findIndex(p => p.symbol === symbol);
      if (existing >= 0) {
        const updated = [...portfolio];
        updated[existing] = result;
        setPortfolio(updated);
      } else {
        setPortfolio([...portfolio, result]);
      }
      setNewSymbol('');
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const removeAsset = (symbol) => {
    setPortfolio(portfolio.filter(p => p.symbol !== symbol));
  };

  const handleRefresh = async () => {
    setCryptoLoading(true);
    await fetchTopStocks();
    await fetchTopCryptos();
    setCryptoLoading(false);
  };

  const handleAddAsset = () => {
    if (newSymbol.trim()) {
      fetchAsset(newSymbol.trim().toUpperCase(), assetType);
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>📊 Finance Dashboard</h1>
        <div className="header-stats">
          <div className={`stat ${apiHealth ? 'healthy' : 'unhealthy'}`}>
            <span className="stat-label">API</span>
            <span className="stat-value">{apiHealth ? '✓' : '✗'}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Top Cryptos</span>
            <span className="stat-value">{topCryptos.length}</span>
          </div>
        </div>
      </header>

      <div className="tabs-section">
        <div className="tabs-controls">
          <div className="tabs">
          <button 
            className={`tab ${activeTab === 'top-stocks' ? 'active' : ''}`}
            onClick={() => setActiveTab('top-stocks')}
          >
            📈 Top Stocks
          </button>
          <button 
            className={`tab ${activeTab === 'top-cryptos' ? 'active' : ''}`}
            onClick={() => setActiveTab('top-cryptos')}
          >
            🏆 Top Cryptos
          </button>
          <button 
            className={`tab ${activeTab === 'portfolio' ? 'active' : ''}`}
            onClick={() => setActiveTab('portfolio')}
          >
            💼 Portfolio
          </button>
          </div>
          <button 
            className="btn-refresh"
            onClick={handleRefresh}
            disabled={cryptoLoading}
            title="Manually refresh top stocks & cryptos"
          >
            {cryptoLoading ? '⏳ Refreshing...' : '🔄 Refresh Data'}
          </button>
        </div>
      </div>

      {activeTab === 'top-stocks' && (
        <section className="top-cryptos-section">
          {cryptoLoading ? (
            <div className="loading">Loading...</div>
          ) : topStocks.length === 0 ? (
            <div className="empty-state"><p>No stock data available. Use Alpha Vantage API key for real data.</p></div>
          ) : (
            <div className="crypto-cards-grid">
              {topStocks.map((stock, idx) => (
                <CryptoCard key={stock.symbol} crypto={stock} rank={idx + 1} />
              ))}
            </div>
          )}
        </section>
      )}

      {activeTab === 'top-cryptos' && (
        <section className="top-cryptos-section">
          {cryptoLoading ? (
            <div className="loading">Loading...</div>
          ) : topCryptos.length === 0 ? (
            <div className="empty-state"><p>No crypto data</p></div>
          ) : (
            <div className="crypto-cards-grid">
              {topCryptos.map((crypto, idx) => (
                <CryptoCard key={crypto.symbol} crypto={crypto} rank={idx + 1} />
              ))}
            </div>
          )}
        </section>
      )}

      {activeTab === 'portfolio' && (
        <>
          <section className="search-section">
            <div className="search-container">
              <input
                type="text"
                placeholder="Enter symbol (AAPL, BTC, ETH)"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddAsset()}
                disabled={loading}
              />
              <select value={assetType} onChange={(e) => setAssetType(e.target.value)} disabled={loading}>
                <option value="stock">Stock</option>
                <option value="crypto">Crypto</option>
              </select>
              <button onClick={handleAddAsset} disabled={loading || !apiHealth} className="btn-primary">
                {loading ? 'Loading...' : 'Add'}
              </button>
            </div>
          </section>
          <section className="portfolio-section">
            {portfolio.length === 0 ? (
              <div className="empty-state"><p>No assets yet</p></div>
            ) : (
              <div className="portfolio-grid">
                {portfolio.map((asset) => (
                  <AssetCard key={asset.symbol} asset={asset} onRemove={removeAsset} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
};

const CryptoCard = ({ crypto, rank }) => {
  const ret24 = crypto.metrics?.return_24h || 0;
  const ret7d = crypto.metrics?.return_7d || 0;
  const ret30d = crypto.metrics?.return_30d || 0;

  return (
    <div className="crypto-score-card">
      <div className="rank-badge">#{rank}</div>
      <h3 className="symbol">{crypto.symbol}</h3>
      <p className="price">${(crypto.price || 0).toFixed(2)}</p>
      
      <div className="score-box">
        <span className="score-num">{(crypto.score || 0).toFixed(1)}</span>
        <span className="score-max">/100</span>
      </div>

      <div className="metrics">
        <div className="metric">
          <span>Momentum</span>
          <span className="metric-val">{(crypto.scores?.momentum || 0).toFixed(1)}</span>
        </div>
        <div className="metric">
          <span>Market</span>
          <span className="metric-val">{(crypto.scores?.market_health || 0).toFixed(1)}</span>
        </div>
      </div>

      <div className="returns">
        <div className={`ret ${ret24 >= 0 ? 'pos' : 'neg'}`}>
          <span>24h</span>
          <span>{ret24 >= 0 ? '+' : ''}{ret24.toFixed(2)}%</span>
        </div>
        <div className={`ret ${ret7d >= 0 ? 'pos' : 'neg'}`}>
          <span>7d</span>
          <span>{ret7d >= 0 ? '+' : ''}{ret7d.toFixed(2)}%</span>
        </div>
        <div className={`ret ${ret30d >= 0 ? 'pos' : 'neg'}`}>
          <span>30d</span>
          <span>{ret30d >= 0 ? '+' : ''}{ret30d.toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
};

const AssetCard = ({ asset, onRemove }) => {
  const data = asset.data || {};
  const isPos = (data.change_percent || 0) >= 0;

  return (
    <div className={`asset-card ${data.data_type || 'stock'}`}>
      <div className="card-top">
        <h3>{asset.symbol}</h3>
        <button onClick={() => onRemove(asset.symbol)} className="btn-remove">✕</button>
      </div>
      <p className="asset-price">${(data.price || 0).toFixed(2)}</p>
      <span className={`change ${isPos ? 'pos' : 'neg'}`}>
        {isPos ? '▲' : '▼'} {Math.abs(data.change_percent || 0).toFixed(2)}%
      </span>
    </div>
  );
};

export default Dashboard;
