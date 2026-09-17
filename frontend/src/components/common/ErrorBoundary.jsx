import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '24px',
          margin: '20px',
          borderRadius: '12px',
          background: 'var(--bg-surface, #FFFFFF)',
          border: '1px solid #FECACA',
          boxShadow: '0 4px 12px rgba(220, 38, 38, 0.08)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          maxWidth: '640px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#DC2626' }}>
            <AlertTriangle size={22} />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Workspace Display Notice</h3>
          </div>
          <p style={{ margin: 0, fontSize: '0.92rem', color: '#475569', lineHeight: 1.5 }}>
            A temporary display issue occurred while rendering this petition. Your data is safely stored in the database.
          </p>
          <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
            <button
              type="button"
              onClick={this.handleReset}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                backgroundColor: '#102C57',
                color: '#FEFAF6',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 600,
                fontSize: '0.88rem',
                cursor: 'pointer'
              }}
            >
              <RotateCcw size={14} />
              <span>Retry Rendering</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
