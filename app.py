# app.py (Final Corrected Version)

import streamlit as st
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import requests
from bs4 import BeautifulSoup
import re
import time
import io

# --- 1. SET PAGE CONFIG (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Skincare Data Analyst Tool")

# --- 2. DEFINE FUNCTIONS AND DOWNLOAD DATA ---
@st.cache_resource
def download_nltk_data():
    """Checks for and downloads required NLTK data, using the correct exception."""
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        nltk.download('vader_lexicon')
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')

# Run the download function at the start
download_nltk_data()

# --- CORE ANALYSIS FUNCTIONS ---

@st.cache_data
def analyze_product_mentions(text_data, product_list, claim_keywords, platform):
    """Analyzes text data for product mentions, sentiment, and claims."""
    sid = SentimentIntensityAnalyzer()
    product_mentions = []

    for text in text_data:
        for product in product_list:
            if re.search(r'\b' + re.escape(product.lower()) + r'\b', text.lower()):
                sentiment_score = sid.polarity_scores(text)['compound']
                if sentiment_score >= 0.05: sentiment = "Positive"
                elif sentiment_score <= -0.05: sentiment = "Negative"
                else: sentiment = "Mixed"
                
                found_claim = "General Skincare"
                for claim, keywords in claim_keywords.items():
                    if any(keyword in text.lower() for keyword in keywords):
                        found_claim = claim
                        break
                
                product_mentions.append({
                    "Product Name": product,
                    "Platform Mentioned On": platform,
                    "Most Common Use or Claim": found_claim,
                    "User Sentiment": sentiment
                })
    
    if not product_mentions: return pd.DataFrame()

    df = pd.DataFrame(product_mentions)
    summary = df.groupby(['Product Name', 'Platform Mentioned On', 'Most Common Use or Claim', 'User Sentiment']).size().reset_index(name='Approximate Number of Mentions')
    return summary.sort_values(by='Approximate Number of Mentions', ascending=False).reset_index(drop=True)

@st.cache_data
def get_trending_keywords(text_data):
    """Extracts trending keywords/phrases from text data."""
    stop_words = set(stopwords.words('english'))
    stop_words.update(['skin', 'product', 'products', 'use', 'using', 'like', 'get', 'help', 'really', 'ive', 'im', 'would', 'routine', 'feel', 'look'])
    all_words = []
    for text in text_data:
        words = [word for word in word_tokenize(text.lower()) if word.isalpha() and word not in stop_words and len(word) > 2]
        all_words.extend(words)

    bigrams = list(nltk.bigrams(all_words))
    bigram_freq = Counter(bigrams)
    
    keyword_insights = []
    for phrase, _ in bigram_freq.most_common(5):
        keyword = ' '.join(phrase)
        explanation = "High frequency in discussions suggests strong user interest or a common topic."
        if "acid" in keyword or "retin" in keyword or "niacinamide" in keyword: explanation = "Trending due to its popularity as a powerful active ingredient."
        if "sunscreen" in keyword or "spf" in keyword: explanation = "A cornerstone of skincare, consistently discussed for daily protection."
        if "dark spots" in keyword or "hyperpigmentation" in keyword: explanation = "A common concern that users are actively seeking solutions for."
        keyword_insights.append({"Trending Keyword": keyword, "Reason for Trend": explanation})
    return pd.DataFrame(keyword_insights)

