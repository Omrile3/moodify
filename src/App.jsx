import React from 'react';
import { Routes, Route } from 'react-router-dom';
import MusicBot from './pages/musicbot';
import Layout from './layout';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<MusicBot />} />
        {/* Add more routes here if needed */}
      </Routes>
    </Layout>
  );
}

export default App;
