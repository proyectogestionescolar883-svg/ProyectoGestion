import Login from './components/Login/login';
import PanelProfesores from './components/Profesores/PanelProfesores';
import PreceptorDashboard from './components/Preceptores/PreceptorDashboard';
import JefePreceptorDashboard from './components/JefePreceptores/JefePreceptorDashboard';
import FamiliaDashboard from './components/Familia/FamiliaDashboard';
import AdminDashboard from './components/Administracion/AdminDashboard';
import EstudianteDashboard from './components/Estudiante/EstudianteDashboard';
import LoadingScreen from './components/Shared/LoadingScreen';
import SeleccionRol from './components/Shared/SeleccionRol';
import { useAuth } from './context/AuthContext';
import { DataProvider, useData } from './context/DataContext';
import NotificacionToast from './components/Shared/NotificacionToast';

function RolDesconocido({ rolActivo, onLogout }) {
  return (
    <div className="card" style={{ maxWidth: 560, margin: '48px auto' }}>
      <div className="card-header-flex">
        <h3><i className="fas fa-triangle-exclamation" aria-hidden="true" /> Rol no reconocido</h3>
      </div>
      <p className="card-description">
        El rol activo no tiene un panel asignado. Cerra sesion y volve a ingresar.
      </p>
      {rolActivo && <p className="text-muted text-small">Rol recibido: {rolActivo}</p>}
      <div className="mt-16">
        <button type="button" className="btn btn-primary" onClick={onLogout}>
          Cerrar sesion
        </button>
      </div>
    </div>
  );
}

function Dashboard({ user, rolActivo, logout }) {
  switch (rolActivo) {
    case 'preceptor':
      return <PreceptorDashboard user={user} onLogout={logout} />;
    case 'jefe_preceptores':
      return <JefePreceptorDashboard user={user} onLogout={logout} />;
    case 'admin':
    case 'director':
      return <AdminDashboard user={user} onLogout={logout} />;
    case 'docente':
      return <PanelProfesores user={user} onLogout={logout} />;
    case 'familia':
      return <FamiliaDashboard user={user} onLogout={logout} />;
    case 'alumno':
      return <EstudianteDashboard user={user} onLogout={logout} />;
    default:
      return <RolDesconocido rolActivo={rolActivo} onLogout={logout} />;
  }
}

function DashboardConDatos({ user, rolActivo, logout }) {
  const { loading, refreshing } = useData();

  if (loading && !refreshing) {
    return <LoadingScreen fixed text="Cargando el sistema" />;
  }

  return (
    <>
      <Dashboard user={user} rolActivo={rolActivo} logout={logout} />
      <NotificacionToast userRole={user.role} />
    </>
  );
}

function App() {
  const { user, rolActivo, loading, logout } = useAuth();

  if (loading) {
    return <LoadingScreen fixed text="Iniciando sesión" />;
  }

  if (!user) {
    return <Login />;
  }

  if (!rolActivo) {
    return <SeleccionRol />;
  }

  return (
    <DataProvider>
      <DashboardConDatos user={user} rolActivo={rolActivo} logout={logout} />
    </DataProvider>
  );
}

export default App;
