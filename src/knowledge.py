import json
import os
import random
# spaCy imported lazily in load_spacy() to avoid startup overhead if not needed
from src.config import GEMINI_API_KEYS, PODCAST_API_KEYS
from google import genai
from src.gemini_utils import get_gemini_model, gemini_generate_content_pacing, mark_key_failed, is_key_on_cooldown

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
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
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

async def generate_quiz_with_llm(text, output_path):
    print("Using Gemini for Quiz Generation with Key Rotation...")
    
    from src.config import get_allocated_keys
    available_keys = get_allocated_keys(purpose="knowledge")
    
    if not available_keys:
        return generate_quiz_with_spacy(text, output_path)
        
    last_error = None
    for i, key in enumerate(available_keys):
        try:
            print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for Quiz...")
            client, model_name = get_gemini_model(capability="text", api_key=key)
            
            prompt = f"""
            Generate 5 multiple choice questions based on the following text.
            Return the result as a JSON array of objects with keys: question, options (list of 4 strings), answer (string).
            
            Text: {text[:3000]}
            """
            
            from src.gemini_utils import gemini_generate_content_pacing
            response = await gemini_generate_content_pacing(
                client, 
                model_name, 
                contents=prompt,
                api_key=key
            )
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            quiz_data = json.loads(response_text)
            
            if isinstance(quiz_data, dict) and "questions" in quiz_data:
                quiz_data = quiz_data["questions"]
                
            with open(output_path, 'w') as f:
                json.dump(quiz_data, f, indent=4)
            return output_path
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str:
                print(f"WARNING: Key {i+1} failed ({error_str}). Trying next...")
                continue
            else:
                break
                
    print(f"Error generating quiz with Gemini pool: {last_error}. Falling back to Spacy.")
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

async def ask_question(context, question):
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
                "model": "nvidia/nemotron-3-super-120b-a12b:free",
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
    return await ask_question_with_gemini(context, question)

async def ask_question_with_gemini(context, question):
    print(f"Asking Gemini with Key Rotation: {question}")
    
    from src.config import get_allocated_keys
    available_keys = get_allocated_keys(purpose="knowledge")
    
    if not available_keys:
        return "No API keys available for Q&A."
        
    last_error = None
    for i, key in enumerate(available_keys):
        try:
            print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for Q&A...")
            client, model_name = get_gemini_model(capability="text", api_key=key)
            
            prompt = f"""
            You are an AI assistant helping a user understand a book.
            Answer the question based ONLY on the provided context.
            Keep the answer concise (max 3 sentences).
            
            Context: {context[:10000]}...
            
            Question: {question}
            """
            
            response = await gemini_generate_content_pacing(client, model_name, contents=prompt, api_key=key)
            return response.text.strip()
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str:
                print(f"WARNING: Key {i+1} failed ({error_str}). Trying next...")
                continue
            else:
                break
                
    return f"Error with Gemini pool: {str(last_error)}"

async def suggest_questions(context):
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
                "model": "nvidia/nemotron-3-super-120b-a12b:free",
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
    return await suggest_questions_with_gemini(context)

async def suggest_questions_with_gemini(context):
    """Generates suggested questions using Gemini with key rotation and circuit breaker."""
    from src.gemini_utils import is_key_on_cooldown, mark_key_failed
    
    print("Using Gemini for Suggested Questions with Key Rotation...")
    
    from src.config import get_allocated_keys
    available_keys = get_allocated_keys(purpose="knowledge")
    
    if not available_keys:
        return ["What is the main plot?", "Who are the key characters?"]
        
    last_error = None
    for i, key in enumerate(available_keys):
        if is_key_on_cooldown(key):
            print(f"  -> Skipping Gemini Key {i+1} (on cooldown)")
            continue
            
        try:
            print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for Suggestions...")
            client, model_name = get_gemini_model(capability="text", api_key=key)
            
            prompt = f"""
            Generate 2 interesting questions a reader might ask about this book.
            Return ONLY a JSON array of strings. Example: ["Question 1?", "Question 2?"]
            
            Context: {context[:5000]}...
            """
            
            response = await gemini_generate_content_pacing(client, model_name, contents=prompt, api_key=key)
            questions = parse_json_list(response.text.strip())
            if questions:
                return questions
        except Exception as e:
            last_error = e
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                mark_key_failed(key)
            print(f"WARNING: Key {i+1} failed ({e}). Trying next...")
            continue
            
    print(f"Gemini Suggestion Error (Pool): {last_error}")
    return ["What is the plot?", "Who are the characters?"]

async def ask_question_with_gemini(text, question):
    """Asks a question using Gemini with key rotation and circuit breaker."""
    from src.gemini_utils import is_key_on_cooldown, mark_key_failed
    
    print(f"Answering question using Gemini with rotation...")
    
    available_keys = PODCAST_API_KEYS + GEMINI_API_KEYS
    available_keys = list(dict.fromkeys(available_keys))
    
    last_error = None
    for i, key in enumerate(available_keys):
        if is_key_on_cooldown(key):
            continue
            
        try:
            print(f"  -> Using Gemini Key {i+1}/{len(available_keys)} for Q&A...")
            client, model_name = get_gemini_model(capability="text", api_key=key)
            
            prompt = f"""
            Answer the following question based on the provided text.
            If the answer isn't in the text, say you don't know based on the provided context.
            
            Context: {text[:10000]}...
            
            Question: {question}
            """
            
            response = await gemini_generate_content_pacing(client, model_name, contents=prompt, api_key=key)
            return response.text
        except Exception as e:
            last_error = e
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                mark_key_failed(key)
            print(f"WARNING: Key {i+1} failed. Trying next...")
            continue
            
    return f"I'm sorry, I couldn't generate an answer right now. (All AI keys exhausted or failed). Error: {last_error}"

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
