    let productosSeleccionados = new Set();

    function actualizarSeleccion() {
        document.querySelectorAll('.select-checkbox').forEach(checkbox => {
            const id = checkbox.value;
            checkbox.checked = productosSeleccionados.has(id);
        });
    }

    // Al cargar la página, o después de paginar
    document.addEventListener('DOMContentLoaded', function () {
        document.addEventListener('change', function (e) {
            if (e.target.classList.contains('select-checkbox')) {
                const id = e.target.value;
                if (e.target.checked) {
                    productosSeleccionados.add(id);
                } else {
                    productosSeleccionados.delete(id);
                }
            }

            if (e.target.id === 'select-all') {
                const checked = e.target.checked;
                document.querySelectorAll('.select-checkbox').forEach(cb => {
                    cb.checked = checked;
                    const id = cb.value;
                    if (checked) {
                        productosSeleccionados.add(id);
                    } else {
                        productosSeleccionados.delete(id);
                    }
                });
            }
        });

        document.getElementById('btn-imprimir').addEventListener('click', function () {
            const ids = Array.from(productosSeleccionados);
            if (ids.length === 0) {
                alert("Selecciona al menos un producto para imprimir.");
                return;
            }
            const url = `/imprimir-codigos/?productos=${ids.join(',')}`;
            window.open(url, '_blank');
        });
    });