@st.cache_data
def trace_manufacturer(product_name):
    """Performs a web search to find the manufacturer's official page."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    query = f"{product_name} skincare official website"
    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        link = soup.find('a', class_='result__a')
        if link and link['href']:
            clean_url = requests.utils.unquote(link['href']).split("uddg=")[-1]
            return clean_url, "Successfully found a likely official link."
        return "Not Found", "Could not automatically find a link."
    except requests.RequestException:
        return "Search Failed", "An error occurred during search."

# Helper function to convert DataFrame to Excel in memory for download
def to_excel(df_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    processed_data = output.getvalue()
    return processed_data

# --- 3. BUILD THE APP LAYOUT ---
st.title("🧪 Skincare Data Analysis Assistant")
st.markdown("""
This tool helps you analyze skincare discussions from online sources.
1.  **Configure** the product list and platform name in the sidebar.
2.  **Paste** your research data (from TikTok, Reddit, forums, etc.) into the text box.
3.  **Click 'Analyze Data'** to see the insights.
""")

# --- SIDEBAR FOR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    DEFAULT_PRODUCTS = [
        "CeraVe", "The Ordinary", "La Roche-Posay", "Paula's Choice", "SkinCeuticals",
        "Drunk Elephant", "Supergoop", "EltaMD", "Tretinoin", "Kojic Acid",
        "Azelaic Acid", "Niacinamide", "Hyaluronic Acid", "Vitamin C Serum", "Anthelios"
    ]
    
    CLAIM_KEYWORDS = {
        "Fades Dark Spots / Hyperpigmentation": ["hyperpigmentation", "dark spots", "pih", "melasma", "even tone", "brighter"],
        "Helps Acne / Breakouts": ["acne", "pimples", "breakouts", "clogged pores", "comedones"],
        "Anti-Aging / Wrinkles": ["anti-aging", "wrinkles", "fine lines", "aging", "retinol", "tretinoin"],
        "Hydration / Moisturizing": ["hydration", "dry skin", "moisture", "hydrating", "moisturizer", "plump"],
        "Sun Protection": ["sunscreen", "spf", "sun protection", "uv", "white cast"],
        "Improves Skin Texture": ["texture", "smooth", "bumpy", "keratosis pilaris", "kp", "pores"]
    }

    selected_products = st.multiselect(
        "Select products to search for:",
        options=DEFAULT_PRODUCTS,
        default=DEFAULT_PRODUCTS[:7]
    )
    
    platform_name = st.text_input(
        "Platform Mentioned On:",
        value="TikTok / Online Forums"
    )

# --- MAIN PAGE FOR INPUT AND OUTPUT ---
st.header("1. Paste Your Research Data")

default_text = """
I've been using The Ordinary's Niacinamide for a month and my pores look so much smaller! Amazing for oily skin.
Has anyone tried the La Roche-Posay Anthelios sunscreen? Worried about a white cast.
Ugh, the Drunk Elephant Vitamin C serum completely broke me out. A negative experience for me.
The CeraVe hydrating cleanser is my holy grail for dry skin. It's so gentle.
Looking for a good hyperpigmentation fix. Someone suggested Kojic Acid soap.
This tretinoin journey is tough, my skin is peeling so much but my acne is slowly getting better. It's a mixed bag.
"""
user_text = st.text_area("Each new line should be a separate comment or post.", default_text, height=250)

if st.button("🚀 Analyze Data"):
    if not user_text.strip():
        st.warning("Please paste some data into the text box before analyzing.")
    elif not selected_products:
        st.warning("Please select at least one product to search for in the sidebar.")
    else:
        with st.spinner("Analyzing your data... This may take a moment."):
            text_lines = [line.strip() for line in user_text.strip().split('\n') if line.strip()]
            
            df_summary = analyze_product_mentions(text_lines, selected_products, CLAIM_KEYWORDS, platform_name)
            df_keywords = get_trending_keywords(text_lines)
            
            manufacturer_info = []
            if not df_summary.empty:
                top_2_products = df_summary['Product Name'].unique()[:2]
                for product in top_2_products:
                    link, note = trace_manufacturer(product)
                    manufacturer_info.append({
                        "Product Name": product,
                        "Official Link (Best Guess)": link,
                        "Note": note
                    })
                    time.sleep(0.5) 
            df_manufacturer = pd.DataFrame(manufacturer_info)

            st.success("Analysis Complete!")
            
            st.header("📊 Results")

            if df_summary.empty:
                st.info("No mentions of the selected products were found in the provided text.")
            else:
                st.subheader("1. Product Mention Summary")
                st.dataframe(df_summary, use_container_width=True)

                st.subheader("2. Trend & Keyword Insights")
                st.dataframe(df_keywords, use_container_width=True)
                
                st.subheader("3. Manufacturer Info (Basic Trace)")
                st.dataframe(df_manufacturer, use_container_width=True)

                excel_data = to_excel({
                    'Product Mention Summary': df_summary,
                    'Trend & Keyword Insights': df_keywords,
                    'Manufacturer Info': df_manufacturer
                })
                
                st.download_button(
                    label="📥 Download Full Report as Excel",
                    data=excel_data,
                    file_name="Skincare_Analysis_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
