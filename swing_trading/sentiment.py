import requests
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# ==============================================================================
# SENTIMENT ANALYSIS ENGINE
# ==============================================================================

class SentimentEngine:
    """
    A dedicated engine for fetching real-time news data and analyzing its sentiment.
    """
    def __init__(self):
        """
        Initializes the sentiment analyzer.
        """
        # Ensure VADER lexicon is available
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except nltk.downloader.DownloadError:
            print("Downloading VADER lexicon for sentiment analysis...")
            nltk.download('vader_lexicon')
        
        self.analyzer = SentimentIntensityAnalyzer()
        self.news_api_url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN&categories=BTC"

    def get_live_news(self):
        """
        Fetches the latest news headlines for Bitcoin from a live API.
        In a production system, you'd add more sources (Reddit, Twitter, etc.)
        """
        print("Fetching live news headlines from CryptoCompare...")
        try:
            response = requests.get(self.news_api_url)
            response.raise_for_status()  # Raise an exception for bad status codes
            news_data = response.json()
            
            # Extract just the titles for analysis
            headlines = [article['title'] for article in news_data.get('Data', [])]
            if not headlines:
                print("Warning: No news headlines were returned from the API.")
            return headlines
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news data: {e}")
            return [] # Return an empty list on error

    def analyze_sentiment(self):
        """
        Analyzes the sentiment of fetched headlines and returns an aggregate score.
        Score > 0.05 is Positive
        Score < -0.05 is Negative
        Otherwise, Neutral
        """
        headlines = self.get_live_news()
        if not headlines:
            print("No headlines to analyze. Defaulting to NEUTRAL sentiment.")
            return 'neutral'

        sentiment_scores = [self.analyzer.polarity_scores(h)['compound'] for h in headlines]
        avg_score = sum(sentiment_scores) / len(sentiment_scores)
        
        print(f"Analyzed {len(headlines)} headlines.")
        print(f"Average sentiment score: {avg_score:.4f}")

        if avg_score > 0.05:
            print("Sentiment: POSITIVE")
            return 'positive'
        elif avg_score < -0.05:
            print("Sentiment: NEGATIVE")
            return 'negative'
        else:
            print("Sentiment: NEUTRAL")
            return 'neutral'

# Helper function to be called from our main application
def get_current_market_sentiment():
    """
    Main function to instantiate and run the sentiment engine.
    """
    engine = SentimentEngine()
    return engine.analyze_sentiment()

if __name__ == '__main__':
    # This allows you to run this file directly to test the sentiment engine
    print("Testing the Sentiment Engine independently...")
    sentiment = get_current_market_sentiment()
    print(f"\nFinal determined sentiment: {sentiment}")
