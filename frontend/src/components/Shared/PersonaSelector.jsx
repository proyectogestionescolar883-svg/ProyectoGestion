import { useId, useMemo } from 'react';

function PersonaSelector({ 
  personas, 
  value, 
  onChange, 
  label = 'Seleccionar persona',
  placeholder = 'Seleccione una persona...',
  required = false,
  disabled = false 
}) {
  const idGenerado = useId();
  const selectId = idGenerado;
  const ayudaId = `${selectId}-ayuda`;
  const opciones = useMemo(() =>
    (Array.isArray(personas) ? personas : [])
      .filter((p) => p && (p.id_usuario != null || p.id != null))
      .map((p) => ({
        id: p.id_usuario ?? p.id,
        label: `${p.apellido || ''}, ${p.nombre || ''} (${p.tipo || p.rol || 'Usuario'}) - DNI: ${p.dni || '—'}`,
        datos: p,
      })), [personas]
  );

  return (
    <div className="form-group-filter">
      <label htmlFor={selectId}>{label}</label>
      <select
        id={selectId}
        value={value != null ? String(value) : ''}
        onChange={(e) => { if (typeof onChange === 'function') onChange(e.target.value); }}
        required={required}
        disabled={disabled}
        aria-describedby={value ? ayudaId : undefined}
      >
        <option value="">{placeholder}</option>
        {opciones.map((opt) => (
          <option key={opt.id} value={opt.id}>{opt.label}</option>
        ))}
      </select>
      {value && (
        <p id={ayudaId} className="m-0 mt-8" style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>
          Se usará el usuario existente. Los datos personales se completarán automáticamente.
        </p>
      )}
    </div>
  );
}

export default PersonaSelector;