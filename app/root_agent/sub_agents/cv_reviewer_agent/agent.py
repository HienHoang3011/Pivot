from .prompt import cv_reviewer_agent_instruction
from google.adk.agents import Agent
from dotenv import load_dotenv

load_dotenv()
cv_reviewer_agent = Agent(
    name = "cv_reviewer_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân đánh giá CV và cung cấp phản hồi để cải thiện CV",
    instruction = cv_reviewer_agent_instruction,
    disallow_transfer_to_parent=True
)
