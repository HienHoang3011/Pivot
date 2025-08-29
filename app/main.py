import json
import warnings
from google.adk.sessions import InMemorySessionService
from dotenv import load_dotenv
from pydantic import BaseModel

from google.genai.types import (
    Part,
    Content,
)

from google.adk.runners import Runner

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from root_agent import root_agent

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
load_dotenv()

APP_NAME = "Pivot"
user_id = "user123"
session_id = "session123"
# --- ỨNG DỤNG WEB FASTAPI ---

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model để định nghĩa cấu trúc của request body
class QueryRequest(BaseModel):
    query: str
    user_id: str = "default_user" # Tùy chọn: vẫn giữ user_id để agent có ngữ cảnh
    
async def create_sessions():
    session_service = InMemorySessionService()
    session = await session_service.create_session(
    app_name=APP_NAME,
    user_id= user_id,
    session_id= session_id
    )
    return session, session_service


@app.post("/query")
async def handle_query(request: QueryRequest):
    """
    Nhận một câu hỏi, chờ agent xử lý xong và trả về câu trả lời cuối cùng.
    """
    print(f"Received query from {request.user_id}: {request.query}")

    # 1. Khởi tạo session và Runner cho mỗi request (sử dụng request.user_id)
    session_service = InMemorySessionService()
    session_id_local = f"session-{request.user_id}"
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=request.user_id,
        session_id=session_id_local
    )
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service
    )

    # 2. Tạo nội dung đầu vào từ query của người dùng (ĐÃ SỬA LỖI Ở ĐÂY)
    user_content = Content(role="user", parts=[Part(text=request.query)])

    # 3. Chạy agent và thu thập tất cả các phần của câu trả lời
    final_response_parts = []
    async for event in runner.run_async(
        user_id=request.user_id,
        new_message=user_content,
        session_id=session_id_local
    ):
        # Lấy nội dung từ các sự kiện trả về
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_response_parts.append(part.text)

    # 4. Ghép các phần lại thành một câu trả lời hoàn chỉnh
    final_response = "".join(final_response_parts)
    print(f"Final response for {request.user_id}: {final_response}")

    # 5. Trả về câu trả lời cuối cùng trong một JSON object
    return {"response": final_response}