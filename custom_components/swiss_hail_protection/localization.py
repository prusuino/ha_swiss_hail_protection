"""Runtime string localization (entity names, device info).

Home Assistant's translation files only cover config-flow text and entity
state values. The names this integration assigns in Python are looked up
here, keyed by hass.config.language, with English as the fallback.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

SUPPORTED_LANGUAGES = ("de", "en", "fr", "it")

STRINGS: dict[str, dict[str, str]] = {
    "vkf_device_name": {
        "de": "Hagelschutz VKF {device_id}",
        "en": "Hail Protection VKF {device_id}",
        "fr": "Protection grêle VKF {device_id}",
        "it": "Protezione grandine VKF {device_id}",
    },
    "vkf_manufacturer": {
        "de": "Vereinigung Kantonaler Feuerversicherungen (VKF)",
        "en": "Association of Cantonal Fire Insurers (VKF)",
        "fr": "Association des établissements cantonaux d'assurance incendie (AEAI)",
        "it": "Associazione degli istituti cantonali di assicurazione antincendio (AICAA)",
    },
    "vkf_model": {
        "de": "Hagelschutz – einfach automatisch (REST-Schnittstelle)",
        "en": "Hagelschutz – einfach automatisch (REST interface)",
        "fr": "Protection contre la grêle – tout simplement automatique (interface REST)",
        "it": "Protezione antigrandine – semplicemente automatica (interfaccia REST)",
    },
    "meteoswiss_device_name": {
        "de": "Hagelradar MeteoSchweiz (Umkreis {radius} km)",
        "en": "Hail Radar MeteoSwiss (Radius {radius} km)",
        "fr": "Radar grêle MétéoSuisse (Rayon {radius} km)",
        "it": "Radar grandine MeteoSvizzera (Raggio {radius} km)",
    },
    "meteoswiss_manufacturer": {
        "de": "Bundesamt für Meteorologie und Klimatologie MeteoSchweiz",
        "en": "Federal Office of Meteorology and Climatology MeteoSwiss",
        "fr": "Office fédéral de météorologie et de climatologie MétéoSuisse",
        "it": "Ufficio federale di meteorologia e climatologia MeteoSvizzera",
    },
    "meteoswiss_model": {
        "de": "Hagel-Radarprodukte POH / MESHS (Open Data)",
        "en": "Hail radar products POH / MESHS (Open Data)",
        "fr": "Produits radar grêle POH / MESHS (Open Data)",
        "it": "Prodotti radar grandine POH / MESHS (Open Data)",
    },
    "status_sensor_name": {
        "de": "Hagelwarnung Status",
        "en": "Hail Warning Status",
        "fr": "Alerte grêle – état",
        "it": "Allarme grandine – stato",
    },
    "alarm_sensor_name": {
        "de": "Hagelalarm",
        "en": "Hail Alarm",
        "fr": "Alarme grêle",
        "it": "Allarme grandine",
    },
    "probability_sensor_name": {
        "de": "Hagelwahrscheinlichkeit",
        "en": "Hail Probability",
        "fr": "Probabilité de grêle",
        "it": "Probabilità di grandine",
    },
    "size_sensor_name": {
        "de": "Hagelkorngrösse",
        "en": "Hail Size",
        "fr": "Taille des grêlons",
        "it": "Dimensione dei chicchi",
    },
    "radar_time_sensor_name": {
        "de": "Radarzeitpunkt",
        "en": "Radar Time",
        "fr": "Heure du radar",
        "it": "Ora del radar",
    },
}


def _language(hass: HomeAssistant) -> str:
    lang = (hass.config.language or "en").split("-")[0].lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def t(key: str, hass: HomeAssistant, **kwargs) -> str:
    """Translate key into the Home Assistant language; English if missing."""
    entry = STRINGS.get(key, {})
    text = entry.get(_language(hass)) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text
