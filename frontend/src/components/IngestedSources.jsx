import React, { useState, useEffect, useCallback } from 'react';
import { Search, Plus, ExternalLink, Info, Trash2, AlertCircle, Globe, Loader, FileText, Loader2, Copy, Check, X, FileSpreadsheet, Presentation, RefreshCw, Upload } from 'lucide-react';
import SourceMetadataModal from './SourceMetadataModal';
import DeleteConfirmModal from './DeleteConfirmModal';

const API_BASE = import.meta.env.VITE_API_BASE || '';

// Static fallback only if server cannot be reached at all
const ALL_SOURCES_FALLBACK = [
  {
    id: 'sample-1',
    name: 'ZymeRag Architecture Overview.pdf',
    type: 'Pdf',
    status: 'Ingested',
    chunks: 42,
    url: 'https://arxiv.org/pdf/2312.10997.pdf',
  }
];

export default function IngestedSources({ onNavigateToAdd }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);

  // Chunks viewer modal state
  const [chunksSource, setChunksSource] = useState(null);
  const [chunksText, setChunksText] = useState('');
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunksCopied, setChunksCopied] = useState(false);

  // Replace content modal state
  const [replaceTarget, setReplaceTarget] = useState(null);
  const [replaceFile, setReplaceFile] = useState(null);
  const [isReplacing, setIsReplacing] = useState(false);

  // All sources (fetched from backend /sources/all_sources)
  const [allSources, setAllSources] = useState([]);

  const fetchSources = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    const endpoint = '/sources/all_sources';

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'GET',
        headers: {},
      });

      if (!res.ok) {
        throw new Error(`Failed to fetch sources (${res.status})`);
      }

      const data = await res.json();
      const list = data.sources || [];
      setAllSources(list);
    } catch (err) {
      console.error('Error fetching sources:', err);
      setLoadError('Could not load sources. Please check connection.');
      if (allSources.length === 0) {
        setAllSources([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch all chunks for a specific source via the /sources/show_chunks endpoint
  const fetchChunks = useCallback(async (uuid, type) => {
    setChunksLoading(true);
    setChunksText('');
    try {
      const t = (type || '').toLowerCase();
      const isFeed = t === 'website' || t === 'feed' || t === 'url';
      const url = isFeed
        ? `${API_BASE}/sources/show_chunks?feed_id=${encodeURIComponent(uuid)}`
        : `${API_BASE}/sources/show_chunks?content_id=${encodeURIComponent(uuid)}`;
      const res = await fetch(url, {
        method: 'GET',
        headers: {},
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch chunks (${res.status})`);
      }
      const data = await res.json();
      setChunksText(data.chunks || '');
    } catch (err) {
      console.error('Fetch chunks error:', err);
      setChunksText(`Error loading chunks: ${err.message}`);
    } finally {
      setChunksLoading(false);
    }
  }, []);

  // Fetch sources when viewMode changes
  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const activeSources = allSources;


  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);

    try {
      const formData = new FormData();
      formData.append('id', deleteTarget.id);
      await fetch(`${API_BASE}/delete/delete_content`, {
        method: 'DELETE',
        headers: {},
        body: formData
      });
      setAllSources(prev => prev.filter(s => s.id !== deleteTarget.id));
    } catch (err) {
      setAllSources(prev => prev.filter(s => s.id !== deleteTarget.id));
    } finally {
      setIsDeleting(false);
      setDeleteTarget(null);
    }
  };

  const handleReplaceContent = async () => {
    if (!replaceFile || !replaceTarget) return;
    if (replaceFile.size > 15 * 1024 * 1024) {
      return;
    }
    setIsReplacing(true);
    const formData = new FormData();
    formData.append('content_id', replaceTarget.id);
    formData.append('file', replaceFile);
    formData.append('name', replaceFile.name.substring(0, replaceFile.name.lastIndexOf('.')) || replaceFile.name);

    try {
      const res = await fetch(`${API_BASE}/upload/replace_content`, {
        method: 'POST',
        headers: {},
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        // Update the source in place with new ID
        setAllSources(prev => prev.map(s => s.id === replaceTarget.id ? { ...s, id: data.new_id, name: data.name } : s));
      }
    } catch (err) {
      console.error('Replace error:', err);
    } finally {
      setIsReplacing(false);
      setReplaceTarget(null);
      setReplaceFile(null);
    }
  };

  const filteredSources = activeSources.filter(s => 
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTargetUrl = (item) => {
    if (item.url) return item.url;
    if (item.name && (item.name.startsWith('http://') || item.name.startsWith('https://'))) return item.name;
    return null;
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

      {/* Filter Row: Search */}
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

        </div>
      </div>

      {/* Loading / Error State */}
      {isLoading && (
        <div className="my-sources-loading-bar">
          <Loader size={16} className="animate-spin" />
          <span>Loading ingested sources…</span>
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
              <th>Type</th>
              <th>Vector Chunks</th>
              <th>Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="empty-table-cell">
                  <Loader size={20} className="animate-spin" style={{ margin: '0 auto 8px', display: 'block' }} />
                  Fetching sources…
                </td>
              </tr>
            ) : filteredSources.length === 0 ? (
              <tr>
                <td colSpan={5} className="empty-table-cell">
                  <AlertCircle size={20} className="mx-auto mb-2 text-gray-400" />
                  {searchQuery
                    ? `No ingested sources found matching "${searchQuery}".`
                    : "No ingested sources found. Start by ingesting new data!"
                  }
                </td>
              </tr>
            ) : (
              filteredSources.map((item) => {
                return (
                  <tr key={item.id} className="table-row-item">
                                        <td>
                      <div className="source-title-cell">
                        <span className="source-title-text">{item.name}</span>
                        {getTargetUrl(item) && (
                          <a 
                            href={getTargetUrl(item)} 
                            target="_blank"
                            rel="noopener noreferrer"
                            className="link-external-icon"
                            title={`Open ${item.name} in new tab`}
                          >
                            <ExternalLink size={13} />
                          </a>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`type-tag type-${(item.type || '').toLowerCase() === 'url' ? 'website' : (item.type || '').toLowerCase()}`}>
                        {(item.type || '').toLowerCase() === 'csv' && <FileSpreadsheet size={12} />}
                        {((item.type || '').toLowerCase() === 'pptx' || (item.type || '').toLowerCase() === 'presentation') && <Presentation size={12} />}
                        {((item.type || '').toLowerCase() === 'url' || (item.type || '').toLowerCase() === 'website' || (item.type || '').toLowerCase() === 'feed') && <Globe size={12} />}
                        {(item.type || '').toLowerCase() !== 'csv' && (item.type || '').toLowerCase() !== 'pptx' && (item.type || '').toLowerCase() !== 'presentation' && (item.type || '').toLowerCase() !== 'url' && (item.type || '').toLowerCase() !== 'website' && (item.type || '').toLowerCase() !== 'feed' && <FileText size={12} />}
                        <span>{item.type || 'Document'}</span>
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

                        {/* View Chunks Button */}
                        <button 
                          className="action-pill-btn inspect-pill" 
                          title="View Document Chunks"
                            onClick={() => {
                              setChunksSource(item);
                              fetchChunks(item.id, item.type);
                            }}
                        >
                          <FileText size={13} />
                          <span>View Chunks</span>
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

                        {/* Replace Content Button */}
                        <button
                          className="action-pill-btn inspect-pill"
                          title="Replace with new file"
                          onClick={() => setReplaceTarget(item)}
                        >
                          <RefreshCw size={13} />
                          <span>Replace</span>
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

      {/* Chunks Viewer Modal */}
      {chunksSource && (
        <div className="modal-backdrop" onClick={() => setChunksSource(null)}>
          <div className="modal-card metadata-modal-card" style={{ maxWidth: '700px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-styled">
              <div className="flex-header-title">
                <div className="modal-icon-badge badge-indigo">
                  <FileText size={18} />
                </div>
                <div>
                  <h3 className="modal-title-text">Document Chunks</h3>
                  <p className="modal-subtitle-text">Vectorized text chunks for <strong>{chunksSource.name}</strong></p>
                </div>
              </div>
              <button onClick={() => setChunksSource(null)} className="modal-close-icon-btn">
                <X size={16} />
              </button>
            </div>

            <div className="modal-body-container" style={{ paddingBottom: 8 }}>
              <div className="metadata-info-box mb-4">
                <div className="flex-between mb-1">
                  <div className="info-label">CHUNKS CONTENT</div>
                  <button className="copy-uuid-btn" onClick={() => {
                    navigator.clipboard.writeText(chunksText);
                    setChunksCopied(true);
                    setTimeout(() => setChunksCopied(false), 2000);
                  }}>
                    {chunksCopied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                    <span>{chunksCopied ? 'Copied' : 'Copy All'}</span>
                  </button>
                </div>
                {chunksLoading ? (
                  <div className="loading-spinner-box" style={{ padding: '40px 0' }}>
                    <Loader2 className="animate-spin text-indigo" size={28} />
                    <span className="uploading-text">Loading chunks…</span>
                  </div>
                ) : chunksText.trim() === '' ? (
                  <div className="empty-table-cell" style={{ padding: '30px 0' }}>
                    <p className="info-value-text" style={{ color: '#64748b' }}>No chunks found for this source.</p>
                  </div>
                ) : (
                  <div className="code-uuid-block" style={{ 
                    background: '#f8fafc', 
                    color: '#0f172a', 
                    fontSize: '12.5px', 
                    maxHeight: '420px', 
                    overflowY: 'auto', 
                    whiteSpace: 'pre-wrap', 
                    lineHeight: '1.6' 
                  }}>
                    {chunksText}
                  </div>
                )}
              </div>
            </div>

            <div className="modal-footer-styled">
              <button onClick={() => setChunksSource(null)} className="primary-modal-btn">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Replace Content Modal */}
      {replaceTarget && (
        <div className="modal-backdrop" onClick={() => { setReplaceTarget(null); setReplaceFile(null); }}>
          <div className="modal-card metadata-modal-card" style={{ maxWidth: '560px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-styled">
              <div className="flex-header-title">
                <div className="modal-icon-badge badge-emerald">
                  <RefreshCw size={18} />
                </div>
                <div>
                  <h3 className="modal-title-text">Replace Content</h3>
                  <p className="modal-subtitle-text">Swap <strong>{replaceTarget.name}</strong> with a new file</p>
                </div>
              </div>
              <button
                onClick={() => { setReplaceTarget(null); setReplaceFile(null); }}
                className="modal-close-icon-btn"
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body-container">
              <div className="metadata-info-box mb-4">
                <div className="info-label">SOURCE ID (PRESERVED)</div>
                <div className="info-value-text" style={{ fontFamily: 'monospace', fontSize: '13px' }}>
                  {replaceTarget.id}
                </div>
              </div>

              <label className="custom-dropzone" style={{ margin: 0 }}>
                <input
                  type="file"
                  accept=".pdf,.docx,.csv,.pptx,image/*,video/*,audio/*"
                  onChange={(e) => {
                    if (e.target.files[0]) {
                      setReplaceFile(e.target.files[0]);
                    }
                  }}
                />
                {isReplacing ? (
                  <div className="loading-spinner-box">
                    <Loader2 className="animate-spin text-emerald" size={28} />
                    <span className="uploading-text">Replacing content...</span>
                  </div>
                ) : (
                  <>
                    <Upload className="dropzone-svg-icon text-emerald" size={28} />
                    <div className="dropzone-main-text">
                      {replaceFile ? replaceFile.name : 'Drop new file or browse'}
                    </div>
                    <span className="dropzone-sub-text">Supported: .pdf, .docx, .csv, .pptx, images, video, audio (up to 15MB)</span>
                  </>
                )}
              </label>
            </div>

            <div className="modal-footer-styled">
              <button
                onClick={() => { setReplaceTarget(null); setReplaceFile(null); }}
                className="primary-modal-btn"
                style={{ background: '#6b7280' }}
              >
                Cancel
              </button>
              <button
                onClick={handleReplaceContent}
                className="primary-modal-btn"
                disabled={!replaceFile || isReplacing}
              >
                {isReplacing ? (
                  <span className="btn-spinner-content">
                    <Loader2 className="animate-spin" size={14} />
                    <span>Replacing...</span>
                  </span>
                ) : (
                  'Replace Content'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
