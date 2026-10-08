"""Runtime string localization (entity names, device info).

Home Assistant's translation files only cover config-flow text and entity
state values. The names this integration assigns in Python are looked up
here, keyed by hass.config.language, with English as the fallback.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

SUPPORTED_LANGUAGES = ("de", "en", "fr", "it")

STRINGS: dict[str, dict[str, str]] = {
    "device_name": {
        "de": "Hagelschutz VKF {device_id}",
        "en": "Hail Protection VKF {device_id}",
        "fr": "Protection grêle VKF {device_id}",
        "it": "Protezione grandine VKF {device_id}",
    },
    "manufacturer": {
        "de": "Vereinigung Kantonaler Feuerversicherungen (VKF)",
        "en": "Association of Cantonal Fire Insurers (VKF)",
        "fr": "Association des établissements cantonaux d'assurance incendie (AEAI)",
        "it": "Associazione degli istituti cantonali di assicurazione antincendio (AICAA)",
    },
    "model": {
        "de": "Hagelschutz – einfach automatisch (REST-Schnittstelle)",
        "en": "Hagelschutz – einfach automatisch (REST interface)",
        "fr": "Protection contre la grêle – tout simplement automatique (interface REST)",
        "it": "Protezione antigrandine – semplicemente automatica (interfaccia REST)",
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
}


def _language(hass: HomeAssistant) -> str:
    lang = (hass.config.language or "en").split("-")[0].lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def t(key: str, hass: HomeAssistant, **kwargs) -> str:
    """Translate key into the Home Assistant language; English if missing."""
    entry = STRINGS.get(key, {})
    text = entry.get(_language(hass)) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text
