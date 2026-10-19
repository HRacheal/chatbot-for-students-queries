from difflib import SequenceMatcher
from textblob import TextBlob
from collections import defaultdict, Counter
import datetime
import re

def similar(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def is_general_chat(text):
    """Detect if the input is general chat with improved matching"""
    general_phrases = {
        'greetings': {
            'patterns': ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening'],
            'response': 'Hello! How can I help you today?'
        },
        'farewell': {
            'patterns': ['bye', 'goodbye', 'see you', 'good night'],
            'response': 'Goodbye! Have a great day!'
        },
        'thanks': {
            'patterns': ['thanks', 'thank you', 'appreciate it', 'thx'],
            'response': 'You\'re welcome! Let me know if you need anything else.'
        },
        'acknowledgment': {
            'patterns': ['nice', 'ok', 'okay', 'great', 'good', 'understood', 'alright'],
            'response': 'Is there anything specific you\'d like to know?'
        },
        'well_being': {
            'patterns': ['how are you', 'how do you do', 'how\'s it going'],
            'response': 'I\'m functioning well, thank you! How can I assist you today?'
        }
    }
    
    text_lower = text.lower().strip()
    
    # Check for matches with word boundaries
    for category in general_phrases.values():
        for pattern in category['patterns']:
            # For single words, use word boundaries to avoid partial matches
            if ' ' not in pattern:
                # Use regex word boundary for single words
                if re.search(r'\b' + re.escape(pattern) + r'\b', text_lower):
                    return category['response']
            else:
                # For phrases, check if the entire phrase is present
                if pattern in text_lower:
                    return category['response']
            
            # Only check similarity for very short inputs (1-3 words)
            words = text_lower.split()
            if len(words) <= 3 and len(text_lower) <= 20:
                if similar(text_lower, pattern) > 0.85:
                    return category['response']
    
    # Special check for standalone greetings
    words = text_lower.split()
    if len(words) == 1 and words[0] in ['hi', 'hello', 'hey', 'bye']:
        for category in general_phrases.values():
            if words[0] in category['patterns']:
                return category['response']
    
    return None

def analyze_sentiment_and_topics(queries):
    """Analyze sentiment and extract trending topics from queries"""
    sentiment_by_date = defaultdict(list)
    word_counter = Counter()
    # A simple stopwords list – extend it as needed.
    stopwords = set(["the", "is", "at", "on", "and", "a", "an", "to", "of", "in", "i", "you", "it"])

    for record in queries:
        question = record.get("question")
        ts = record.get("timestamp")
        if not question or not ts:
            continue

        # Convert the timestamp to date string:
        if isinstance(ts, datetime.datetime):
            date_str = ts.date().isoformat()
        else:
            date_str = str(ts).split("T")[0]

        # Analyze sentiment using TextBlob
        polarity = TextBlob(question).sentiment.polarity
        sentiment_by_date[date_str].append(polarity)

        # Count words for trending topics (do a simple word count)
        for word in question.lower().split():
            # Remove non-alphanumeric characters
            word = ''.join([ch for ch in word if ch.isalnum()])
            if word and word not in stopwords:
                word_counter[word] += 1

    # Prepare sentiment analytics: average sentiment per date
    sentiment_analytics = []
    for date, polarities in sentiment_by_date.items():
        avg_sentiment = sum(polarities) / len(polarities)
        sentiment_analytics.append({
            "date": date,
            "avg_sentiment": avg_sentiment,
            "count": len(polarities)
        })

    # Get trending topics – top 5 words
    trending_topics = word_counter.most_common(5)

    return sentiment_analytics, trending_topics

def format_response_data(data, convert_object_ids=True):
    """Format response data for JSON serialization"""
    if isinstance(data, list):
        for item in data:
            if convert_object_ids and "_id" in item:
                item["_id"] = str(item["_id"])
            if "user_id" in item and item["user_id"]:
                item["user_id"] = str(item["user_id"])
            if "timestamp" in item and hasattr(item["timestamp"], "isoformat"):
                item["timestamp"] = item["timestamp"].isoformat()
    elif isinstance(data, dict):
        if convert_object_ids and "_id" in data:
            data["_id"] = str(data["_id"])
        if "user_id" in data and data["user_id"]:
            data["user_id"] = str(data["user_id"])
        if "timestamp" in data and hasattr(data["timestamp"], "isoformat"):
            data["timestamp"] = data["timestamp"].isoformat()
    
    return data
