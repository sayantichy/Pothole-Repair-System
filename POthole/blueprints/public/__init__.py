from flask import Blueprint
bp = Blueprint("public", __name__, template_folder="../../templates/public")
from . import routes  # noqa
