from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from Chat_logic.Chat import get_answer
from Parent_agent import parent_agent
import uuid
from langchain_neo4j import Neo4jGraph
from pathlib import Path
from pydantic import BaseModel
from qdrant_client import QdrantClient
import os
from KG.kg import Create_KG, Store_graph_Neo4j, Store_graph_Qdrant
import shutil

class repo_input(BaseModel):
    job_id : str
    url : str
    owner : str
    repo_name : str
    branch : str

client = QdrantClient(
    url=os.getenv('QDRANT_CLUSTER'),
    api_key=os.getenv('QDRANT_API_KEY')
)

graph=Neo4jGraph(
    url=os.getenv('NEO4J_URI'),
    username=os.getenv('NEO4J_USERNAME'),
    password=os.getenv('NEO4J_PASSWORD')
)

app=FastAPI()
@app.get("/")
async def serve_frontend():
    index_path = Path("frontend.html")
    if not index_path.exists():
        return JSONResponse(status_code=404, content={"error": "frontend.html not found"})
    return FileResponse('frontend.html')

@app.post('/create_folder')
async def Create_folder():
    job_id=str(uuid.uuid4())
    job_path=Path(job_id)
    job_path.mkdir(parents=True, exist_ok=True)
    
    return {'job_id': job_id}

@app.post('/github-repo')
async def Enter_Info(repo_input:repo_input):

    # To avoid the parameters being shown in url as query parameter
    # Making branch explicit as LLM tried either master or main
    message=f'Explain this repo---> url:{repo_input.url}, owner:{repo_input.owner}, repo_name:{repo_input.repo_name}, branch:{repo_input.branch}'
    job_path=Path(repo_input.job_id)
    try:
        return StreamingResponse(
            parent_agent(message=message, filename=job_path),
            media_type='text/markdown')
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=e
        )

#download the pdf file created
@app.get('/download')
async def Download_PDF(job_id:str):
    try:
        file_path=Path(job_id)
        pdf_path=file_path/'repo.pdf'
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename="repo.pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=e
        )

@app.websocket("/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    #making sure previous collections are deleted
    client.delete_collection(collection_name="documents")
    list_graph_docs=Create_KG()
    
    #deleting previously created graphs
    graph.query("MATCH (n) DETACH DELETE n")
    Store_graph_Neo4j(list_graph_docs)

    Store_graph_Qdrant(list_graph_docs)

    await websocket.accept()
    history = []
    try:
        while True:
            user_message = await websocket.receive_text()
            
            full_response = ""
            async for chunk in get_answer(message=user_message, history=history):
                full_response += chunk
                await websocket.send_text(chunk)
            
            history.append({
                "role": "user",
                "content": user_message
            })
            history.append({
                "role": "assistant", 
                "content": full_response
            })

    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")

@app.delete('/delete')
async def delete_job(job_id:str):
    job_dir=Path(job_id)
    if not job_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f'{job_dir} not found'
        )
    
    try:
        shutil.rmtree(job_dir)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'Unexpected error occurred : {e}'
        )
    return JSONResponse(
        status_code=200,
        content={
            'job id': f'{job_id}',
            'status':'job delted'
        }
    )