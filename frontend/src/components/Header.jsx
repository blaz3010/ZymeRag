import React from 'react';
import { Zap, Upload, Database, FlaskConical } from 'lucide-react';

export default function Header({ activeTab, setActiveTab }) {
  return (
    <header className="zymerag-header">
      <div className="header-container">
        <div className="header-brand">
          <div className="brand-badge">
            <Zap size={18} className="fill-current text-white" />
          </div>
          <div className="brand-text">
            <span className="brand-name">ZymeRag</span>
            <span className="brand-sub">Multimodal RAG Engine</span>
          </div>
        </div>

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
          <button
            className={`tab-pill ${activeTab === 'playground' ? 'active' : ''}`}
            onClick={() => setActiveTab('playground')}
          >
            <FlaskConical size={15} />
            <span>RAG Test Lab</span>
            <span className="tab-pill-sparkle">Test</span>
          </button>
        </nav>

        <div className="header-actions">
          <span className="connection-badge">
            <span className="green-pulse"></span>
            Supabase Connected
          </span>
        </div>
      </div>
    </header>
  );
}