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

# Create indexes for better performance
questions_collection.create_index("subject")
questions_collection.create_index("question")
processed_files.create_index("file_path")  # Index for fast lookup
