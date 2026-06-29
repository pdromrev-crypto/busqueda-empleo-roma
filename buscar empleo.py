"""
Buscador diario de empleo en Roma - adaptado al perfil de Pedro Martínez Reverte
(Project Assistant/Manager, Event Coordinator, Non-profit, Erasmus/EU projects)

Fuente: API de Adzuna (gratuita) - https://developer.adzuna.com/
Envío: email vía SMTP (Gmail)

Variables de entorno necesarias (se configuran como GitHub Secrets):
    ADZUNA_APP_ID
    ADZUNA_APP_KEY
    EMAIL_FROM
    EMAIL_PASSWORD
    EMAIL_TO
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ----------------------------
# CONFIGURACIÓN
# ----------------------------

ADZUNA_APP_ID = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY = os.environ["ADZUNA_APP_KEY"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_TO = os.environ["EMAIL_TO"]

PAIS = "it"  # Italia
CIUDAD = "Roma"

# Búsquedas que se hacen (puedes añadir/quitar términos)
QUERIES = [
    "project assistant",
    "project manager",
    "project coordinator",
    "event coordinator",
    "event manager",
    "non profit",
    "ONG",
    "EU projects",
    "Erasmus",
]

# Palabras clave de tu CV para puntuar relevancia (más peso = más relevante)
KEYWORDS_PESO = {
    "project": 3,
    "progett": 3,  # italiano: progetto/progettazione
    "event": 3,
    "evento": 3,
    "erasmus": 4,
    "non profit": 4,
    "nonprofit": 4,
    "ong": 3,
    "ngo": 3,
    "eu": 2,
    "ue": 2,
    "coordinat": 3,
    "coordinaz": 3,
    "amministrat": 1,
    "social media": 1,
    "comunicazione": 1,
    "volontari": 2,
    "tirocini": 2,
}

MODALIDADES_ACEPTADAS = ["presencial", "hibrido", "remoto"]  # informativo, Adzuna no siempre lo distingue


# ----------------------------
# BÚSQUEDA EN ADZUNA
# ----------------------------

def buscar_ofertas(query):
    url = f"https://api.adzuna.com/v1/api/jobs/{PAIS}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "where": CIUDAD,
        "distance": 20,
        "results_per_page": 20,
        "content-type": "application/json",
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("results", [])


def puntuar_oferta(oferta):
    texto = (oferta.get("title", "") + " " + oferta.get("description", "")).lower()
    puntuacion = 0
    for palabra, peso in KEYWORDS_PESO.items():
        if palabra in texto:
            puntuacion += peso
    return puntuacion


def recopilar_ofertas():
    vistas = {}
    for q in QUERIES:
        try:
            resultados = buscar_ofertas(q)
        except Exception as e:
            print(f"Error buscando '{q}': {e}")
            continue
        for oferta in resultados:
            id_oferta = oferta.get("id") or oferta.get("redirect_url")
            if id_oferta in vistas:
                continue  # evitar duplicados
            puntuacion = puntuar_oferta(oferta)
            if puntuacion > 0:  # solo nos interesan las que tengan algo de match
                vistas[id_oferta] = {
                    "titulo": oferta.get("title", "Sin título"),
                    "empresa": oferta.get("company", {}).get("display_name", "Empresa no especificada"),
                    "ubicacion": oferta.get("location", {}).get("display_name", CIUDAD),
                    "url": oferta.get("redirect_url", ""),
                    "puntuacion": puntuacion,
                }
    # ordenar de más a menos relevante
    return sorted(vistas.values(), key=lambda x: x["puntuacion"], reverse=True)


# ----------------------------
# ENVÍO DE EMAIL
# ----------------------------

def construir_email(ofertas):
    if not ofertas:
        cuerpo = "<p>Hoy no se han encontrado ofertas nuevas relevantes en Roma.</p>"
    else:
        filas = ""
        for o in ofertas[:25]:  # máximo 25 para no saturar el email
            filas += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><b>{o['titulo']}</b><br>
                    <span style="color:#555;">{o['empresa']} — {o['ubicacion']}</span><br>
                    <a href="{o['url']}">Ver oferta</a>
                </td>
                <td style="padding:8px; border-bottom:1px solid #ddd; text-align:center;">{o['puntuacion']}</td>
            </tr>
            """
        cuerpo = f"""
        <p>Se han encontrado <b>{len(ofertas)}</b> ofertas relevantes hoy en Roma.</p>
        <table style="width:100%; border-collapse:collapse; font-family:Arial, sans-serif;">
            <tr style="background:#f0f0f0;">
                <th style="padding:8px; text-align:left;">Oferta</th>
                <th style="padding:8px;">Relevancia</th>
            </tr>
            {filas}
        </table>
        """
    return cuerpo


def enviar_email(cuerpo_html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Ofertas de empleo en Roma - resumen diario"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(cuerpo_html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())


# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":
    ofertas = recopilar_ofertas()
    print(f"Ofertas encontradas: {len(ofertas)}")
    cuerpo_html = construir_email(ofertas)
    enviar_email(cuerpo_html)
    print("Email enviado correctamente.")
