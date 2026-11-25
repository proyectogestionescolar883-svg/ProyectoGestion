import { useEffect, useMemo, useRef, useState } from 'react';
import LoadingSpinner from './LoadingSpinner';
import {
  getMateriasAdeudadas,
  getRendicionesMateriasAdeudadas,
  getActividadesMateriasAdeudadas,
  getIntensificacionesAcademicas,
} from '../../services/api';
import { buildMediaUrl } from '../../utils/medios';

/**
 * Punto 5.19 (Alumno) / 5.20 (Familia).
 *
 * Implementación compartida de "Materias Adeudadas". Los dos portales muestran
 * exactamente lo mismo y en solo lectura; lo único que cambia es el texto, que se
 * adapta a quién está mirando ("no tenés" vs "no tiene"). Se Sharing en vez de
 * duplicar el panel para que una corrección en uno no deje al otro desactualizado.
 *
 * El backend ya acota los cuatro endpoints al ámbito del rol
 * (`permissions.alumnos_permitidos` / `alumno_ids_familia`), pero se manda el
 * `alumno` explícito igual: en Familia es lo que hace que al cambiar de hijo
 * seleccionado se recargue la información del hijo correcto (punto 15.1 del plan).
 */
function fmtFecha(value) {
  if (!value) return '—';
  const texto = String(value);
  const partes = texto.match(
    /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(Z|[+-]\d{2}:?\d{2})?$/,
  );
  const date = partes && !partes[8]
    ? new Date(
      Number(partes[1]), Number(partes[2]) - 1, Number(partes[3]),
      Number(partes[4] || 0), Number(partes[5] || 0), Number(partes[6] || 0),
    )
    : new Date(texto);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('es-AR', { dateStyle: 'short' }).format(date);
}

function fmtNota(value) {
  if (value === null || value === undefined || String(value).trim() === '') return '—';
  return Number(value);
}

function periodoLabel(periodo) {
  const labels = {
    MARZO: 'Marzo',
    JULIO: 'Julio',
    AGOSTO: 'Agosto',
    DICIEMBRE_1: 'Diciembre 1',
    DICIEMBRE_2: 'Diciembre 2',
    FEBRERO: 'Febrero',
  };
  return labels[periodo] || periodo || '—';
}

function badgeEstado(estado) {
  const clases = {
    ADEUDADA: 'badge-warning',
    RECURSANDO: 'badge-neutral',
    APROBADA: 'badge-success',
    PENDIENTE: 'badge-neutral',
    DESAPROBADA: 'badge-danger',
  };
  const etiquetas = {
    ADEUDADA: 'Adeudada',
    RECURSANDO: 'Recursando',
    APROBADA: 'Aprobada',
    PENDIENTE: 'Pendiente',
    DESAPROBADA: 'Desaprobada',
  };
  return <span className={`badge ${clases[estado] || 'badge-neutral'}`}>{etiquetas[estado] || estado}</span>;
}

