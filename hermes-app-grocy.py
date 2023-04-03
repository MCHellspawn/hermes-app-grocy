"""Skill to work with the Grocy App."""

import logging
from skill import RhasspySkill
from rhasspyhermes_app import HermesApp

_APPNAME = "GrocyApp"
_LOGGER = logging.getLogger(_APPNAME)

if __name__ == "__main__":
    _LOGGER.info(f"Starting Hermes App: {_APPNAME}")
    app = HermesApp(_APPNAME)
    _LOGGER.info(f"Setup starting App: {_APPNAME}")
    skill = RhasspySkill(name = _APPNAME, app = app, logger = _LOGGER)
    _LOGGER.info(f"Setup Completed App: {_APPNAME}")
    _LOGGER.info(f"Running App: {_APPNAME}")
    app.run()
