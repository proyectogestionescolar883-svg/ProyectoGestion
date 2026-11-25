import React from 'react'
import ReactDOM from 'react-dom/client'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { ConfirmProvider } from './context/ConfirmContext'
import App from './App'
import './index.css'

import { ErrorOverlayProvider } from './context/ErrorOverlayContext'

class RenderErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error) {
    console.error('Error de renderizado', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" style={{ padding: 24, fontFamily: 'sans-serif' }}>
          <h1 style={{ fontSize: 20, marginBottom: 8 }}>Ocurrio un error inesperado</h1>
          <p style={{ marginBottom: 16 }}>Recarga la pagina para continuar.</p>
          <button type="button" onClick={() => window.location.reload()}>
            Recargar
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RenderErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <ConfirmProvider>
            <ErrorOverlayProvider>
              <App />
            </ErrorOverlayProvider>
          </ConfirmProvider>
        </ToastProvider>
      </AuthProvider>
    </RenderErrorBoundary>
  </React.StrictMode>
)