function PanelMateriasAdeudadas({
  alumno,
  titulo = 'Materias Adeudadas',
  descripcion,
  textoSinDeudas = 'No tenés materias adeudadas actualmente. ¡Felicitaciones!',
}) {
  const [deudas, setDeudas] = useState([]);
  const [rendiciones, setRendiciones] = useState([]);
  const [actividades, setActividades] = useState([]);
  const [intensificaciones, setIntensificaciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const cargasRef = useRef(0);
  const alumnoId = alumno?.id;

  useEffect(() => {
    const seq = ++cargasRef.current;
    setDeudas([]);
    setRendiciones([]);
    setActividades([]);
    setIntensificaciones([]);
    if (!alumnoId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    const params = { alumno: alumnoId };
    Promise.all([
      getMateriasAdeudadas(params),
      getRendicionesMateriasAdeudadas(params),
      getActividadesMateriasAdeudadas(params),
      getIntensificacionesAcademicas(params),
    ])
      .then(([deudasRes, rendRes, actsRes, intensRes]) => {
        if (seq !== cargasRef.current) return;
        setDeudas(Array.isArray(deudasRes) ? deudasRes : []);
        setRendiciones(Array.isArray(rendRes) ? rendRes : []);
        setActividades(Array.isArray(actsRes) ? actsRes : []);
        setIntensificaciones(Array.isArray(intensRes) ? intensRes : []);
      })
      .catch(() => {
        if (seq !== cargasRef.current) return;
        setDeudas([]);
        setRendiciones([]);
        setActividades([]);
        setIntensificaciones([]);
      })
      .finally(() => {
        if (seq === cargasRef.current) setLoading(false);
      });
  }, [alumnoId]);

  const rendicionesPorDeuda = useMemo(() => {
    const mapa = {};
    rendiciones.forEach((r) => {
      const key = Number(r.id_materia_adeudada);
      if (!mapa[key]) mapa[key] = [];
      mapa[key].push(r);
    });
    return mapa;
  }, [rendiciones]);

  const actividadesPorMateria = useMemo(() => {
    const mapa = {};
    actividades.forEach((a) => {
      const key = a.materia_nombre || 'Sin materia';
      if (!mapa[key]) mapa[key] = [];
      mapa[key].push(a);
    });
    return mapa;
  }, [actividades]);

  const intensificacionesPorMateria = useMemo(() => {
    const mapa = {};
    intensificaciones.forEach((i) => {
      const key = i.materia_nombre || 'Sin materia';
      if (!mapa[key]) mapa[key] = [];
      mapa[key].push(i);
    });
    return mapa;
  }, [intensificaciones]);

  const rendicionesPorMateria = useMemo(() => {
    const mapa = {};
    rendiciones.forEach((r) => {
      const key = r.materia_nombre || `Materia #${r.id_materia}`;
      if (!mapa[key]) mapa[key] = [];
      mapa[key].push(r);
    });
    return mapa;
  }, [rendiciones]);

  const materiasDerivadas = useMemo(() => {
    const mapa = new Map();
    const asegurar = (nombre) => {
      const key = nombre || 'Sin materia';
      if (!mapa.has(key)) {
        mapa.set(key, {
          id_materia_adeudada: `derivada-${mapa.size}`,
          id_materia: null,
          materia_nombre: key,
          estado: 'INTENSIFICANDO',
          tipo_deuda: 'INTENSIFICACION',
          observaciones: '',
        });
      }
      return mapa.get(key);
    };
    intensificaciones.forEach((i) => {
      const fila = asegurar(i.materia_nombre);
      if (i.estado === 'APROBADA') fila.estado = 'APROBADA';
    });
    actividades.forEach((a) => {
      const fila = asegurar(a.materia_nombre);
      if (a.tipo === 'PREVIA') fila.tipo_deuda = 'PREVIA';
    });
    rendiciones.forEach((r) => {
      const fila = asegurar(r.materia_nombre || `Materia #${r.id_materia}`);
      fila.tipo_deuda = 'PREVIA';
      if (r.estado === 'APROBADA') fila.estado = 'APROBADA';
    });
    return Array.from(mapa.values());
  }, [actividades, intensificaciones, rendiciones]);

  if (loading) {
    return (
      <div className="card">
        <div className="card-header"><h2 className="m-0">{titulo}</h2></div>
        <div className="card-body"><LoadingSpinner text="Cargando materias adeudadas..." size="sm" inline /></div>
      </div>
    );
  }

  const sinDatos = deudas.length === 0 && rendiciones.length === 0 && actividades.length === 0 && intensificaciones.length === 0;
  if (sinDatos) {
    return (
      <div className="card">
        <div className="card-header"><h2 className="m-0">{titulo}</h2></div>
        <div className="card-body">
          <p className="empty-state-message">{textoSinDeudas}</p>
        </div>
      </div>
    );
  }

  const deudasParaMostrar = deudas.length > 0 ? deudas : materiasDerivadas;

  return (
    <div className="card">
      <div className="card-header"><h2 className="m-0">{titulo}</h2></div>
      <div className="card-body">
        <p className="text-muted">
          {descripcion || 'Estado actual de las materias que todavía adeudás: si debés intensificarla, si pasaste a previa o si ya la aprobaste (con fecha y nota).'}
        </p>

        <div style={{ display: 'grid', gap: '16px', marginTop: '16px' }}>
          {deudasParaMostrar.map((d) => {
            const rends = rendicionesPorDeuda[Number(d.id_materia_adeudada)] || rendicionesPorMateria[d.materia_nombre] || [];
            const actApo = actividadesPorMateria[d.materia_nombre] || [];
            const intens = intensificacionesPorMateria[d.materia_nombre] || [];
            const actividadesIntensificacion = actApo.filter((a) => a.tipo === 'INTENSIFICACION');
            const actividadesPrevia = actApo.filter((a) => a.tipo === 'PREVIA');
            const ultimaAprobada = rends
              .filter((r) => r.estado === 'APROBADA')
              .sort((a, b) => String(b.fecha_rendicion || '').localeCompare(String(a.fecha_rendicion || '')))[0];

            return (
              <div
                key={d.id_materia_adeudada}
                className="card"
                style={{ background: '#f8f9fa', borderLeft: `4px solid ${d.estado === 'APROBADA' ? '#4caf50' : (d.tipo_deuda === 'PREVIA' ? '#e53935' : '#ff9800')}` }}
              >
                <div className="flex-row--between" style={{ flexWrap: 'wrap', gap: '8px' }}>
                  <h3 style={{ margin: 0 }}>
                    {d.materia_nombre || `Materia #${d.id_materia}`}
                    {d.curso_origen_nombre && (
                      <small className="text-muted" style={{ marginLeft: '8px' }}>
                        ({d.curso_origen_nombre})
                      </small>
                    )}
                  </h3>
                  <div className="flex-row" style={{ gap: '6px', flexWrap: 'wrap' }}>
                    {badgeEstado(d.estado)}
                    {d.tipo_deuda === 'RECURSADA' && <span className="badge badge-neutral">Recursada</span>}
                    {d.tipo_deuda === 'PREVIA' && <span className="badge badge-danger">Previa</span>}
                  </div>
                </div>

                {d.estado === 'APROBADA' && (
                  <div className="mt-12" style={{ background: '#e8f5e9', border: '1px solid #c8e6c9', borderRadius: '8px', padding: '12px' }}>
                    <strong>¡Aprobada!</strong>{' '}
                    {d.fecha_aprobacion && <span>Fecha de aprobación: <strong>{fmtFecha(d.fecha_aprobacion)}</strong>.</span>}
                    {ultimaAprobada && (
                        <span> Nota: <strong>{fmtNota(ultimaAprobada.nota)}</strong> ({periodoLabel(ultimaAprobada.periodo)}{' '}
                        {ultimaAprobada.anio_rendicion}).</span>
                    )}
                  </div>
                )}

                {d.estado === 'RECURSANDO' && (
                  <p className="mt-12 text-muted">
                    <i className="fas fa-book-reader" aria-hidden="true" /> Debe recursar esta materia.
                  </p>
                )}

                {d.estado !== 'APROBADA' && (
                  <>
                    <h4 className="mt-16" style={{ marginBottom: '8px' }}>
                      <i className="fas fa-pen" aria-hidden="true" /> Intensificaciones
                    </h4>
                    {actividadesIntensificacion.length === 0 && intens.length === 0 ? (
                      <p className="text-muted" style={{ fontSize: '0.9rem' }}>
                        No hay intensificaciones registradas todavía para esta materia.
                      </p>
                    ) : (
                      <ul style={{ paddingLeft: '20px', fontSize: '0.9rem', display: 'grid', gap: '8px' }}>
                        {intens.map((i) => (
                          <li key={i.id_intensificacion}>
                            <strong>{periodoLabel(i.periodo)} {i.anio_rendicion}</strong>{' '}
                            {badgeEstado(i.estado)}
                            {i.nota != null && <span> — Nota: <strong>{fmtNota(i.nota)}</strong></span>}
                            {i.fecha_registro && <span className="text-muted"> · {fmtFecha(i.fecha_registro)}</span>}
                          </li>
                        ))}
                        {actividadesIntensificacion.map((act) => (
                          <li key={act.id_actividad}>
                            <strong>Actividad: {act.titulo}</strong>
                            {act.periodo_intensificacion && <span> ({act.periodo_intensificacion})</span>}
                            {act.descripcion && <span> — {act.descripcion}</span>}
                            {act.archivo_pdf && (
                              <div style={{ marginTop: '4px' }}>
                                <a href={buildMediaUrl(act.archivo_pdf)} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-secondary">
                                  <i className="fas fa-file-pdf" /> Descargar PDF
                                </a>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}

                    {d.tipo_deuda === 'PREVIA' && (
                      <>
                        <h4 className="mt-16" style={{ marginBottom: '8px' }}>
                          <i className="fas fa-book" aria-hidden="true" /> Previas
                        </h4>
                        {rends.length === 0 ? (
                          <p className="text-muted" style={{ fontSize: '0.9rem' }}>
                            Todavía no rendiste esta previa.
                          </p>
                        ) : (
                          <div className="table-responsive">
                            <table>
                              <thead>
                                <tr>
                                  <th>Instancia</th>
                                  <th>Estado</th>
                                  <th>Nota</th>
                                  <th>Fecha</th>
                                </tr>
                              </thead>
                              <tbody>
                                {rends.map((r) => (
                                  <tr key={r.id_rendicion}>
                                    <td>{periodoLabel(r.periodo)} {r.anio_rendicion}</td>
                                    <td>{badgeEstado(r.estado)}</td>
                                    <td>{fmtNota(r.nota)}</td>
                                    <td>{fmtFecha(r.fecha_rendicion)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}

                        {actividadesPrevia.length > 0 && (
                          <>
                            <h4 className="mt-16" style={{ marginBottom: '8px' }}>
                              <i className="fas fa-book-open" aria-hidden="true" /> Actividades de apoyo para la previa
                            </h4>
                            <ul style={{ paddingLeft: '20px', fontSize: '0.9rem', display: 'grid', gap: '8px' }}>
                              {actividadesPrevia.map((act) => (
                                <li key={act.id_actividad}>
                                  <strong>{act.titulo}</strong>
                                  {act.descripcion && <span> — {act.descripcion}</span>}
                                  {act.archivo_pdf && (
                                    <div style={{ marginTop: '4px' }}>
                                      <a href={buildMediaUrl(act.archivo_pdf)} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-secondary">
                                        <i className="fas fa-file-pdf" /> Descargar PDF
                                      </a>
                                    </div>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </>
                        )}
                      </>
                    )}
                  </>
                )}

                {d.observaciones && (
                  <p className="text-muted mt-12" style={{ fontSize: '0.85rem' }}>
                    <i className="fas fa-sticky-note" aria-hidden="true" /> <strong>Observaciones:</strong> {d.observaciones}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default PanelMateriasAdeudadas;
