// static/js/carrito.js
// Carrito JS completo para plantilla
// Requisitos en plantilla:
//  - <div id="add-url-base" data-url="{% url 'carrito:agregar_al_carrito' 0 %}" class="hidden"></div>
//  - forms con class="add-to-cart-form" que contengan:
//      select[name="producto_talla_id"] (cada option con data-stock)
//      input[name="cantidad"]
//      .error-msg y .success-msg elementos para feedback opcional
//  - botones tipo <button class="btn-add-ajax">Añadir</button>
//  - spans con ids: cart-count, mini-cart-count, cart-badge o total_items_carrito para mostrar el total

(function () {
  'use strict';

  /* -------------------- Helpers -------------------- */

  function getCSRF() {
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : null;
  }

  // postForm: versión robusta y debug-friendly
  async function postForm(url, data) {
    const csrftoken = getCSRF();
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken,
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
        body: new URLSearchParams(data)
      });

      const text = await res.text();
      console.log(`[postForm] ${url} -> status ${res.status} (len ${text.length})`);
      console.debug('[postForm] preview:', text.slice(0, 1000));

      try {
        const json = JSON.parse(text);
        return json;
      } catch (err) {
        console.warn('[postForm] JSON.parse failed:', err);
        // devolver objeto consistente para que el caller lo maneje
        return { success: false, raw: text, status: res.status, parse_error: String(err) };
      }
    } catch (networkErr) {
      console.error('[postForm] fetch error:', networkErr);
      return { success: false, network_error: String(networkErr) };
    }
  }

  function updateCartBadges(count) {
    if (typeof count === 'undefined' || count === null) return;
    const ids = ['cart-badge', 'cart-count', 'mini-cart-count', 'total_items_carrito'];
    ids.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = count;
    });
  }

  function replaceMiniCartHtml(html) {
    if (!html) return;
    const el = document.getElementById('mini-cart-content');
    if (!el) return;
    el.innerHTML = html;
  }

  // find closest ancestor matching selector
  function closestBySelector(el, sel) {
    while (el && el !== document) {
      if (el.matches && el.matches(sel)) return el;
      el = el.parentNode;
    }
    return null;
  }

  // cerrar modal Alpine-friendly: intenta disparar el @click o cambiar open=false
  function tryCloseModalFrom(element) {
    if (!element) return;
    // buscar botón con × o texto 'Cancelar' o 'Cerrar'
    const candidates = element.querySelectorAll('button');
    for (const b of candidates) {
      const txt = (b.textContent || '').trim().toLowerCase();
      if (txt === '×' || txt === 'x' || txt.includes('cancelar') || txt.includes('cerrar')) {
        try { b.click(); return; } catch(e) { /* ignore */ }
      }
    }
    // si es un modal manejado por Alpine con atributo x-data, establecer open=false via dispatch
    const root = closestBySelector(element, '[x-data]');
    if (root) {
      // dispatch event - your Alpine listener might react to it, otherwise this is a no-op
      root.dispatchEvent(new CustomEvent('close-modal', { bubbles: true }));
    }
  }

  /* -------------------- Main wiring -------------------- */

  document.addEventListener('DOMContentLoaded', function () {
    // obtener base URL (ej: "/carrito/agregar/0/")
    const baseEl = document.getElementById('add-url-base');
    const baseUrl = baseEl ? baseEl.dataset.url : '/carrito/agregar/0/';

    // behavior para select de variantes: mostrar stock y ajustar input cantidad si lo deseas
    document.querySelectorAll('.add-to-cart-form select[name="producto_talla_id"]').forEach(select => {
      select.addEventListener('change', function () {
        const form = closestBySelector(select, '.add-to-cart-form') || select.closest('form');
        if (!form) return;
        const selected = select.selectedOptions && select.selectedOptions[0];
        if (!selected) return;
        const stock = parseInt(selected.dataset.stock || 0, 10);
        const qtyInput = form.querySelector('input[name="cantidad"]');
        const info = form.querySelector('.variant-stock-info');
        if (info) info.textContent = `Stock disponible: ${stock}`;
        if (qtyInput) {
          qtyInput.max = Math.max(stock, 1);
          if (parseInt(qtyInput.value || 1, 10) > stock) qtyInput.value = stock;
        }
        const err = form.querySelector('.error-msg');
        if (err) err.classList.add('hidden');
      });
    });

    // manejador para botones .btn-add-ajax
    document.querySelectorAll('.btn-add-ajax').forEach(btn => {
      btn.addEventListener('click', async function (ev) {
        ev.preventDefault();
        const btnEl = btn;
        const form = closestBySelector(btnEl, '.add-to-cart-form') || btnEl.closest('form');
        if (!form) {
          console.error('No se encontró el formulario asociado al botón .btn-add-ajax');
          alert('Error interno: formulario no encontrado.');
          return;
        }

        // elementos del form
        const select = form.querySelector('select[name="producto_talla_id"]');
        const qtyInput = form.querySelector('input[name="cantidad"]');
        const errEl = form.querySelector('.error-msg');
        const successEl = form.querySelector('.success-msg');

        // limpiar mensajes previos
        if (errEl) { errEl.textContent = ''; errEl.classList.add('hidden'); }
        if (successEl) { successEl.textContent = ''; successEl.classList.add('hidden'); }

        if (!select) {
          const msg = 'Selecciona una variante antes de añadir.';
          if (errEl) { errEl.textContent = msg; errEl.classList.remove('hidden'); } else alert(msg);
          return;
        }

        const ptId = select.value;
        if (!ptId) {
          const msg = 'Selecciona una variante válida.';
          if (errEl) { errEl.textContent = msg; errEl.classList.remove('hidden'); } else alert(msg);
          return;
        }

        const selectedOption = select.selectedOptions && select.selectedOptions[0];
        const stock = selectedOption ? parseInt(selectedOption.dataset.stock || 0, 10) : null;

        let cantidad = 1;
        if (qtyInput) {
          cantidad = parseInt(qtyInput.value || 1, 10);
          if (!Number.isInteger(cantidad) || cantidad < 1) cantidad = 1;
        }

        if (stock !== null && cantidad > stock) {
          const msg = `Cantidad mayor al stock disponible (${stock}).`;
          if (errEl) { errEl.textContent = msg; errEl.classList.remove('hidden'); } else alert(msg);
          return;
        }

        // construir URL reemplazando el 0 por el ptId
        const url = baseUrl.replace(/0\/?$/, String(ptId) + '/');

        // feedback UI: desactivar botón mientras se hace la petición
        btnEl.disabled = true;
        const origHtml = btnEl.innerHTML;
        try {
          btnEl.innerHTML = 'Añadiendo...';
          const resp = await postForm(url, { cantidad });

          // Si hubo problema de network la función devuelve { success:false, network_error: ... }
          if (resp && resp.network_error) {
            console.error('Network error:', resp.network_error);
            alert('Error de red. Revisa la consola para más detalles.');
            return;
          }

          // Si el servidor devolvió texto no-JSON, resp.success será false y resp.raw contendrá el HTML
          if (!resp || resp.success === false) {
            const raw = resp && resp.raw ? resp.raw : null;
            console.warn('Respuesta no-OK del servidor:', resp);
            // mostrar mensaje útil al usuario (si viene)
            const msg = resp && resp.message ? resp.message : 'No se pudo añadir al carrito.';
            if (errEl) { errEl.textContent = msg; errEl.classList.remove('hidden'); }
            else alert(msg);
            // además, si vino raw (HTML/traceback) mostrar en consola para debugging
            if (raw) console.debug('Raw server response (preview):', String(raw).slice(0, 2000));
            return;
          }

          // Éxito: actualizar badges y mini cart si aplica
          if (typeof resp.cart_count !== 'undefined') updateCartBadges(resp.cart_count);
          if (resp.mini_cart_html) replaceMiniCartHtml(resp.mini_cart_html);

          if (successEl) {
            successEl.textContent = 'Añadido al carrito';
            successEl.classList.remove('hidden');
            setTimeout(() => successEl.classList.add('hidden'), 1800);
          } else {
            // log si no hay elemento success
            console.log('Añadido al carrito', resp);
          }

          // intentar cerrar modal
          tryCloseModalFrom(form);

          // pequeño efecto visual en el badge
          const badge = document.getElementById('cart-count') || document.getElementById('cart-badge');
          if (badge) {
            badge.classList.add('animate-pulse');
            setTimeout(() => badge.classList.remove('animate-pulse'), 700);
          }
        } catch (err) {
          // Esto sólo ocurrirá si hay un error JS en el handler
          console.error('Error en el handler de añadir al carrito:', err);
          alert('Ocurrió un error en el cliente. Revisa la consola (F12).');
        } finally {
          btnEl.disabled = false;
          btnEl.innerHTML = origHtml;
        }
      });
    });

    /* Abrir mini cart drawer si existiera un botón con id 'open-mini-cart' */
    const openMiniBtn = document.getElementById('open-mini-cart');
    if (openMiniBtn) {
      openMiniBtn.addEventListener('click', async function (e) {
        e.preventDefault();
        const drawer = document.getElementById('mini-cart-drawer');
        const content = document.getElementById('mini-cart-content');
        // si está vacío, intenta cargar partial desde endpoint opcional /carrito/partial/
        if (content && !content.innerHTML.trim()) {
          try {
            const r = await fetch('/carrito/partial/');
            if (r.ok) content.innerHTML = await r.text();
          } catch (err) {
            console.warn('No se pudo cargar partial del mini-cart:', err);
          }
        }
        if (drawer) drawer.classList.remove('hidden');
      });
    }

    // cerrar mini cart
    document.getElementById('mini-cart-close')?.addEventListener('click', () => {
      document.getElementById('mini-cart-drawer')?.classList.add('hidden');
    });

    // opcional: detectar evento custom close-modal disparado arriba
    document.addEventListener('close-modal', function (ev) {
      const drawer = document.getElementById('mini-cart-drawer');
      if (drawer) drawer.classList.add('hidden');
    });
  });

})();
