import { useEffect, useState } from 'react';
import { getRiteAcademico } from '../services/api';
import { setRiteImpresionBloqueada } from '../utils/rite';

// Obtiene las secciones adicionales del rite desde
// /api/boletin-academico/<alumnoId>/.
// Claves devueltas por el endpoint:
//   - intensificaciones_1c: { [materia_nombre]: nota }  (intensificacion 1er cuatrimestre)
//   - bloqueos_por_materia: { [materia_nombre]: { bloqueada, motivo } }
//   - intensificaciones_posteriores: [{ materia, anio, diciembre, febrero }]
//   - recursadas: [{ materia, anio, estado, prenota1, nota1, prenota2, nota2,
//                    intensificacion_1c, diciembre, febrero, observaciones }]
//   - previas: [{ materia, anio, rendiciones: { [PERIODO]: nota }, calificacion_final }]
export function useRiteAcademico(alumnoId) {
  const [intensificaciones_1c, setIntensificaciones1c] = useState({});
  const [bloqueos_por_materia, setBloqueos] = useState({});
  const [intensificaciones_posteriores, setPosteriores] = useState([]);
  const [recursadas, setRecursadas] = useState([]);
  const [previas, setPrevias] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const clave = String(alumnoId || '');
    if (!alumnoId) {
      setIntensificaciones1c({});
      setBloqueos({});
      setPosteriores([]);
      setRecursadas([]);
      setPrevias([]);
      setLoading(false);
      setError(null);
      setRiteImpresionBloqueada(clave, false);
      return undefined;
    }
    let cancel = false;
    setLoading(true);
    setError(null);
    setRiteImpresionBloqueada(clave, false);
    getRiteAcademico(alumnoId)
      .then((res) => {
        if (cancel) return;
        const d = res || {};
        setIntensificaciones1c(d.intensificaciones_1c || {});
        setBloqueos(d.bloqueos_por_materia || {});
        setPosteriores(d.intensificaciones_posteriores || []);
        setRecursadas(d.recursadas || []);
        setPrevias(d.previas || []);
      })
      .catch(() => {
        if (cancel) return;
        setError('No se pudieron cargar los datos académicos del RITE.');
        setRiteImpresionBloqueada(clave, true);
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
      setRiteImpresionBloqueada(clave, false);
    };
  }, [alumnoId]);

  return {
    intensificaciones_1c,
    bloqueos_por_materia,
    intensificaciones_posteriores,
    recursadas,
    previas,
    loading,
    error,
    puedeImprimir: !error,
  };
}
