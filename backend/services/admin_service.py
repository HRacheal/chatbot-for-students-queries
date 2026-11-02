import logging

from models.models import ChatHistory, Query, QueryLog, User
from utils.helpers import analyze_sentiment_and_topics, format_response_data

logger = logging.getLogger(__name__)


class AdminService:
    """Service for handling admin operations"""

    def __init__(self, email_service=None, storage=None, source_registry=None, enquiry_service=None):
        self.user_model = User()
        self.query_model = Query()
        self.chat_history_model = ChatHistory()
        self.query_log = QueryLog()
        self.enquiry_service = enquiry_service
        self.email_service = email_service
        self.storage = storage
        self.source_registry = source_registry

    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        queries = self.query_log.summary()
        stats = {
            "total_users": self.user_model.get_total_users(),
            "total_chats": self.chat_history_model.get_total_chats(),
            "unanswered_queries": self.query_model.get_unanswered_count(),
            "total_queries": queries["total"],
            "queries_by_status": queries["by_status"],
            "queries_by_department": queries["by_department"],
        }
        if self.enquiry_service is not None:
            enquiries = self.enquiry_service.stats()
            stats["unresolved_enquiries"] = enquiries["unresolved"]
            stats["total_enquiries"] = enquiries["total"]
            stats["enquiries_by_department"] = enquiries["by_department"]
        return stats, 200

    def get_unanswered_queries(self):
        """Get all unanswered queries"""
        unanswered = self.query_model.get_unanswered_queries()
        return {"queries": format_response_data(unanswered)}, 200

    def delete_query(self, query_id):
        """Delete a query"""
        result = self.query_model.delete_query(query_id)
        if result.deleted_count > 0:
            logger.info("Query %s deleted by admin", query_id)
            return {"message": "Query deleted successfully"}, 200
        return {"error": "Query not found"}, 404

    def get_all_chat_history(self):
        """Get all chat history with user details"""
        history = self.chat_history_model.get_all_history_with_users()
        if self.source_registry is not None:
            for chat in history:
                chat["citations"] = self.source_registry.check_citations(chat.get("citations"))
        return {"history": format_response_data(history)}, 200

    def get_query_analytics(self):
        """Get query analytics including sentiment and trending topics"""
        queries = self.chat_history_model.get_all_questions_with_timestamps()
        sentiment_analytics, trending_topics = analyze_sentiment_and_topics(queries)
        return {
            "sentiment_analytics": sentiment_analytics,
            "trending_topics": trending_topics,
        }, 200

    def add_response_to_query(self, query_id, response, department="general_university"):
        """Record an admin answer, save it as a draft source and notify the user.

        The answer is always saved on the query first. It is also stored as a *draft*
        staff-answer source, which the chatbot ignores until an administrator approves
        it under Approved Sources. Draft and email steps are reported separately so a
        failure in either is visible to the admin.
        """
        query_doc = self.query_model.find_by_id(query_id)
        if not query_doc:
            return {"error": "Query not found"}, 404

        self.query_model.update_query(query_id, response)
        logger.info("Query %s answered by admin", query_id)

        draft_source_id = None
        if self.source_registry is not None:
            try:
                draft = self.source_registry.create_staff_answer(
                    query_doc["question"], response, query_id, department=department
                )
                draft_source_id = str(draft["_id"])
            except Exception as e:
                logger.error("Could not save the answer as a draft source (%s)", type(e).__name__)

        if not query_doc.get("user_id"):
            email_status = "not_applicable"
        elif not self.email_service:
            email_status = "failed"
        else:
            sent = self.email_service.send_query_response_notification(
                query_doc["user_id"], query_doc["question"], response
            )
            email_status = "sent" if sent else "failed"

        return {
            "message": "Response added successfully",
            "draft_source_created": draft_source_id is not None,
            "draft_source_id": draft_source_id,
            "email_notification": email_status,
        }, 200
