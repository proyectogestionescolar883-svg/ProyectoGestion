import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

const ErrorOverlayContext = createContext({ mostrarError: () => {} });

/* ------------------------------------------------------------------
   Store a nivel de módulo para que los errores produced fuera del árbol
   de React (p. ej. el interceptor de axios en services/api.js) puedan
   abrir la misma capa global de error.
   ------------------------------------------------------------------ */
const suscriptores = new Set();

export function reportarErrorGlobal(mensaje) {
  if (!mensaje) return;
  suscriptores.forEach((fn) => {
    try {
      fn(mensaje);
    } catch {
      /* un suscriptor roto no debe romper el resto */
    }
  });
}

function extraerMensaje(error) {
  if (!error) return 'Ocurrió un error inesperado.';
  if (typeof error === 'string') return error;
  return (
    error.detail ||
    (typeof error.error === 'string' ? error.error : null) ||
    error.message ||
    'Ocurrió un error inesperado.'
  );
}

export function useErrorOverlay() {
  return useContext(ErrorOverlayContext).mostrarError;
}

export function ErrorOverlayProvider({ children }) {
  const [errorActual, setErrorActual] = useState(null);
  const cardRef = useRef(null);
  const textoRef = useRef(null);
  const focoAnteriorRef = useRef(null);

  const mostrarError = useCallback((mensaje) => {
    if (!mensaje) return;
    setErrorActual(extraerMensaje(mensaje));
  }, []);

  const mostrarErrorDirecto = useCallback((mensaje) => {
    setErrorActual(extraerMensaje(mensaje));
  }, []);

  const cerrarError = useCallback(() => setErrorActual(null), []);

  useEffect(() => {
    suscriptores.add(mostrarErrorDirecto);
    return () => {
      suscriptores.delete(mostrarErrorDirecto);
    };
  }, [mostrarErrorDirecto]);

  // 5.16 — Escape cierra la capa de error global. Antes el Escape solo estaba
  // atado al botón "Cerrar" mediante onKeyDown, y como el foco estaba en el texto
  // del mensaje nunca se disparaba.
  useEffect(() => {
    if (!errorActual) return undefined;
    focoAnteriorRef.current = document.activeElement;
    textoRef.current?.focus();
    const alPresionar = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        cerrarError();
        return;
      }
      if (e.key !== 'Tab') return;
      const focusables = Array.from(
        cardRef.current?.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])') || [],
      );
      if (focusables.length === 0) {
        e.preventDefault();
        return;
      }
      const primero = focusables[0];
      const ultimo = focusables[focusables.length - 1];
      if (e.shiftKey && (document.activeElement === primero || document.activeElement === textoRef.current)) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    };
    document.addEventListener('keydown', alPresionar);
    return () => {
      document.removeEventListener('keydown', alPresionar);
      focoAnteriorRef.current?.focus?.();
    };
  }, [errorActual, cerrarError]);

  return (
    <ErrorOverlayContext.Provider value={{ mostrarError }}>
      {children}
      {errorActual &&
        createPortal(
          <div className="form-error-overlay" role="alertdialog" aria-modal="true" aria-labelledby="error-overlay-text">
            <div className="form-error-overlay-card" ref={cardRef}>
              <i className="fas fa-triangle-exclamation" aria-hidden="true"></i>
              <span className="form-error-overlay-text" id="error-overlay-text" tabIndex={-1} ref={textoRef}>
                {errorActual}
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={cerrarError}
              >
                Cerrar
              </button>
            </div>
          </div>,
          document.body,
        )}
    </ErrorOverlayContext.Provider>
  );
}
