from google.adk.agents import Agent
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompt import admission_agent_instruction

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
def connect_to_mongo():
    mongo_uri = os.getenv("MONGODB_ADMISSION")
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
        db = mongo_client['vietnamese-llms']
        collection = db['vietnamese-llms-data']
        for doc in collection.find():
            if "embedding" not in doc or not doc["embedding"] or len(doc["embedding"]) != 768:
                print(f"Processing document ID: {doc['_id']}")
                string_data = doc.get("header", "") + "\nContent" \
                + doc.get("content", "") +"\nKeywords" +  " ".join(doc.get("keywords", []))
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
store_embedding(connect_to_mongo())
print("Done")
def safe_log_warning(message):
    print(f"WARNING: {message}")
    
def safe_log_info(message):
    print(f"INFO: {message}")

def format_string(doc: dict) -> str:
    """
    Định dạng một tài liệu thành chuỗi để tạo embedding hay đưa vào kết quả
    """
    return  doc.get("header", "") + "\nContent" \
            + doc.get("content", "") +"\nKeywords" +  " ".join(doc.get("keywords", []))
    
mongo_client = connect_to_mongo()
def find_similar_documents_by_hybrid_search(
    query: str,
    limit: int = 10,
    candidates: int = 20,
    vector_search_index: str = "embedding_search",
    atlas_search_index: str = "header_text"
):
    """
    Tìm kiếm tài liệu liên quan đến tuyển sinh và thông tin về Học viện Công nghệ Bưu chính Viễn thông (PTIT)
    trong kho dữ liệu bằng hybrid vector + text search. Sử dụng tool này khi người dùng hỏi về:
    - điều kiện xét tuyển, chỉ tiêu, học phí, lịch tuyển sinh, hồ sơ;
    - thông tin chương trình/ ngành, cơ sở đào tạo hoặc liên hệ trường;
    Hàm sẽ kết hợp tìm kiếm ngữ nghĩa (embedding) và tìm kiếm văn bản để trả về các tài liệu phù hợp đã được format.

    Parameters:
        query (str): Câu truy vấn mô tả thông tin cần tìm (ví dụ: "điều kiện xét tuyển PTIT", "địa chỉ campus Hà Nội").
        limit (int): Số lượng kết quả tối đa trả về. Mặc định 10.
        candidates (int): Số ứng viên cho vector search. Mặc định 20.
        vector_search_index (str): Tên index MongoDB cho vector search. Mặc định là "embedding_search".
        atlas_search_index (str): Tên index MongoDB Atlas cho text search. Mặc định là "header_text".

    Returns:
        dict: Một từ điển chứa kết quả tìm kiếm với các khóa:
            - 'status': 'success' nếu tìm kiếm thành công, 'error' nếu có lỗi
            - 'data': danh sách các tài liệu/tài nguyên tìm được dưới dạng chuỗi đã format (header, content, keywords)
            - 'message': thông báo về kết quả hoặc lỗi

    Ghi chú:
        - Kết hợp vector search (ngữ nghĩa) và text search (văn bản). Nếu hybrid search lỗi, hàm sẽ fallback sang text search đơn giản.
    """
    collection = mongo_client['vietnamese-llms']['vietnamese-llms-data']
    query_embedding = get_embedding(query)
    
    # Common project fields
    project_fields = {
        '_id': 1, 'header': 1, 'content': 1, 'keywords': 1
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
            return {"status": "error", "message": str(fallback_e)}
        
admission_agent = Agent(
    name = "admission_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân thông tin tuyển sinh và trường: cung cấp thông tin về tuyển sinh và các thông tin chung về Học viện Công nghệ Bưu chính Viễn thông (PTIT) — lịch sử, địa chỉ của trường",
    instruction = admission_agent_instruction,
    tools = [find_similar_documents_by_hybrid_search],
    disallow_transfer_to_parent=True
)