import praw
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent=os.getenv('REDDIT_USER_AGENT')
)

def fetch_reddit_posts(keyword, limit=10):
    """
    Fetch Reddit posts based on a keyword.
    
    :param keyword: The search term to look for in posts
    :param limit: Maximum number of posts to fetch (default 10)
    :return: A list of dictionaries containing post information
    """
    posts = []
    for submission in reddit.subreddit('all').search(keyword, limit=limit):
        posts.append({
            'title': submission.title,
            'url': submission.url,
            'score': submission.score,
            'num_comments': submission.num_comments,
            'created_utc': submission.created_utc
        })
    return posts

if __name__ == '__main__':
    search_keyword = input("Enter a keyword to search for: ")
    results = fetch_reddit_posts(search_keyword)
    
    print(f"\nTop {len(results)} posts for '{search_keyword}':\n")
    for i, post in enumerate(results, 1):
        print(f"{i}. {post['title']}")
        print(f"   URL: {post['url']}")
        print(f"   Score: {post['score']}")
        print(f"   Comments: {post['num_comments']}")
        print()
