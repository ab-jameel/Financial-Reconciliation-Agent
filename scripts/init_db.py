"""Creates the orchestration database tables."""

from dotenv import load_dotenv
load_dotenv()
from recon_orchestration.db.tables import Base
from recon_orchestration.db.session import get_engine

if __name__ == "__main__":
    Base.metadata.create_all(get_engine())
    print("Tables created.")
