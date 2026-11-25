import { iconoAccion, nombreAccion } from './AccionesCelda';

const ACCIONES = [
  { id: 'editar', emoji: '✏️' },
  { id: 'deshabilitar', emoji: '🚫' },
  { id: 'programar', emoji: '🗓️' },
  { id: 'eliminar', emoji: '🗑️' },
  { id: 'habilitar', emoji: '✅' },
  { id: 'finalizar', emoji: '🏁' },
  { id: 'ver', emoji: '👁️' },
  { id: 'ddjj-descargar', emoji: '⬇️' },
  { id: 'ddjj-verificar', emoji: '🔎' },
];

function AccionesLeyenda({ acciones = [] }) {
  const items = ACCIONES.filter((a) => acciones.includes(a.id));
  if (items.length === 0) return null;

  return (
    <div className="acciones-leyenda" aria-label="Leyenda de acciones">
      {items.map((item) => (
        <span key={item.id} className="acciones-leyenda-item">
          <span className="acciones-leyenda-emoji" aria-hidden="true">
            <i className={iconoAccion(item.id) || item.emoji} />
          </span>{' '}
          {nombreAccion(item.id)}
        </span>
      ))}
    </div>
  );
}

export default AccionesLeyenda;
