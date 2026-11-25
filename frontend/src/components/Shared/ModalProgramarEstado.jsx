import { useEffect, useRef, useState } from 'react';
import FormModal from './FormModal';
import { aApiDateTime, aInputDateTime, errorProgramacion, ZONA_PROGRAMACION } from '../../utils/programacionEstado';

function formatearFecha(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short', timeZone: ZONA_PROGRAMACION }).format(d);
}

/**
 * Programación de habilitación / deshabilitación de una cuenta (punto 6.2).
 *
 * El backend ya expone `fecha_deshabilitacion_programada` y
 * `fecha_habilitacion_programada` y las aplica con
 * `escuela.usuario_estado.aplicar_programaciones_usuario` (middleware) cuando
 * llega la fecha. Este modal es el patrón único para agendar, consultar lo
 * pendiente y cancelar. Cancelar es enviar `null` en el campo correspondiente.
 */
export default function ModalProgramarEstado({
  abierto,
  persona,
  estadoActual,
  fechaDeshabilitacion,
  fechaHabilitacion,
  guardando,
  onCerrar,
  onGuardar,
  onCancelarProgramacion,
}) {
  const [form, setForm] = useState({ fecha_deshabilitacion_programada: '', fecha_habilitacion_programada: '' });
  const [error, setError] = useState('');
  const abiertoAntesRef = useRef(false);

  useEffect(() => {
    if (!abierto) {
      abiertoAntesRef.current = false;
      return;
    }
    if (abiertoAntesRef.current) return;
    abiertoAntesRef.current = true;
    setForm({
      fecha_deshabilitacion_programada: aInputDateTime(fechaDeshabilitacion),
      fecha_habilitacion_programada: aInputDateTime(fechaHabilitacion),
    });
    setError('');
  }, [abierto, fechaDeshabilitacion, fechaHabilitacion]);

  if (!abierto || !persona) return null;

  const pendientes = [
    fechaDeshabilitacion ? { tipo: 'Deshabilitar', campo: 'fecha_deshabilitacion_programada', fecha: fechaDeshabilitacion } : null,
    fechaHabilitacion ? { tipo: 'Habilitar', campo: 'fecha_habilitacion_programada', fecha: fechaHabilitacion } : null,
  ].filter(Boolean);

  // R2: la próxima acción es la de menor fecha, no siempre la deshabilitación.
  const proxima = pendientes.length
    ? [...pendientes].sort((a, b) => new Date(a.fecha) - new Date(b.fecha))[0]
    : null;

  return (
    <FormModal
      title={`Programar estado: ${persona.apellido}, ${persona.nombre}`}
      onClose={onCerrar}
      cerrarConEscape={!guardando}
    >
      <form
        className="preceptor-form"
        onSubmit={(e) => {
          e.preventDefault();
          // 5.9 — la primera acción agendada tiene que ser la opuesta al estado
          // actual de la cuenta. Así se puede agendar la re-habilitación
          // posterior a una deshabilitación ya programada (y al revés), que antes
          // quedaba bloqueado.
          const err = errorProgramacion({
            estadoInicial: estadoActual,
            deshabilitacion: form.fecha_deshabilitacion_programada,
            habilitacion: form.fecha_habilitacion_programada,
          });
          if (err) {
            setError(err);
            return;
          }
          setError('');
          onGuardar({
            fecha_deshabilitacion_programada: aApiDateTime(form.fecha_deshabilitacion_programada),
            fecha_habilitacion_programada: aApiDateTime(form.fecha_habilitacion_programada),
          });
        }}
      >
        <div className="standard-modal-body" style={{ display: 'grid', gap: '14px' }}>
          <p className="m-0" style={{ color: '#cbd5e1', lineHeight: '1.5' }}>
            La cuenta está{' '}
            <strong>
              {estadoActual === null || estadoActual === undefined
                ? 'sin usuario'
                : (estadoActual ? 'habilitada' : 'deshabilitada')}
            </strong>
            .{' '}
            {estadoActual === null || estadoActual === undefined
              ? 'Definí las fechas de deshabilitación y habilitación en el orden en que quieras aplicarlas.'
              : estadoActual
                ? 'Definí primero la fecha de deshabilitación; si querés volver a habilitarla después, agregá una fecha de habilitación posterior.'
                : 'Definí primero la fecha de habilitación; si querés volver a deshabilitarla después, agregá una fecha de deshabilitación posterior.'}{' '}
            El cambio se aplica recién en la fecha indicada. Mientras haya una programación pendiente, el estado real del usuario no cambia.
          </p>

          <div className="preceptor-form-row preceptor-form-row--two">
            <div className="form-group-filter">
              <label htmlFor="prog-deshabilitacion">Deshabilitación programada</label>
              <small className="form-text">Fecha en que la cuenta pasa a deshabilitada.</small>
              <input
                id="prog-deshabilitacion"
                type="datetime-local"
                value={form.fecha_deshabilitacion_programada}
                onChange={(e) => {
                  setError('');
                  setForm((prev) => ({ ...prev, fecha_deshabilitacion_programada: e.target.value }));
                }}
              />
            </div>
            <div className="form-group-filter">
              <label htmlFor="prog-habilitacion">Habilitación programada</label>
              <small className="form-text">Fecha en que la cuenta pasa a habilitada.</small>
              <input
                id="prog-habilitacion"
                type="datetime-local"
                value={form.fecha_habilitacion_programada}
                onChange={(e) => {
                  setError('');
                  setForm((prev) => ({ ...prev, fecha_habilitacion_programada: e.target.value }));
                }}
              />
            </div>
          </div>

          {error && (
            <p className="form-error-message" role="alert">{error}</p>
          )}

          <div className="form-group-filter">
            <span style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem' }}>
              Programaciones registradas
            </span>
            {pendientes.length === 0 ? (
              <p className="empty-state-message m-0" style={{ padding: '12px', margin: 0 }}>
                No hay programaciones pendientes para esta cuenta.
              </p>
            ) : (
              <ul className="programacion-lista">
                {pendientes.map((p) => (
                  <li key={p.campo}>
                    <span>
                      <strong>{p.tipo}</strong> el {formatearFecha(p.fecha)}
                    </span>
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      onClick={() => onCancelarProgramacion(p.campo)}
                      disabled={guardando}
                      aria-label={`Quitar la fecha de ${p.tipo.toLowerCase()}`}
                    >
                      <i className="fas fa-xmark" aria-hidden="true" /> Quitar fecha
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {proxima && (
              <p className="proxima-accion-hint" role="status">
                Próxima acción: {proxima.tipo} el {formatearFecha(proxima.fecha)}
              </p>
            )}
          </div>
        </div>
        <div className="standard-modal-footer">
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            <i className="fas fa-save" aria-hidden="true" />{' '}
            {guardando ? 'Guardando...' : 'Guardar'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCerrar} disabled={guardando}>
            Cancelar
          </button>
        </div>
      </form>
    </FormModal>
  );
}
