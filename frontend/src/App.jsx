import React, { useState } from 'react';
import Header from './components/Header';
import UploadContent from './components/UploadContent';
import IngestedSources from './components/IngestedSources';
import QueryPlayground from './components/QueryPlayground';

export default function App() {
  const [activeTab, setActiveTab] = useState('playground');

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {activeTab === 'upload' && (
          <UploadContent onUploadSuccess={() => setActiveTab('playground')} />
        )}
        {activeTab === 'sources' && (
          <IngestedSources onNavigateToAdd={() => setActiveTab('upload')} />
        )}
        {activeTab === 'playground' && (
          <QueryPlayground onNavigateToIngest={() => setActiveTab('upload')} />
        )}
      </main>
    </div>
  );
}