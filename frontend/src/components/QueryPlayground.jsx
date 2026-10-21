import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  FlaskConical,
  Send,
  Upload,
  CheckSquare,
  Square,
  Search,
  FileText,
  Globe,
  User,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Layers,
  Filter,
  RefreshCw,
  Clock,
  Trash2,
  AlertCircle,
  FileSpreadsheet,
  Image as ImageIcon,
  CheckCircle2,
  Loader2,
  ExternalLink,
  History,
  X,
  PlusCircle,
  Info,
  Database,
  ArrowRight,
  Zap,
  MessageSquare,
  Bot,
  Cpu,
  BookOpen,
  BarChart3,
  Target,
  Hash
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export default function QueryPlayground({ onNavigateToIngest }) {
  // Source selection & listing state
  const [sourceScope, setSourceScope] = useState('all'); // 'all' or 'mine'
  const [sources, setSources] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourceSearch, setSourceSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  // Quick Ingest Modal (optional secondary shortcut)
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadTab, setUploadTab] = useState('file'); // 'file' | 'url'
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadUrl, setUploadUrl] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  // RAG Query & Testing State
  const [question, setQuestion] = useState('');
  const [querying, setQuerying] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [expandedChunks, setExpandedChunks] = useState({});
  const [copiedId, setCopiedId] = useState(null);
  const [retrievalMode, setRetrievalMode] = useState('hybrid'); // 'hybrid' | 'fullcontext'

  // Query History & Drawer
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
  const [queryHistory, setQueryHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Toast Notification
  const [toast, setToast] = useState(null);
  const chatBottomRef = useRef(null);
  const textareaRef = useRef(null);
  const [textareaHeight, setTextareaHeight] = useState(48);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };

  const getAuthHeaders = () => {
    const token = localStorage.getItem('zymerag_access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  // 1. Fetch queryable sources from backend based on selected scope
  const fetchSources = async (scope = sourceScope) => {
    setSourcesLoading(true);
    try {
      const endpoint = scope === 'mine' ? '/query/my_queryable_sources' : '/query/all_queryable_sources';
      let res = await fetch(`${API_BASE}${endpoint}`, {
        headers: getAuthHeaders(),
      });
      let fetched = [];
      if (res.ok) {
        const data = await res.json();
        fetched = data.sources || [];
      }

      // If empty or endpoint fallback needed, try /sources/ route
      if (fetched.length === 0) {
        const fallbackEndpoint = scope === 'mine' ? '/sources/my_sources' : '/sources/all_sources';
        const resSources = await fetch(`${API_BASE}${fallbackEndpoint}`, {
          headers: getAuthHeaders(),
        });
        if (resSources.ok) {
          const sData = await resSources.json();
          fetched = sData.sources || [];
        }
      }

      setSources(fetched);

      // Automatically select all available ingested sources by default for immediate testing
      if (fetched.length > 0) {
        setSelectedIds(new Set(fetched.map((s) => s.id)));
      } else {
        setSelectedIds(new Set());
      }
    } catch (err) {
      showToast(`Error connecting to server: ${err.message}`, 'error');
    } finally {
      setSourcesLoading(false);
    }
  };

  // 2. Fetch user's saved query history
  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/query/history`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setQueryHistory(data.history || []);
      }
    } catch (err) {
      console.error('History fetch error:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
    fetchHistory();
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, querying]);

  // Auto-grow textarea so long questions never force horizontal scroll
  const adjustTextareaHeight = useCallback((el) => {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
    setTextareaHeight(el.scrollHeight);
  }, []);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.max(el.scrollHeight, 48) + 'px';
      setTextareaHeight(Math.max(el.scrollHeight, 48));
    }
  }, [question]);

  // Toggle single source selection
  const toggleSource = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Select / Deselect All
  const selectAllSources = () => {
    setSelectedIds(new Set(filteredSources.map((s) => s.id)));
  };

  const deselectAllSources = () => {
    setSelectedIds(new Set());
  };

  // Filter sources by search term and file type
  const filteredSources = sources.filter((s) => {
    const matchesSearch = (s.name || '').toLowerCase().includes(sourceSearch.toLowerCase());
    if (!matchesSearch) return false;
    if (typeFilter === 'all') return true;
    const typeLower = (s.type || '').toLowerCase();
    if (typeFilter === 'pdf') return typeLower === 'pdf';
    if (typeFilter === 'url') return typeLower === 'url' || typeLower === 'website';
    if (typeFilter === 'docx') return typeLower === 'docx' || typeLower === 'word';
    if (typeFilter === 'csv') return typeLower === 'csv';
    if (typeFilter === 'image') return ['image', 'jpeg', 'png', 'jpg'].includes(typeLower);
    return true;
  });

  // Calculate counts per filter
  const filterCounts = {
    all: sources.length,
    pdf: sources.filter((s) => (s.type || '').toLowerCase() === 'pdf').length,
    url: sources.filter((s) => ['url', 'website'].includes((s.type || '').toLowerCase())).length,
    docx: sources.filter((s) => ['docx', 'word'].includes((s.type || '').toLowerCase())).length,
    image: sources.filter((s) => ['image', 'png', 'jpg', 'jpeg'].includes((s.type || '').toLowerCase())).length,
    csv: sources.filter((s) => (s.type || '').toLowerCase() === 'csv').length,
  };

  // Total chunks across selected
  const selectedChunksCount = sources
    .filter((s) => selectedIds.has(s.id))
    .reduce((acc, s) => acc + (s.chunks || 0), 0);

  // Handle Quick Ingest if user desires
  const handleQuickUpload = async (e) => {
    e.preventDefault();
    setUploadError('');
    setUploadSuccess('');

    if (uploadTab === 'file') {
      if (!uploadFile) {
        setUploadError('Please select a file to ingest');
        return;
      }
      setUploading(true);
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('name', uploadFile.name.substring(0, uploadFile.name.lastIndexOf('.')) || uploadFile.name);

      const ext = uploadFile.name.split('.').pop()?.toLowerCase();
      let endpoint = '/upload/pdf';
      if (ext === 'docx') endpoint = '/upload/docx';
      else if (['png', 'jpg', 'jpeg'].includes(ext)) endpoint = '/upload/image';
      else if (['csv', 'xlsx', 'xls'].includes(ext)) endpoint = '/upload/csv';

      try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData,
        });
        const data = await res.json();
        if (res.ok) {
          setUploadSuccess(`Ingested "${uploadFile.name}" successfully!`);
          setUploadFile(null);
          await fetchSources();
          if (data.id) {
            setSelectedIds((prev) => new Set([...prev, data.id]));
          }
          setTimeout(() => setShowUploadModal(false), 1400);
        } else {
          setUploadError(data.detail || 'Upload failed');
        }
      } catch (err) {
        setUploadError(`Network error: ${err.message}`);
      } finally {
        setUploading(false);
      }
    } else {
      if (!uploadUrl.trim()) {
        setUploadError('Please enter a website URL');
        return;
      }
      setUploading(true);
      const formData = new FormData();
      formData.append('url', uploadUrl.trim());

      try {
        const res = await fetch(`${API_BASE}/upload/upload_website`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData,
        });
        const data = await res.json();
        if (res.ok) {
          setUploadSuccess('Website crawled & vectorized successfully!');
          setUploadUrl('');
          await fetchSources();
          if (data.id) {
            setSelectedIds((prev) => new Set([...prev, data.id]));
          }
          setTimeout(() => setShowUploadModal(false), 1400);
        } else {
          setUploadError(data.detail || 'Website ingestion failed');
        }
      } catch (err) {
        setUploadError(`Network error: ${err.message}`);
      } finally {
        setUploading(false);
      }
    }
  };

  // Execute RAG Query
  const handleSendQuery = async (queryText = question) => {
    const prompt = (queryText || '').trim();
    if (!prompt) return;

    if (selectedIds.size === 0) {
      showToast('Please check at least 1 document on the left to query against', 'warning');
      return;
    }

    const activeIds = Array.from(selectedIds);
    const activeDocNames = sources
      .filter((s) => selectedIds.has(s.id))
      .map((s) => s.name);

    const startTime = performance.now();
    const userMsgId = `msg-user-${Date.now()}`;
    const assistantMsgId = `msg-assistant-${Date.now()}`;

    // Add user message
    const userMessage = {
      id: userMsgId,
      role: 'user',
      question: prompt,
      targetedDocCount: activeIds.length,
      targetedDocNames: activeDocNames,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages((prev) => [...prev, userMessage]);
    setQuestion('');
    setTextareaHeight(48);
    if (textareaRef.current) textareaRef.current.style.height = '48px';
    setQuerying(true);

    try {
      const endpoint = retrievalMode === 'fullcontext' ? '/query/query_fullcontext' : '/query/user_query';
      const isFullContext = retrievalMode === 'fullcontext';
      let res;
      if (isFullContext) {
        const params = new URLSearchParams();
        params.append('question', prompt);
        activeIds.forEach((id) => params.append('ids', id));
        res = await fetch(`${API_BASE}${endpoint}?${params.toString()}`, {
          method: 'GET',
          headers: {
            ...getAuthHeaders(),
          },
        });
      } else {
        res = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify({
            question: prompt,
            selected_ids: activeIds,
          }),
        });
      }

      const latencyMs = Math.round(performance.now() - startTime);

      if (res.ok) {
        const data = await res.json();
        const answer = typeof data === 'string' ? data : (data.answer ?? '');
        const assistantMessage = {
          id: assistantMsgId,
          role: 'assistant',
          queryId: typeof data === 'object' ? data.query_id : undefined,
          answer,
          chunksFound: (typeof data === 'object' ? (data.chunks_found ?? (data.chunks?.length || 0)) : 0),
          sourcesQueried: (typeof data === 'object' ? (data.sources_queried ?? activeIds.length) : activeIds.length),
          chunks: (typeof data === 'object' ? (data.chunks || []) : []),
          latencyMs,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          retrievalMode,
        };
        setChatMessages((prev) => [...prev, assistantMessage]);
        fetchHistory(); // Refresh DB query history
      } else {
        const errData = await res.json().catch(() => ({}));
        const errorMessage = {
          id: assistantMsgId,
          role: 'assistant',
          isError: true,
          answer: errData.detail || 'Failed to generate answer from selected documents.',
          chunksFound: 0,
          latencyMs,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          retrievalMode,
        };
        setChatMessages((prev) => [...prev, errorMessage]);
      }
    } catch (err) {
      const latencyMs = Math.round(performance.now() - startTime);
      setChatMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: 'assistant',
          isError: true,
          answer: `Network error connecting to RAG pipeline: ${err.message}`,
          chunksFound: 0,
          latencyMs,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          retrievalMode,
        },
      ]);
    } finally {
      setQuerying(false);
    }
  };

  // Delete query from DB history
  const handleDeleteHistoryItem = async (queryId, e) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${API_BASE}/query/history/${queryId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setQueryHistory((prev) => prev.filter((q) => q.query_id !== queryId));
        showToast('Query deleted from history', 'info');
      }
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  // Copy answer to clipboard
  const copyAnswer = (text, msgId) => {
    navigator.clipboard.writeText(text);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Render file type badge and icon
  const getSourceIcon = (type) => {
    const t = (type || '').toLowerCase();
    if (t === 'pdf') return <FileText size={14} />;
    if (t === 'url' || t === 'website') return <Globe size={14} />;
    if (t === 'docx' || t === 'word') return <FileText size={14} />;
    if (t === 'csv') return <FileSpreadsheet size={14} />;
    if (['image', 'png', 'jpg', 'jpeg'].includes(t)) return <ImageIcon size={14} />;
    return <FileText size={14} />;
  };

  const getSourceTypeClass = (type) => {
    const t = (type || '').toLowerCase();
    if (t === 'pdf') return 'qp-type-pdf';
    if (t === 'url' || t === 'website') return 'qp-type-url';
    if (t === 'docx' || t === 'word') return 'qp-type-docx';
    if (t === 'csv') return 'qp-type-csv';
    if (['image', 'png', 'jpg', 'jpeg'].includes(t)) return 'qp-type-image';
    return 'qp-type-generic';
  };

  // Quick Prompt suggestion chips
  const promptSuggestions = [
    {
      icon: <BookOpen size={18} />,
      title: 'Summarize Key Findings',
      prompt: 'Summarize the core findings, conclusions, and objectives across the selected documents.',
      gradient: 'qp-suggestion-gradient-1',
    },
    {
      icon: <Cpu size={18} />,
      title: 'Technical Deep Dive',
      prompt: 'What are the main technical methods, architectures, or implementation constraints described?',
      gradient: 'qp-suggestion-gradient-2',
    },
    {
      icon: <BarChart3 size={18} />,
      title: 'Extract Data & Metrics',
      prompt: 'Extract all specific quantitative metrics, performance stats, and numerical data points mentioned.',
      gradient: 'qp-suggestion-gradient-3',
    },
    {
      icon: <AlertCircle size={18} />,
      title: 'Risks & Limitations',
      prompt: 'What are the key limitations, challenges, risks, or edge cases discussed in these documents?',
      gradient: 'qp-suggestion-gradient-4',
    },
  ];

  return (
    <div className="workspace-container">
      {/* Toast Notification */}
      {toast && (
        <div className={`qp-toast qp-toast-${toast.type}`}>
          {toast.type === 'error' && <AlertCircle size={16} />}
          {toast.type === 'warning' && <AlertCircle size={16} />}
          {toast.type === 'success' && <CheckCircle2 size={16} />}
          {toast.type === 'info' && <Info size={16} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* ===== HERO HEADER ===== */}
      <div className="workspace-header-center">
        <div className="gradient-badge-small">
          <FlaskConical size={14} />
          <span>RAG Testing Lab</span>
        </div>
        <h1 className="title-hero">Query Playground</h1>
        <p className="subtitle-hero">
          Test retrieval accuracy and synthesis quality against your ingested knowledge base in real time.
        </p>
      </div>

      {/* Action bar: History + Ingest */}
      <div className="qp-action-bar">
        <button
          className="qp-btn qp-btn-ghost"
          onClick={() => {
            setShowHistoryDrawer(!showHistoryDrawer);
            fetchHistory();
          }}
        >
          <History size={15} />
          <span>History</span>
          {queryHistory.length > 0 && <span className="qp-btn-badge">{queryHistory.length}</span>}
        </button>

        {onNavigateToIngest && (
          <button
            className="qp-btn qp-btn-primary-outline"
            onClick={onNavigateToIngest}
          >
            <PlusCircle size={15} />
            <span>Ingest Data</span>
          </button>
        )}
      </div>

      {/* ===== MAIN SPLIT LAYOUT ===== */}
      <div className="qp-layout">
        {/* ===== LEFT: SOURCE SELECTOR ===== */}
        <aside className="qp-sidebar">
          <div className="qp-sidebar-header">
            <div className="qp-sidebar-title-row">
              <div className="qp-sidebar-icon-wrap">
                <Database size={16} />
              </div>
              <div>
                <h2 className="qp-sidebar-title">Knowledge Sources</h2>
                <p className="qp-sidebar-subtitle">Select documents to query against</p>
              </div>
            </div>
            <div className={`qp-counter ${selectedIds.size > 0 ? 'qp-counter-active' : ''}`}>
              {selectedIds.size}/{sources.length}
            </div>
          </div>

          {/* Scope Toggle */}
          <div className="qp-scope-toggle" id="playground-scope-toggle">
            <button
              type="button"
              className={`qp-scope-btn ${sourceScope === 'all' ? 'active' : ''}`}
              onClick={() => {
                setSourceScope('all');
                fetchSources('all');
              }}
            >
              <Globe size={13} />
              <span>All Sources</span>
            </button>
            <button
              type="button"
              className={`qp-scope-btn ${sourceScope === 'mine' ? 'active' : ''}`}
              onClick={() => {
                setSourceScope('mine');
                fetchSources('mine');
              }}
            >
              <User size={13} />
              <span>My Sources</span>
            </button>
          </div>

          {/* Search & Batch Controls */}
          <div className="qp-search-row">
            <div className="qp-search-field">
              <Search size={14} className="qp-search-icon" />
              <input
                type="text"
                placeholder="Filter sources…"
                value={sourceSearch}
                onChange={(e) => setSourceSearch(e.target.value)}
                className="qp-search-input"
              />
              {sourceSearch && (
                <button className="qp-search-clear" onClick={() => setSourceSearch('')}>
                  <X size={12} />
                </button>
              )}
            </div>
            <div className="qp-batch-btns">
              <button className="qp-mini-btn" onClick={selectAllSources} title="Select all">
                <CheckSquare size={13} />
              </button>
              <button className="qp-mini-btn" onClick={deselectAllSources} title="Deselect all">
                <Square size={13} />
              </button>
              <button
                className="qp-mini-btn"
                onClick={() => fetchSources(sourceScope)}
                title="Refresh"
              >
                <RefreshCw size={13} className={sourcesLoading ? 'qp-spin' : ''} />
              </button>
            </div>
          </div>

          {/* Type Filter Chips */}
          <div className="qp-type-chips">
            {[
              { id: 'all', label: 'All', count: filterCounts.all },
              { id: 'pdf', label: 'PDF', count: filterCounts.pdf },
              { id: 'url', label: 'Web', count: filterCounts.url },
              { id: 'docx', label: 'Doc', count: filterCounts.docx },
              { id: 'image', label: 'Img', count: filterCounts.image },
              { id: 'csv', label: 'CSV', count: filterCounts.csv },
            ]
              .filter((f) => f.id === 'all' || f.count > 0)
              .map((f) => (
                <button
                  key={f.id}
                  className={`qp-chip ${typeFilter === f.id ? 'active' : ''}`}
                  onClick={() => setTypeFilter(f.id)}
                >
                  {f.label}
                  <span className="qp-chip-num">{f.count}</span>
                </button>
              ))}
          </div>

          {/* Source Cards List */}
          <div className="qp-source-list">
            {sourcesLoading ? (
              <div className="qp-source-empty">
                <Loader2 size={28} className="qp-spin qp-spin-indigo" />
                <span>Loading documents…</span>
              </div>
            ) : filteredSources.length === 0 ? (
              <div className="qp-source-empty">
                <div className="qp-empty-icon-wrap">
                  <Database size={24} />
                </div>
                <p className="qp-empty-title">No documents found</p>
                <p className="qp-empty-desc">
                  {sourceSearch
                    ? 'Try a different search term.'
                    : `No sources in ${sourceScope === 'mine' ? 'your uploads' : 'the knowledge base'}.`}
                </p>
                {sourceSearch ? (
                  <button className="qp-btn qp-btn-xs" onClick={() => setSourceSearch('')}>
                    Clear Search
                  </button>
                ) : onNavigateToIngest ? (
                  <button className="qp-btn qp-btn-xs qp-btn-primary-outline" onClick={onNavigateToIngest}>
                    <PlusCircle size={13} />
                    <span>Ingest Data</span>
                  </button>
                ) : null}
              </div>
            ) : (
              filteredSources.map((source) => {
                const isChecked = selectedIds.has(source.id);
                return (
                  <div
                    key={source.id}
                    className={`qp-source-card ${isChecked ? 'checked' : ''}`}
                    onClick={() => toggleSource(source.id)}
                  >
                    <div className={`qp-custom-checkbox ${isChecked ? 'checked' : ''}`}>
                      {isChecked && <Check size={12} strokeWidth={3} />}
                    </div>

                    <div className="qp-card-body">
                      <div className="qp-card-row-top">
                        <span className={`qp-type-tag ${getSourceTypeClass(source.type)}`}>
                          {getSourceIcon(source.type)}
                          <span>{(source.type || 'file').toUpperCase()}</span>
                        </span>
                        {sourceScope === 'all' && (
                          <span className={`qp-owner-tag ${source.is_mine ? 'qp-owner-you' : 'qp-owner-shared'}`}>
                            {source.is_mine ? 'You' : (source.owner || 'Shared')}
                          </span>
                        )}
                      </div>

                      <div className="qp-card-name" title={source.name}>
                        {source.name}
                      </div>

                      <div className="qp-card-meta">
                        {source.chunks !== undefined && (
                          <span className="qp-meta-item">
                            <Hash size={12} />
                            <span>{source.chunks} chunks</span>
                          </span>
                        )}
                        <span className="qp-meta-divider">·</span>
                        <span className={`qp-status-dot ${isChecked ? 'active' : 'idle'}`} />
                        <span className="qp-meta-status">
                          {isChecked ? 'In Context' : 'Excluded'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer Status */}
          <div className="qp-sidebar-footer">
            <div className={`qp-footer-dot ${selectedIds.size > 0 ? 'online' : ''}`} />
            {selectedIds.size === 0 ? (
              <span className="qp-footer-warn">No sources selected</span>
            ) : (
              <span className="qp-footer-info">
                <strong>{selectedIds.size}</strong> source{selectedIds.size === 1 ? '' : 's'} · {selectedChunksCount} chunks
              </span>
            )}
          </div>
        </aside>

        {/* ===== RIGHT: CHAT CONSOLE ===== */}
        <div className="qp-console">
          {/* Console Top Bar */}
          <div className="qp-console-bar">
            <div className="qp-console-pills">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0', background: '#1a1a1a', padding: '2px', borderRadius: '6px', border: '1px solid #333' }}>
                <button
                  onClick={() => setRetrievalMode('hybrid')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '3px 10px',
                    borderRadius: '4px',
                    border: 'none',
                    background: retrievalMode === 'hybrid' ? '#f59e0b' : 'transparent',
                    color: retrievalMode === 'hybrid' ? '#000' : '#ccc',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: 600
                  }}
                >
                  <Sparkles size={11} />
                  <span>Hybrid</span>
                </button>
                <button
                  onClick={() => setRetrievalMode('fullcontext')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '3px 10px',
                    borderRadius: '4px',
                    border: 'none',
                    background: retrievalMode === 'fullcontext' ? '#f59e0b' : 'transparent',
                    color: retrievalMode === 'fullcontext' ? '#000' : '#ccc',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: 600
                  }}
                >
                  <BookOpen size={11} />
                  <span>Full Context</span>
                </button>
              </div>
              <span className="qp-pill qp-pill-slate">
                <Cpu size={12} />
                <span>Groq LLaMA 3.3 70B</span>
              </span>
              <span className="qp-pill qp-pill-indigo">
                <Target size={12} />
                <span>{selectedIds.size}/{sources.length} sources</span>
              </span>
            </div>

            {chatMessages.length > 0 && (
              <button
                className="qp-btn-text-danger"
                onClick={() => setChatMessages([])}
              >
                <Trash2 size={13} />
                <span>Clear</span>
              </button>
            )}
          </div>

          {/* Chat Canvas */}
          <div className="qp-chat-canvas">
            {chatMessages.length === 0 ? (
              <div className="qp-welcome">
                  <div className="qp-welcome-orb">
                    <div className="qp-welcome-orb-inner">
                      <FlaskConical size={30} />
                    </div>
                    <div className="qp-welcome-orb-ring" />
                  </div>
                  <h2 className="qp-welcome-title">Knowledge Retrieval Lab</h2>
                  <p className="qp-welcome-desc">
                    Select sources on the left and ask questions to evaluate your RAG pipeline's accuracy and retrieval quality.
                    Currently using <strong>{retrievalMode === 'fullcontext' ? 'Full Context' : 'Hybrid RAG'}</strong> mode.
                  </p>

                {/* Suggestion Cards */}
                <div className="qp-suggestions">
                  <span className="qp-suggestions-label">Quick test prompts</span>
                  <div className="qp-suggestions-grid qp-suggestions-centered">
                    {promptSuggestions.map((item, idx) => (
                      <button
                        key={idx}
                        className={`qp-suggestion-card ${item.gradient}`}
                        onClick={() => {
                          setQuestion(item.prompt);
                          handleSendQuery(item.prompt);
                        }}
                      >
                        <div className="qp-suggestion-icon">{item.icon}</div>
                        <div className="qp-suggestion-text">
                          <span className="qp-suggestion-title">{item.title}</span>
                          <span className="qp-suggestion-desc">{item.prompt}</span>
                        </div>
                        <ArrowRight size={14} className="qp-suggestion-arrow" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="qp-messages">
                {chatMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`qp-msg ${msg.role === 'user' ? 'qp-msg-user' : 'qp-msg-ai'}`}
                  >
                    {msg.role === 'user' ? (
                      /* ---- USER MESSAGE ---- */
                      <div className="qp-msg-user-bubble">
                        <div className="qp-msg-user-avatar">
                          <User size={14} />
                        </div>
                        <div className="qp-msg-user-content">
                          <div className="qp-msg-user-header">
                            <span className="qp-msg-user-label">You</span>
                            <span className="qp-msg-time">{msg.timestamp}</span>
                          </div>
                          <div className="qp-msg-user-text">{msg.question}</div>
                          <div className="qp-msg-user-meta">
                            <Layers size={11} />
                            <span>{msg.targetedDocCount} source{msg.targetedDocCount === 1 ? '' : 's'} targeted</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* ---- ASSISTANT MESSAGE ---- */
                      <div className={`qp-msg-ai-card ${msg.isError ? 'qp-msg-error' : ''}`}>
                        <div className="qp-msg-ai-header">
                          <div className="qp-msg-ai-brand">
                            <div className="qp-msg-ai-avatar">
                              <Bot size={15} />
                            </div>
                            <span className="qp-msg-ai-name">Zyme RAG</span>
                            {msg.retrievalMode && (
                              <span className="qp-latency" title="Retrieval mode">
                                {msg.retrievalMode === 'fullcontext' ? <BookOpen size={10} /> : <Sparkles size={10} />}
                                {msg.retrievalMode === 'fullcontext' ? 'Full' : 'Hybrid'}
                              </span>
                            )}
                            {msg.latencyMs && (
                              <span className="qp-latency">
                                <Zap size={10} />
                                {msg.latencyMs}ms
                              </span>
                            )}
                          </div>
                          <div className="qp-msg-ai-actions">
                            <button
                              className="qp-copy-btn"
                              onClick={() => copyAnswer(msg.answer, msg.id)}
                            >
                              {copiedId === msg.id ? (
                                <>
                                  <Check size={12} className="qp-copy-ok" />
                                  <span>Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={12} />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>

                        <div className="qp-msg-ai-body">{msg.answer}</div>

                        {/* Diagnostics */}
                        {!msg.isError && (
                          <div className="qp-diagnostics">
                            <div className="qp-diag-pills">
                              <span className="qp-diag-pill">
                                <FileText size={11} />
                                <strong>{msg.chunksFound}</strong> chunks
                              </span>
                              <span className="qp-diag-pill">
                                <Target size={11} />
                                <strong>{msg.sourcesQueried}</strong> sources
                              </span>
                              {msg.latencyMs && (
                                <span className="qp-diag-pill">
                                  <Clock size={11} />
                                  {(msg.latencyMs / 1000).toFixed(2)}s
                                </span>
                              )}
                            </div>

                            {msg.chunks && msg.chunks.length > 0 && (
                              <button
                                className="qp-chunks-toggle"
                                onClick={() =>
                                  setExpandedChunks((prev) => ({
                                    ...prev,
                                    [msg.id]: !prev[msg.id],
                                  }))
                                }
                              >
                                <span>View Chunks ({msg.chunks.length})</span>
                                {expandedChunks[msg.id] ? (
                                  <ChevronUp size={14} />
                                ) : (
                                  <ChevronDown size={14} />
                                )}
                              </button>
                            )}
                          </div>
                        )}

                        {/* Expandable Chunks */}
                        {expandedChunks[msg.id] && msg.chunks && (
                          <div className="qp-chunks-panel">
                            <div className="qp-chunks-title">Retrieved Context Passages</div>
                            <div className="qp-chunks-list">
                              {msg.chunks.map((chk, cIdx) => (
                                <div key={cIdx} className="qp-chunk-item">
                                  <div className="qp-chunk-header">
                                    <div className="qp-chunk-rank">
                                      <span className="qp-rank-num">#{cIdx + 1}</span>
                                      <span className="qp-chunk-source">{chk.source}</span>
                                    </div>
                                    {chk.score !== null && chk.score !== undefined && (
                                      <span className="qp-chunk-score">
                                        {typeof chk.score === 'number' ? chk.score.toFixed(4) : chk.score}
                                      </span>
                                    )}
                                  </div>
                                  <div className="qp-chunk-text">
                                    {chk.snippet || chk.full_snippet}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {querying && (
                  <div className="qp-thinking">
                    <div className="qp-thinking-dots">
                      <span /><span /><span />
                    </div>
                  <span className="qp-thinking-text">
                    Retrieving from {selectedIds.size} source{selectedIds.size === 1 ? '' : 's'} and synthesizing…
                    {retrievalMode === 'fullcontext' ? ' (Full Context)' : ' (Hybrid RAG)'}
                  </span>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="qp-input-area">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', padding: '6px 10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
              <span style={{ fontSize: '11px', color: '#a1a1aa', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Zap size={12} />
                Retrieval Mode
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '2px', background: 'rgba(0,0,0,0.3)', padding: '2px', borderRadius: '6px' }}>
                <button
                  onClick={() => setRetrievalMode('hybrid')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    borderRadius: '4px',
                    border: 'none',
                    background: retrievalMode === 'hybrid' ? '#f59e0b' : 'transparent',
                    color: retrievalMode === 'hybrid' ? '#000' : '#a1a1aa',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: 600,
                    transition: 'all 0.15s ease'
                  }}
                >
                  <Sparkles size={12} />
                  <span>Hybrid RAG</span>
                </button>
                <button
                  onClick={() => setRetrievalMode('fullcontext')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    borderRadius: '4px',
                    border: 'none',
                    background: retrievalMode === 'fullcontext' ? '#f59e0b' : 'transparent',
                    color: retrievalMode === 'fullcontext' ? '#000' : '#a1a1aa',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: 600,
                    transition: 'all 0.15s ease'
                  }}
                >
                  <BookOpen size={12} />
                  <span>Full Context</span>
                </button>
              </div>
            </div>
            <div className="qp-input-context-bar">
              <Layers size={12} />
              {selectedIds.size === 0 ? (
                <span className="qp-input-ctx-warn">Select documents to enable querying</span>
              ) : (
                <span className="qp-input-ctx-ok">
                  {selectedIds.size} source{selectedIds.size === 1 ? '' : 's'} · {selectedChunksCount} chunks in context
                </span>
              )}
            </div>
            <div className="qp-input-row">
              <textarea
                ref={textareaRef}
                className="qp-textarea"
                placeholder={
                  selectedIds.size === 0
                    ? 'Select at least one source to ask a question…'
                    : 'Ask anything about your documents… (Enter ↵ to send)'
                }
                value={question}
                onChange={(e) => {
                  setQuestion(e.target.value);
                  adjustTextareaHeight(e.target);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (!querying && selectedIds.size > 0 && question.trim()) {
                      handleSendQuery();
                    }
                  }
                }}
                style={{ height: textareaHeight }}
                disabled={querying}
              />
              <button
                className={`qp-send-btn ${
                  querying || selectedIds.size === 0 || !question.trim() ? 'disabled' : ''
                }`}
                onClick={() => handleSendQuery()}
                disabled={querying || selectedIds.size === 0 || !question.trim()}
              >
                {querying ? (
                  <Loader2 size={18} className="qp-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
            <div className="qp-input-hint">
              <kbd>Enter</kbd> send · <kbd>Shift + Enter</kbd> new line
            </div>
          </div>
        </div>
      </div>

      {/* ===== HISTORY DRAWER ===== */}
      {showHistoryDrawer && (
        <div className="qp-overlay" onClick={() => setShowHistoryDrawer(false)}>
          <div className="qp-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="qp-drawer-header">
              <div className="qp-drawer-title">
                <History size={18} />
                <h3>Query History</h3>
              </div>
              <button className="qp-drawer-close" onClick={() => setShowHistoryDrawer(false)}>
                <X size={18} />
              </button>
            </div>

            <p className="qp-drawer-subtitle">
              Past queries stored in your account. Click to reload into the lab.
            </p>

            <div className="qp-drawer-body">
              {historyLoading ? (
                <div className="qp-drawer-empty">
                  <Loader2 size={24} className="qp-spin qp-spin-indigo" />
                  <span>Loading…</span>
                </div>
              ) : queryHistory.length === 0 ? (
                <div className="qp-drawer-empty">
                  <Clock size={28} className="qp-empty-clock" />
                  <p className="qp-empty-title">No queries yet</p>
                  <p className="qp-empty-desc">Run test queries to log evaluation history.</p>
                </div>
              ) : (
                <div className="qp-history-list">
                  {queryHistory.map((item) => (
                    <div
                      key={item.query_id}
                      className="qp-history-card"
                      onClick={() => {
                        setQuestion(item.question);
                        setTextareaHeight(48);
                        if (textareaRef.current) textareaRef.current.style.height = '48px';
                        setShowHistoryDrawer(false);
                      }}
                    >
                      <div className="qp-history-top">
                        <span className="qp-history-time">
                          {item.created_at
                            ? new Date(item.created_at).toLocaleString([], {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : 'Recent'}
                        </span>
                        <div className="qp-history-actions">
                          <span className="qp-history-chunks">{item.chunks_found || 0} chunks</span>
                          <button
                            className="qp-history-del"
                            onClick={(e) => handleDeleteHistoryItem(item.query_id, e)}
                            title="Delete"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                      <div className="qp-history-question">{item.question}</div>
                      <div className="qp-history-answer">
                        {item.answer ? item.answer.substring(0, 140) + '…' : ''}
                      </div>
                      {item.selected_ids && item.selected_ids.length > 0 && (
                        <div className="qp-history-sources">
                          <Layers size={11} />
                          <span>{item.selected_ids.length} sources</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
