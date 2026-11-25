import { useMemo, useState, useEffect, useRef, useCallback } from 'react';
import { useData } from '../../context/DataContext';
import { useToast } from '../../context/ToastContext';
import {
  getCursoMateria,
  getHorarios,
  createHorario,
  updateHorario,
  deleteHorario,
  getHorariosEspeciales,
  createHorarioEspecial,
  updateHorarioEspecial,
  deleteHorarioEspecial,
} from '../../services/api';
import VistaHorarios from './VistaHorarios';
import AccionesCelda from '../../components/Shared/AccionesCelda';
import AvisoDatosMaestros from '../../components/Shared/AvisoDatosMaestros';
import confirmarEliminacion from '../../utils/confirmarEliminacion';
import { mensajeErrorAmigable } from '../../utils/errores';
import LoadingSpinner from '../Shared/LoadingSpinner';

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

function esMateriaEF(nombre) {
  const normalizado = (nombre || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/^ed\.\s*/, 'educacion ')
    .replace(/^ed\s+/, 'educacion ')
    .replace(/\s+/g, ' ')
    .trim();
  return normalizado === 'educacion fisica';
}

function timeStr(value) {
  if (!value) return '';
  const s = typeof value === 'string' ? value : String(value);
  return s.slice(0, 5);
}

function sanitizarTexto(value) {
  return String(value ?? '')
    .replace(/[\u0000-\u001F<>]/g, '')
    .trim();
}

