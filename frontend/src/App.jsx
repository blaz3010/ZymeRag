import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import UploadContent from './components/UploadContent';
import IngestedSources from './components/IngestedSources';
import AuthPage from './components/AuthPage';
import { getStoredUser, logoutCurrentSession } from './utils/auth';

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    // Check for existing session
    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
    }
    setInitializing(false);
  }, []);

  const handleLogout = () => {
    logoutCurrentSession();
    setUser(null);
  };

  if (initializing) {
    return (
      <div className="loading-viewport">
        <div className="loading-card">
          <div className="brand-badge" style={{ width: 48, height: 48 }}>
            <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          </div>
          <span className="loading-label">Initializing ZymeRag Workspace...</span>
        </div>
      </div>
    );
  }

  // If not authenticated, render login/signup screen
  if (!user) {
    return <AuthPage onLoginSuccess={(loggedInUser) => setUser(loggedInUser)} />;
  }

  // Once authenticated, display the main dashboard (Ingest Data & Ingested Sources)
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Top Header Navbar with user profile & logout */}
      <Header 
        user={user}
        onLogout={handleLogout}
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
      />

      {/* Main Workspace Body */}
      <main className="max-w-6xl mx-auto px-6 py-6">
        {activeTab === 'upload' ? (
          <UploadContent onUploadSuccess={() => setActiveTab('sources')} />
        ) : (
          <IngestedSources onNavigateToAdd={() => setActiveTab('upload')} />
        )}
      </main>
    </div>
  );
}