import praw
import os
import time
import sys
from dotenv import load_dotenv
from prawcore.exceptions import PrawcoreException
from pymongo import MongoClient
from datetime import datetime, timedelta
from transformers import pipeline

print("Script version: 6.1")  # Updated version number

# Load environment variables
load_dotenv()

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent=os.getenv('REDDIT_USER_AGENT')
)

# Initialize MongoDB client
mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client[os.getenv('MONGODB_DB')]
collection = db[os.getenv('MONGODB_COLLECTION')]

# Initialize sentiment analysis pipeline with a model that includes neutral sentiment
sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")

def fetch_reddit_posts(keyword):
    """
    Continuously fetch Reddit posts based on a keyword, perform sentiment analysis, and save to MongoDB.
    
    :param keyword: The search term to look for in posts
    """
    start_time = datetime.now()
    requests_made = 0
    last_fetch_time = 0
    cycle_count = 0

    while True:
        try:
            cycle_count += 1
            current_time = time.time()
            if current_time - last_fetch_time < 60:  # Wait at least 60 seconds between searches
                time_to_wait = 60 - (current_time - last_fetch_time)
                print(f"\rWaiting {time_to_wait:.2f} seconds until next fetch cycle...", end="", flush=True)
                time.sleep(time_to_wait)

            print(f"\nStarting fetch cycle {cycle_count} for '{keyword}'")
            search_results = reddit.subreddit('all').search(query=keyword, sort='new', limit=100, time_filter='hour')
            
            posts_fetched = 0
            new_posts_added = 0
            for submission in search_results:
                posts_fetched += 1
                
                # Check if post already exists in MongoDB
                existing_post = collection.find_one({'id': submission.id})
                if existing_post:
                    continue  # Skip this post if it already exists

                # Perform sentiment analysis
                sentiment_result = sentiment_pipeline(submission.title)[0]
                sentiment_label = sentiment_result['label']
                sentiment_score = sentiment_result['score']

                new_posts_added += 1
                post_data = {
                    'keyword': keyword,
                    'title': submission.title,
                    'url': submission.url,
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'created_utc': submission.created_utc,
                    'subreddit': submission.subreddit.display_name,
                    'id': submission.id,
                    'sentiment_label': sentiment_label,
                    'sentiment_score': sentiment_score
                }
                collection.insert_one(post_data)

                print(f"\rFetched new post: {submission.title[:50]}... | Sentiment: {sentiment_label}", end="", flush=True)

                requests_made += 1
                if requests_made >= 100:
                    wait_for_rate_limit(start_time)
                    start_time = datetime.now()
                    requests_made = 0

            print(f"\nCycle {cycle_count} complete. Posts fetched: {posts_fetched}, New posts added: {new_posts_added}")

            last_fetch_time = time.time()

        except PrawcoreException as e:
            print(f"\nReddit API error: {e}")
            print("Waiting for 60 seconds before retrying...")
            time.sleep(60)
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            print("Waiting for 60 seconds before retrying...")
            time.sleep(60)

def wait_for_rate_limit(start_time):
    """Wait if close to hitting the rate limit."""
    elapsed_time = datetime.now() - start_time
    if elapsed_time < timedelta(minutes=1):
        wait_time = 60 - elapsed_time.total_seconds()
        print(f"\nApproaching rate limit. Waiting for {wait_time:.2f} seconds.")
        time.sleep(wait_time)

def display_sentiment_stats():
    """Display sentiment statistics for collected posts."""
    sentiment_counts = collection.aggregate([
        {"$group": {"_id": "$sentiment_label", "count": {"$sum": 1}}}
    ])
    total = 0
    stats = {}
    for result in sentiment_counts:
        stats[result['_id']] = result['count']
        total += result['count']
    
    print("\nSentiment Statistics:")
    for sentiment, count in stats.items():
        percentage = (count / total) * 100
        print(f"{sentiment}: {count} ({percentage:.2f}%)")

if __name__ == '__main__':
    if len(sys.argv) != 2 or not sys.argv[1].startswith("keyword="):
        print("Usage: python main.py keyword=<search_term>")
        sys.exit(1)
    
    search_keyword = sys.argv[1].split("=", 1)[1]
    
    print(f"Starting continuous fetch for posts containing '{search_keyword}' with sentiment analysis.")
    print(f"Results will be saved to MongoDB. Press Ctrl+C to stop.")

    try:
        fetch_reddit_posts(search_keyword)
    except KeyboardInterrupt:
        print("\nFetching stopped by user.")
        display_sentiment_stats()
    
    print("\nScript execution ended.")