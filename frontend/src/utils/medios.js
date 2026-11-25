const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const ORIGEN = API_BASE.replace(/\/api\/?$/, '');
const PREFIJO_API_MEDIA = '/api/media/';
const PREFIJO_MEDIA = '/media/';

function dividirUrl(ruta) {
  const valor = ruta.trim();
  const absoluta = /^[a-z][a-z\d+.-]*:\/\//i.test(valor);
  if (!absoluta && (valor.startsWith('blob:') || valor.startsWith('data:'))) {
    return null;
  }
  const destino = absoluta
    ? valor
    : `${ORIGEN}${valor.startsWith('/') ? '' : '/'}${valor}`;
  const url = new URL(destino);
  let pathname = url.pathname;
  const indiceApiMedia = pathname.indexOf(PREFIJO_API_MEDIA);
  if (indiceApiMedia >= 0) {
    pathname = pathname.slice(indiceApiMedia + PREFIJO_API_MEDIA.length);
  } else if (pathname.startsWith(PREFIJO_MEDIA)) {
    pathname = pathname.slice(PREFIJO_MEDIA.length);
  } else {
    pathname = pathname.replace(/^\/+/, '');
  }
  return { ruta: pathname, firma: url.search + url.hash };
}

export function buildMediaUrl(ruta) {
  if (!ruta || typeof ruta !== 'string') return '';
  const valor = ruta.trim();
  if (!valor) return '';
  if (/^(blob:|data:)/i.test(valor)) return valor;
  if (/^https?:\/\//i.test(valor) && new URL(valor).origin !== ORIGEN) return valor;
  const partes = dividirUrl(valor);
  if (!partes || !partes.ruta) return '';
  return `${ORIGEN}${PREFIJO_API_MEDIA}${partes.ruta}${partes.firma}`;
}

export default buildMediaUrl;
