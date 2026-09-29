import React from 'react';
import { Zap, Upload, Database, LogOut } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, user, onLogout }) {
  const getInitials = (name) => {
    if (!name) return 'ZR';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  return (
    <header className="zymerag-header">
      <div className="header-container">
        {/* Brand Logo */}
        <div className="header-brand">
          <div className="brand-badge">
            <Zap size={18} className="fill-current text-white" />
          </div>
          <div className="brand-text">
            <span className="brand-name">ZymeRag</span>
            <span className="brand-sub">Multimodal RAG Engine</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="header-tabs">
          <button 
            className={`tab-pill ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            <Upload size={15} />
            <span>Ingest Data</span>
          </button>
          <button 
            className={`tab-pill ${activeTab === 'sources' ? 'active' : ''}`}
            onClick={() => setActiveTab('sources')}
          >
            <Database size={15} />
            <span>Ingested Sources</span>
          </button>
        </nav>

        {/* Right Status Indicator & User Pill */}
        <div className="header-actions">
          <span className="connection-badge">
            <span className="green-pulse"></span>
            Supabase Connected
          </span>
          <div className="user-badge">
            <div className="user-avatar">{getInitials(user?.username)}</div>
            <span className="user-name">{user?.username || 'Zyme Admin'}</span>
          </div>
          {onLogout && (
            <button 
              className="btn-logout-header"
              onClick={onLogout}
              title="Sign Out of ZymeRag"
            >
              <LogOut size={15} />
              <span>Logout</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
