from google.adk.agents import Agent
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompt import path_learning_agent_instruction, google_search_agent_instruction
from google.adk.tools import google_search
from google.adk.tools import AgentTool
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
def connect_to_mongo():
    mongo_uri = os.getenv("MONGODB_URI")
    try:
        mongo_client = MongoClient(mongo_uri)
        print("connected to mongo")
        return mongo_client
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None
    
def get_embedding(text: str):
    try:
        client = genai.Client()
        result = client.models.embed_content(
            model = "text-embedding-004",
            contents=text
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Error getting embeddings: {e}")
        return None
    
def store_embedding(mongo_client):
    try:
        db = mongo_client['Pivot']
        collection = db['coursera-data']
        for doc in collection.find():
            if "embedding" not in doc or not doc["embedding"] or len(doc["embedding"]) != 768:
                print(f"Processing document ID: {doc['_id']}")
                string_data = doc.get("Title", "") + "\nDescription" \
                + doc.get("description", "") +"\nModules/Courses" +  doc.get("modules/courses", "") + doc.get("level", "") + doc.get("schedule", "")
                embedding = get_embedding(string_data)
                if embedding:
                    collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"embedding": embedding}}
                    )
                print(f"Updated document ID: {doc['_id']} with new embedding.")
    except Exception as e:
        print(f"Error storing embeddings: {e}")
        return None

def safe_log_warning(message):
    print(f"WARNING: {message}")
    
def safe_log_info(message):
    print(f"INFO: {message}")

def format_string(doc: dict) -> str:
    """
    Định dạng một tài liệu thành chuỗi để tạo embedding hay đưa vào kết quả
    """
    return f"Title: {doc.get('title', '')}\n" + \
        f"Description: {doc.get('description', '')}\n" + \
        f"Modules/Courses: {doc.get('modules/courses', '')}\n" + \
        f"Level: {doc.get('level', '')}\n" + \
        f"Schedule: {doc.get('schedule', '')}\n"
    
mongo_client = connect_to_mongo()
def find_similar_documents_by_hybrid_search(
    query: str,
    limit: int = 10,
    candidates: int = 20,
    vector_search_index: str = "embedding_search",
    atlas_search_index: str = "header_text"
):
    """
    Đây là một tool tìm kiếm hybrid để tìm kiếm tài liệu khóa học tương tự sử dụng kết hợp vector search và text search.
    Sử dụng tool này khi cần tìm kiếm các khóa học liên quan đến một chủ đề hoặc câu hỏi cụ thể,
    với khả năng tìm kiếm ngữ nghĩa (vector) và tìm kiếm văn bản (text) được thực hiện song song.

    Parameters:
        query (str): Câu truy vấn tìm kiếm khóa học.
                    Có thể là từ khóa, câu hỏi hoặc mô tả về nội dung khóa học cần tìm.
                    Ví dụ: "machine learning", "Python programming course", "data science beginner".
        limit (int, optional): Số lượng khóa học tối đa trả về. Mặc định là 10.
                              Giá trị hợp lệ từ 1 đến 50.
        candidates (int, optional): Số lượng ứng viên cho vector search. Mặc định là 20.
                                   Càng cao thì chất lượng tìm kiếm càng tốt nhưng chậm hơn.
        vector_search_index (str, optional): Tên index MongoDB cho vector search. 
                                            Mặc định là "embedding_search".
        atlas_search_index (str, optional): Tên index MongoDB Atlas cho text search.
                                           Mặc định là "header_text".

    Returns:
        dict: Một từ điển chứa kết quả tìm kiếm với các khóa:
            - 'status': 'success' nếu tìm kiếm thành công, 'error' nếu có lỗi
            - 'data': danh sách các khóa học tìm được dưới dạng chuỗi formatted (chỉ khi thành công)
            - 'message': thông báo về kết quả hoặc lỗi
    """
    collection = mongo_client['Pivot']['coursera-data']
    query_embedding = get_embedding(query)
    
    # Common project fields
    project_fields = {
        '_id': 1, 'title': 1, 'description': 1, 'modules/courses': 1,
        'level': 1, 'schedule': 1
    }
    
    def perform_vector_search():
        try:
            pipeline = [
                {"$vectorSearch": {
                    "index": vector_search_index,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "limit": limit,
                    "numCandidates": candidates
                }},
                {"$project": {**project_fields, "vector_score": {"$meta": "vectorSearchScore"}}}
            ]
            results = list(collection.aggregate(pipeline))
            for doc in results:
                doc['combined_score'] = doc.get('vector_score', 0) * 0.6
            return results
        except Exception as e:
            return []

    def perform_text_search():
        if not query.strip():
            return []
        try:
            pipeline = [
                {"$search": {
                    "index": atlas_search_index,
                    "text": {"query": query, "path": ["header", "content"]}
                }},
                {"$project": {**project_fields, "text_score": {"$meta": "searchScore"}}}
            ]
            results = list(collection.aggregate(pipeline))
            for doc in results:
                doc['combined_score'] = doc.get('text_score', 0) * 0.4
            return results
        except Exception:
            return []

    try:
        # Chạy song song hai truy vấn
        with ThreadPoolExecutor(max_workers=2) as executor:
            vector_future = executor.submit(perform_vector_search)
            text_future = executor.submit(perform_text_search)
            all_results = vector_future.result() + text_future.result()

        # Hợp nhất và loại bỏ trùng lặp
        merged_map = {}
        for doc in all_results:
            doc_id = doc['_id']
            if doc_id in merged_map:
                merged_map[doc_id]['combined_score'] += doc['combined_score']
            else:
                merged_map[doc_id] = doc

        # Sắp xếp và giới hạn kết quả
        final_results = sorted(merged_map.values(), 
                             key=lambda x: x.get('combined_score', 0), 
                             reverse=True)[:limit]

        return {
            "status": "success",
            "data": [format_string(doc) for doc in final_results],
            "message": "Tìm kiếm thành công"
        }

    except Exception as e:
        try:
            # Fallback với text search đơn giản
            pipeline = [
                {"$search": {"index": atlas_search_index, "text": {"query": query, "path": ["description", "title"]}}},
                {"$project": project_fields},
                {"$limit": limit}
            ]
            fallback_results = list(collection.aggregate(pipeline))
            return {
                "status": "success", 
                "data": [format_string(doc) for doc in fallback_results],
                "message": "Tìm kiếm thành công (fallback)"
            }
        except Exception as fallback_e:
            return {"status": "error", "message": str(fallback_e)}\
                
google_search_agent = Agent(
    name = "google_search_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân tìm kiếm thông tin trên Google để hỗ trợ các tác nhân khác",
    instruction = google_search_agent_instruction,
    tools= [google_search],
    disallow_transfer_to_parent=True
)
google_search = AgentTool(agent=google_search_agent)
        
path_learning_agent = Agent(
    name = "path_learning_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân đề xuất các khóa học trên Coursera để người dùng tham khảo và định hướng tốt hơn",
    instruction = path_learning_agent_instruction,
    tools = [find_similar_documents_by_hybrid_search, google_search],
    disallow_transfer_to_parent=True
)