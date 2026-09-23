# Lista amplia de destinos turísticos (nacionales e internacionales) para
# el autocompletado del campo "Destino". No requiere ninguna API externa:
# es una lista curada que además se combina en vivo con los destinos que
# ya hayan escrito los asesores (ver `_sugerencias` en app.py), así que
# crece con el uso real de la agencia.

DESTINOS_POPULARES = [
    # --- Colombia ---
    "Bogotá, Colombia", "Medellín, Colombia", "Cali, Colombia",
    "Barranquilla, Colombia", "Cartagena, Colombia", "Santa Marta, Colombia",
    "Bucaramanga, Colombia", "Pereira, Colombia", "Manizales, Colombia",
    "Armenia, Colombia", "Ibagué, Colombia", "Villavicencio, Colombia",
    "Cúcuta, Colombia", "Neiva, Colombia", "Pasto, Colombia",
    "Popayán, Colombia", "Montería, Colombia", "Sincelejo, Colombia",
    "Valledupar, Colombia", "Riohacha, Colombia", "Tunja, Colombia",
    "Yopal, Colombia", "Florencia, Colombia", "Quibdó, Colombia",
    "Mocoa, Colombia", "San Andrés, Colombia", "Providencia, Colombia",
    "Leticia, Colombia", "Arauca, Colombia", "Puerto Carreño, Colombia",
    "Mitú, Colombia", "Inírida, Colombia", "Salento, Colombia",
    "Guatapé, Colombia", "Girardot, Colombia", "Villa de Leyva, Colombia",
    "San Gil, Colombia", "Nuquí, Colombia", "Capurganá, Colombia",

    # --- México y Centroamérica ---
    "Ciudad de México, México", "Cancún, México", "Playa del Carmen, México",
    "Puerto Vallarta, México", "Los Cabos, México", "Guadalajara, México",
    "Tulum, México", "Cozumel, México", "Mérida, México", "Acapulco, México",
    "Ciudad de Panamá, Panamá", "San José, Costa Rica",
    "Guanacaste, Costa Rica", "Tamarindo, Costa Rica",
    "Antigua Guatemala, Guatemala", "Ciudad de Guatemala, Guatemala",
    "Managua, Nicaragua", "Granada, Nicaragua", "Roatán, Honduras",
    "Tegucigalpa, Honduras", "San Salvador, El Salvador",
    "Belize City, Belice",

    # --- Suramérica ---
    "Quito, Ecuador", "Guayaquil, Ecuador", "Islas Galápagos, Ecuador",
    "Lima, Perú", "Cusco, Perú", "Machu Picchu, Perú", "Arequipa, Perú",
    "La Paz, Bolivia", "Santa Cruz de la Sierra, Bolivia",
    "Salar de Uyuni, Bolivia", "Santiago de Chile, Chile",
    "Valparaíso, Chile", "San Pedro de Atacama, Chile",
    "Patagonia, Chile", "Buenos Aires, Argentina", "Bariloche, Argentina",
    "Mendoza, Argentina", "Cataratas del Iguazú, Argentina",
    "Asunción, Paraguay", "Montevideo, Uruguay", "Punta del Este, Uruguay",
    "Caracas, Venezuela", "Isla Margarita, Venezuela",
    "Río de Janeiro, Brasil", "São Paulo, Brasil", "Florianópolis, Brasil",
    "Salvador de Bahía, Brasil", "Fortaleza, Brasil", "Búzios, Brasil",

    # --- Caribe ---
    "Punta Cana, República Dominicana", "Santo Domingo, República Dominicana",
    "Puerto Plata, República Dominicana", "La Habana, Cuba",
    "Varadero, Cuba", "Aruba", "Curazao", "Bonaire",
    "Montego Bay, Jamaica", "Kingston, Jamaica", "Nassau, Bahamas",
    "San Juan, Puerto Rico", "Islas Caimán", "San Martín",
    "Barbados", "Trinidad y Tobago",

    # --- Estados Unidos y Canadá ---
    "Miami, Estados Unidos", "Orlando, Estados Unidos",
    "Nueva York, Estados Unidos", "Los Ángeles, Estados Unidos",
    "Las Vegas, Estados Unidos", "San Francisco, Estados Unidos",
    "Chicago, Estados Unidos", "Washington D.C., Estados Unidos",
    "Houston, Estados Unidos", "Boston, Estados Unidos",
    "Seattle, Estados Unidos", "Filadelfia, Estados Unidos",
    "Atlanta, Estados Unidos", "Nueva Orleans, Estados Unidos",
    "San Diego, Estados Unidos", "Honolulu, Hawái",
    "Toronto, Canadá", "Vancouver, Canadá", "Montreal, Canadá",
    "Niágara Falls, Canadá",

    # --- Europa ---
    "Madrid, España", "Barcelona, España", "Sevilla, España",
    "Valencia, España", "Málaga, España", "Ibiza, España",
    "Tenerife, España", "Gran Canaria, España", "París, Francia",
    "Niza, Francia", "Roma, Italia", "Milán, Italia", "Venecia, Italia",
    "Florencia, Italia", "Londres, Reino Unido", "Lisboa, Portugal",
    "Oporto, Portugal", "Ámsterdam, Países Bajos", "Berlín, Alemania",
    "Múnich, Alemania", "Zúrich, Suiza", "Ginebra, Suiza", "Viena, Austria",
    "Praga, República Checa", "Bruselas, Bélgica", "Atenas, Grecia",
    "Santorini, Grecia", "Mykonos, Grecia", "Estambul, Turquía",
    "Moscú, Rusia", "Dublín, Irlanda", "Copenhague, Dinamarca",
    "Estocolmo, Suecia", "Oslo, Noruega", "Budapest, Hungría",
    "Varsovia, Polonia",

    # --- Asia, Medio Oriente y Oceanía ---
    "Dubái, Emiratos Árabes Unidos", "Abu Dabi, Emiratos Árabes Unidos",
    "Doha, Catar", "Tokio, Japón", "Osaka, Japón", "Kioto, Japón",
    "Seúl, Corea del Sur", "Bangkok, Tailandia", "Phuket, Tailandia",
    "Bali, Indonesia", "Yakarta, Indonesia", "Singapur",
    "Hong Kong", "Shanghái, China", "Beijing, China",
    "Nueva Delhi, India", "Male, Maldivas", "Sídney, Australia",
    "Melbourne, Australia", "Auckland, Nueva Zelanda",

    # --- África ---
    "El Cairo, Egipto", "Marrakech, Marruecos", "Casablanca, Marruecos",
    "Ciudad del Cabo, Sudáfrica", "Zanzíbar, Tanzania", "Isla Mauricio",
]
