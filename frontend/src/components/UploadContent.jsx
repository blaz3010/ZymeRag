import React, { useState } from 'react';
import {
  FileText,
  Image as IMAGE,
  Video,
  Headphones,
  Globe,
  Upload,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  FileSpreadsheet,
  Presentation,
  RefreshCw,
  X
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '';

export default function UploadContent({ onUploadSuccess }) {
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [rawText, setRawText] = useState('');
  const [rawTextName, setRawTextName] = useState('');
  const [loading, setLoading] = useState({});
  const [toast, setToast] = useState(null);
  const [dragOverCard, setDragOverCard] = useState(null);

  // Replace Content modal state
  const [showReplaceModal, setShowReplaceModal] = useState(false);
  const [replaceContentId, setReplaceContentId] = useState('');
  const [replaceFile, setReplaceFile] = useState(null);

  const RAW_TEXT_MAX_WORDS = 200;

  const showNotification = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3800);
  };

  const wordCount = rawText.trim() ? rawText.trim().split(/\s+/).length : 0;
  const rawTextTooLong = wordCount > RAW_TEXT_MAX_WORDS;

  // Helper for Uploading Files to Backend
  const handleFileUpload = async (file, endpoint, defaultType) => {
    if (!file) return;
    if (file.size > 15 * 1024 * 1024) {
      showNotification('File exceeds maximum limit of 15MB', 'error');
      return;
    }

    setLoading(prev => ({ ...prev, [defaultType]: true }));
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', file.name.substring(0, file.name.lastIndexOf('.')) || file.name);

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {},
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        showNotification(`Successfully ingested "${file.name}" into Supabase vector store!`, 'success');
        if (onUploadSuccess) onUploadSuccess();
      } else {
        showNotification(data.detail || 'Upload failed', 'error');
      }
    } catch (err) {
      showNotification(`Upload error: ${err.message}`, 'error');
    } finally {
      setLoading(prev => ({ ...prev, [defaultType]: false }));
    }
  };

  // Helper for Uploading non-file (form field) content to Backend
  const handleFormUpload = async (fields, endpoint, key, successMessage) => {
    setLoading(prev => ({ ...prev, [key]: true }));
    const formData = new FormData();
    Object.entries(fields).forEach(([field, value]) => formData.append(field, value));

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {},
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        showNotification(successMessage, 'success');
        if (onUploadSuccess) onUploadSuccess();
        return true;
      }
      showNotification(data.detail || 'Upload failed', 'error');
      return false;
    } catch (err) {
      showNotification(`Upload error: ${err.message}`, 'error');
      return false;
    } finally {
      setLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const handleWebsiteSubmit = async () => {
    const url = websiteUrl.trim();
    if (!url) return;
    const ok = await handleFormUpload(
      { url, idempotent_key: url },
      '/upload/upload_website',
      'web',
      `Successfully crawled and ingested "${url}"!`
    );
    if (ok) setWebsiteUrl('');
  };

const handleRawTextSubmit = async () => {
    const text = rawText.trim();
    if (!text || rawTextTooLong) return;
    const name = rawTextName.trim() || text.slice(0, 40);
    const ok = await handleFormUpload(
      { text, name, idempotent_key: `${name}-${text.length}` },
      '/upload/upload_raw_text',
      'raw',
      `Successfully ingested raw text snippet "${name}!"`
    );
    if (ok) {
      setRawText('');
      setRawTextName('');
    }
  };

  const handleReplaceContent = async () => {
    if (!replaceFile || !replaceContentId.trim()) {
      setToast({ msg: 'Please select a file and enter a content ID', type: 'error' });
      return;
    }
    if (replaceFile.size > 15 * 1024 * 1024) {
      setToast({ msg: 'File exceeds maximum limit of 15MB', type: 'error' });
      return;
    }
    setLoading(prev => ({ ...prev, replace: true }));
    const formData = new FormData();
    formData.append('content_id', replaceContentId.trim());
    formData.append('file', replaceFile);
    formData.append('name', replaceFile.name.substring(0, replaceFile.name.lastIndexOf('.')) || replaceFile.name);

    try {
      const res = await fetch(`${API_BASE}/upload/replace_content`, {
        method: 'POST',
        headers: {},
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setToast({ msg: `Content replaced successfully! Old: ${data.old_id} → New: ${data.new_id}`, type: 'success' });
        if (onUploadSuccess) onUploadSuccess();
        setShowReplaceModal(false);
        setReplaceContentId('');
        setReplaceFile(null);
      } else {
        setToast({ msg: data.detail || 'Replace failed', type: 'error' });
      }
    } catch (err) {
      setToast({ msg: `Replace error: ${err.message}`, type: 'error' });
    } finally {
      setLoading(prev => ({ ...prev, replace: false }));
    }
  };

  return (
    <div className="workspace-container">
      {/* Notification Toast Banner */}
      {toast && (
        <div className={`toast-banner-box ${toast.type}`}>
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{toast.msg}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="workspace-header-center">
        <div className="gradient-badge-small">
          <Sparkles size={14} />
          <span>Multimodal Ingestion</span>
        </div>
        <h1 className="title-hero">Ingest Data into ZymeRag</h1>
        <p className="subtitle-hero">
          Upload documents, images, video, audio, or web content to generate vector embeddings stored in Supabase pgvector.
        </p>
      </div>

      {/* 2-Column Grid of Cards */}
      <div className="ingestion-grid">
        
        {/* Card 6: Website URLs (Feeds) */}
        <div className="ingestion-card span-2-cols">
          <div className="card-top-header">
            <div className="icon-wrapper icon-emerald">
              <Globe size={22} />
            </div>
            <div>
              <h3 className="card-heading">Website Ingestion</h3>
              <p className="card-subtext">Crawl a public URL, split it into chunks and index it as a feed</p>
            </div>
          </div>

          <div className="web-ingest-box">
            <input
              type="url"
              className="custom-textarea url-input"
              placeholder="https://example.com/article"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              disabled={loading.web}
            />
            <div className="web-ingest-footer">
              <span className="text-count-hint">One URL at a time</span>
              <button
                className="btn-submit-web btn-emerald"
                disabled={!websiteUrl.trim() || loading.web}
                onClick={handleWebsiteSubmit}
              >
                {loading.web ? (
                  <span className="btn-spinner-content">
                    <Loader2 className="animate-spin" size={14} />
                    <span>Crawling...</span>
                  </span>
                ) : (
                  '+ Ingest Website'
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Card 1: PDF & Word Documents */}
        <div 
          className={`ingestion-card ${dragOverCard === 'doc' ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOverCard('doc'); }}
          onDragLeave={() => setDragOverCard(null)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverCard(null);
            if (e.dataTransfer.files[0]) {
              const file = e.dataTransfer.files[0];
              const endpoint = file.name.endsWith('.docx') ? '/upload/upload_docx' : '/upload/upload_pdf';
              handleFileUpload(file, endpoint, 'doc');
            }
          }}
        >
          <div className="card-top-header">
            <div className="icon-wrapper icon-indigo">
              <FileText size={22} />
            </div>
            <div>
              <h3 className="card-heading">PDF & Word Documents</h3>
              <p className="card-subtext">Process text and pages from documents</p>
            </div>
          </div>

          <label className="custom-dropzone">
            <input 
              type="file" 
              accept=".pdf,.docx,.txt"
              onChange={(e) => {
                if (e.target.files[0]) {
                  const file = e.target.files[0];
                  const endpoint = file.name.endsWith('.docx') ? '/upload/upload_docx' : '/upload/upload_pdf';
                  handleFileUpload(file, endpoint, 'doc');
                }
              }}
            />
            {loading.doc ? (
              <div className="loading-spinner-box">
                <Loader2 className="animate-spin text-indigo" size={28} />
                <span className="uploading-text">Generating Embeddings...</span>
              </div>
            ) : (
              <>
                <Upload className="dropzone-svg-icon text-indigo" size={28} />
                <div className="dropzone-main-text">
                  Drop PDF / Word file or <span className="highlight-browse">browse</span>
                </div>
                <span className="dropzone-sub-text">Supported: .pdf, .docx, .txt (up to 15MB)</span>
              </>
            )}
          </label>
        </div>

        {/* Card 4: CSV Files */}
        <div 
          className={`ingestion-card ${dragOverCard === 'csv' ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOverCard('csv'); }}
          onDragLeave={() => setDragOverCard(null)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverCard(null);
            if (e.dataTransfer.files[0]) {
              const file = e.dataTransfer.files[0];
              handleFileUpload(file, '/upload/upload_csv', 'csv');
            }
          }}
        >
          <div className="card-top-header">
            <div className="icon-wrapper icon-green">
              <FileSpreadsheet size={22} />
            </div>
            <div>
              <h3 className="card-heading">CSV Files</h3>
              <p className="card-subtext">Tabular data from spreadsheets</p>
            </div>
          </div>

          <label className="custom-dropzone">
            <input 
              type="file" 
              accept=".csv"
              onChange={(e) => {
                if (e.target.files[0]) {
                  const file = e.target.files[0];
                  handleFileUpload(file, '/upload/upload_csv', 'csv');
                }
              }}
            />
            {loading.csv ? (
              <div className="loading-spinner-box">
                <Loader2 className="animate-spin text-green-500" size={28} />
                <span className="uploading-text">Generating Embeddings...</span>
              </div>
            ) : (
              <>
                <Upload className="dropzone-svg-icon text-green-500" size={28} />
                <div className="dropzone-main-text">
                  Drop CSV file or <span className="highlight-browse">browse</span>
                </div>
                <div className="dropzone-sub-text">.CSV files up to 15MB</div>
              </>
            )}
          </label>
        </div>

        {/* Card: PowerPoint Presentations */}
        <div 
          className={`ingestion-card ${dragOverCard === 'pptx' ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOverCard('pptx'); }}
          onDragLeave={() => setDragOverCard(null)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverCard(null);
            if (e.dataTransfer.files[0]) {
              const file = e.dataTransfer.files[0];
              handleFileUpload(file, '/upload/upload_presentation', 'pptx');
            }
          }}
        >
          <div className="card-top-header">
            <div className="icon-wrapper icon-orange">
              <Presentation size={22} />
            </div>
            <div>
              <h3 className="card-heading">PowerPoint Presentations</h3>
              <p className="card-subtext">Extract text and slides from presentation decks</p>
            </div>
          </div>

          <label className="custom-dropzone">
            <input 
              type="file" 
              accept=".pptx"
              onChange={(e) => {
                if (e.target.files[0]) {
                  const file = e.target.files[0];
                  handleFileUpload(file, '/upload/upload_presentation', 'pptx');
                }
              }}
            />
            {loading.pptx ? (
              <div className="loading-spinner-box">
                <Loader2 className="animate-spin text-orange" size={28} />
                <span className="uploading-text">Parsing Slides & Generating Embeddings...</span>
              </div>
            ) : (
              <>
                <Upload className="dropzone-svg-icon text-orange" size={28} />
                <div className="dropzone-main-text">
                  Drop PPTX file or <span className="highlight-browse">browse</span>
                </div>
                <span className="dropzone-sub-text">Supported: .pptx (up to 15MB)</span>
              </>
            )}
          </label>
        </div>

        {/* Card 2: Multimodal Images */}
        <div 
          className={`ingestion-card ${dragOverCard === 'img' ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOverCard('img'); }}
          onDragLeave={() => setDragOverCard(null)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverCard(null);
            if (e.dataTransfer.files[0]) {
              handleFileUpload(e.dataTransfer.files[0], '/upload/upload_image', 'img');
            }
          }}
        >
          <div className="card-top-header">
            <div className="icon-wrapper icon-violet">
              <IMAGE size={22} />
            </div>
            <div>
              <h3 className="card-heading">Multimodal Images</h3>
              <p className="card-subtext">Extract text and layout from images</p>
            </div>
          </div>

          <label className="custom-dropzone">
            <input 
              type="file" 
              accept="image/*"
              onChange={(e) => {
                if (e.target.files[0]) {
                  handleFileUpload(e.target.files[0], '/upload/upload_image', 'img');
                }
              }}
            />
            {loading.img ? (
              <div className="loading-spinner-box">
                <Loader2 className="animate-spin text-violet" size={28} />
                <span className="uploading-text">Extracting Image OCR...</span>
              </div>
            ) : (
              <>
                <Upload className="dropzone-svg-icon text-violet" size={28} />
                <div className="dropzone-main-text">
                  Drop image here or <span className="highlight-browse text-violet">browse</span>
                </div>
                <span className="dropzone-sub-text">Supported: .png, .jpg, .jpeg, .webp, .tiff</span>
              </>
            )}
          </label>
        </div>

        {/* Card 3: Video Transcription */}
        <div 
          className={`ingestion-card ${dragOverCard === 'vid' ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOverCard('vid'); }}
          onDragLeave={() => setDragOverCard(null)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverCard(null);
            if (e.dataTransfer.files[0]) {
              handleFileUpload(e.dataTransfer.files[0], '/upload/upload_video', 'vid');
            }
          }}
        >
          <div className="card-top-header">
            <div className="icon-wrapper icon-purple">
              <Video size={22} />
            </div>
            <div>
              <h3 className="card-heading">Video Transcription</h3>
              <p className="card-subtext">Transcribe speech and index video audio</p>
            </div>
          </div>

          <label className="custom-dropzone">
            <input 
              type="file" 
              accept="video/*"
              onChange={(e) => {
                if (e.target.files[0]) {
                  handleFileUpload(e.target.files[0], '/upload/upload_video', 'vid');
                }
              }}
            />
            {loading.vid ? (
              <div className="loading-spinner-box">
                <Loader2 className="animate-spin text-purple" size={28} />
                <span className="uploading-text">Transcribing Video...</span>
              </div>
            ) : (
              <>
                <Upload className="dropzone-svg-icon text-purple" size={28} />
                <div className="dropzone-main-text">
                  Drop MP4 video or <span className="highlight-browse text-purple">browse</span>
                </div>
                <span className="dropzone-sub-text">Supported: .mp4 (Speech-to-text)</span>
              </>
            )}
          </label>
        </div>

        {/* Card 4: Audio Processing */}
        <div 
          className={`ingestion-card ${dragOverCard === 'aud' ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOverCard('aud'); }}
          onDragLeave={() => setDragOverCard(null)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverCard(null);
            if (e.dataTransfer.files[0]) {
              handleFileUpload(e.dataTransfer.files[0], '/upload/upload_audio', 'aud');
            }
          }}
        >
          <div className="card-top-header">
            <div className="icon-wrapper icon-blue">
              <Headphones size={22} />
            </div>
            <div>
              <h3 className="card-heading">Audio Processing</h3>
              <p className="card-subtext">Convert speech audio into searchable vectors</p>
            </div>
          </div>

          <label className="custom-dropzone">
            <input 
              type="file" 
              accept="audio/*"
              onChange={(e) => {
                if (e.target.files[0]) {
                  handleFileUpload(e.target.files[0], '/upload/upload_audio', 'aud');
                }
              }}
            />
            {loading.aud ? (
              <div className="loading-spinner-box">
                <Loader2 className="animate-spin text-blue" size={28} />
                <span className="uploading-text">Processing Audio...</span>
              </div>
            ) : (
              <>
                <Upload className="dropzone-svg-icon text-blue" size={28} />
                <div className="dropzone-main-text">
                  Drop audio file or <span className="highlight-browse text-blue">browse</span>
                </div>
                <span className="dropzone-sub-text">Supported: .mp3, .wav, .m4a</span>
              </>
            )}
          </label>
        </div>

      

        {/* Card 5: Raw Text Snippets */}
        <div className="ingestion-card">
          <div className="card-top-header">
            <div className="icon-wrapper icon-blue">
              <FileText size={22} />
            </div>
            <div>
              <h3 className="card-heading">Raw Text Snippet</h3>
              <p className="card-subtext">Paste a short note, summary or paragraph to index as a single chunk</p>
            </div>
          </div>

          <div className="web-ingest-box">
            <input
              type="text"
              className="custom-textarea url-input"
              placeholder="Optional name for this snippet"
              value={rawTextName}
              onChange={(e) => setRawTextName(e.target.value)}
              disabled={loading.raw}
            />
            <textarea
              className="custom-textarea"
              rows={5}
              placeholder="Paste your raw text here (max 200 words)..."
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              disabled={loading.raw}
            />
            <div className="web-ingest-footer">
              <span className={`text-count-hint ${rawTextTooLong ? 'limit-exceeded' : ''}`}>
                {wordCount} / {RAW_TEXT_MAX_WORDS} words
                {rawTextTooLong ? ' — limit exceeded' : ''}
              </span>
              <button
                className="btn-submit-web btn-blue"
                disabled={!rawText.trim() || rawTextTooLong || loading.raw}
                onClick={handleRawTextSubmit}
              >
                {loading.raw ? (
                  <span className="btn-spinner-content">
                    <Loader2 className="animate-spin" size={14} />
                    <span>Indexing...</span>
                  </span>
                ) : (
                  '+ Ingest Raw Text'
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Card 6: Replace Existing Content */}
        <div className="ingestion-card">
          <div className="card-top-header">
            <div className="icon-wrapper icon-emerald">
              <RefreshCw size={22} />
            </div>
            <div>
              <h3 className="card-heading">Replace Existing Content</h3>
              <p className="card-subtext">Swap an ingested document/feed with a new file, keeping the same source ID</p>
            </div>
          </div>

          <div className="web-ingest-box">
            <input
              type="text"
              className="custom-textarea url-input"
              placeholder="Content ID to replace (e.g. from Ingested Sources table)"
              value={replaceContentId}
              onChange={(e) => setReplaceContentId(e.target.value)}
              disabled={loading.replace}
            />
            <label className="custom-dropzone" style={{ marginTop: '12px' }}>
              <input
                type="file"
                accept=".pdf,.docx,.csv,.pptx,image/*,video/*,audio/*"
                onChange={(e) => {
                  if (e.target.files[0]) {
                    setReplaceFile(e.target.files[0]);
                  }
                }}
                disabled={loading.replace}
              />
              {loading.replace ? (
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
            <div className="web-ingest-footer">
              <span className="text-count-hint">Same source ID is preserved after replacement</span>
              <button
                className="btn-submit-web btn-emerald"
                disabled={!replaceFile || !replaceContentId.trim() || loading.replace}
                onClick={handleReplaceContent}
              >
                {loading.replace ? (
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

      </div>

      {/* Replace Content Confirmation Modal */}
      {showReplaceModal && (
        <div className="modal-backdrop" onClick={() => setShowReplaceModal(false)}>
          <div className="modal-card metadata-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-styled">
              <div className="flex-header-title">
                <div className="modal-icon-badge badge-emerald">
                  <RefreshCw size={18} />
                </div>
                <div>
                  <h3 className="modal-title-text">Replace Content</h3>
                  <p className="modal-subtitle-text">Swap an existing source with a new file</p>
                </div>
              </div>
              <button onClick={() => setShowReplaceModal(false)} className="modal-close-icon-btn">
                <X size={16} />
              </button>
            </div>
            <div className="modal-body-container">
              <p className="info-value-text">
                This will delete the old chunks and content record for ID <strong>{replaceContentId}</strong> and ingest the new file under the same ID.
              </p>
            </div>
            <div className="modal-footer-styled">
              <button onClick={() => setShowReplaceModal(false)} className="primary-modal-btn" style={{ background: '#6b7280' }}>
                Cancel
              </button>
              <button onClick={handleReplaceContent} className="primary-modal-btn">
                Replace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
