import json
import os
import random
# spaCy imported lazily in load_spacy() to avoid startup overhead if not needed
from src.config import GEMINI_API_KEY
import google.generativeai as genai
from src.gemini_utils import get_gemini_model

nlp = None

def get_referer():
    """Get HTTP referer URL with correct port from environment."""
    port = os.getenv("PORT", "8000")
    return f"http://localhost:{port}"

def load_spacy():
    """
    Lazily load spaCy English model for NLP tasks.
    
    Returns:
        Loaded spaCy model or None if loading fails.
    """
    global nlp
    if nlp is None:
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"Warning: Spacy load failed: {e}")
            print("Install with: python -m spacy download en_core_web_sm")
            nlp = None
    return nlp

def generate_flashcards(text, output_path="flashcards.json"):
    """
    Generates flashcards from text.
    """
    print("Generating flashcards...")
    flashcards = []
    sentences = text.split('.')
    for sentence in sentences:
        if "is a" in sentence and len(sentence) < 100:
            parts = sentence.split("is a")
            flashcards.append({
                "front": parts[0].strip(),
                "back": parts[1].strip()
            })
    
    with open(output_path, 'w') as f:
        json.dump(flashcards, f, indent=4)
    
    return output_path

def generate_quizzes(text, output_path="quiz.json"):
    """
    Generates quizzes. Uses DeepSeek if available, then Gemini, else Spacy fallback.
    """
    print("Generating quiz...")
    
    if os.getenv("DEEPSEEK_API_KEY"):
        return generate_quiz_with_deepseek(text, output_path)
    elif os.getenv("GEMINI_API_KEY"):
        return generate_quiz_with_llm(text, output_path)
    else:
        return generate_quiz_with_spacy(text, output_path)

