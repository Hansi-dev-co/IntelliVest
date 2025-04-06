import os
import io
from fastapi import FastAPI, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import aiplatform
import pandas as pd
from typing import Optional
from pydantic import BaseModel
import requests  # To fetch data from Google Finance

# Load environment variables
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "asia-south1")  # Changed to India region (Mumbai)
NEWS_DATA_SOURCE = os.environ.get("NEWS_DATA_SOURCE", "https://www.google.com/finance/?hl=en")  

# Initialize Vertex AI
aiplatform.init(project=PROJECT_ID, location=REGION)

# FastAPI app
app = FastAPI()

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins.  In a production app, restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for Question
class QuestionRequest(BaseModel):
    question: str


def fetch_google_finance_csv(ticker: str) -> str:
    """
    Fetches a simplified CSV of portfolio data from Google Finance for a single ticker.

    Args:
        ticker (str): The stock ticker symbol (e.g., "AAPL").

    Returns:
        str: A CSV string containing price and shares, or an empty string on error.
    """
    # Construct a simplified URL.  Google Finance doesn't provide shares, so mock 1 share.
    url = f"https://www.google.com/finance/quote/{ticker}" # simplified URL.

    try:
        # Fetch the content from Google Finance
        response = requests.get(url, timeout=5)  # Short timeout for MVP
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Mock the CSV data.  In a real scenario, you'd extract from the HTML.
        # This is extremely basic and prone to breaking if Google Finance changes its layout.
        # Extracting the price is the most challenging part here.
        price_str = response.text.split('data-last-price="')[1].split('"')[0]
        price = float(price_str.replace(",", "")) # Remove the ','
        csv_data = f"Stock,Shares,Price\n{ticker},1,{price:.2f}"
        return csv_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Google Finance for {ticker}: {e}")
        return ""  # Return empty string on error, handle in main function
    except IndexError:
        print(f"Error parsing price from Google Finance for {ticker}")
        return ""
    except ValueError:
        print(f"Error converting price to float from Google Finance for {ticker}")
        return ""

# 1. Stock Summary Endpoint
@app.get("/summary/{ticker}")
async def get_stock_summary(ticker: str):
    """
    Fetches stock data from Google Finance and generates a summary using Vertex AI's Gemini.

    Args:
        ticker (str): The stock ticker symbol (e.g., AAPL).

    Returns:
        dict: A dictionary containing the summary.

    Raises:
        HTTPException: If there's an error fetching data or generating the summary.
    """
    try:
        # 1. Fetch stock data from Google Finance CSV
        csv_data = fetch_google_finance_csv(ticker)
        if not csv_data:
            raise HTTPException(
                status_code=404, detail=f"Could not retrieve stock data for '{ticker}' from Google Finance."
            )

        # 1.1.  Parse the CSV data using pandas
        df = pd.read_csv(io.StringIO(csv_data))
        price = df['Price'][0] # Get price from dataframe.
        # 2. Prepare prompt for Gemini
        prompt = f"""
        Summarize the following financial data for a novice investor in three concise sentences.
        Do not use technical jargon. Include the company name, and current price.
        
        Current Price: ${price:.2f}
        """

        # 3. Call Vertex AI Gemini
        response = aiplatform.preview.get_PaLM2_model_response(prompt=prompt)
        gemini_summary = response.text

        return {"summary": gemini_summary}

    except HTTPException as e:
        raise e # Re-raise HTTPExceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {e}")



# 2. Educational Q&A Endpoint
@app.post("/question")
async def ask_question(request: QuestionRequest):
    """
    Answers a user's financial question using Vertex AI's Gemini.

    Args:
        request (QuestionRequest): The user's question.

    Returns:
        dict: A dictionary containing the answer.

    Raises:
        HTTPException: If there's an error generating the answer.
    """
    try:
        question = request.question
        # 1.  Prompt the LLM
        prompt = f"""
        Answer the following financial question in simple terms for a novice investor. Avoid jargon.
        Question: {question}
        """
        # 2. Call Vertex AI Gemini
        response = aiplatform.preview.get_PaLM2_model_response(prompt=prompt)
        gemini_answer = response.text

        return {"answer": gemini_answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {e}")



# 3. Portfolio Analysis Endpoint
@app.post("/portfolio/analyze")
async def analyze_portfolio(csvData: str = Form(...)):
    """
    Analyzes a simplified portfolio from a CSV file. Uses Gemini to provide a basic overview.

    Args:
        csvData (str): The portfolio data in CSV format.

    Returns:
        dict: A dictionary containing the portfolio analysis.

    Raises:
        HTTPException: If there's an error processing the CSV data or generating the analysis.
    """
    try:
        # 1.  Process the CSV data using pandas
        df = pd.read_csv(io.StringIO(csvData))
        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

        # Basic portfolio analysis (for MVP -  extend this in future)
        total_value = (df['Shares'] * df['Price']).sum()  # <-- Assumes 'Shares' and 'Price' columns
        top_holdings = df.nlargest(3, 'Shares')  # Changed from Value
        num_holdings = len(df)

        # Format top holdings for the prompt
        top_holdings_str = ""
        for index, row in top_holdings.iterrows():
            top_holdings_str += f"{row['Stock']}: {row['Shares']} shares, "
        top_holdings_str = top_holdings_str.rstrip(', ') # remove trailing comma

        # 2.  Prepare prompt for Gemini
        prompt = f"""
        Here is a simplified portfolio:

        {df.to_string()}

        Provide a brief overview for a novice investor. Include:
        - Total portfolio value: ${total_value:.2f}.
        - Top holdings (ticker symbols and shares): {top_holdings_str}.
        - The number of holdings: {num_holdings}.

        Do NOT give specific investment advice.  Do not mention columns that are not in the data.
        """

        # 3. Call Vertex AI Gemini
        response = aiplatform.preview.get_PaLM2_model_response(prompt=prompt)
        gemini_analysis = response.text

        return {"analysis": gemini_analysis}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing portfolio: {e}")



# 4. News and Filings Endpoint
@app.get("/news/{ticker}")
async def get_news_and_filings(ticker: str):
    """
    Fetches news and filings for a company using Vertex AI and a mock source.

    Args:
        ticker (str): The ticker symbol of the company.

    Returns:
        dict: A dictionary containing summarized news and filings.

    Raises:
        HTTPException: If there's an error fetching or summarizing the information.
    """
    try:
        # 1.  Mock News (for MVP).  Replace with actual news retrieval.
        mock_news = {
            "AAPL": [
                "Apple's Q1 earnings exceed expectations.",
                "Apple announces new product launch.",
            ],
            "GOOG": [
                "Google announces new AI initiatives.",
                "Google faces regulatory scrutiny.",
            ],
            "MSFT": [
                "Microsoft releases new software version.",
                "Microsoft's cloud business is growing.",
            ],
            "RELIANCE.NS": [
                "Reliance Industries announces new investment.",
                "Reliance reports quarterly profits.",
            ],
            "INFY.NS": [
                "Infosys wins a major contract.",
                "Infosys expands its operations.",
            ]
        }
        # 2.  Prepare prompt for Gemini
        prompt = f"""
        Summarize the following news articles for {ticker} in three concise sentences for an investor.
        Do not include information that is not in the articles.

        News:
        {mock_news.get(ticker.upper(), [])}
        """

        # 3. Call Vertex AI Gemini
        response = aiplatform.preview.get_PaLM2_model_response(prompt=prompt)
        gemini_summary = response.text

        return {"summary": gemini_summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news and filings: {e}")