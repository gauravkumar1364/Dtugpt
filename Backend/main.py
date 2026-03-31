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

    raw_text = response.content

    thinking = re.search(r"<think>([\s\S]*?)</think>", raw_text)

    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()

    thinking_text = thinking.group(1).strip() if thinking else None

    print("Thinking:", thinking_text if thinking_text else "None")
        
    return {
        "reply": cleaned,
        "thinking": thinking_text
    }


