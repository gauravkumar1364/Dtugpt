import os
from fastapi.middleware.cors import CORSMiddleware
from langchain_groq import ChatGroq
from fastapi import FastAPI
from pydantic import BaseModel
import re
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()

os.environ["GROQ_API_KEY"]= os.getenv("GROQ_API_KEY")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = ChatGroq( model="qwen/qwen3-32b");

class chat_request(BaseModel):
    message : str

@app.post("/chat")
async def chat(req:chat_request):

    response = model.invoke(req.message)

    text = response.content
    leaned_text = re.sub(r"<think>[\s\S]*?</think>", "", text)
    
    return {
        "reply" : response.content
    }


