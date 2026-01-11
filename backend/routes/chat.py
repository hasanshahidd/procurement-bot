from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from openai import OpenAI
import json
import asyncio
import os

from backend.services import database, openai_client

router = APIRouter()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    history: List[Dict[str, Any]] = []

class ChatResponse(BaseModel):
    response: str
    sql: Optional[str] = None
    data: Optional[list] = None

class QueryRequest(BaseModel):
    sql: str

class SuggestionRequest(BaseModel):
    partial_input: str
    language: str = "en"
    conversation_context: List[str] = []

class SuggestionResponse(BaseModel):
    suggestions: List[str]

@router.get("/health")
async def health_check():
    try:
        count = database.get_record_count()
        return {
            "status": "healthy",
            "recordCount": count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats():
    try:
        stats = database.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Check if message contains multiple questions
        questions = openai_client.split_questions(request.message)
        
        if len(questions) > 1:
            # Process multiple questions - limit to 10 for performance
            all_responses = []
            max_questions = min(len(questions), 10)
            
            for i, question in enumerate(questions[:max_questions], 1):
                result = openai_client.process_chat(question, request.language, request.history)
                sql = result.get("sql")
                
                if sql and openai_client.validate_sql(sql):
                    try:
                        data = database.execute_query(sql)
                        # Limit to 20 rows per question for faster processing
                        data_list = [dict(row) for row in data][:20]
                        
                        response_text = openai_client.generate_response(
                            data_list, 
                            question, 
                            request.language
                        )
                        all_responses.append(response_text)
                    except Exception as e:
                        all_responses.append(f"**Error:** {str(e)}")
                else:
                    all_responses.append(result.get("explanation", ""))
            
            # Add note if questions were limited
            if len(questions) > 10:
                all_responses.append(f"\\n*Note: Showing first 10 of {len(questions)} questions. Please ask fewer questions at once for faster responses.*")
            
            # Combine all responses with separators
            combined_response = "\\n\\n---\\n\\n".join(all_responses)
            
            return ChatResponse(
                response=combined_response,
                sql=None,
                data=None
            )
        
        else:
            # Single question - original logic
            result = openai_client.process_chat(request.message, request.language, request.history)
            
            sql = result.get("sql")
            explanation = result.get("explanation", "")
            
            if sql and openai_client.validate_sql(sql):
                try:
                    data = database.execute_query(sql)
                    data_list = [dict(row) for row in data]
                    
                    response_text = openai_client.generate_response(
                        data_list, 
                        request.message, 
                        request.language
                    )
                    
                    return ChatResponse(
                        response=response_text,
                        sql=sql,
                        data=data_list[:100]
                    )
                except Exception as e:
                    # If query fails, try to fix it
                    error_msg = str(e)
                    fixed_result = openai_client.fix_failed_query(
                        sql, error_msg, request.message, request.language
                    )
                    
                    if fixed_result.get("sql"):
                        # Try the fixed query
                        try:
                            data = database.execute_query(fixed_result["sql"])
                            data_list = [dict(row) for row in data]
                            response_text = openai_client.generate_response(
                                data_list, request.message, request.language
                            )
                            return ChatResponse(
                                response=response_text,
                                sql=fixed_result["sql"],
                                data=data_list[:100]
                            )
                        except:
                            pass
                    
                    # If still failing, return helpful error
                    return ChatResponse(
                        response=openai_client.generate_error_response(
                            error_msg, request.message, request.language
                        ),
                        sql=sql
                    )
            else:
                return ChatResponse(response=explanation)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggestions")
async def get_suggestions(request: SuggestionRequest):
    """Generate smart query suggestions based on user's partial input"""
    try:
        if not request.partial_input or len(request.partial_input.strip()) < 3:
            return SuggestionResponse(suggestions=[])
        
        # Generate suggestions using AI
        suggestions = openai_client.generate_query_suggestions(
            request.partial_input,
            request.language,
            request.conversation_context
        )
        
        return SuggestionResponse(suggestions=suggestions)
    except Exception as e:
        # Don't fail hard on suggestions - just return empty
        print(f"Suggestion error: {e}")
        return SuggestionResponse(suggestions=[])

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming endpoint for typing animation effect - optimized for speed"""
    async def generate_stream():
        try:
            # Step 1: Analyzing query (0-25%) - FASTER
            yield f"data: {json.dumps({'type': 'progress', 'step': 1, 'total': 4, 'status': 'active', 'message': 'Analyzing your question'})}\n\n"
            await asyncio.sleep(0.2)
            
            # Get the complete response first
            result = openai_client.process_chat(request.message, request.language, request.history)
            
            # Step 1 Complete
            yield f"data: {json.dumps({'type': 'progress', 'step': 1, 'total': 4, 'status': 'completed', 'message': 'Analyzing your question'})}\n\n"
            await asyncio.sleep(0.05)
            
            sql = result.get("sql")
            explanation = result.get("explanation", "")
            response_text = ""
            data_list = []
            
            if sql and openai_client.validate_sql(sql):
                # Step 2: Searching for information (25-50%) - FASTER
                yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'total': 4, 'status': 'active', 'message': 'Searching for information'})}\n\n"
                await asyncio.sleep(0.2)
                
                try:
                    data = database.execute_query(sql)
                    data_list = [dict(row) for row in data]
                    
                    # Step 2 Complete
                    yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'total': 4, 'status': 'completed', 'message': 'Searching for information'})}\n\n"
                    await asyncio.sleep(0.05)
                    
                    # Step 3: Generating response (50-75%) - FASTER
                    yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'active', 'message': 'Generating response..'})}\n\n"
                    await asyncio.sleep(0.2)
                    
                    response_text = openai_client.generate_response(
                        data_list, 
                        request.message, 
                        request.language
                    )
                    
                    # Step 3 Complete
                    yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'completed', 'message': 'Generating response..'})}\n\n"
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    # If query fails, try to fix it
                    error_msg = str(e)
                    fixed_result = openai_client.fix_failed_query(
                        sql, error_msg, request.message, request.language
                    )
                    
                    if fixed_result.get("sql"):
                        try:
                            data = database.execute_query(fixed_result["sql"])
                            data_list = [dict(row) for row in data]
                            
                            # Step 2 Complete
                            yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'total': 4, 'status': 'completed', 'message': 'Searching for information'})}\n\n"
                            await asyncio.sleep(0.1)
                            
                            # Step 3: Generating response
                            yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'active', 'message': 'Generating response..'})}\n\n"
                            await asyncio.sleep(0.2)
                            
                            response_text = openai_client.generate_response(
                                data_list, request.message, request.language
                            )
                            sql = fixed_result["sql"]
                            
                            # Step 3 Complete
                            yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'completed', 'message': 'Generating response..'})}\n\n"
                            await asyncio.sleep(0.1)
                        except:
                            response_text = fixed_result.get("explanation", explanation)
                            yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'total': 4, 'status': 'completed', 'message': 'Searching for information'})}\n\n"
                            yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'completed', 'message': 'Generating response..'})}\n\n"
                    else:
                        response_text = fixed_result.get("explanation", explanation)
                        yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'total': 4, 'status': 'completed', 'message': 'Searching for information'})}\n\n"
                        yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'completed', 'message': 'Generating response..'})}\n\n"
            else:
                # For non-SQL queries
                yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'total': 4, 'status': 'active', 'message': 'Searching for information'})}\n\n"
                await asyncio.sleep(0.3)
                yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'total': 4, 'status': 'completed', 'message': 'Searching for information'})}\n\n"
                
                yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'active', 'message': 'Generating response..'})}\n\n"
                await asyncio.sleep(0.4)
                response_text = explanation
                yield f"data: {json.dumps({'type': 'progress', 'step': 3, 'total': 4, 'status': 'completed', 'message': 'Generating response..'})}\n\n"
                await asyncio.sleep(0.1)
            
            # Step 4: Finalizing answer (75-100%) - FASTER
            yield f"data: {json.dumps({'type': 'progress', 'step': 4, 'total': 4, 'status': 'active', 'message': 'Finalizing answer..'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Stream the response word by word - FASTER
            words = response_text.split(' ')
            for i, word in enumerate(words):
                chunk_data = {
                    "type": "content",
                    "content": word + (' ' if i < len(words) - 1 else ''),
                    "done": False
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
                await asyncio.sleep(0.015)  # 15ms delay (was 30ms) for faster typing
            
            # Send final metadata
            final_data = {
                "type": "complete",
                "content": response_text,
                "done": True
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            error_data = {
                "type": "error",
                "content": str(e),
                "done": True
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/query")
async def direct_query(request: QueryRequest):
    try:
        if not openai_client.validate_sql(request.sql):
            raise HTTPException(status_code=400, detail="Invalid or unsafe SQL query. Only SELECT queries are allowed.")
        
        data = database.execute_query(request.sql)
        return {"data": [dict(row) for row in data]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DetailRequest(BaseModel):
    question: str
    sql: str
    language: str = "en"

@router.post("/chat/details")
async def get_details(request: DetailRequest):
    """Get detailed table view for a query - only called when user clicks 'Show Details'"""
    try:
        if not openai_client.validate_sql(request.sql):
            raise HTTPException(status_code=400, detail="Invalid SQL query")
        
        # Execute query and get all results
        data = database.execute_query(request.sql)
        data_list = [dict(row) for row in data]
        
        # Generate detailed response with properly formatted tables
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"""Generate a properly formatted table view for the data.

STRICT FORMATTING RULES:
1. Start with a brief one-line summary (COUNT MUST BE ACCURATE)
2. Create a well-formatted markdown table:
   - Show ALL data rows (no limit)
   - Use proper column alignment with spaces
   - Align numbers to the right
   - Align text to the left
   - Ensure all columns are properly padded
   - Use consistent spacing between | separators
3. Format currency with $ and thousand separators (1,000.00)
4. COUNT ACCURATELY - verify the number of rows matches actual data
5. NO "remaining records" text - show ALL rows in table

Example format:
| Project Name          | Budget      | Status     |
|:---------------------|------------:|:-----------|
| Infrastructure       | $1,250,000  | Active     |
| Software Dev         | $850,000    | Completed  |

CRITICAL: The table row count MUST match the exact data provided. Do not approximate.

Respond in {request.language}."""},
                {"role": "user", "content": f"Question: {request.question}\n\nData ({len(data_list)} records):\n{str(data_list)}\n\nCreate a well-formatted table showing ALL {len(data_list)} records."}
            ],
            temperature=0.1,
            max_tokens=3000
        )
        
        return {
            "response": response.choices[0].message.content,
            "total_records": len(data_list),
            "data": data_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
