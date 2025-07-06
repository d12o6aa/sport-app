from infrastructure.db.session import Base, engine
import infrastructure.db.base  # يستورد كل الموديلات تلقائيًا

def init_db():
    Base.metadata.create_all(bind=engine)
