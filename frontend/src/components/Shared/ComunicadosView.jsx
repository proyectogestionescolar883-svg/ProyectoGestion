import { useEffect, useMemo, useRef, useState } from 'react';
import { buildMediaUrl } from '../../utils/medios';
import { useData } from '../../context/DataContext';
import { useAuth } from '../../context/AuthContext';
import { parseCurso } from '../../utils/orientacion';
import { BASE_URL } from '../../services/api';

const API_BASE = BASE_URL;

function badgeClass(estado) {
  if (estado === 'Presente') return 'badge-presente';
  if (estado === 'Ausente') return 'badge-ausente';
  return 'badge-tarde';
}

function getAlcances(comunicado) {
  if (Array.isArray(comunicado?.alcances)) return comunicado.alcances;
  if (comunicado?.alcance) return [comunicado.alcance];
  return [];
}

function comunicadoMatchesAlcance(cursoObj, alcance, idMateria) {
  if (!cursoObj || !alcance) return false;

  const hasCiclo = alcance.id_ciclo !== null && alcance.id_ciclo !== undefined;
  const hasCurso = alcance.curso !== null && alcance.curso !== undefined;
  const hasDivision = alcance.division !== null && alcance.division !== undefined;
  const hasMateria = alcance.id_materia !== null && alcance.id_materia !== undefined;

  if (!hasCiclo && !hasCurso && !hasDivision && !hasMateria) return true;
  if (hasCiclo && Number(cursoObj.id_ciclo) !== Number(alcance.id_ciclo)) return false;

  const parts = parseCurso(cursoObj.nombre_curso || '');
  if (hasCurso && parts.anio !== Number(alcance.curso)) return false;
  if (hasDivision && parts.division !== Number(alcance.division)) return false;
  if (hasMateria) {
    if (idMateria === undefined) return true;
    if (idMateria === null) return false;
    return Number(alcance.id_materia) === Number(idMateria);
  }

  return true;
}

function comunicadoMatchesCurso(comunicado, cursoObj, idMateria) {
  if (!comunicado || !cursoObj) return false;
  const alcances = getAlcances(comunicado);
  const coincideAlcance = alcances.length
    ? alcances.some((alcance) => comunicadoMatchesAlcance(cursoObj, alcance, idMateria))
    : true;
  if (!coincideAlcance) return false;
  if (
    idMateria !== undefined &&
    comunicado.id_materia !== null &&
    comunicado.id_materia !== undefined
  ) {
    if (idMateria === null) return false;
    return Number(comunicado.id_materia) === Number(idMateria);
  }
  return true;
}

function comunicadoEstaVigente(comunicado, ciclosLectivos) {
  if (comunicado?.estado === false) return false;
  const alcances = getAlcances(comunicado);
  if (!alcances.length) return true;

  const cicloActual = ciclosLectivos
    .filter((c) => c && c.estado !== false && !c.fecha_eliminacion)
    .sort((a, b) => Number(b.anio) - Number(a.anio))[0];
  if (!cicloActual) return false;

  return alcances.some((alcance) => {
    const cicloId = alcance.id_ciclo;
    if (!cicloId) return true;
    return Number(cicloId) === Number(cicloActual.id_ciclo);
  });
}

