import { useEffect, useMemo } from 'react';
import { useData } from '../../context/DataContext';
import FiltrosAnioCurso from '../Shared/FiltrosAnioCurso';
import { estudiantesPorAnioYCurso } from '../Preceptores/preceptorUtils';

function TutoresEstudiantesEditor({
  anioEstudiante,
  setAnioEstudiante,
  cursoEstudiante,
  setCursoEstudiante,
  alumnos_ids,
  setEstudiantesIds,
  idPrefix = 'tut-estudiante',
}) {
  const { inscripciones, estudiantes, aniosLectivos, cursosObj, ensureData } = useData();
  const idsSeleccionados = useMemo(
    () => (Array.isArray(alumnos_ids) ? alumnos_ids : []),
    [alumnos_ids],
  );
  const ayudaId = `${idPrefix}-ayuda`;
  useEffect(() => {
    if (typeof ensureData === 'function') ensureData('inscripciones');
  }, [ensureData]);

  const listaEstudiantes = estudiantesPorAnioYCurso(
    anioEstudiante,
    cursoEstudiante,
    inscripciones,
    estudiantes,
  );

  const toggleEstudiante = (id) => {
    const idNum = Number(id);
    if (Number.isNaN(idNum) || idNum <= 0) return;
    const yaExiste = idsSeleccionados.includes(idNum);
    if (yaExiste) {
      setEstudiantesIds(idsSeleccionados.filter((x) => x !== idNum));
    } else {
      setEstudiantesIds([...idsSeleccionados, idNum]);
    }
  };

  return (
    <div style={{ display: 'grid', gap: '10px' }}>
      <FiltrosAnioCurso
        aniosLectivos={aniosLectivos}
        cursosObj={cursosObj}
        anioLectivo={anioEstudiante}
        curso={cursoEstudiante}
        onAnioChange={setAnioEstudiante}
        onCursoChange={setCursoEstudiante}
      />
      {!anioEstudiante || !cursoEstudiante ? (
        <p className="empty-state-message">
          Seleccioná año lectivo y curso para asignar estudiantes.
        </p>
      ) : listaEstudiantes.length === 0 ? (
        <p className="empty-state-message">
          No hay estudiantes registrados en ese curso.
        </p>
      ) : (
        <div
          aria-describedby={ayudaId}
          style={{
            maxHeight: 220,
            overflowY: 'auto',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
          }}
        >
          {listaEstudiantes.map((al) => {
            const activo = idsSeleccionados.includes(Number(al.id));
            return (
              <label
                key={al.id}
                className={`preceptor-curso-option${activo ? ' preceptor-curso-option--selected' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '9px 12px',
                  cursor: 'pointer',
                  borderBottom: '1px solid var(--border-color)',
                  margin: 0,
                }}
              >
                <input
                  type="checkbox"
                  id={`${idPrefix}-${al.id}`}
                  checked={activo}
                  onChange={() => toggleEstudiante(al.id)}
                />
                <span>
                  {al.apellido}, {al.nombre}
                </span>
              </label>
            );
          })}
        </div>
      )}
      <p id={ayudaId} className="m-0" style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>
        Asignados: <strong>{idsSeleccionados.length}</strong> estudiante(s)
      </p>
    </div>
  );
}

export default TutoresEstudiantesEditor;