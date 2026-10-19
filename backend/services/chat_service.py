import datetime
import signal
import time
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatHuggingFace
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts.chat import ChatPromptTemplate
from config.config import Config
from models.models import Query, ChatHistory
from utils.helpers import is_general_chat
from utils.pdf_utils import update_vectorstore
import re
import warnings
import random
from functools import wraps

# Suppress LangChain deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

def retry_with_exponential_backoff(max_retries=3, base_delay=1):
    """Decorator for retrying function calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    # Check if it's a retryable error
                    if any(keyword in error_str for keyword in ['timeout', '504', '503', '502', 'deadline', 'rate limit']):
                        if attempt < max_retries - 1:
                            # Exponential backoff with jitter
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            print(f"Attempt {attempt + 1} failed, retrying in {delay:.2f} seconds: {str(e)}")
                            time.sleep(delay)
                            continue
                    raise e
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Global variables for session management
conversation_memories = {}  # Store conversation memories by session
session_timestamps = {}    # Track last activity time for each session

# Template for AI responses
template = """
You are a knowledgeable academic assistant helping students with their queries. Use the following context to provide accurate, helpful answers.

INSTRUCTIONS:
- Answer based ONLY on the provided context
- If the context doesn't contain enough information, respond with exactly "I do not know."
- Provide clear, concise answers
- Be helpful and professional in your tone
- If multiple pieces of information are relevant, organize them clearly

Context: {context}

Question: {question}

