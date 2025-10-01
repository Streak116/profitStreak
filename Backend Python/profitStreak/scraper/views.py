import requests
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from django.http import JsonResponse
from langchain_groq import ChatGroq
import json
from django.views.decorators.csrf import csrf_exempt
import threading  # Added for periodic task

# Global variables for FAISS index and data
faiss_index = None
chunks_data = []
encoder = SentenceTransformer("all-mpnet-base-v2")  # Load encoder once
links = []


# Function to scrape articles, chunk them, and build the FAISS index
def initialize_index():
    global faiss_index, chunks_data
    base_url = 'https://www.moneycontrol.com/news/business/stocks/page-'
    MAX_PAGES = 5

    # Fetch article links
    for page in range(1, MAX_PAGES + 1):
        url = f"{base_url}{page}/"
        print(f"Fetching URL: {url}")
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for li in soup.find_all('li', {'id': lambda x: x and x.startswith('newslist-')}):
            link = li.find('a')['href'] if li.find('a') else None
            if link and link not in links:
                links.append(link)

    # Scrape details for each link
    for link in links:
        print(f"Scraping link: {link}")
        response = requests.get(link)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract article content
        content_div = soup.find('div', id='contentdata')
        if content_div:
            article_content = '\n'.join(
                p.get_text(strip=True) for p in content_div.find_all('p') 
                if 'Moneycontrol.com' not in p.get_text(strip=True)
            )
            chunks = split_chunks(article_content)
            chunks_data.extend(chunks)

    # Generate embeddings for all chunks
    if chunks_data:
        vectors = encoder.encode(chunks_data)
        if faiss_index is None:
            faiss_index = faiss.IndexFlatL2(vectors.shape[1])
        faiss_index.add(vectors)
    print("FAISS index initialized with data.")


# Function to split text into chunks
def split_chunks(text):
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n"],
        chunk_size=200,
        chunk_overlap=0
    )
    return splitter.split_text(text)


# Function to periodically update the FAISS index
def update_index_periodically():
    global faiss_index, chunks_data, links
    print("Starting periodic index update...")
    base_url = 'https://www.moneycontrol.com/news/business/stocks/page-'
    MAX_PAGES = 1

    new_links = []
    # Fetch new article links
    for page in range(1, MAX_PAGES + 1):
        url = f"{base_url}{page}/"
        print(f"Fetching URL for periodic update: {url}")
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for li in soup.find_all('li', {'id': lambda x: x and x.startswith('newslist-')}):
            link = li.find('a')['href'] if li.find('a') else None
            if link and link not in links:
                new_links.append(link)

    # Scrape and add new links to index
    for link in new_links:
        print(f"Scraping new link: {link}")
        response = requests.get(link)
        soup = BeautifulSoup(response.content, 'html.parser')
        content_div = soup.find('div', id='contentdata')
        if content_div:
            article_content = '\n'.join(
                p.get_text(strip=True) for p in content_div.find_all('p') 
                if 'Moneycontrol.com' not in p.get_text(strip=True)
            )
            chunks = split_chunks(article_content)
            if chunks:
                chunks_data.extend(chunks)
                vectors = encoder.encode(chunks)
                if faiss_index is None:
                    faiss_index = faiss.IndexFlatL2(vectors.shape[1])
                faiss_index.add(vectors)
                print(f"Added {len(chunks)} new chunks to the index.")

    # Append new links to the global list
    links.extend(new_links)
    print("Periodic index update complete.")

    # Schedule the next execution in 2 minutes
    threading.Timer(120, update_index_periodically).start()

# def query_ollama(model_name, prompt):
#     url = f"http://localhost:11434/api/llm/{model_name}"
#     payload = {
#         "prompt": prompt,
#         "max_tokens": 500,
#         "temperature": 0.7
#     }
#     response = requests.post(url, json=payload)
#     if response.status_code == 200:
#         return response.json().get("completion", "")
#     else:
#         raise Exception(f"Ollama API error: {response.text}")


