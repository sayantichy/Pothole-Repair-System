from flask import Blueprint
bp = Blueprint("user", __name__, template_folder="../../templates/user")
from . import routes  # noqa