def generate_quiz_with_deepseek(text, output_path):
    print("Using DeepSeek (via OpenRouter) for Quiz Generation...")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return generate_quiz_with_llm(text, output_path)

    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": get_referer(),
            "X-Title": "Book2Vision"
        }
        
        prompt = f"""
        Generate 5 multiple choice questions based on the following text.
        Return the result as a JSON array of objects with keys: question, options (list of 4 strings), answer (string).
        Ensure the JSON is valid and strictly follows the format.
        
        Text: {text[:3000]}
        """
        
        data = {
            "model": "deepseek/deepseek-chat", # Or specific deepseek model supported by OpenRouter
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        
        print(f"OpenRouter Suggestion Status: {response.status_code}")
        print(f"OpenRouter Suggestion Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean up response text
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
                
            quiz_data = json.loads(content)
            
            # Handle if it returns a dict with a key like "questions"
            if isinstance(quiz_data, dict) and "questions" in quiz_data:
                quiz_data = quiz_data["questions"]
                
            with open(output_path, 'w') as f:
                json.dump(quiz_data, f, indent=4)
            return output_path
        else:
            print(f"DeepSeek API Error: {response.status_code} - {response.text}")
            return generate_quiz_with_llm(text, output_path)
            
    except Exception as e:
        print(f"Error generating quiz with DeepSeek: {e}. Falling back to Gemini.")
        return generate_quiz_with_llm(text, output_path)

def generate_quiz_with_llm(text, output_path):
    print("Using Gemini for Quiz Generation...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return generate_quiz_with_spacy(text, output_path)
        
    try:
        model = get_gemini_model(capability="text", api_key=api_key)
        
        prompt = f"""
        Generate 5 multiple choice questions based on the following text.
        Return the result as a JSON array of objects with keys: question, options (list of 4 strings), answer (string).
        
        Text: {text[:3000]}
        """
        
        response = model.generate_content(prompt)
        # Clean up response text
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        quiz_data = json.loads(response_text)
        
        # Handle if it returns a dict with a key like "questions"
        if isinstance(quiz_data, dict) and "questions" in quiz_data:
            quiz_data = quiz_data["questions"]
            
        with open(output_path, 'w') as f:
            json.dump(quiz_data, f, indent=4)
        return output_path
    except Exception as e:
        print(f"Error generating quiz with Gemini: {e}. Falling back to Spacy.")
        return generate_quiz_with_spacy(text, output_path)

def generate_quiz_with_spacy(text, output_path):
    print("Using Spacy for Fill-in-the-blank Quiz...")
    nlp_model = load_spacy()
    if not nlp_model:
        print("Spacy not loaded. Cannot generate quiz.")
        return None
        
    doc = nlp_model(text)
    quiz = []
    
    # Find sentences with entities or nouns
    sentences = [sent.text.strip() for sent in doc.sents if len(sent.text) > 20 and len(sent.text) < 150]
    selected_sentences = random.sample(sentences, min(5, len(sentences)))
    
    for sent in selected_sentences:
        sent_doc = nlp_model(sent)
        # Pick a noun or entity to mask
        candidates = [token for token in sent_doc if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop]
        if candidates:
            target = random.choice(candidates)
            question = sent.replace(target.text, "______")
            quiz.append({
                "question": f"Fill in the blank: {question}",
                "options": ["(Write the answer)"],
                "answer": target.text
            })
            
    with open(output_path, 'w') as f:
        json.dump(quiz, f, indent=4)
    return output_path

def ask_question(context, question):
    """
    Answers a question based on the book context. Tries DeepSeek first, then Gemini.
    """
    # Try DeepSeek/OpenRouter first
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        print(f"Asking DeepSeek: {question}")
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": get_referer(),
                "X-Title": "Book2Vision"
            }
            
            prompt = f"""
            You are an AI assistant helping a user understand a book.
            Answer the question based ONLY on the provided context.
            Keep the answer concise (max 3 sentences).
            
            Context: {context[:10000]}...
            
            Question: {question}
            """
            
            data = {
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                print(f"OpenRouter Error: {response.status_code}. Falling back to Gemini.")
        except Exception as e:
            print(f"DeepSeek Error: {e}. Falling back to Gemini.")

    # Fallback to Gemini
    return ask_question_with_gemini(context, question)

def ask_question_with_gemini(context, question):
    print(f"Asking Gemini: {question}")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "No API keys available for Q&A."
        
    try:
        model = get_gemini_model(capability="text", api_key=api_key)
        
        prompt = f"""
        You are an AI assistant helping a user understand a book.
        Answer the question based ONLY on the provided context.
        Keep the answer concise (max 3 sentences).
        
        Context: {context[:10000]}...
        
        Question: {question}
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error with Gemini: {str(e)}"

def suggest_questions(context):
    """
    Suggests 2 interesting questions. Tries DeepSeek first, then Gemini.
    """
    print("Generating suggested questions...")
    
    # Try DeepSeek/OpenRouter
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": get_referer(),
                "X-Title": "Book2Vision"
            }
            
            prompt = f"""
            Generate 2 interesting questions a reader might ask about this book.
            Return ONLY a JSON array of strings. Example: ["Question 1?", "Question 2?"]
            
            Context: {context[:5000]}...
            """
            
            data = {
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                return parse_json_list(content)
            else:
                print(f"OpenRouter Suggestion Error: {response.status_code}. Falling back to Gemini.")
        except Exception as e:
            print(f"DeepSeek Suggestion Error: {e}. Falling back to Gemini.")

    # Fallback to Gemini
    return suggest_questions_with_gemini(context)

def suggest_questions_with_gemini(context):
    print("Using Gemini for Suggested Questions...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ["What is the plot?", "Who are the characters?"]
        
    try:
        model = get_gemini_model(capability="text", api_key=api_key)
        
        prompt = f"""
        Generate 2 interesting questions a reader might ask about this book.
        Return ONLY a JSON array of strings. Example: ["Question 1?", "Question 2?"]
        
        Context: {context[:5000]}...
        """
        
        response = model.generate_content(prompt)
        return parse_json_list(response.text.strip())
    except Exception as e:
        print(f"Gemini Suggestion Error: {e}")
        return ["What is the plot?", "Who are the characters?"]

def parse_json_list(content):
    try:
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content)
    except:
        return ["What is the plot?", "Who are the characters?"]

def generate_mindmap(text, output_path="mindmap.png"):
    """
    Generates a mindmap (placeholder).
    """
    print("Generating mindmap data...")
    # In a real app, use graphviz or similar
    return output_path
