"""
Mapeo nombre_completo (mayúsculas oficiales del catálogo) -> nombre corto que usamos
para hablar con Staff/Don Titi/Nancy.
Regla: [[nombres-no-apellidos]] — primer nombre; desambiguar con apellido/segundo nombre solo si hace falta.
"""

NOMBRE_CORTO = {
    "MARTINEZ DOMINGUEZ JENNIFER AYLIN": "Jennifer",
    "LEYLANI MARTINEZ ARMENTA": "Leylani",
    "NORIEGA ROSALES GEHU ALEJANDRO": "Gehu",
    "ROJAS COBIAN JUAN DE DIOS": "Juan de Dios",
    "FRANCISCO JAVIER": "Francisco Javier",
    "VELAZQUEZ PEREZ OSCAR": "Óscar",
    "GONZALEZ MONTOYA BRYAN": "Bryan",
    "FLORES GALVAN JOSE ANTONIO": "José Antonio",
    "NORIEGA ROSALES LUCINA ALEJANDRA": "Lucina",
    "HERNANDEZ ROSALES CARLOS FRANCISCO": "Carlos",
    "MAGAÑA LOPEZ ROSA MARIA": "Rosa María",
    "MEJIA AYALA HERBERTH ANTONIO": "Herberth",
    "MEJIA ORTEGA FELIX ERNESTO": "Félix",
    "QUINTERO MARTINEZ ADRIAN ANTONIO": "Adrián",
    "ACOSTA ANGULO GUILLERMO GEOVANNY": "Guillermo",
    "CONTRERAS ALEJANDRO GUILLERMO ANTONIO": "Guillermo Antonio",
    "JIMENEZ SERRANO AMERICA ELIZABETH": "América",
    "DE LA O CASTELAN ENRIQUE": "Enrique",
    "SANTILLAN TAFOYA ALI EDSEL": "Ali",
    "ZELAYA RAMOS ANGEL GEOVANNI": "Angel",
    "BAUTISTA GOMEZ ANDRONICA": "Andrónica",
    "DOMINGUEZ LOPEZ YAZMIN": "Yazmín",
    "RIOS OROZCO SANDRA": "Sandra",
    "ROCHA RODRIGUEZ SUSANO ANDRES": "Susano",
    "AGUIRRE MEJIA DAVID": "David",
    "SERRANO CEDANO NANCY LIZETH": "Nancy Lizeth",
}


def nombre_corto_para(nombre_completo: str) -> str:
    """Devuelve nombre corto; si no está mapeado, usa último token."""
    if nombre_completo in NOMBRE_CORTO:
        return NOMBRE_CORTO[nombre_completo]
    return nombre_completo.split()[-1].capitalize()
