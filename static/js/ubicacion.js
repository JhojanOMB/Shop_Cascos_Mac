// Define los enlaces a las redes sociales con un mensaje predefinido
const socialLinks = {
    whatsapp: "https://wa.me/573212692311?text=Hola%20W%20Cascos"
};

// Asigna los enlaces a los iconos correspondientes por el id
document.getElementById("whatsapp").addEventListener("click", function() {
    window.open(socialLinks.whatsapp, "_blank");
});
