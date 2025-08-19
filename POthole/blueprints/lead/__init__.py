from flask import Blueprint
bp = Blueprint("lead", __name__, template_folder="../../templates/lead")
from . import routes  # noqa
