import { useId, useRef, useState } from 'react';

function aceptaArchivo(file, accept) {
  const permitidos = String(accept || '')
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (permitidos.length === 0) return true;
  const nombre = String(file.name || '').toLowerCase();
  const tipo = String(file.type || '').toLowerCase();
  return permitidos.some((p) => {
    if (p.startsWith('.')) return nombre.endsWith(p);
    if (p.endsWith('/*')) return tipo.startsWith(p.slice(0, -1));
    return tipo === p;
  });
}

function FilePicker({
  id,
  label,
  hint,
  accept,
  multiple = false,
  value = [],
  onChange,
  disabled = false,
}) {
  const idGenerado = useId();
  const inputId = id || idGenerado;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const inputRef = useRef(null);
  const [error, setError] = useState('');
  const files = Array.isArray(value) ? value : [];

  const handleChange = (e) => {
    const nuevos = Array.from(e.target.files || []);
    const invalidos = nuevos.filter((file) => !aceptaArchivo(file, accept));
    if (invalidos.length > 0) {
      setError(`Formato no permitido: ${invalidos.map((f) => f.name).join(', ')}.`);
      e.target.value = '';
      return;
    }
    setError('');
    if (typeof onChange === 'function') {
      if (multiple) {
        onChange([...files, ...nuevos]);
      } else {
        onChange(nuevos.slice(0, 1));
      }
    }
    e.target.value = '';
  };

  const quitar = (index) => {
    if (typeof onChange !== 'function') return;
    onChange(files.filter((_, i) => i !== index));
  };

  const descritoPor = [hint && hintId, error && errorId].filter(Boolean).join(' ') || undefined;

  return (
    <div className="form-group-filter">
      {label && <label htmlFor={inputId}>{label}</label>}
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
        disabled={disabled}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={descritoPor}
      />
      {error && (
        <span id={errorId} className="form-error-text" role="alert">{error}</span>
      )}
      {files.length > 0 && (
        <div style={{ display: 'grid', gap: '8px', marginTop: '8px' }}>
          {files.map((file, index) => (
            <div
              key={`${file.name}-${file.size}-${file.lastModified}-${index}`}
              className="flex-row--between"
              style={{
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '8px 10px',
                background: 'var(--card-bg)',
              }}
            >
              <span style={{ wordBreak: 'break-word', fontSize: '0.9rem' }}>
                <i className="fas fa-file" aria-hidden="true" /> {file.name}
              </span>
              <button
                type="button"
                className="btn-link-danger"
                onClick={() => quitar(index)}
                disabled={disabled}
              >
                <i className="fas fa-times" aria-hidden="true" /> Quitar
              </button>
            </div>
          ))}
        </div>
      )}
      {hint && <small id={hintId} className="upload-hint">{hint}</small>}
    </div>
  );
}

export default FilePicker;
