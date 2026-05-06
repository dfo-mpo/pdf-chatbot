from fastapi import File, UploadFile, WebSocket, WebSocketDisconnect, FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.utils.document_inteligence import get_content, get_vectors
from app.utils.openai import request_openai_chat, get_relevent_chunks
from app.utils.file import add_page_numbers
from typing import List
import json

app = FastAPI(title="PDF Chatbot Tool")

# Configure CORS  
origins = [  
    "http://localhost:3000",  # React frontend  
    "http://localhost:3001",  # React frontend  
    "http://localhost:3080",  # React frontend  
    "https://sdpa-ai-computervision-portal.azurewebsites.net",
    "https://sdpa-ai-tools-frontend.azurewebsites.net",
    "http://ai-ml-tools-frontend",
    "http://frontend",
    # Add other origins if needed  
]  
print(origins)

app.add_middleware(  
    CORSMiddleware,  
    allow_origins=origins,  
    allow_credentials=True,  
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Performs DI extraction on document so document can be processed with openAI
@app.post("/di_extract_document/")
async def pdf_to_json_string(file: UploadFile = File(...)):
    try:
        refined_content = "Start of Document or pdf"
        refined_content += get_content(file, content=False, polygon=False, di_api="3.1")
        refined_content += "End of Document or pdf"

        return JSONResponse({"extracted_document": refined_content})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )

# Web socket for asking a LLM a question and streaming the responce, uses RAG
@app.websocket("/ws/chat_stream")
async def llm_responce(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()  
        chat_history = data['chat_history']  
        document_vectors = data['document_vectors']
        model = data.get('model', 'gpt-4o-mini')  
        temperature = data.get('temperature', 0.3)  
        reasoning_effort = data.get('reasoning_effort', 'high') 
        token_limit = data.get('token_limit', 100000)
        isAuth = data.get('isAuth', False)
        api_key = data.get('api_key', None)
        # User-supplied API key for non-default models; None for gpt-4o-mini
        api_key = data.get('api_key', None)

        document_chunks = document_vectors['text_chunks']
        document_metadata = document_vectors['metadata']
        
        document_content = get_relevent_chunks(chat_history, document_chunks, document_metadata) 

        llm_stream = request_openai_chat(chat_history, document_content=document_content, model=model, temperature=temperature, reasoning_effort=reasoning_effort, token_remaining=token_limit, isAuth=isAuth, api_key=api_key)
            
        # Simulate processing and responding with chunks  
        async for chunk in llm_stream:
            chunk_data = json.loads(chunk[6:])  # Removing 'data: ' part
            await websocket.send_json(chunk_data)

    except WebSocketDisconnect:  
        print("Client disconnected")  
    except Exception as e:  
        await websocket.send_json({"error": str(e)})  
        await websocket.close() 

# Performs DI extraction and divides documents into chunks of markdown, to be used for RAG. Only works for a single document.
@app.post("/di_chunk_single_document/")
async def pdf_to_chunks(file: UploadFile = File(...)):
    try:
        paged_file = add_page_numbers(file)
        doc_chunks, doc_metadata = get_vectors(paged_file, file.filename)
        text_chunks = doc_chunks
        metadata = doc_metadata

        print(f"Total number of chunks: {len(text_chunks)}")
        print(f"Metadata entries (must equal chunk number): {len(metadata)}")
        return JSONResponse({"text_chunks": text_chunks, "metadata": metadata})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )
    
# Performs DI extraction and divides documents into chunks of markdown, to be used for RAG. Requires a set of documents.
@app.post("/di_chunk_multi_document/")
async def pdf_to_chunks(files: List[UploadFile] = File(...)):
    try:
        text_chunks = []
        metadata = []
        for file in files:
            paged_file = add_page_numbers(file)
            doc_chunks, doc_metadata = get_vectors(paged_file, file.filename)
            text_chunks.extend(doc_chunks)
            metadata.extend(doc_metadata)

        print(f"Total number of chunks: {len(text_chunks)}")
        print(f"Metadata entries (must equal chunk number): {len(metadata)}")
        return JSONResponse({"text_chunks": text_chunks, "metadata": metadata})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred: {str(e)}"}
        )