import { useState, useMemo, useEffect, useRef } from 'react';

import Sidebar from './sidebar';
import Header from './header';

import Estudiantes from './estudiantes';
import TutoresFamilias from './tutoresFamilias';
import Asistencias from './asistencias';
import Notas from './notas';
import Actas from './actas';
import Docentes from './docentes';
import GestionDiaria from './GestionDiaria';
import LibroTemasPreceptor from './LibroTemasPreceptor';
import Proyectos from './Proyectos';
import ActividadesView from '../Shared/ActividadesView';
import Horarios from '../Administracion/horarios';
import Notificaciones from '../Notificaciones';
import ComunicadosView from '../Shared/ComunicadosView';
import CalendarioInstitucional from '../Administracion/CalendarioInstitucional';
import AdelantosHoras from '../Shared/AdelantosHoras';
import PanelPreceptor from './PanelPreceptor';
import { useData } from '../../context/DataContext';
import { viewDesdeDestino } from '../../utils/navDestinos';

function PreceptorDashboard({ user, onLogout }) {

  const { preceptores, navIntent, cursosObj, cursoMateria } = useData();

  const userId = user?.id_usuario ?? user?.id ?? null;
  const miPreceptor = useMemo(
    () => preceptores.find((p) => p.id_usuario === userId) || null,
    [preceptores, userId],
  );
  const nombreCompletoPreceptor = miPreceptor ? `${miPreceptor.apellido}, ${miPreceptor.nombre}` : null;

  const [view, setView] = useState('perfil');
  const [anioLectivo, setAnioLectivo] = useState('');
  const [curso, setCurso] = useState('');

  // Parte 8 / 5.1: manejar navegación desde notificaciones. Además de la vista,
  // deja año lectivo y curso ya seleccionados. El curso puede venir por nombre o
  // por id; si llega por id se resuelve contra `cursosObj` (una vez, por
  // timestamp, para no pisar la elección manual del header).
  const navAplicadoRef = useRef(null);
  const navCmAplicadoRef = useRef(null);
  const [cursoPendienteNav, setCursoPendienteNav] = useState('');
  const [navContext, setNavContext] = useState(null);

  useEffect(() => {
    if (!navIntent || !navIntent.destino) return;
    if (navAplicadoRef.current === navIntent.timestamp) return;
    navAplicadoRef.current = navIntent.timestamp;

    const vista = viewDesdeDestino(navIntent.destino, 'preceptor');
    if (vista) setView(vista);

    const p = navIntent.params || {};
    setNavContext({ ...p, destino: navIntent.destino, timestamp: navIntent.timestamp });
    const anio = p.anio ?? p.anioLectivo ?? null;
    if (anio) setAnioLectivo(String(anio));

    const porNombre = p.cursoNombre ?? p.curso_nombre
      ?? (typeof p.curso === 'string' && /[°º]/.test(p.curso) ? p.curso : null)
      ?? null;
    const porId = p.cursoId ?? p.curso_id
      ?? (typeof p.curso === 'string' && p.curso && !/[°º]/.test(p.curso) ? p.curso : null)
      ?? null;

    if (porNombre) {
      setCurso(String(porNombre));
      setCursoPendienteNav('');
    } else if (porId) {
      setCursoPendienteNav(String(porId));
    }
  }, [navIntent]);

  useEffect(() => {
    if (!cursoPendienteNav) return;
    const encontrado = (cursosObj || []).find(
      (c) => String(c.id_curso) === String(cursoPendienteNav),
    );
    if (encontrado) {
      setCurso(String(encontrado.nombre_curso));
      setCursoPendienteNav('');
    }
  }, [cursoPendienteNav, cursosObj]);

  useEffect(() => {
    const marca = navContext?.timestamp;
    const cmId = navContext?.cursoMateriaId ?? navContext?.curso_materia_id;
    if (!marca || !cmId || navCmAplicadoRef.current === marca) return;
    const asignacion = (cursoMateria || []).find(
      (cm) => String(cm.id) === String(cmId),
    );
    if (!asignacion) return;
    const cursoDelCm = (cursosObj || []).find(
      (c) => String(c.id_curso) === String(asignacion.id_curso),
    );
    if (!cursoDelCm) return;
    navCmAplicadoRef.current = marca;
    setCurso(String(cursoDelCm.nombre_curso));
    setCursoPendienteNav('');
  }, [navContext, cursoMateria, cursosObj]);

  const materiaNav = useMemo(() => {
    const p = navContext || {};
    if (p.materia_nombre || p.materiaNombre) return String(p.materia_nombre || p.materiaNombre);
    const idMateria = p.materiaId ?? p.materia_id;
    if (idMateria) {
      return (cursoMateria || []).find(
        (cm) => String(cm.id_materia) === String(idMateria),
      )?.materia_nombre || '';
    }
    const cmId = p.cursoMateriaId ?? p.curso_materia_id;
    if (cmId) {
      return (cursoMateria || []).find((cm) => String(cm.id) === String(cmId))?.materia_nombre || '';
    }
    return '';
  }, [navContext, cursoMateria]);

  const handleAnioChange = (nuevoAnio) => {
    setAnioLectivo(nuevoAnio);
    setCurso('');
  };

  const filtrosProps = {
    anioLectivo,
    curso,
    onAnioChange: handleAnioChange,
    onCursoChange: setCurso,
  };

  const cursoId = useMemo(
    () => (curso ? (cursosObj || []).find((c) => c.nombre_curso === curso)?.id_curso || null : null),
    [curso, cursosObj],
  );

  const renderView = () => {

    switch (view) {

      case 'perfil':
        return (
          <div className="view-section active">
            <PanelPreceptor miPreceptor={miPreceptor} />
          </div>
        );

      case 'alumnos':
        return (
          <div className="view-section active">
            <Estudiantes
              preceptorCursos={miPreceptor?.cursos || []}
              anioLectivo={anioLectivo}
              curso={curso}
              onAnioChange={handleAnioChange}
              onCursoChange={setCurso}
            />
          </div>
        );

      case 'tutores':
        return (
          <div className="view-section active">
            <TutoresFamilias
              anioLectivo={anioLectivo}
              curso={curso}
              preceptorCursos={miPreceptor?.cursos}
            />
          </div>
        );

      case 'docentes':
        return (
          <div className="view-section active">
            <Docentes anioLectivo={anioLectivo} curso={curso} />
          </div>
        );

      case 'horarios':
        return (
          <div className="view-section active">
            <Horarios cursoGlobal={curso} />
          </div>
        );

      case 'panel-diario':
        return (
          <div className="view-section active">
            <GestionDiaria anioLectivo={anioLectivo} curso={curso} onNavigate={setView} />
          </div>
        );

      case 'proyectos':
        return (
          <div className="view-section active">
            <Proyectos anioLectivo={anioLectivo} curso={curso} />
          </div>
        );

      case 'libro-temas':
        return (
          <div className="view-section active">
            <LibroTemasPreceptor {...filtrosProps} />
          </div>
        );

      case 'actividades':
        return (
          <div className="view-section active">
            <ActividadesView userRole="preceptor" cursoId={cursoId} cursoNombre={curso} />
          </div>
        );

      case 'adelantos-horas':
        return (
          <div className="view-section active">
            <AdelantosHoras />
          </div>
        );

      case 'asistencias':
        return (
          <div className="view-section active">
            <Asistencias {...filtrosProps} navContext={navContext} />
          </div>
        );

      case 'notas':
        return (
          <div className="view-section active">
            <Notas {...filtrosProps} navContext={navContext} />
          </div>
        );

      case 'actas':
        return (
          <div className="view-section active">
            <Actas {...filtrosProps} navContext={navContext} />
          </div>
        );

      case 'notificaciones':
        return (
          <div className="view-section active">
            <Notificaciones userRole="preceptor" />
          </div>
        );

      case 'comunicados':
        return (
          <div className="view-section active">
            <ComunicadosView
              userRole="preceptor"
              cursoSeleccionado={cursoId}
              materiaSeleccionada={materiaNav || undefined}
            />
          </div>
        );

      case 'calendario':
        return (
          <div className="view-section active">
            <CalendarioInstitucional readOnly navContext={navContext} />
          </div>
        );

      default:
        return (
          <div className="view-section active">
            <Estudiantes
              anioLectivo={anioLectivo}
              curso={curso}
              onAnioChange={handleAnioChange}
              onCursoChange={setCurso}
            />
          </div>
        );
    }
  };

  return (
    <div className="dashboard-layout">

      <Sidebar
        view={view}
        setView={setView}
        onLogout={onLogout}
      />

      <main className="main-content">

        <Header
          user={user}
          nombreCompleto={nombreCompletoPreceptor}
          anioLectivo={anioLectivo}
          curso={curso}
          onAnioChange={handleAnioChange}
          onCursoChange={setCurso}
          miPreceptor={miPreceptor}
        />

        {/* ===================================================== */}
        {/* CONTENIDO PRINCIPAL                                   */}
        {/* ===================================================== */}

        <div className="dashboard-content">
          {renderView()}
        </div>

      </main>
    </div>
  );
}

export default PreceptorDashboard;