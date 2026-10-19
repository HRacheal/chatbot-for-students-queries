from difflib import SequenceMatcher
from textblob import TextBlob
from collections import defaultdict, Counter
import datetime
import re

def similar(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Small-talk messages answered without calling the AI. A message only counts as
# small talk when the *entire* message is one of these phrases, so genuine
# questions that merely contain a greeting ("Hi, what are the entry
# requirements?") or a common word ("Is it ok to defer?") are never intercepted.
SMALL_TALK = [
    (
        {"hi", "hello", "hey", "hiya", "greetings", "good morning", "good afternoon",
         "good evening", "hi there", "hello there", "hey there"},
        "Hello! How can I help you today?",
    ),
    (
        {"bye", "goodbye", "bye bye", "see you", "see you later", "good night"},
        "Goodbye! Have a great day!",
    ),
    (
        {"thanks", "thank you", "thank you so much", "thank you very much", "thanks a lot",
         "many thanks", "appreciate it", "thx", "ok thanks", "okay thanks", "ok thank you",
         "okay thank you"},
        "You're welcome! Let me know if you need anything else.",
    ),
    (
        {"ok", "okay", "nice", "great", "good", "understood", "alright", "cool", "noted"},
        "Is there anything specific you'd like to know?",
    ),
    (
        {"how are you", "how are you doing", "how do you do", "how's it going", "hows it going"},
        "I'm functioning well, thank you! How can I assist you today?",
    ),
]
_MAX_SMALL_TALK_LENGTH = 40


def _normalise_small_talk(text):
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z' ]+", " ", text)
    return " ".join(text.split())


def is_general_chat(text):
    """Return a canned reply if the whole message is small talk, otherwise ``None``."""
    if not isinstance(text, str):
        return None
    normalised = _normalise_small_talk(text)
    if not normalised or len(normalised) > _MAX_SMALL_TALK_LENGTH:
        return None

    for phrases, response in SMALL_TALK:
        if normalised in phrases:
            return response

    # Tolerate small typos in single-word greetings ("helo", "thnks").
    if " " not in normalised and len(normalised) >= 4:
        for phrases, response in SMALL_TALK:
            for phrase in phrases:
                if " " not in phrase and len(phrase) >= 4 and similar(normalised, phrase) >= 0.85:
                    return response

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
