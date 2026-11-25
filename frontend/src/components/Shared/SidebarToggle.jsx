import { useEffect, useState } from 'react';

const ID_SIDEBAR = 'sidebar-nav-toggle';

function SidebarToggle() {
  const [open, setOpen] = useState(false);
  const [sidebarId, setSidebarId] = useState(null);

  useEffect(() => {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return undefined;
    if (!sidebar.id) sidebar.setAttribute('id', ID_SIDEBAR);
    setSidebarId(sidebar.id);
    return () => {
      if (sidebar.id === ID_SIDEBAR) sidebar.removeAttribute('id');
    };
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const cerrarConEscape = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', cerrarConEscape);
    return () => document.removeEventListener('keydown', cerrarConEscape);
  }, [open]);

  useEffect(() => {
    document.body.classList.toggle('sidebar-open', open);
    return () => document.body.classList.remove('sidebar-open');
  }, [open]);

  useEffect(() => {
    const handleClick = (event) => {
      const target = event.target;
      if (target.closest('.hamburger')) return;
      if (target.closest('.sidebar')) {
        const control = target.closest('button, a');
        if (control && !control.classList.contains('sidebar-section-header')) {
          setOpen(false);
        }
        return;
      }
      setOpen(false);
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  return (
    <button
      type="button"
      className="hamburger"
      aria-label={open ? 'Cerrar menú de navegación' : 'Abrir menú de navegación'}
      aria-expanded={open}
      aria-controls={sidebarId || undefined}
      onClick={() => setOpen((value) => !value)}
    >
      <span />
      <span />
      <span />
    </button>
  );
}

export default SidebarToggle;