# API to handle user queries
@csrf_exempt
def process_query(request):
    global faiss_index, chunks_data
    if faiss_index is None:
        return JsonResponse({'error': 'FAISS index not initialized.'})

    try:
        request_data = json.loads(request.body.decode('utf-8'))
        query = request_data.get('question', '')
        if not query:
            return JsonResponse({'error': 'Query cannot be empty.'})

        # Generate vector for query
        query_vector = encoder.encode([query]).reshape(1, -1)

        # Search the FAISS index
        distances, indices = faiss_index.search(query_vector, k=10)
        relevant_chunks = [chunks_data[idx] for idx in indices[0]]

        # Prepare payload for Ollama Chat API
        model_name = request.GET.get('model', 'default')
        
        print('=------------------------------------', model_name)
        
        chat_payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": """You are a financial advisor chatbot called profitStreak designed by Imran Streak. Please respond to the question with a friendly and helpful answer. If it's not about finance or investing, still reply politely and clearly. Always include: 'Disclaimer: Do your own research. We are not responsible for any losses.' at the end."""
                },
                {
                    "role": "user",
                    "content": f"""
User asked:
{query}

If it's related to finance or investing, use this context:
{relevant_chunks}

If not, respond naturally and briefly.
"""
                }
            ],
            "stream": False
        }
        
        # Send request to Ollama
        res = requests.post("http://localhost:11434/api/chat", json=chat_payload)
        res.raise_for_status()
        data = res.json()
        answer = data["message"]["content"]
        
        return JsonResponse({"response": answer})
    
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Ollama API error: {str(e)}'})
    except KeyError:
        return JsonResponse({'error': 'Unexpected Ollama response format.'})
    except Exception as e:
        return JsonResponse({'error': f'Failed to process query: {str(e)}'})




# API to handle user queries
# @csrf_exempt
# def process_query(request):
#     global faiss_index, chunks_data
#     if faiss_index is None:
#         return JsonResponse({'error': 'FAISS index not initialized.'})

#     try:
#         request_data = json.loads(request.body.decode('utf-8'))
#         query = request_data.get('question', '')
#         if not query:
#             return JsonResponse({'error': 'Query cannot be empty.'})

#         # Generate vector for query
#         query_vector = encoder.encode([query]).reshape(1, -1)

#         # Search the FAISS index
#         distances, indices = faiss_index.search(query_vector, k=10)
#         relevant_chunks = [chunks_data[idx] for idx in indices[0]]

#         # Pass the chunks to LLM
#         llm = ChatGroq(
#             temperature=1.0,
#             max_tokens=1000,
#             groq_api_key='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',
#             model_name='llama3-70b-8192',
#         )
        
#         print('Query:', query)
#         print('Relevant Chunks:', relevant_chunks)
#         prompt = f'''
# You are a financial advisor chatbot called profitStreak designed by Imran Streak. Please respond to the question with a friendly and helpful answer. The user asked:
# {query}

# if the question is not related finance or investment, respond with a good friendly answer to the question, while keeping the answer natural, short, and easy to understand.
# else if the question is related finance or investment, respond with a detailed response based on the following data:
# {relevant_chunks}

# If the question does not relate to the data, respond as a financial advisor with friendly relevant answer to the question, while keeping the answer natural, short, and easy to understand.

# Ensure your response is clear, accurate, and concise, focusing on insights directly related to the data provided. Keep the answer between 100-150 words, offering actionable advice based on the details, metrics, and insights.

# Please also include a short disclaimer at the last line: "Disclaimer: Do your own research. We are not responsible for any losses."
# '''
#         response = query_ollama("llama3", prompt)
#         return JsonResponse({"response": response.content})

#     except Exception as e:
#         return JsonResponse({'error': f'Failed to process query: {str(e)}'})

# Initialize index when server starts
initialize_index()

# Start periodic updates
update_index_periodically()
