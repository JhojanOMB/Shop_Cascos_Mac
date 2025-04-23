// Script para formatear inputs númericos
document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll(".precio-input").forEach(input => {
        // Función para formatear el valor
        function formatInput() {
            let value = input.value.replace(/\D/g, ""); // Elimina todo lo que no sea número
            input.value = value ? `$ ${new Intl.NumberFormat("es-CO").format(value)}` : "";
        }

        // Aplicar formato cuando se carga la página
        formatInput();

        // Aplicar formato mientras se escribe
        input.addEventListener("input", formatInput);

        // Antes de enviar el formulario, limpiar el valor para que el backend reciba solo números
        input.closest("form").addEventListener("submit", function() {
            input.value = input.value.replace(/\D/g, ""); // Solo deja números
        });
    });
});
