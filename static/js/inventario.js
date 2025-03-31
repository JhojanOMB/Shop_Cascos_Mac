// Función de búsqueda en tiempo real
document.getElementById('searchInput').addEventListener('keyup', function (event) {
    // Permitir búsqueda al presionar Enter (Código de tecla "Enter" es 13)
    if (event.key === 'Enter' || event.keyCode === 13) {
        realizarBusqueda();
    } else {
        realizarBusqueda(); // Busca también mientras escribe
    }
});

function realizarBusqueda() {
    var searchValue = document.getElementById('searchInput').value.toLowerCase(); // Convertir a minúsculas
    var tableRows = document.querySelectorAll('#productoTable tr');

    tableRows.forEach(function (row) {
        var productName = row.querySelector('td:first-child').textContent.toLowerCase();
        var productReference = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
        var productCode = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        
        // Filtrar por nombre, referencia o código de barras
        if (productName.includes(searchValue) || productReference.includes(searchValue) || productCode.includes(searchValue)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}
