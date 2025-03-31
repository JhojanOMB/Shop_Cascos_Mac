document.addEventListener("DOMContentLoaded", function() {
    // Formatear los inputs de precio mientras se escribe
    document.querySelectorAll(".precio-input").forEach(function(input) {
        function formatInput() {
            // Eliminar todo lo que no sea dígito
            let value = input.value.replace(/\D/g, "");
            if (value) {
                input.value = `$ ${new Intl.NumberFormat("es-CO").format(value)}`;
            } else {
                input.value = "";
            }
        }
        // Aplica el formato al cargar la página
        formatInput();
        // Aplica el formato en cada input
        input.addEventListener("input", formatInput);
    });

    // Capturar el submit del formulario para darle un retardo antes de enviarlo
    var form = document.getElementById('productoForm');
    if(form) {
        form.addEventListener('submit', function(event) {
            // Prevenir el envío inmediato del formulario
            event.preventDefault();
            // Esperar 200 milisegundos para que se aplique el formato final
            setTimeout(function() {
                // Limpiar los inputs, dejando solo números
                form.querySelectorAll(".precio-input").forEach(function(input) {
                    input.value = input.value.replace(/[^0-9]/g, "");
                });
                // Enviar el formulario manualmente
                form.submit();
            }, 200);
        });
    }
});