Answer:
"""

class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self, vectorstore):
        self.vectorstore = vectorstore
        self.query_model = Query()
        self.chat_history_model = ChatHistory()
    
    def _get_llm(self):
        """Get LLM instance based on configured provider"""
        if not Config.GROQ_API_KEY:
            raise ValueError("No AI provider configured. Please set GROQ_API_KEY.")
        print(f"Using Groq AI with model: {Config.GROQ_MODEL}")
        return ChatGroq(
            groq_api_key=Config.GROQ_API_KEY,
            model_name=Config.GROQ_MODEL,
            temperature=0.3,
            max_tokens=2048,
            timeout=Config.GROQ_TIMEOUT,
            max_retries=3
        )
    
    def format_response(self, text):
        """Format markdown-style text to HTML"""
        if not text:
            return text
        
        # Split text into lines for processing
        lines = text.split('\n')
        formatted_lines = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_list:
                    formatted_lines.append('')  # Empty line in list
                else:
                    formatted_lines.append('<br>')  # Line break outside list
                continue
            
            # Convert headings
            if line.startswith('### '):
                line = f'<h3>{line[4:]}</h3>'
                in_list = False
            elif line.startswith('## '):
                line = f'<h2>{line[3:]}</h2>'
                in_list = False
            elif line.startswith('# '):
                line = f'<h1>{line[2:]}</h1>'
                in_list = False
            # Convert bullet points
            elif re.match(r'^[\*\-\+] ', line):
                if not in_list:
                    formatted_lines.append('<ul>')
                    in_list = 'ul'
                line = f'<li>{line[2:]}</li>'
            # Convert numbered lists
            elif re.match(r'^\d+\. ', line):
                if not in_list:
                    formatted_lines.append('<ol>')
                    in_list = 'ol'
                line = f'<li>{re.sub(r"^\d+\. ", "", line)}</li>'
            else:
                # Close any open list
                if in_list:
                    formatted_lines.append(f'</{in_list}>')
                    in_list = False
            
            # Apply text formatting
            # Convert bold text (**text**)
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'__(.*?)__', r'<strong>\1</strong>', line)
            
            # Convert italic text (*text*)
            line = re.sub(r'(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)', r'<em>\1</em>', line)
            line = re.sub(r'(?<!_)_(?!_)([^_]+)(?<!_)_(?!_)', r'<em>\1</em>', line)
            
            # Convert inline code (`code`)
            line = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
            
            formatted_lines.append(line)
        
        # Close any remaining open list
        if in_list:
            formatted_lines.append(f'</{in_list}>')
        
        # Join lines and handle code blocks
        result = '\n'.join(formatted_lines)
        
        # Convert code blocks (```code```)
        result = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', result, flags=re.DOTALL)
        
        return result

    def cleanup_expired_sessions(self):
        """Clean up expired sessions if needed"""
        current_time = time.time()
        expired_sessions = [
            sid for sid, last_active in session_timestamps.items()
            if current_time - last_active > Config.SESSION_TIMEOUT
        ]
        
        for sid in expired_sessions:
            if sid in conversation_memories:
                del conversation_memories[sid]
            if sid in session_timestamps:
                del session_timestamps[sid]
        
        if expired_sessions:
            print(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def update_session_timestamp(self, session_id):
        """Update last activity time for a session"""
        session_timestamps[session_id] = time.time()
    
    def get_conversation_chain(self, session_id):
        """Create or retrieve a conversation chain for a session"""
        self.update_session_timestamp(session_id)
        
        if session_id not in conversation_memories:
            # Suppress the deprecation warning for memory
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                memory = ConversationBufferMemory(
                    memory_key='chat_history',
                    return_messages=True
                )
            conversation_memories[session_id] = memory
        else:
            memory = conversation_memories[session_id]

        # Initialize LLM based on configured provider
        llm = self._get_llm()

        # Configure the retriever with optimized search parameters
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 10}  # Reduced from 15 to 10 for faster processing
        )

        conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": ChatPromptTemplate.from_template(template)}
        )
        return conversation_chain
    
    def process_query(self, question, session_id, user_id=None):
        """Process a user query and return response"""
        try:
            # Cleanup expired sessions
            self.cleanup_expired_sessions()
            
            # Generate session ID if not provided
            if not session_id:
                session_id = str(datetime.datetime.now().timestamp())
            
            print("\n" + "="*50)
            print(f"Session: {session_id}")
            print("Question received:", question)
            print("="*50)

            # Check if it's general chat
            general_response = is_general_chat(question)
            if general_response:
                # Get chat history for this session
                memory = conversation_memories.get(session_id)
                chat_history = []
                if memory:
                    memory.chat_memory.add_user_message(question)
                    memory.chat_memory.add_ai_message(general_response)
                    chat_history = [str(msg) for msg in memory.chat_memory.messages]
                
                return {
                    "answer": self.format_response(general_response),
                    "raw_answer": general_response,
                    "chat_history": chat_history,
                    "status": "answered",
                    "session_id": session_id
                }, 200

            # Get conversation chain for this session
            chat_chain = self.get_conversation_chain(session_id)
            
            # Get response with timeout handling and retry logic
            @retry_with_exponential_backoff(max_retries=3, base_delay=2)
            def call_ai_chain():
                # Use invoke method instead of deprecated __call__
                try:
                    return chat_chain.invoke({"question": question})
                except AttributeError:
                    # Fallback to old method if invoke doesn't exist
                    return chat_chain({"question": question})
            
            try:
                result = call_ai_chain()
                answer = result["answer"].strip()
                
            except TimeoutError:
                print("AI processing timed out")
                return {
                    "error": "The AI service is taking longer than expected. Please try again with a shorter question.",
                    "user_friendly_error": True,
                    "session_id": session_id
                }, 408  # Request Timeout
            except Exception as ai_error:
                print(f"AI processing error: {str(ai_error)}")
                error_str = str(ai_error).lower()
                
                if "quota" in error_str or "rate limit" in error_str:
                    return {
                        "error": "AI service is currently at capacity. Please try again in a few moments.",
                        "user_friendly_error": True,
                        "session_id": session_id
                    }, 429  # Too Many Requests
                elif "504" in error_str or "deadline exceeded" in error_str or "timeout" in error_str:
                    return {
                        "error": "The AI service is taking longer than expected to process your query. Please try again with a simpler question or wait a moment and retry.",
                        "user_friendly_error": True,
                        "session_id": session_id
                    }, 408  # Request Timeout
                elif "embedding" in error_str:
                    return {
                        "error": "There was an issue processing your query for search. Please try rephrasing your question or try again later.",
                        "user_friendly_error": True,
                        "session_id": session_id
                    }, 503  # Service Unavailable
                raise ai_error
            
            print("\nGenerated answer:", answer)
            print("="*50 + "\n")
            
            # Check for various forms of "no answer" responses
            no_answer_phrases = [
                "i do not know",
                "i don't know",
                "cannot find",
                "no information",
                "insufficient information",
                "the document does not contain",
                "no relevant information",
                "cannot answer",
                "unable to answer"
            ]
            
            if any(phrase in answer.lower() for phrase in no_answer_phrases):
                print("No answer found - adding to unanswered queries")
                
                # Store unanswered query
                self.query_model.create_query(question, user_id, answered=False)
                
                return {
                    "answer": "I apologize, but I don't have enough information to answer this question accurately. Your query has been logged for manual review.",
                    "status": "unanswered",
                    "session_id": session_id
                }, 404
            
            # Store chat history if user is logged in and query was answered
            if user_id and "i do not know" not in answer.lower():
                try:
                    self.chat_history_model.create_chat(user_id, question, answer)
                except Exception as e:
                    print(f"Error storing chat history: {str(e)}")
            
            # Get chat history for this session
            memory = conversation_memories.get(session_id)
            chat_history = []
            if memory:
                chat_history = [str(msg) for msg in memory.chat_memory.messages]
            
            # Format the response
            formatted_answer = self.format_response(answer)
            
            return {
                "answer": formatted_answer,
                "raw_answer": answer,
                "chat_history": chat_history,
                "status": "answered",
                "session_id": session_id
            }, 200
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print("\nError:", error_msg)
            print("="*50 + "\n")
            
            # Check if this is a timeout error from the embedding service
            if "504 Deadline Exceeded" in str(e) or "Error embedding content" in str(e):
                return {
                    "error": "The AI service is currently experiencing high demand. Please try again in a few moments.",
                    "user_friendly_error": True,
                    "session_id": session_id
                }, 503  # Service Unavailable
            
            return {
                "error": error_msg,
                "session_id": session_id
            }, 500
    
    def add_response_to_query(self, query_id, response):
        """Add admin response to unanswered query"""
        try:
            # Get the question from the database
            query_doc = self.query_model.find_by_id(query_id)
            if not query_doc:
                return {"error": "Query not found"}, 404
            
            # Update database
            self.query_model.update_query(query_id, response)
            
            # Append to PDF and update vectorstore
            from utils.pdf_utils import append_to_pdf
            success = append_to_pdf(query_doc["question"], response)
            
            # Intentionally skip vectorstore update after admin answers
            # The vectorstore should be updated only manually through the admin dashboard
            # if success:
            #     try:
            #         # Call update_vectorstore with correct parameters - question and answer only
            #         update_vectorstore(question=query_doc["question"], answer=response)
            #     except Exception as e:
            #         print(f"Error updating vectorstore: {str(e)}")
            
            # Send email notification if user exists
            user_id = query_doc.get("user_id")
            if user_id:
                try:
                    from flask import current_app
                    print("trying to mail")
                    email_service = current_app.config.get('EMAIL_SERVICE')
                    if email_service:
                        email_service.send_query_response_notification(user_id, query_doc["question"], response)
                    else:
                        print("Email service not found in app config")
                except Exception as e:
                    print(f"Error sending email: {str(e)}")
            
            return {"message": "Response added successfully"}, 200
            
        except Exception as e:
            return {"error": f"Failed to add response: {str(e)}"}, 500