function esErrorConflicto(err) {
  const texto = mensajeErrorAmigable(err, '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
  return /ya tiene otra clase|ya tiene otra materia|ya esta ocupada/.test(texto);
}

const HorarioSemanal = function HorarioSemanal({ cursoIdExterno = '', onRegisterSave, soloLectura = false }) {
  const { modulos, refreshData } = useData() || {};
  const toast = useToast();
  const cursoSeleccionado = cursoIdExterno;
  const [materiasCurso, setMateriasCurso] = useState([]);
  const [celdas, setCeldas] = useState({});
  const [originalCeldas, setOriginalCeldas] = useState({});
  const [mensaje, setMensaje] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [cargandoGrilla, setCargandoGrilla] = useState(false);
  const [celdasInvalidas, setCeldasInvalidas] = useState(() => new Set());

  const handleGuardar = useCallback(async () => {
    if (!cursoSeleccionado) return;
    setGuardando(true);
    setMensaje('');
    const celdasSiguientes = { ...celdas };
    const operaciones = [];
    let claveIntentada = null;
    try {
      // La clave de cada celda es `${dia_semana}_${id_modulo}` (ver cargarGrilla).
      const clavesNuevas = Object.keys(celdas).filter((k) => !(k in originalCeldas));
      const clavesEliminadas = Object.keys(originalCeldas).filter((k) => !(k in celdas));
      const clavesActualizadas = Object.keys(celdas).filter(
        (k) => k in originalCeldas
          && celdas[k].id_curso_materia !== originalCeldas[k].id_curso_materia,
      );

      clavesEliminadas.forEach((key) => {
        delete celdasSiguientes[key];
      });

      for (const key of clavesNuevas) {
        claveIntentada = key;
        const [dia, moduloId] = key.split('_');
        const creado = await createHorario({
          id_curso_materia: celdas[key].id_curso_materia,
          id_modulo: Number(moduloId),
          dia_semana: dia,
        });
        if (creado && creado.id_horario != null) {
          celdasSiguientes[key] = {
            ...celdasSiguientes[key],
            id_horario: creado.id_horario,
          };
        }
        operaciones.push({
          revertir: async () => {
            if (creado && creado.id_horario != null) {
              await deleteHorario(creado.id_horario);
            }
            delete celdasSiguientes[key];
          },
        });
      }

      for (const key of clavesActualizadas) {
        claveIntentada = key;
        const anterior = originalCeldas[key];
        await updateHorario(celdas[key].id_horario, {
          id_curso_materia: celdas[key].id_curso_materia,
        });
        operaciones.push({
          revertir: async () => {
            await updateHorario(celdas[key].id_horario, {
              id_curso_materia: anterior.id_curso_materia,
            });
            celdasSiguientes[key] = anterior;
          },
        });
      }

      for (const key of clavesEliminadas) {
        claveIntentada = key;
        const anterior = originalCeldas[key];
        await deleteHorario(anterior.id_horario);
        operaciones.push({
          revertir: async () => {
            const [dia, moduloId] = key.split('_');
            const recreado = await createHorario({
              id_curso_materia: anterior.id_curso_materia,
              id_modulo: Number(moduloId),
              dia_semana: dia,
            });
            if (recreado && recreado.id_horario != null) {
              celdasSiguientes[key] = {
                ...anterior,
                id_horario: recreado.id_horario,
              };
            }
          },
        });
      }

      if (operaciones.length === 0) {
        setMensaje('No hay cambios para guardar.');
        return;
      }

      setCeldas(celdasSiguientes);
      setOriginalCeldas(JSON.parse(JSON.stringify(celdasSiguientes)));
      setMensaje('Horarios guardados correctamente.');
      if (typeof refreshData === 'function') {
        try {
          await refreshData();
        } catch {
          toast.warning('Los horarios se guardaron, pero no se pudo actualizar el resto de los datos.');
        }
      }
    } catch (err) {
      if (claveIntentada && esErrorConflicto(err)) {
        setCeldasInvalidas((prev) => new Set(prev).add(claveIntentada));
      }
      const erroresReversion = [];
      for (const operacion of operaciones.reverse()) {
        try {
          await operacion.revertir();
        } catch (errReversion) {
          erroresReversion.push(mensajeErrorAmigable(errReversion));
        }
      }
      setCeldas(celdasSiguientes);
      setOriginalCeldas(JSON.parse(JSON.stringify(celdasSiguientes)));
      const avisoReversion = erroresReversion.length
        ? ` No se pudo revertir todo: ${erroresReversion.join('; ')}`
        : ' Se revirtieron los cambios parciales.';
      setMensaje(`Error al guardar horarios: ${mensajeErrorAmigable(err)}.${avisoReversion}`);
    } finally {
      setGuardando(false);
    }
  }, [celdas, originalCeldas, cursoSeleccionado, refreshData, toast]);

  useEffect(() => {
    if (onRegisterSave) onRegisterSave(handleGuardar);
  }, [onRegisterSave, handleGuardar]);

  const modulosSorted = useMemo(() => {
    if (!Array.isArray(modulos)) return [];
    return [...modulos].sort((a, b) => (a.hora_inicio || '').localeCompare(b.hora_inicio || ''));
  }, [modulos]);

  useEffect(() => {
    if (!cursoSeleccionado) {
      setMateriasCurso([]);
      setCeldas({});
      setOriginalCeldas({});
      setCeldasInvalidas(new Set());
      return;
    }
    setCargandoGrilla(true);
    setMensaje('');
    setCeldasInvalidas(new Set());
    Promise.all([
      getCursoMateria({ curso: cursoSeleccionado }),
      getHorarios({ curso: cursoSeleccionado }),
    ])
      .then(([cmData, horData]) => {
        const cmList = Array.isArray(cmData) ? cmData : cmData.results || [];
        const horList = Array.isArray(horData) ? horData : horData.results || [];

        const materias = cmList
          .filter((cm) => cm.materia_nombre && !esMateriaEF(cm.materia_nombre))
          .map((cm) => ({ id: cm.id_curso_materia, nombre: cm.materia_nombre }));

        const unicas = [];
        const vistos = new Set();
        materias.forEach((m) => {
          if (!vistos.has(m.nombre)) {
            vistos.add(m.nombre);
            unicas.push(m);
          }
        });
        unicas.sort((a, b) => a.nombre.localeCompare(b.nombre));

        setMateriasCurso(unicas);

        const celdasInit = {};
        horList.forEach((h) => {
          const key = `${h.dia_semana}_${h.id_modulo}`;
          celdasInit[key] = {
            id_horario: h.id_horario,
            id_curso_materia: h.id_curso_materia,
          };
        });
        setCeldas(celdasInit);
        setOriginalCeldas(JSON.parse(JSON.stringify(celdasInit)));
      })
      .catch(() => toast.error('Error al cargar datos del curso.'))
      .finally(() => setCargandoGrilla(false));
  }, [cursoSeleccionado]);

  const getCellValue = (dia, idModulo) => {
    const key = `${dia}_${idModulo}`;
    if (celdasInvalidas.has(key)) return '';
    const cell = celdas[key];
    if (!cell) return '';
    const cm = materiasCurso.find((m) => m.id === cell.id_curso_materia);
    return cm ? cm.nombre : '';
  };

  const handleCellChange = (dia, idModulo, materiaNombre) => {
    const key = `${dia}_${idModulo}`;
    setCeldasInvalidas((prev) => {
      if (!prev.has(key)) return prev;
      const siguiente = new Set(prev);
      siguiente.delete(key);
      return siguiente;
    });
    setCeldas((prev) => {
      const next = { ...prev };
      if (!materiaNombre) {
        delete next[key];
      } else {
        const cm = materiasCurso.find((m) => m.nombre === materiaNombre);
        if (cm) {
          next[key] = {
            id_horario: prev[key]?.id_horario || null,
            id_curso_materia: cm.id,
          };
        }
      }
      return next;
    });
  };

  return (
    <div>
      {cursoSeleccionado && (
        <div>
          {mensaje && (
            <p
              className={`form-error-message ${mensaje.includes('Error') ? '' : 'form-error-message--ok'}`}
              role="status"
            >
              {mensaje}
            </p>
          )}
          {cargandoGrilla ? (
            <LoadingSpinner text="Cargando horarios..." size="sm" inline />
          ) : modulosSorted.length === 0 ? (
            <AvisoDatosMaestros
              mensaje="No hay módulos horarios definidos en el sistema."
              detalle="Los módulos son las franjas horarias que se usan para armar la grilla de horarios."
              accion="Crear módulo horario"
              destino="modulos_horarios"
            />
          ) : materiasCurso.length === 0 ? (
            <p className="empty-state-message empty-state-centered">
              El curso no tiene materias asignadas.
            </p>
          ) : (
            <div>
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th style={{ minWidth: '110px' }}>Horario</th>
                      {DIAS.map((d) => (
                        <th key={d} style={{ minWidth: '140px' }}>{d}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {modulosSorted.map((mod) => (
                      <tr key={mod.id_modulo}>
                        <td className="font-bold nowrap">
                          {timeStr(mod.hora_inicio)} - {timeStr(mod.hora_fin)}
                        </td>
                        {DIAS.map((dia) => (
                          <td key={`${dia}_${mod.id_modulo}`} style={{ padding: '4px 6px' }}>
                            {soloLectura ? (
                              <span className="horario-solo-lectura">{getCellValue(dia, mod.id_modulo)}</span>
                            ) : (
                              <select
                                className="form-control"
                                style={{ width: '100%', padding: '6px 8px', fontSize: '0.8rem' }}
                                value={getCellValue(dia, mod.id_modulo)}
                                onChange={(e) => handleCellChange(dia, mod.id_modulo, e.target.value)}
                              >
                                <option value="" />
                                {materiasCurso.map((m) => (
                                  <option key={m.id} value={m.nombre}>{m.nombre}</option>
                                ))}
                              </select>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
</tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EducacionFisica({ cursoIdExterno = '', soloLectura = false }) {
  const toast = useToast();
  const { refreshData } = useData() || {};
  const cursoSeleccionado = cursoIdExterno;
  const [horarios, setHorarios] = useState([]);
  const [cmEf, setCmEf] = useState(null);
  const [form, setForm] = useState(null);
  const [mensaje, setMensaje] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [cargando, setCargando] = useState(false);

  const FORM_VACIO = { dia_semana: '', hora_inicio: '', hora_fin: '', aula: '' };

  useEffect(() => {
    if (!cursoSeleccionado) {
      setHorarios([]);
      setCmEf(null);
      return;
    }
    setCargando(true);
    setMensaje('');
    Promise.all([
      getCursoMateria({ curso: cursoSeleccionado }),
      getHorariosEspeciales({ curso: cursoSeleccionado }),
    ])
      .then(([cmData, heData]) => {
        const cmList = Array.isArray(cmData) ? cmData : cmData.results || [];
        const heList = Array.isArray(heData) ? heData : heData.results || [];

        const ef = cmList.find((cm) => esMateriaEF(cm.materia_nombre));
        setCmEf(ef || null);

        heList.sort((a, b) => {
          const diaA = DIAS.indexOf(a.dia_semana);
          const diaB = DIAS.indexOf(b.dia_semana);
          if (diaA !== diaB) return diaA - diaB;
          return (a.hora_inicio || '').localeCompare(b.hora_inicio || '');
        });
        setHorarios(heList);
      })
      .catch(() => toast.error('Error al cargar datos.'))
      .finally(() => setCargando(false));
  }, [cursoSeleccionado]);

  const resetForm = () => {
    setForm(null);
    setMensaje('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.dia_semana || !form.hora_inicio || !form.hora_fin) {
      toast.warning('Completá día, hora inicio y hora fin.');
      return;
    }
    if (!cmEf) {
      toast.warning('El curso no tiene Educación Física asignada.');
      return;
    }
    setGuardando(true);
    setMensaje('');
    try {
      const payload = {
        id_curso_materia: cmEf.id_curso_materia,
        dia_semana: form.dia_semana,
        hora_inicio: form.hora_inicio,
        hora_fin: form.hora_fin,
        aula: sanitizarTexto(form.aula) || null,
      };
      if (form.id) {
        await updateHorarioEspecial(form.id, payload);
      } else {
        await createHorarioEspecial(payload);
      }
      resetForm();
      if (typeof refreshData === 'function') {
        try {
          await refreshData();
        } catch {
          toast.warning('El horario se guardó, pero no se pudo actualizar el resumen global.');
        }
      }
      const [heData] = await Promise.all([
        getHorariosEspeciales({ curso: cursoSeleccionado }),
      ]);
      const heList = Array.isArray(heData) ? heData : heData.results || [];
      heList.sort((a, b) => {
        const diaA = DIAS.indexOf(a.dia_semana);
        const diaB = DIAS.indexOf(b.dia_semana);
        if (diaA !== diaB) return diaA - diaB;
        return (a.hora_inicio || '').localeCompare(b.hora_inicio || '');
      });
      setHorarios(heList);
    } catch (err) {
      toast.error(mensajeErrorAmigable(err));
    } finally {
      setGuardando(false);
    }
  };

  const handleEditar = (h) => {
    setForm({
      id: h.id_horario_especial,
      dia_semana: h.dia_semana,
      hora_inicio: timeStr(h.hora_inicio),
      hora_fin: timeStr(h.hora_fin),
      aula: sanitizarTexto(h.aula),
    });
    setMensaje('');
  };

  const handleEliminar = async (h) => {
    await confirmarEliminacion('¿Querés eliminar este horario especial?\n\nEl horario se dará de baja y no aparecerá más en los listados.', {
      onConfirm: async () => {
        try {
          await deleteHorarioEspecial(h.id_horario_especial);
          const [heData] = await Promise.all([
            getHorariosEspeciales({ curso: cursoSeleccionado }),
          ]);
          const heList = Array.isArray(heData) ? heData : heData.results || [];
          heList.sort((a, b) => {
            const diaA = DIAS.indexOf(a.dia_semana);
            const diaB = DIAS.indexOf(b.dia_semana);
            if (diaA !== diaB) return diaA - diaB;
            return (a.hora_inicio || '').localeCompare(b.hora_inicio || '');
          });
          setHorarios(heList);
        } catch (err) {
          toast.error(`No se pudo eliminar: ${mensajeErrorAmigable(err)}`);
        }
      },
    });
  };

  const handleChange = (campo, valor) => {
    setForm((prev) => ({
      ...prev,
      [campo]: campo === 'aula' ? sanitizarTexto(valor) : valor,
    }));
  };

  return (
    <div>
      {mensaje && (
        <p
          className={`form-error-message ${mensaje.includes('Error') ? '' : 'form-error-message--ok'}`}
          role="status"
        >
          {mensaje}
        </p>
      )}

      {cursoSeleccionado && (
        <div>
          {cargando ? (
            <LoadingSpinner text="Cargando horarios..." size="sm" inline />
          ) : !cmEf ? (
            <p className="empty-state-message empty-state-centered">
              El curso no tiene Educación Física asignada.
            </p>
          ) : (
            <div>
              {!soloLectura && form && (
                <form onSubmit={handleSubmit} className="mb-20">
                  <div className="filter-row">
                    <div className="form-group-filter">
                      <label htmlFor="ef-dia">Día</label>
                      <select
                        id="ef-dia"
                        value={form.dia_semana}
                        onChange={(e) => handleChange('dia_semana', e.target.value)}
                      >
                        <option value="">— Día —</option>
                        {DIAS.map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group-filter">
                      <label htmlFor="ef-hora-inicio">Hora inicio</label>
                      <input
                        id="ef-hora-inicio"
                        type="time"
                        value={form.hora_inicio}
                        onChange={(e) => handleChange('hora_inicio', e.target.value)}
                      />
                    </div>
                    <div className="form-group-filter">
                      <label htmlFor="ef-hora-fin">Hora fin</label>
                      <input
                        id="ef-hora-fin"
                        type="time"
                        value={form.hora_fin}
                        onChange={(e) => handleChange('hora_fin', e.target.value)}
                      />
                    </div>
                    <div className="form-group-filter">
                      <label htmlFor="ef-aula">Aula (opcional)</label>
                      <input
                        id="ef-aula"
                        type="text"
                        value={form.aula}
                        onChange={(e) => handleChange('aula', e.target.value)}
                        placeholder="Ej: Gimnasio"
                      />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary" disabled={guardando}>
                      {form.id ? 'Actualizar horario' : 'Agregar horario'}
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={resetForm}>
                      Cancelar
                    </button>
                  </div>
                </form>
              )}

              {!soloLectura && !form && (
                <button
                  type="button"
                  className="btn btn-primary mb-16"
                  onClick={() => setForm({ ...FORM_VACIO })}
                >
                  Agregar horario
                </button>
              )}

              {horarios.length === 0 ? (
                <p className="empty-state-message empty-state-centered">
                  No hay horarios de Educación Física cargados.
                </p>
              ) : (
                <div className="table-responsive">
                  <table>
                    <thead>
                      <tr>
                        <th>Día</th>
                        <th>Hora inicio</th>
                        <th>Hora fin</th>
                        <th>Aula</th>
                        {!soloLectura && <th>Acciones</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {horarios.map((h) => (
                        <tr key={h.id_horario_especial}>
                          <td>{h.dia_semana}</td>
                          <td>{timeStr(h.hora_inicio)}</td>
                          <td>{timeStr(h.hora_fin)}</td>
                          <td>{h.aula || '—'}</td>
                          {!soloLectura && (
                            <AccionesCelda
                              acciones={[
                                { accion: 'editar', onClick: () => handleEditar(h) },
                                { accion: 'eliminar', onClick: () => handleEliminar(h) },
                              ]}
                              entidad="horario"
                            />
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Horarios({ cursoGlobal = '', curso = '', soloLectura = false, navContext }) {
  const { cursosObj, selectedCursoId } = useData();
  const [modo, setModo] = useState('semanal');
  const [guardando, setGuardando] = useState(false);
  const saveFnRef = useRef(null);

  useEffect(() => {
    if (navContext?.destino === 'horarios') setModo('ver');
  }, [navContext]);

  const registerSaveFn = useCallback((fn) => {
    saveFnRef.current = fn;
  }, []);

  const executeSave = useCallback(() => {
    if (saveFnRef.current) {
      setGuardando(true);
      Promise.resolve(saveFnRef.current()).finally(() => setGuardando(false));
    }
  }, []);

  // Al salir de la grilla semanal se descarta el handler registrado para que
  // el boton Guardar de la barra nunca dispare el guardado de otra pestana.
  useEffect(() => {
    if (modo !== 'semanal') saveFnRef.current = null;
  }, [modo]);

  const cursosOptions = useMemo(() => {
    if (!Array.isArray(cursosObj)) return [];
    return [...cursosObj].sort((a, b) => (a.nombre_curso || '').localeCompare(b.nombre_curso || ''));
  }, [cursosObj]);

  // El curso puede venir por prop (nombre, desde Preceptores) o desde el selector
  // global de Administracion (`selectedCursoId` en DataContext).
  const cursoNombreExterno = curso || cursoGlobal;

  const cursoIdExterno = useMemo(() => {
    if (cursoNombreExterno) {
      const c = (cursosObj || []).find(
        (x) => String(x.nombre_curso) === String(cursoNombreExterno),
      );
      return c ? String(c.id_curso) : '';
    }
    return selectedCursoId ? String(selectedCursoId) : '';
  }, [cursoNombreExterno, cursosObj, selectedCursoId]);

  const sinCurso = !cursoIdExterno;
  const puedeGuardar = modo === 'semanal' && !sinCurso;

  return (
    <div className="card">
      <div className="card-header-flex">
        <h3><i className="fas fa-calendar-alt" aria-hidden="true" /> Horarios</h3>
        {soloLectura && (
          <span className="badge badge-neutral">
            <i className="fas fa-eye" aria-hidden="true" /> Solo lectura
          </span>
        )}
      </div>

      <div className="horarios-toolbar mb-20">
        <div className="horarios-toolbar__views">
          <button
            type="button"
            className={`btn btn-sm ${modo === 'semanal' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setModo('semanal')}
          >
            Horario semanal
          </button>
          <button
            type="button"
            className={`btn btn-sm ${modo === 'ef' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setModo('ef')}
          >
            Educación Física
          </button>
          <button
            type="button"
            className={`btn btn-sm ${modo === 'ver' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setModo('ver')}
          >
            Ver horarios
          </button>
        </div>
        {!soloLectura && (
          <button
            type="button"
            className="btn btn-sm btn-primary horarios-toolbar__save"
            disabled={guardando || !puedeGuardar}
            onClick={executeSave}
          >
            <i className="fas fa-save" aria-hidden="true" />{' '}
            {guardando ? 'Guardando...' : 'Guardar'}
          </button>
        )}
      </div>

      {sinCurso && (
        <p className="empty-state-message empty-state-centered">
          Selecciona un curso en el filtro superior para ver sus horarios.
        </p>
      )}

      {modo === 'semanal' && !sinCurso && <HorarioSemanal cursoIdExterno={cursoIdExterno} onRegisterSave={registerSaveFn} soloLectura={soloLectura} />}
      {modo === 'ef' && !sinCurso && <EducacionFisica cursoIdExterno={cursoIdExterno} soloLectura={soloLectura} />}
      {modo === 'ver' && !sinCurso && (
        <VistaHorarios
          cursosOptions={cursosOptions}
          cursoForzado={cursoIdExterno}
          mostrarTitulo={false}
        />
      )}
    </div>
  );
}

export default Horarios;
