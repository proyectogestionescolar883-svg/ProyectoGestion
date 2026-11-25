import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  login as apiLogin,
  logout as apiLogout,
  getMe,
  seleccionarRol as apiSeleccionarRol,
  setRolActivoHeader,
} from '../services/api';

const AuthContext = createContext(null);

const ROL_STORAGE_PREFIX = 'rol_activo_';

function limpiarRolGuardado(username) {
  if (username) {
    sessionStorage.removeItem(ROL_STORAGE_PREFIX + username);
    return;
  }
  Object.keys(sessionStorage)
    .filter((clave) => clave.startsWith(ROL_STORAGE_PREFIX))
    .forEach((clave) => sessionStorage.removeItem(clave));
}

function usernameDesdeToken(token) {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const datos = JSON.parse(atob(payload));
    return datos.usuario || datos.username || null;
  } catch {
    return null;
  }
}

function buildUser(data, rolActivo) {
  const roles = Array.isArray(data.roles) ? data.roles : [];
  const perfil = data.perfil || {};
  return {
    id: data.id_usuario,
    id_usuario: data.id_usuario,
    username: data.usuario,
    roles,
    role: rolActivo || '',
    nombreCompleto: perfil.nombre_completo || null,
    nombre: perfil.nombre || null,
    apellido: perfil.apellido || null,
  };
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [rolActivo, setRolActivo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [intento, setIntento] = useState(0);
  const reintentar = useCallback(() => setIntento((n) => n + 1), []);

  // Con un único rol se entra directo. Con varios se conserva el rol ya
  // elegido en esta sesión (si pertenece a los roles reales del usuario);
  // en cualquier otro caso el usuario debe elegir en el selector.
  const resolverRolInicial = useCallback((roles, username) => {
    if (roles.length === 1) return roles[0];
    if (roles.length > 1) {
      const guardado = sessionStorage.getItem(ROL_STORAGE_PREFIX + username);
      if (guardado && roles.includes(guardado)) return guardado;
    }
    return null;
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    setError(null);
    getMe()
      .then((data) => {
        const roles = Array.isArray(data.roles) ? data.roles : [];
        const inicial = resolverRolInicial(roles, data.usuario);
        setUser(buildUser(data, inicial));
        setRolActivo(inicial);
        setRolActivoHeader(inicial);
      })
      .catch((err) => {
        if (err?.response?.status === 401) {
          limpiarRolGuardado(usernameDesdeToken(token));
          apiLogout();
          setRolActivoHeader(null);
          setUser(null);
          setRolActivo(null);
          setError(null);
          return;
        }
        setError('No se pudo verificar la sesión. Revise su conexión e intente nuevamente.');
      })
      .finally(() => setLoading(false));
  }, [resolverRolInicial, intento]);

  const login = useCallback(
    async (usuario, contrasena) => {
      try {
        const data = await apiLogin(usuario, contrasena);
        const roles = Array.isArray(data.roles) ? data.roles : [];
        const inicial = resolverRolInicial(roles, data.usuario);
        setUser(buildUser(data, inicial));
        setRolActivo(inicial);
        setRolActivoHeader(inicial);
        setError(null);
        return data;
      } catch (err) {
        limpiarRolGuardado(usuario);
        setError(null);
        throw err;
      }
    },
    [resolverRolInicial],
  );

  const seleccionarRol = useCallback(
    async (rol) => {
      if (!user || !Array.isArray(user.roles) || !user.roles.includes(rol)) {
        throw new Error('El rol seleccionado no está asignado a tu usuario.');
      }
      // Validación en backend: rechaza roles que el usuario no posee.
      const data = await apiSeleccionarRol(rol);
      const roles = Array.isArray(data.roles) ? data.roles : [];
      setUser((prev) => ({ ...prev, roles, role: rol }));
      setRolActivo(rol);
      setRolActivoHeader(rol);
      sessionStorage.setItem(ROL_STORAGE_PREFIX + user.username, rol);
      return data;
    },
    [user],
  );

  const cambiarRol = useCallback(() => {
    if (user) {
      sessionStorage.removeItem(ROL_STORAGE_PREFIX + user.username);
    }
    setRolActivo(null);
    setRolActivoHeader(null);
    setUser((prev) => (prev ? { ...prev, role: '' } : prev));
  }, [user]);

  const logout = useCallback(() => {
    if (user) {
      sessionStorage.removeItem(ROL_STORAGE_PREFIX + user.username);
    }
    apiLogout();
    setRolActivoHeader(null);
    setUser(null);
    setRolActivo(null);
  }, [user]);

  return (
    <AuthContext.Provider
      value={{
        user,
        rolActivo,
        loading,
        login,
        seleccionarRol,
      cambiarRol,
      logout,
      error,
      reintentar,
    }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function useAuthOpcional() {
  return useContext(AuthContext);
}
