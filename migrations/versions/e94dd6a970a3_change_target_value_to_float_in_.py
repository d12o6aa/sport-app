"""Change target_value to Float in AthleteGoal

Revision ID: e94dd6a970a3
Revises: dee723e8bcc8
Create Date: 2025-09-11 13:52:49.828690

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e94dd6a970a3'
down_revision = 'dee723e8bcc8'
branch_labels = None
depends_on = None
def upgrade():
    op.execute(
        """
        ALTER TABLE athlete_goals
        ALTER COLUMN target_value
        TYPE DOUBLE PRECISION
        USING CASE
            WHEN target_value ~ '^[0-9.]+$' THEN target_value::DOUBLE PRECISION
            ELSE 0
        END
        """
    )

def downgrade():
    op.execute(
        """
        ALTER TABLE athlete_goals
        ALTER COLUMN target_value
        TYPE VARCHAR
        USING target_value::TEXT
        """
    )