from google.adk.agents import Agent
from .prompt import general_agent_instruction, google_search_agent_instruction
import requests
from dotenv import load_dotenv
import numexpr
import os
from google.adk.tools import google_search, AgentTool
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent.parent.parent))
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import zoneinfo

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
def get_weather(city: str):
    """
    Đây là một tool thời tiết để lấy thông tin thời tiết hiện tại của một thành phố.
    Sử dụng tool này khi cần kiểm tra thời tiết của bất kỳ thành phố nào trên thế giới,
    bao gồm nhiệt độ, mô tả thời tiết và cảm giác nhiệt độ.

    Parameters:
        city (str): Tên thành phố cần lấy thông tin thời tiết.
                   Tên thành phố được chuẩn hóa tiếng Anh.
                   Ví dụ: "Hanoi", "New York".

    Returns:
        dict: Một từ điển chứa thông tin thời tiết với các khóa:
            - 'status': 'success' nếu lấy thông tin thành công, 'error' nếu có lỗi
            - 'temperature': nhiệt độ hiện tại (độ C) (chỉ khi thành công)
            - 'description': mô tả thời tiết (chỉ khi thành công)
            - 'feel_like': cảm giác nhiệt độ (độ C) (chỉ khi thành công)
            - 'message': thông báo về kết quả hoặc lỗi
    """
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=vi"

    response = requests.get(url)
    if response.status_code == 200:
        try:
            data = response.json()
            
            temperature = data['main']['temp']
            description = data['weather'][0]['description']
            feel_like = data['main']['feels_like']
            return{
                "status": "success",
                "temperature": temperature,
                "description": description,
                "feel_like": feel_like,
                "message": "Lấy thông tin thời tiết thành công"
            }
        except KeyError as e:
            return {
                "status": "error",
                "message": f"Không thể lấy thông tin thời tiết: {str(e)}"
            }
    else:
        return{
            "status": "error",
            "message": "Phương thức trả về HTTP không hợp lệ, trả về " + str(response.status_code)
        }
        
        
def calculator(expression: str) -> str:
    """
    Đây là một tool máy tính đơn giản để thực hiện các phép tính toán học.
    Sử dụng tool này khi cần thực hiện bất kỳ phép tính toán học nào, 
    ví dụ như cộng, trừ, nhân, chia, lũy thừa, v.v.

    Parameters:
        expression (str): Chuỗi biểu thức toán học cần tính toán.
                         Có thể sử dụng các toán tử +, -, *, /, **, 
                         cũng như dấu ngoặc đơn ().
                         Ký tự 'x' hoặc 'X' sẽ được tự động chuyển thành 
                         toán tử nhân '*'.

    Returns:
        dict: Một từ điển chứa kết quả tính toán với các khóa:
            - 'status': 'success' nếu tính toán thành công, 'error' nếu có lỗi
            - 'result': kết quả tính toán (chỉ khi thành công)
            - 'message': thông báo về kết quả hoặc lỗi
    """
    expression = expression.replace('x', '*').replace('X', '*')  # Thay thế 'x' bằng '*'
    try:
        result = str(numexpr.evaluate(expression))
        return {
            "status": "success",
            "result": result,
            "message": "Tính toán thành công"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }
        
def get_current_datetime(city: str):
    """
    Đây là một tool thời gian để lấy thông tin thời gian hiện tại của một thành phố.
    Sử dụng tool này khi cần kiểm tra thời gian hiện tại tại bất kỳ thành phố nào trên thế giới,
    dựa trên múi giờ của thành phố đó.

    Parameters:
        city (str): Tên thành phố cần lấy thông tin thời gian.
                   Hệ thống sẽ tự động tìm kiếm múi giờ phù hợp.
                   Ví dụ: "Hanoi", "New York", "London", "Tokyo".

    Returns:
        dict: Một từ điển chứa thông tin thời gian với các khóa:
            - 'status': 'success' nếu lấy thông tin thành công, 'error' nếu có lỗi
            - 'datetime': thời gian hiện tại theo format "YYYY-MM-DD HH:MM:SS" (chỉ khi thành công)
            - 'message': thông báo về kết quả hoặc lỗi
    """
    city = city.capitalize()
    city = city.replace(" ", "_")  # Thay thế khoảng trắng bằng dấu gạch dưới
    try:
        timezone = "Asia/Ho_Chi_Minh"
        available_zones = zoneinfo.available_timezones()
        for zone in available_zones:
            if city.lower() in zone.lower():
                timezone = zone
                break
            
        tz = ZoneInfo(timezone)
        current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "status": "success",
            "datetime": current_time,
            "message": "Lấy thông tin thời gian thành công"
        }
    except ZoneInfoNotFoundError:
        return {
            "status": "error",
            "message": "Không tìm thấy thông tin múi giờ cho thành phố này"
        }

google_search_agent = Agent(
    name = "google_search_agent",
    model = "gemini-2.0-flash",
    description = "A Google search agent capable of retrieving information from the web.",
    instruction = google_search_agent_instruction,
    tools = [google_search]
)
        
general_agent = Agent(
    name = "general_agent",
    model = "gemini-2.0-flash",
    description = "Xử lý các tác vụ chung chung như small talk, hỏi thời tiết hay tính toàn các phép tính cơ bản.",
    instruction = general_agent_instruction,
    tools = [get_weather, calculator, get_current_datetime, AgentTool(agent = google_search_agent)],
    disallow_transfer_to_parent=True
)