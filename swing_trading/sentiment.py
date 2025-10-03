import nltk
import requests
import pyperclip
from nltk.sentiment.vader import SentimentIntensityAnalyzer

class SentimentAnalyzer:
    """
    Analyzes market sentiment based on live crypto news headlines.
    """
    def __init__(self):
        self._download_vader_lexicon()
        self.sid = SentimentIntensityAnalyzer()
        self.news_api_url = 'https://min-api.cryptocompare.com/data/v2/news/?lang=EN&categories=BTC'

    def _download_vader_lexicon(self):
        """Downloads the VADER lexicon if not already present."""
        try:
            # Check if the lexicon is available
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            print("VADER lexicon not found. Downloading...")
            try:
                # --- FIX ---
                # Use the top-level download function and a general Exception
                nltk.download('vader_lexicon')
                # --- END FIX ---
                print("Download complete.")
            except Exception as e: # This is more robust than the specific DownloadError
                print(f"Error downloading VADER lexicon: {e}")
                print("Please check your internet connection and try again.")
                print("If the problem persists, try running this command in your terminal:")
                print("python -m nltk.downloader vader_lexicon")
                raise

    def get_current_market_sentiment(self) -> dict:
        """
        Fetches live news and returns a sentiment score.
        """
        print("Fetching live news headlines for sentiment analysis...")
        try:
            response = requests.get(self.news_api_url)
            response.raise_for_status() # Raise an exception for bad status codes
            news_data = response.json().get('Data', [])
            
            if not news_data:
                print("Warning: No news data returned from the API.")
                return {"headlines_analyzed": 0, "sentiment_score": 0.5} # Return neutral if no news

            headlines = [article['title'] for article in news_data if 'title' in article]
            self.copy_headlines_to_clipboard(headlines)
            
            if not headlines:
                print("Warning: News data was found, but it contained no headlines.")
                return {"headlines_analyzed": 0, "sentiment_score": 0.5}

            sentiment_scores = [self.sid.polarity_scores(headline)['compound'] for headline in headlines]
            
            # Average the compound scores
            average_score = sum(sentiment_scores) / len(sentiment_scores)
            
            # Normalize the score to be between 0 (most negative) and 1 (most positive)
            normalized_score = (average_score + 1) / 2
            
            print(f"Analyzed {len(headlines)} headlines. Sentiment Score: {normalized_score:.2f}")
            return {
                "headlines_analyzed": len(headlines),
                "sentiment_score": normalized_score
            }

        except requests.exceptions.RequestException as e:
            print(f"Error fetching news from API: {e}")
            return {"headlines_analyzed": 0, "sentiment_score": 0.5} # Return neutral on API failure
        except Exception as e:
            print(f"An unexpected error occurred during sentiment analysis: {e}")
            return {"headlines_analyzed": 0, "sentiment_score": 0.5}

    def copy_headlines_to_clipboard(self, headlines: list):
        """Formats and copies the fetched headlines to the system clipboard."""
        if not headlines:
            return
        
        try:
            formatted_headlines = "\n".join([f"- {h}" for h in headlines])
            pyperclip.copy(formatted_headlines)
            print("Successfully copied headlines to clipboard.")
        except pyperclip.PyperclipException as e:
            # This can happen in environments without a GUI (like some servers)
            print(f"Could not copy to clipboard: {e}")
