"""crew lead + memberships"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9f9045210d3c"
down_revision = "054c96e8650a"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop legacy team tables if present
    if "team_membership" in insp.get_table_names():
        op.drop_table("team_membership")
    if "team" in insp.get_table_names():
        op.drop_table("team")

    # Add lead_user_id column (NO FK here: SQLite can't ALTER constraints)
    if "lead_user_id" not in [c.get("name") for c in insp.get_columns("crew")]:
        op.add_column("crew", sa.Column("lead_user_id", sa.Integer(), nullable=True))

    # Create crew_membership with FKs (table creation is OK on SQLite)
    if "crew_membership" not in insp.get_table_names():
        op.create_table(
            "crew_membership",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("crew_id", sa.Integer(), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), nullable=False, index=True),
            sa.Column("role", sa.String(length=20), nullable=True, server_default="member"),
            sa.ForeignKeyConstraint(["crew_id"], ["crew.id"], name="fk_crewmembership_crew"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_crewmembership_user"),
        )

def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "crew_membership" in insp.get_table_names():
        op.drop_table("crew_membership")

    # We only drop the column we added
    if "lead_user_id" in [c.get("name") for c in insp.get_columns("crew")]:
        op.drop_column("crew", "lead_user_id")
