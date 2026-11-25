import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

const MENSAJE_DEFECTO = '¿Estás seguro de que querés eliminar este registro?';
const NOTA_DEFECTO = 'Esta acción ocultará el registro del sistema.';
const TITULO_DEFECTO = 'Confirmar eliminación';

export default function ConfirmDeleteModal({
  open = false,
  title = TITULO_DEFECTO,
  message = MENSAJE_DEFECTO,
  note = NOTA_DEFECTO,
  confirmText = 'Eliminar',
  cancelText = 'Cancelar',
  variant = 'danger',
  loading = false,
  loadingText = 'Eliminando...',
  onConfirm,
  onCancel,
}) {
  const cancelarRef = useRef(null);
  const modalRef = useRef(null);
  const onCancelRef = useRef(onCancel);
  useEffect(() => { onCancelRef.current = onCancel; }, [onCancel]);

  useEffect(() => {
    if (!open) return;
    cancelarRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = overflowAnterior; };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const manejarTeclado = (e) => {
      if (e.key === 'Escape' && !loading) {
        e.preventDefault();
        onCancelRef.current?.();
        return;
      }
      if (e.key !== 'Tab') return;
      const nodos = modalRef.current?.querySelectorAll('button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])');
      if (!nodos || nodos.length === 0) return;
      const primero = nodos[0];
      const ultimo = nodos[nodos.length - 1];
      if (!modalRef.current?.contains(document.activeElement)) {
        e.preventDefault();
        primero.focus();
        return;
      }
      if (e.shiftKey && document.activeElement === primero) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    };
    document.addEventListener('keydown', manejarTeclado);
    return () => document.removeEventListener('keydown', manejarTeclado);
  }, [open, loading]);

  if (!open) return null;

  return createPortal(
    <div
      className="ddjj-modal-overlay"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !loading) onCancelRef.current?.();
      }}
    >
      <div
        className="confirm-modal"
        ref={modalRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        aria-describedby="confirm-modal-message"
      >
        <div className={`confirm-modal__icon confirm-modal__icon--${variant}`}>
          <i className={`fas ${variant === 'danger' ? 'fa-triangle-exclamation' : 'fa-circle-question'}`} aria-hidden="true" />
        </div>
        <h3 id="confirm-modal-title" className="confirm-modal__title">{title}</h3>
        <p id="confirm-modal-message" className="confirm-modal__message">{message}</p>
        {note && <p className="confirm-modal__note">{note}</p>}
        <div className="confirm-modal__actions">
          <button
            type="button"
            className="btn btn-secondary"
            ref={cancelarRef}
            disabled={loading}
            onClick={onCancel}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={`btn ${variant === 'danger' ? 'btn-danger' : 'btn-primary'}`}
            disabled={loading}
            onClick={onConfirm}
          >
            {loading ? loadingText : confirmText}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
