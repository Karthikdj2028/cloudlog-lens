import React from 'react';
import ReactDOM from 'react-dom/client';

function ArchitecturePlaceholder() {
  return (
    <main style={{ fontFamily: 'system-ui', padding: '2rem', maxWidth: 760, margin: '0 auto' }}>
      <h1>CloudLog Lens</h1>
      <p>Repository foundation is in place.</p>
      <p>The application interface will be implemented in a later milestone.</p>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ArchitecturePlaceholder />
  </React.StrictMode>,
);
