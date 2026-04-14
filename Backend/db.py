import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Lazy MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL")
client = None
db = None
questions_collection = None
processed_files = None

def get_db():
	"""Lazy-initialize MongoDB connection on first use"""
	global client, db, questions_collection, processed_files
	
	if client is None:
		if not MONGODB_URL:
			print("⚠️  MONGODB_URL not configured - MongoDB disabled")
			return None
		
		try:
			client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
			db = client["dtugpt"]
			questions_collection = db["questions"]
			processed_files = db["processed_files"]
			print("✅ MongoDB connected")
		except Exception as e:
			print(f"❌ MongoDB connection failed: {e}")
			return None
	
	return questions_collection

def ensure_indexes() -> None:
	"""Create MongoDB indexes when the app is ready (avoid blocking imports)."""
	try:
		if not questions_collection:
			get_db()
		
		if questions_collection:
			questions_collection.create_index("subject")
			questions_collection.create_index("question")
			processed_files.create_index("file_path")
			print("✅ MongoDB indexes ensured")
	except Exception as e:
		print(f"⚠️  Failed to ensure MongoDB indexes: {e}")
