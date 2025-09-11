import praw
import pandas as pd
import requests
import uuid
from datetime import datetime, timezone
import json
import streamlit as st
import time
import os

class RedditDataExtractor:
    def __init__(self):

        self.reddit = praw.Reddit(
            client_id=st.secrets.get("iG9C35PhDmFPaObXbS2cvcRhnETVUA"),
            client_secret=st.secrets.get("tt78RM7C0r9aknY1ocVVMA"),
            user_agent=st.secrets.get("web:reddit_data_extractor:v1.0 (by u/EastSlide9495)")
        )

    def fetch_posts_from_subreddit(self, subreddit_name, limit=50, sort_by='hot'):
        """
        Fetch posts from a specific subreddit
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            if sort_by == 'hot':
                posts = subreddit.hot(limit=limit)
            elif sort_by == 'new':
                posts = subreddit.new(limit=limit)
            elif sort_by == 'top':
                posts = subreddit.top(limit=limit)
            else:
                posts = subreddit.hot(limit=limit)

            return posts
        except Exception as e:
            st.error(f"Error fetching from {subreddit_name}: {str(e)}")
            return []

    def process_post(self, post, subreddit_name):
        """
        Process a single post and extract relevant information
        """
        try:
            # Extract text content
            text_content = f"{post.title}\n\n{post.selftext}" if post.selftext else post.title

            # Create record
            record = {
                "id": post.id,
                "source": "reddit",
                "author": post.author.name if post.author else "unknown",
                "timestamp": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                "text": text_content,
                "metadata": {
                    "subreddit": subreddit_name,
                    "language": "en",  # Assuming English by default
                    "likes": post.score,
                    "rating": None,
                    "url": f"https://www.reddit.com{post.permalink}"
                }
            }
            return record
        except Exception as e:
            st.warning(f"Error processing post {post.id}: {str(e)}")
            return None

    def fetch_multiple_subreddits(self, subreddits, limit=50, sort_by='hot', filename="reddit_posts.csv"):
        """
        Fetch posts from multiple subreddits and save to CSV
        """
        all_posts = []

        for subreddit_name in subreddits:
            st.info(f"Fetching from r/{subreddit_name}...")

            posts = self.fetch_posts_from_subreddit(subreddit_name, limit, sort_by)

            for post in posts:
                processed_post = self.process_post(post, subreddit_name)
                if processed_post:
                    all_posts.append(processed_post)

            # Add a small delay to respect API rate limits
            time.sleep(1)

        # Convert to DataFrame and save
        if all_posts:
            df = pd.json_normalize(all_posts)
            df.to_csv(filename, index=False, encoding="utf-8")
            st.success(f"Saved {len(all_posts)} posts from {len(subreddits)} subreddits to {filename}")
            return df
        else:
            st.error("No posts were fetched.")
            return pd.DataFrame()

    def export_to_json(self, df, filename="output_data.json"):
        """
        Export data to JSON format
        """
        if not df.empty:
            # Convert DataFrame to list of dictionaries
            records = df.to_dict('records')

            # Save to JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)

            st.success(f"Data exported to {filename}")
            return True
        return False


# Streamlit UI Application
def main():
    st.set_page_config(page_title="Reddit Data Extractor", page_icon="📊", layout="wide")

    st.title("📊 Reddit Data Extraction Platform")
    st.markdown("Extract text data from Reddit subreddits efficiently")

    # Initialize extractor
    if 'extractor' not in st.session_state:
        st.session_state.extractor = RedditDataExtractor()

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # Subreddit input
        subreddits_input = st.text_input(
            "Subreddits (comma-separated)",
            value="machinelearning, datascience, artificial",
            help="Enter subreddit names separated by commas"
        )

        # Parameters
        limit = st.slider("Posts per subreddit", min_value=10, max_value=100, value=50)
        sort_by = st.selectbox("Sort by", options=['hot', 'new', 'top'], index=0)

        # File naming
        csv_filename = st.text_input("CSV Filename", value="reddit_posts.csv")
        json_filename = st.text_input("JSON Filename", value="output_data.json")

        # Action buttons
        fetch_button = st.button("🚀 Fetch Data")
        export_json_button = st.button("💾 Export to JSON")

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Data Preview")

        if fetch_button:
            # Process subreddits input
            subreddits = [sub.strip() for sub in subreddits_input.split(",") if sub.strip()]

            if subreddits:
                with st.spinner("Fetching data from Reddit..."):
                    df = st.session_state.extractor.fetch_multiple_subreddits(
                        subreddits, limit, sort_by, csv_filename
                    )

                if not df.empty:
                    st.dataframe(df.head(10))

                    # Show statistics
                    st.subheader("Statistics")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Posts", len(df))
                    with col2:
                        st.metric("Subreddits", df['metadata.subreddit'].nunique())
                    with col3:
                        st.metric("Average Likes", round(df['metadata.likes'].mean(), 1))

                    # Store DataFrame in session state
                    st.session_state.df = df
                else:
                    st.warning("No data was fetched. Please check your subreddit names and try again.")
            else:
                st.error("Please enter at least one valid subreddit name.")

    with col2:
        st.header("Export Options")

        if export_json_button:
            if 'df' in st.session_state and not st.session_state.df.empty:
                success = st.session_state.extractor.export_to_json(st.session_state.df, json_filename)
                if success:
                    st.success(f"Data successfully exported to {json_filename}")

                    # Offer download button
                    with open(json_filename, "r") as file:
                        st.download_button(
                            label="Download JSON",
                            data=file,
                            file_name=json_filename,
                            mime="application/json"
                        )
            else:
                st.warning("No data available to export. Please fetch data first.")

        st.info("""
        ### Instructions:
        1. Enter subreddit names in the sidebar
        2. Adjust fetch parameters as needed
        3. Click 'Fetch Data' to retrieve posts
        4. Use 'Export to JSON' to save in JSON format
        """)

    # Additional information section
    st.divider()
    st.subheader("API Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Reddit API Endpoints:**
        - Base URL: `https://www.reddit.com`
        - Authentication: OAuth2
        - Rate Limits: ~60 requests per minute
        """)

    with col2:
        st.markdown("""
        **Data Extracted:**
        - Post ID and URL
        - Author information
        - Timestamp
        - Text content (title + body)
        - Likes/score count
        - Subreddit source
        """)

if __name__ == "__main__":
    main()