function ComunicadosView({ userRole, selectedChild, cursoSeleccionado, materiaSeleccionada, misAsignaciones }) {
  const {
    comunicados,
    estudiantes,
    cursosObj,
    cursoMateria,
    docentes,
    padresTutores,
    preceptores,
    administradores,
    ciclosLectivos,
    navIntent,
  } = useData();
  const { user } = useAuth();

  const [selectedComunicado, setSelectedComunicado] = useState(null);
  const [comunicadoResaltado, setComunicadoResaltado] = useState(null);
  const navComunicadoAplicado = useRef(null);

  useEffect(() => {
    const marca = navIntent?.timestamp;
    const comunicadoId = navIntent?.params?.comunicadoId ?? navIntent?.params?.id_comunicado;
    if (!marca || !comunicadoId || navComunicadoAplicado.current === marca) return;
    navComunicadoAplicado.current = marca;
    setComunicadoResaltado(comunicadoId);
  }, [navIntent]);

  const comunicadosFiltrados = useMemo(() => {
    if (!user || !comunicados) return [];

    const userId = user.id || user.id_usuario;

    switch (userRole) {
      case 'alumno': {
        const miEstudiante = estudiantes.find((a) => a.id_usuario === userId);
        const miCurso = miEstudiante ? cursosObj.find((c) => c.id_curso === miEstudiante.id_curso) : null;
        if (!miCurso) return [];
        return comunicados
          .filter((c) => comunicadoEstaVigente(c, ciclosLectivos))
          .filter((c) => comunicadoMatchesCurso(c, miCurso));
      }

      case 'familia': {
        if (selectedChild && selectedChild.alumnoId) {
          const estudiante = estudiantes.find((a) => a.id === selectedChild.alumnoId);
          const cursoObj = estudiante ? cursosObj.find((c) => c.id_curso === estudiante.id_curso) : null;
          if (!cursoObj) return [];
          return comunicados
            .filter((c) => comunicadoEstaVigente(c, ciclosLectivos))
            .filter((c) => comunicadoMatchesCurso(c, cursoObj));
        }

        const miTutor = padresTutores.find((pt) => pt.id_usuario === userId);
        if (!miTutor) return [];
        const misHijos = estudiantes;
        const cursosHijos = misHijos
          .map((h) => cursosObj.find((c) => c.id_curso === h.id_curso))
          .filter(Boolean);
        return comunicados
          .filter((c) => comunicadoEstaVigente(c, ciclosLectivos))
          .filter((c) => cursosHijos.some((cursoObj) => comunicadoMatchesCurso(c, cursoObj)));
      }

      case 'docente': {
        const asignaciones = Array.isArray(misAsignaciones) ? misAsignaciones : [];
        const cursosDocente = new Set(asignaciones.map((cm) => String(cm.id_curso)));
        if (cursosDocente.size === 0) return [];

        if (!cursoSeleccionado) return [];

        const cursoSeleccionadoObj = cursosObj.find((c) => String(c.id_curso) === String(cursoSeleccionado));
        if (!cursoSeleccionadoObj) return [];
        if (!cursosDocente.has(String(cursoSeleccionadoObj.id_curso))) return [];

        const idMateriaSeleccionada = materiaSeleccionada
          ? (asignaciones.find(
              (cm) => cm.materia_nombre === materiaSeleccionada && String(cm.id_curso) === String(cursoSeleccionado)
            )?.id_materia || null)
          : null;

        return comunicados
          .filter((c) => comunicadoEstaVigente(c, ciclosLectivos))
          .filter((c) => {
            const alcances = getAlcances(c);
            if (!alcances.some((alcance) => comunicadoMatchesAlcance(cursoSeleccionadoObj, alcance))) return false;
            if (idMateriaSeleccionada !== null) {
              const materiasDelComunicado = new Set();
              alcances.forEach((alcance) => {
                if (alcance?.id_materia !== null && alcance?.id_materia !== undefined) {
                  materiasDelComunicado.add(Number(alcance.id_materia));
                }
              });
              if (c.id_materia !== null && c.id_materia !== undefined) {
                materiasDelComunicado.add(Number(c.id_materia));
              }
              if (materiasDelComunicado.size === 0) return true;
              return materiasDelComunicado.has(Number(idMateriaSeleccionada));
            }
            return true;
          });
      }

      case 'preceptor': {
        const miPreceptor = preceptores.find((p) => p.id_usuario === userId);
        if (!miPreceptor) return [];
        let misCursos = cursosObj.filter((c) => Number(c.id_preceptor) === Number(miPreceptor.id));
        if (cursoSeleccionado) {
          misCursos = misCursos.filter(
            (c) => String(c.id_curso) === String(cursoSeleccionado),
          );
          if (misCursos.length === 0) return [];
        }
        let idMateriaSeleccionada = null;
        if (cursoSeleccionado && materiaSeleccionada) {
          const asignacion = cursoMateria.find(
            (cm) => String(cm.id_curso) === String(cursoSeleccionado) &&
              cm.materia_nombre === materiaSeleccionada,
          );
          if (asignacion) idMateriaSeleccionada = asignacion.id_materia;
        }
        return comunicados
          .filter((c) => comunicadoEstaVigente(c, ciclosLectivos))
          .filter((c) => misCursos.some(
            (cursoObj) => comunicadoMatchesCurso(c, cursoObj, idMateriaSeleccionada),
          ));
      }

      case 'jefe_preceptores':
        return comunicados.filter((c) => comunicadoEstaVigente(c, ciclosLectivos));

      case 'admin':
        return comunicados.filter((c) => comunicadoEstaVigente(c, ciclosLectivos));

      default:
        return [];
    }
  }, [comunicados, user, userRole, estudiantes, cursoMateria, cursosObj, docentes, padresTutores, preceptores, selectedChild, cursoSeleccionado, materiaSeleccionada, ciclosLectivos, misAsignaciones]);

  const comunicadosOrdenados = useMemo(() => {
    return [...comunicadosFiltrados].sort((a, b) => {
      const fechaA = new Date(b.fecha || 0);
      const fechaB = new Date(a.fecha || 0);
      return fechaA - fechaB;
    });
  }, [comunicadosFiltrados]);

  const handleFileDownload = (ruta) => {
    window.open(`${buildMediaUrl(ruta)}`, '_blank');
  };

  const getNombreCurso = (cursoId) => {
    const curso = cursosObj.find((c) => c.id_curso === cursoId);
    return curso ? curso.nombre_curso : '—';
  };

  const getNombreMateria = (materiaId) => {
    const cm = cursoMateria.find((c) => c.id_materia === materiaId);
    return cm ? cm.materia_nombre : '—';
  };

  const getNombreAutor = (usuarioId) => {
    if (!usuarioId) return '—';
    // Buscar en docentes
    const docente = docentes?.find((d) => d.id_usuario === usuarioId);
    if (docente) return `${docente.apellido}, ${docente.nombre}`;
    // Buscar en preceptores
    const preceptor = preceptores?.find((p) => p.id_usuario === usuarioId);
    if (preceptor) return `${preceptor.apellido}, ${preceptor.nombre}`;
    // Buscar en administradores/directivos
    const administrador = administradores?.find((a) => a.id_usuario === usuarioId);
    if (administrador) return `${administrador.apellido}, ${administrador.nombre}`;
    // Buscar en padres/tutores
    const tutor = padresTutores?.find((pt) => pt.id_usuario === usuarioId);
    if (tutor) return `${tutor.apellido}, ${tutor.nombre}`;
    // Buscar en estudiantes
    const estudiante = estudiantes?.find((a) => a.id_usuario === usuarioId);
    if (estudiante) return `${estudiante.apellido}, ${estudiante.nombre}`;
    // Fallback
    return `Usuario #${usuarioId}`;
  };

  if (selectedComunicado) {
    return (
      <div className="card">
        <div className="card-header-flex">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setSelectedComunicado(null)}
          >
            <i className="fas fa-arrow-left" aria-hidden="true" /> Volver
          </button>
          <h3><i className="fas fa-bullhorn" aria-hidden="true" /> Detalle del Comunicado</h3>
        </div>

        <div className="mt-16">
          <h2>{selectedComunicado.titulo}</h2>
          <div className="mt-12 text-muted" style={{ fontSize: '14px' }}>
            <p><strong>Autor:</strong> {selectedComunicado.creador_nombre || getNombreAutor(selectedComunicado.id_usuario_creador)}</p>
            <p><strong>Fecha y hora:</strong> {selectedComunicado.fecha}</p>
            <p><strong>Curso destinatario:</strong> {selectedComunicado.alcance_label || getNombreCurso(selectedComunicado.id_curso) || 'General'}</p>
            {selectedComunicado.id_materia && (
              <p><strong>Materia destinataria:</strong> {getNombreMateria(selectedComunicado.id_materia)}</p>
            )}
          </div>

          <div className="mt-20" style={{ padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
            <p style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{selectedComunicado.cuerpo}</p>
          </div>

          {selectedComunicado.archivos && selectedComunicado.archivos.length > 0 && (
            <div className="mt-20">
              <h4>Archivos adjuntos ({selectedComunicado.archivos.length})</h4>
              <div className="mt-12" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {selectedComunicado.archivos.map((archivo) => (
                  <div
                    key={archivo.id}
                    className="flex-row--between"
                    style={{ padding: '12px', background: '#fff', border: '1px solid #ddd', borderRadius: '4px' }}
                  >
                    <span style={{ fontSize: '14px' }}>
                      <i className="fas fa-paperclip" aria-hidden="true" />{' '}
                      {archivo.ruta_archivo.split('/').pop()}
                    </span>
                    <div className="flex-row">
                      <button
                        type="button"
                        className="btn btn-sm btn-success"
                        onClick={() => handleFileDownload(archivo.ruta_archivo)}
                      >
                        <i className="fas fa-eye" aria-hidden="true" /> Ver
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = buildMediaUrl(archivo.ruta_archivo);
                          link.download = archivo.ruta_archivo.split('/').pop();
                          link.click();
                        }}
                      >
                        <i className="fas fa-download" aria-hidden="true" /> Descargar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header-flex">
        <h3><i className="fas fa-bullhorn" aria-hidden="true" /> Comunicados</h3>
      </div>

      {comunicadosOrdenados.length === 0 ? (
        <p className="empty-state-message empty-state-centered">
          No hay comunicados disponibles para visualizar.
        </p>
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Título</th>
                <th>Fecha de publicación</th>
                <th>Autor</th>
                <th>Curso asignado</th>
                <th>Materia asignada</th>
                <th>Archivos adjuntos</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {comunicadosOrdenados.map((c) => (
                <tr
                  key={c.id || c.id_comunicado}
                  style={String(comunicadoResaltado) === String(c.id ?? c.id_comunicado)
                    ? { background: '#eef2ff', outline: '2px solid #4f46e5' }
                    : undefined}
                >
                  <td className="table-cell-strong">{c.titulo}</td>
                  <td>{c.fecha ? c.fecha.split('T')[0] : '—'}</td>
                  <td>{c.creador_nombre || getNombreAutor(c.id_usuario_creador)}</td>
                  <td>{c.alcance_label || 'General'}</td>
                  <td>{c.id_materia ? getNombreMateria(c.id_materia) : '—'}</td>
                  <td>
                    {c.archivos && c.archivos.length > 0 ? (
                      <span className="badge">{c.archivos.length} archivo(s)</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={() => setSelectedComunicado(c)}
                    >
                      <i className="fas fa-eye" aria-hidden="true" /> Ver
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ComunicadosView;
