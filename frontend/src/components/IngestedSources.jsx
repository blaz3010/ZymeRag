import React, { useState, useEffect, useCallback } from 'react';
import { Search, Plus, ExternalLink, Info, Trash2, AlertCircle, User, Globe, Loader } from 'lucide-react';
import SourceMetadataModal from './SourceMetadataModal';
import DeleteConfirmModal from './DeleteConfirmModal';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// Static fallback only if server cannot be reached at all
const ALL_SOURCES_FALLBACK = [
  { 
    id: 'sample-1', 
    name: 'ZymeRag Architecture Overview.pdf', 
    type: 'Pdf', 
    status: 'Ingested', 
    chunks: 42,
    url: 'https://arxiv.org/pdf/2312.10997.pdf',
    is_mine: false,
    owner: 'System'
  }
];

export default function IngestedSources({ onNavigateToAdd }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [viewMode, setViewMode] = useState('all'); // 'all' or 'mine'
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);

  // All sources (fetched from backend /sources/all_sources)
  const [allSources, setAllSources] = useState([]);
  // My sources (fetched from backend /sources/my_sources)
  const [mySources, setMySources] = useState([]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('zymerag_access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const fetchSources = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    const endpoint = viewMode === 'mine' ? '/sources/my_sources' : '/sources/all_sources';

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'GET',
        headers: getAuthHeaders(),
        credentials: 'include',
      });

      if (!res.ok) {
        throw new Error(`Failed to fetch sources (${res.status})`);
      }

      const data = await res.json();
      const list = data.sources || [];
      if (viewMode === 'mine') {
        setMySources(list);
      } else {
        setAllSources(list);
      }
    } catch (err) {
      console.error('Error fetching sources:', err);
      setLoadError(`Could not load ${viewMode === 'mine' ? 'your' : 'all'} sources. Please check connection.`);
      if (viewMode === 'all' && allSources.length === 0) {
        setAllSources([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [viewMode]);

  // Fetch sources when viewMode changes
  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const activeSources = viewMode === 'all' ? allSources : mySources;


  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);

    try {
      const token = localStorage.getItem('zymerag_access_token');
      const formData = new FormData();
      formData.append('id', deleteTarget.id);
      await fetch(`${API_BASE}/delete/delete_content`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData
      });
      // Remove from both lists
      setAllSources(prev => prev.filter(s => s.id !== deleteTarget.id));
      setMySources(prev => prev.filter(s => s.id !== deleteTarget.id));
    } catch (err) {
      setAllSources(prev => prev.filter(s => s.id !== deleteTarget.id));
      setMySources(prev => prev.filter(s => s.id !== deleteTarget.id));
    } finally {
      setIsDeleting(false);
      setDeleteTarget(null);
    }
  };

  const filteredSources = activeSources.filter(s => 
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTargetUrl = (item) => {
    if (item.url) return item.url;
    if (item.name.startsWith('http://') || item.name.startsWith('https://')) return item.name;
    return 'https://github.com/armanphaugat/ZymeRag';
  };

  return (
    <div className="workspace-container">
      {/* Workspace Header */}
      <div className="workspace-header">
        <div>
          <div className="title-row">
            <h1 className="workspace-title">Ingested Sources</h1>
            <span className="count-badge-pill">{activeSources.length}</span>
          </div>
          <p className="workspace-subtitle">
            Search, inspect, and manage vector embeddings stored in Supabase pgvector
          </p>
        </div>

        <button className="primary-action-btn" onClick={onNavigateToAdd}>
          <Plus size={16} />
          <span>Ingest New Data</span>
        </button>
      </div>

      {/* Filter Row: Search + View Mode Toggle */}
      <div className="search-row">
        <div className="sources-filter-row">
          <div className="search-bar-box">
            <Search size={16} className="search-icon-svg" />
            <input 
              type="text" 
              placeholder="Search ingested files, URLs, or document names..." 
              className="search-input-field"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="clear-search-btn" onClick={() => setSearchQuery('')}>
                &times;
              </button>
            )}
          </div>

          {/* View Mode Toggle */}
          <div className="view-mode-toggle" id="sources-view-toggle">
            <button 
              className={`view-mode-btn ${viewMode === 'all' ? 'active' : ''}`}
              onClick={() => setViewMode('all')}
              id="view-all-sources-btn"
            >
              <Globe size={14} />
              <span>All Sources</span>
            </button>
            <button 
              className={`view-mode-btn ${viewMode === 'mine' ? 'active' : ''}`}
              onClick={() => setViewMode('mine')}
              id="view-my-sources-btn"
            >
              <User size={14} />
              <span>My Sources</span>
            </button>
          </div>
        </div>
      </div>

      {/* Loading / Error State */}
      {isLoading && (
        <div className="my-sources-loading-bar">
          <Loader size={16} className="animate-spin" />
          <span>Loading {viewMode === 'mine' ? 'your' : 'all'} ingested sources…</span>
        </div>
      )}

      {loadError && !isLoading && (
        <div className="my-sources-error-bar">
          <AlertCircle size={16} />
          <span>{loadError}</span>
          <button className="retry-btn" onClick={fetchSources}>Retry</button>
        </div>
      )}

      {/* Sources Data Table */}
      <div className="custom-table-card">
        <table className="custom-data-table">
          <thead>
            <tr>
              <th>Source Name</th>
              <th>Owner</th>
              <th>Type</th>
              <th>Vector Chunks</th>
              <th>Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="empty-table-cell">
                  <Loader size={20} className="animate-spin" style={{ margin: '0 auto 8px', display: 'block' }} />
                  Fetching {viewMode === 'mine' ? 'your' : 'all'} sources…
                </td>
              </tr>
            ) : filteredSources.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty-table-cell">
                  <AlertCircle size={20} className="mx-auto mb-2 text-gray-400" />
                  {viewMode === 'mine' && !searchQuery
                    ? "You haven't ingested any sources yet. Start by ingesting new data!"
                    : `No ingested sources found matching "${searchQuery}".`
                  }
                </td>
              </tr>
            ) : (
              filteredSources.map((item) => {
                const targetUrl = getTargetUrl(item);
                const isMine = item.is_mine || viewMode === 'mine';
                return (
                  <tr key={item.id} className="table-row-item">
                    <td>
                      <div className="source-title-cell">
                        <span className="source-title-text">{item.name}</span>
                        <a 
                          href={targetUrl} 
                          target="_blank"
                          rel="noopener noreferrer"
                          className="link-external-icon"
                          title={`Open ${item.name} in new tab`}
                        >
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    </td>
                    <td>
                      <span className={`owner-badge ${isMine ? 'owner-badge-you' : 'owner-badge-other'}`}>
                        {isMine ? 'You' : (item.owner || 'Shared')}
                      </span>
                    </td>
                    <td>
                      <span className={`type-tag type-${item.type.toLowerCase()}`}>
                        {item.type}
                      </span>
                    </td>
                    <td>
                      <span className="chunks-badge">{item.chunks} chunks</span>
                    </td>
                    <td>
                      <span className="status-badge-ingested">
                        <span className="pulse-dot-green"></span>
                        Ingested
                      </span>
                    </td>
                    <td>
                      <div className="table-actions-cell">
                        {/* High-End Inspect Button */}
                        <button 
                          className="action-pill-btn inspect-pill" 
                          title="Inspect Metadata"
                          onClick={() => setSelectedSource(item)}
                        >
                          <Info size={13} />
                          <span>Inspect</span>
                        </button>

                        {/* High-End Delete Button */}
                        <button 
                          className="action-pill-btn delete-pill" 
                          title="Delete Source"
                          onClick={() => setDeleteTarget(item)}
                        >
                          <Trash2 size={13} />
                          <span>Delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Metadata Inspector Modal */}
      {selectedSource && (
        <SourceMetadataModal 
          source={selectedSource} 
          onClose={() => setSelectedSource(null)} 
        />
      )}

      {/* Delete Warning Confirmation Modal */}
      {deleteTarget && (
        <DeleteConfirmModal 
          sourceName={deleteTarget.name}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
          isDeleting={isDeleting}
        />
      )}
    </div>
  );
}
