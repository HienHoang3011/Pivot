from google.adk.agents import Agent
from .prompt import root_agent_instruction
from .sub_agents.general_agent import general_agent
from .sub_agents.path_learning_agent import path_learning_agent
from dotenv import load_dotenv
from google.genai import types
from google.adk.planners import BuiltInPlanner
from .sub_agents.admission_agent import admission_agent
from .sub_agents.cv_reviewer_agent import cv_reviewer_agent

load_dotenv()

root_agent = Agent(
    name = "root_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân gốc, có chức năng phân tích và định tuyến yêu cầu đến tác nhân phù hợp.",
    instruction= root_agent_instruction,
    planner= BuiltInPlanner(
        thinking_config= types.ThinkingConfig(
            thinking_budget= 1024
        )
    ),
    sub_agents= [general_agent, path_learning_agent, admission_agent, cv_reviewer_agent],
)