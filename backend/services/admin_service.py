from models.models import User, Query, ChatHistory
from utils.helpers import analyze_sentiment_and_topics, format_response_data

class AdminService:
    """Service for handling admin operations"""
    
    def __init__(self, email_service=None):
        self.user_model = User()
        self.query_model = Query()
        self.chat_history_model = ChatHistory()
        self.email_service = email_service
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        try:
            
            stats = {
                "total_users": self.user_model.get_total_users(),
                "total_chats": self.chat_history_model.get_total_chats(),
                "unanswered_queries": self.query_model.get_unanswered_count()
            }
            return stats, 200
        except Exception as e:
            return {"error": f"Failed to fetch stats: {str(e)}"}, 500
    
    def get_unanswered_queries(self):
        """Get all unanswered queries"""
        try:
            # print("=== ADMIN SERVICE: get_unanswered_queries called ===")
            unanswered = self.query_model.get_unanswered_queries()
            # print(f"=== ADMIN SERVICE: Found {len(unanswered)} unanswered queries ===")
            
            # Debug: Check if there are any queries at all
            total_queries = list(self.query_model.collection.find({}))
            # print(f"=== ADMIN SERVICE: Total queries in DB: {len(total_queries)} ===")
            
            # if len(total_queries) > 0:
            #     print(f"=== ADMIN SERVICE: Sample query: {total_queries[0]} ===")
            
            formatted_queries = format_response_data(unanswered)
            result = {"queries": formatted_queries}
            # print(f"=== ADMIN SERVICE: Returning result: {result} ===")
            return result, 200
        except Exception as e:
            print(f"=== ADMIN SERVICE ERROR: {str(e)} ===")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to fetch queries: {str(e)}"}, 500
    
    def delete_query(self, query_id):
        """Delete a query"""
        try:
            result = self.query_model.delete_query(query_id)
            if result.deleted_count > 0:
                return {"message": "Query deleted successfully"}, 200
            return {"error": "Query not found"}, 404
        except Exception as e:
            return {"error": f"Failed to delete query: {str(e)}"}, 500
    
    def get_all_chat_history(self):
        """Get all chat history with user details"""
        try:
            history = self.chat_history_model.get_all_history_with_users()
            formatted_history = format_response_data(history)
            return {"history": formatted_history}, 200
        except Exception as e:
            return {"error": f"Failed to fetch chat history: {str(e)}"}, 500
    
    def get_query_analytics(self):
        """Get query analytics including sentiment and trending topics"""
        try:
            # Get all questions with timestamps for analytics
            queries = self.chat_history_model.get_all_questions_with_timestamps()
            
            # Analyze sentiment and topics
            sentiment_analytics, trending_topics = analyze_sentiment_and_topics(queries)
            
            return {
                "sentiment_analytics": sentiment_analytics,
                "trending_topics": trending_topics
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to generate analytics: {str(e)}"}, 500
    
    def add_response_to_query(self, query_id, response):
        """Add admin response to unanswered query"""
        try:
            # Get the question from the database
            query_doc = self.query_model.find_by_id(query_id)
            if not query_doc:
                return {"error": "Query not found"}, 404
            
            # Update database
            result = self.query_model.update_query(query_id, response)
            
            # Append to Cloudinary PDF (without creating embeddings automatically)
            from utils.pdf_utils import append_to_pdf
            success = append_to_pdf(query_doc["question"], response)
            
            if success:
                print(f"Added Q&A to Cloudinary PDF: {query_doc['question']} -> {response}")
                print(f"Note: Embeddings are not created automatically. Use 'Rebuild Embeddings' in admin dashboard.")
            else:
                print(f"Failed to add Q&A to Cloudinary PDF")
                # Return successful anyway since the database was updated
                # We don't want to fail the whole request just because the PDF update failed
            
            # Send email notification if user exists
            user_id = query_doc.get("user_id")
            if user_id:
                try:
                    print("trying to mail")
                    if self.email_service and self.email_service.mail:
                        result_email = self.email_service.send_query_response_notification(user_id, query_doc["question"], response)
                    else:
                       
                        
                        # Fallback: try to get from Flask app context
                        try:
                            from flask import current_app
                            email_service = current_app.config.get('EMAIL_SERVICE')
                            if email_service and email_service.mail:
                                result_email = email_service.send_query_response_notification(user_id, query_doc["question"], response)
                                if result_email:
                                    print("Email notification sent successfully (fallback)")
                                else:
                                    print("Failed to send email notification (fallback)")
                            else:
                                print("Fallback email service also not available")
                        except Exception as fallback_error:
                            print(f"Fallback email error: {str(fallback_error)}")
                            
                except Exception as e:
                    print(f"Error sending email: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            return {"message": "Response added successfully"}, 200
            
        except Exception as e:
            return {"error": f"Failed to add response: {str(e)}"}, 500
