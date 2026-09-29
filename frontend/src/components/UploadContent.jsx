import React, { useState } from 'react';
import { 
  FileText, 
  Image as ImageIcon, 
  Video, 
  Headphones, 
  Globe,
  Upload, 
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles
} from 'lucide-react';

export default function UploadContent({ onUploadSuccess }) {
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [rawText, setRawText] = useState('');
  const [rawTextName, setRawTextName] = useState('');
  const [loading, setLoading] = useState({});
  const [toast, setToast] = useState(null);
  const [dragOverCard, setDragOverCard] = useState(null);

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
      const token = localStorage.getItem('zymerag_access_token');
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
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
      const token = localStorage.getItem('zymerag_access_token');
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
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
      `Successfully ingested raw text snippet "${name}"!`
    );
    if (ok) {
      setRawText('');
      setRawTextName('');
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
              <ImageIcon size={22} />
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

        {/* Card 5: Website URLs (Feeds) */}
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

        {/* Card 6: Raw Text Snippets */}
        <div className="ingestion-card span-2-cols">
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

      </div>
    </div>
  );
}
