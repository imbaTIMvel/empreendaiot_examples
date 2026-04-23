from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": "Bearer SUA-CHAVE-AQUI", # INSERIR CHAVE API !!!
    "Content-Type": "application/json"
}

def query(prompt):
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        },
        timeout=10
    )

    print("Status:", response.status_code)
    print("Resposta:", response.text)

    try:
        return response.json()
    except:
        return {"error": response.text}

@app.route("/plant")
def plant():
    name = request.args.get("name")

    prompt = f"""
    Planta: {name}
    Responda SOMENTE com JSON válido.
    Sem texto extra.
    Temperatura em graus Celsius, umidade em porcentagem e luminosidade em lux.
    Formato:
    {{
    "temp_min": number,
    "temp_max": number,
    "humidity_min": number,
    "humidity_max": number,
    "light_min": number
    }}
    """

    result = query(prompt)

    try:
        text = result["choices"][0]["message"]["content"]

        # Tenta extrair JSON
        start = text.find("{")
        end = text.find("}") + 1
        json_str = text[start:end]

        data = json.loads(json_str)

        return jsonify(data)
    
    except Exception as e:
        print("AI request error:", e)

        # Fallback seguro
        return jsonify({
            "temp_min": 20,
            "temp_max": 30,
            "humidity_min": 50,
            "humidity_max": 80,
            "light_min": 300
        })

app.run(host="0.0.0.0", port=5000)
