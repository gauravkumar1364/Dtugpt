import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB Atlas connection
MONGODB_URL = os.getenv("MONGODB_URL")

client = MongoClient(MONGODB_URL)
db = client["dtugpt"]
questions_collection = db["questions"]
processed_files = db["processed_files"]  # Track processed PDFs

def ensure_indexes() -> None:
	"""Create MongoDB indexes when the app is ready (avoid blocking imports)."""
	try:
		questions_collection.create_index("subject")
		questions_collection.create_index("question")
		processed_files.create_index("file_path")
		print("✅ MongoDB indexes ensured")
	except Exception as e:
		print(f"⚠️  Failed to ensure MongoDB indexes: {e}")
