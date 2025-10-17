"""empty message

Revision ID: 87300d454452
Revises: 3a0cfa7d6694
Create Date: 2025-10-17 16:32:42.653548

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '87300d454452'
down_revision = '3a0cfa7d6694'
branch_labels = None
depends_on = None

def upgrade():
    # 1. ADD COLUMN (يسمح بـ NULL مؤقتاً)
    op.add_column('training_plans', sa.Column('progress', sa.Integer(), nullable=True, server_default='0')) 
    
    # 2. UPDATE RECORDS (تعبئة السجلات الموجودة بـ 0)
    op.execute("UPDATE training_plans SET progress = 0 WHERE progress IS NULL")
    
    # 3. ALTER COLUMN (إضافة قيد NOT NULL)
    op.alter_column('training_plans', 'progress',
               existing_type=sa.Integer(),
               nullable=False,
               server_default=None) # حذف server_default بعد تعبئة البيانات
    
    # (باقي الأكواد المضافة تلقائياً)

def downgrade():
    with op.batch_alter_table('training_plans', schema=None) as batch_op:
        batch_op.drop_column('progress')