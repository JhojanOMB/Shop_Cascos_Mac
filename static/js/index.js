// Define los enlaces a las redes sociales con un mensaje predefinido
const socialLinks = {
    whatsapp: "https://wa.me/573212692311?text=Hola%20W%20Cascos"
};

// Asigna los enlaces a los iconos correspondientes por el id
document.getElementById("whatsapp").addEventListener("click", function () {
    window.open(socialLinks.whatsapp, "_blank");
});

function showModal(id) {
    document.getElementById(id).classList.remove('hidden');
}
function hideModal(id) {
    document.getElementById(id).classList.add('hidden');
}

// Lógica de variantes y cantidades (tu script existente)
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.variante-select').forEach(select => {
        select.addEventListener('change', () => {
            const productoId = select.dataset.producto;
            const stock = parseInt(select.selectedOptions[0].dataset.stock, 10);
            const info = document.getElementById(`info-variante-${productoId}`);
            const cantidadInput = document.getElementById(`cantidad-${productoId}`);
            info.textContent = `Stock disponible: ${stock}`;
            cantidadInput.max = stock;
            document.getElementById(`error-cantidad-${productoId}`)
                .classList.add('hidden');
        });
    });
    document.querySelectorAll('.btn-agregar').forEach(btn => {
        btn.addEventListener('click', () => {
            /* tu fetch para agregar al carrito, idéntico al que ya tenías */
        });
    });
});

function updatePriceValues() {
    const min = document.getElementById("price-range-min").value;
    const max = document.getElementById("price-range-max").value;

    document.getElementById("price-min-label").textContent = `$${parseInt(min).toLocaleString()}`;
    document.getElementById("price-max-label").textContent = `$${parseInt(max).toLocaleString()}`;
}