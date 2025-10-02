import os
import requests
from dotenv import load_dotenv

load_dotenv()

def generate_seo_article(topic: str, keywords: str = "", lang: str = "ru"):
    if lang == "ru":
        prompt = f"""
        Напиши информативную, уникальную и SEO-дружественную статью на тему: "{topic}".
        Используй ключевые слова: {keywords or topic}.
        Статья должна быть на русском языке, структурирована (заголовки H2, H3), содержать 500–800 слов.
        Не используй маркетинговый жаргон. Пиши как эксперт.
        """
    else:
        prompt = f"""
        Write an informative, unique, SEO-friendly article on the topic: "{topic}".
        Use keywords: {keywords or topic}.
        The article must be in English, structured with H2/H3 headings, 500–800 words.
        Do not use marketing fluff. Write as an expert.
        """

    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct:free",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"<p>Ошибка генерации: {str(e)}</p>"

    return f"<h2>{'Статья по теме' if lang == 'ru' else 'Article about'}: {topic}</h2><p>AI-контент будет здесь после настройки API.</p>"
