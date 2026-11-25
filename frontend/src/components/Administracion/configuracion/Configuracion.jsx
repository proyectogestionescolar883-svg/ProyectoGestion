import CiclosLectivos from './CiclosLectivos';
import ModulosHorarios from './ModulosHorarios';
import PeriodosEvaluacion from './PeriodosEvaluacion';
import EstadosAsistencia from './EstadosAsistencia';
import TiposActa from './TiposActa';

/**
 * Configuración — módulo de datos maestros de Administración.
 *
 * Contenedor con pestañas. Cada pestaña es un catálogo independiente (ciclo
 * lectivo, módulo horario, período de evaluación, estado de asistencia, tipo de
 * acta) y todas comparten el armazón `CatalogoConfiguracion`, que replica el
 * patrón de `Administracion/materias.jsx`.
 *
 * Elimina la dependencia de INSERT SQL manuales para dejar el sistema operable:
 * antes, con la base vacía, no había forma de crear un ciclo lectivo, un módulo
 * horario ni un período de evaluación desde la interfaz.
 *
 * Es un componente CONTROLADO: la pestaña activa es el nombre de vista del
 * dashboard, no estado propio. Así el submenú lateral, las pestañas internas y
 * la navegación por `navIntent` comparten una sola fuente de verdad y el ítem
 * resaltado del sidebar siempre coincide con la pantalla mostrada.
 */
const PESTANAS = [
  { id: 'ciclos-lectivos', etiqueta: 'Ciclos lectivos', Componente: CiclosLectivos },
  { id: 'modulos-horarios', etiqueta: 'Módulos horarios', Componente: ModulosHorarios },
  { id: 'periodos-evaluacion', etiqueta: 'Períodos de evaluación', Componente: PeriodosEvaluacion },
  { id: 'estados-asistencia', etiqueta: 'Estados de asistencia', Componente: EstadosAsistencia },
  { id: 'tipos-acta', etiqueta: 'Tipos de acta', Componente: TiposActa },
];

export default function Configuracion({ pestana, onPestanaChange }) {
  const activa = PESTANAS.find((p) => p.id === pestana) || PESTANAS[0];
  const Componente = activa.Componente;

  return (
    <div className="card configuracion-card">
      <div className="card-header">
        <div className="configuracion-header-row">
          <h2 className="m-0">
            <i className="fas fa-sliders-h" aria-hidden="true" /> Configuración
          </h2>
          <div className="tabs-container configuracion-tabs">
            {PESTANAS.map((p) => (
              <button
                key={p.id}
                type="button"
                className={`tab-btn${activa.id === p.id ? ' active' : ''}`}
                onClick={() => onPestanaChange?.(p.id)}
              >
                {p.etiqueta}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="card-body">
        {/* `key` fuerza el remount al cambiar de pestaña: cada catálogo arranca
            con su propio formulario cerrado y su propio estado de listado. */}
        <Componente key={activa.id} />
      </div>
    </div>
  );
}