document.addEventListener('DOMContentLoaded', () => {
  // Función que carga una URL y mete la respuesta en #main-content
  async function loadPage(url, addToHistory = true) {
    // Opcional: muestra un spinner
    const resp = await fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (!resp.ok) {
      // En caso de error, redirige normalmente
      window.location = url; 
      return;
    }
    const html = await resp.text();
    document.getElementById('main-content').innerHTML = html;
    if (addToHistory) history.pushState(null, '', url);
  }

  // Interceptar clicks en enlaces con clase .ajax-link
  document.body.addEventListener('click', e => {
    const a = e.target.closest('a.ajax-link');
    if (!a) return;
    e.preventDefault();
    loadPage(a.href);
  });

  // Manejar botón “Atrás” y “Adelante”
  window.addEventListener('popstate', () => {
    loadPage(location.href, false);
  });
});