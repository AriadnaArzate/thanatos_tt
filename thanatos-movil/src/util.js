// SQLite guarda las fechas sin zona horaria, pero el backend las crea en UTC:
// si no traen zona se les agrega "Z" para que se muestren en la hora local.
export function aFecha(valor) {
  if (!valor) return null;
  const texto = /[zZ]|[+-]\d\d:?\d\d$/.test(valor) ? valor : `${valor}Z`;
  const d = new Date(texto);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fechaCorta(valor) {
  const d = aFecha(valor);
  if (!d) return '—';
  return d.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
    + ' ' + d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
}

export const EMOCIONES = {
  tristeza: { etiqueta: 'Tristeza', emoji: '😢' },
  ira_frustracion: { etiqueta: 'Ira/Frustración', emoji: '😠' },
  frustracion: { etiqueta: 'Frustración', emoji: '😕' },
  calma: { etiqueta: 'Calma', emoji: '😌' },
  ansiedad_miedo: { etiqueta: 'Ansiedad/Miedo', emoji: '😟' },
  soledad_vacio: { etiqueta: 'Soledad/Vacío', emoji: '🫥' },
};

export const nombreEmocion = (id) => EMOCIONES[id]?.etiqueta ?? (id || '').replace(/_/g, ' ');