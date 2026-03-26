import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai
from groq import Groq
import PyPDF2

app = Flask(__name__)

KAPSO_API_KEY = os.environ.get("a")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def extract_pdf_text(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text()
    return text

def find_pdf(message):
    ramos_dir = "ramos"
    message = message.lower()
    for filename in os.listdir(ramos_dir):
        name = filename.replace(".pdf", "").replace("_", " ")
        parts = name.split(" s")
        if len(parts) == 2:
            ramo = parts[0]
            seccion = parts[1]
            if ramo in message and seccion in message:
                return os.path.join(ramos_dir, filename)
    return None

def send_whatsapp(phone, message, conversation_id):
    url = f"https://api.kapso.ai/v1/conversations/{conversation_id}/messages"
    headers = {
        "Authorization": f"Bearer {KAPSO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"content": message}
    requests.post(url, json=payload, headers=headers)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received:", data)
    
    try:
        message = data["message"]["content"]
        phone = data["conversation"]["contact"]["phone"]
        conversation_id = data["conversation"]["id"]
        
        pdf_path = find_pdf(message)
        
        if not pdf_path:
            reply = "No encontré el programa de ese ramo. Escríbeme el nombre y sección, por ejemplo: *calculo seccion 3*"
        else:
            pdf_text = extract_pdf_text(pdf_path)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": f"Eres AcadBot, asistente académico universitario. Responde preguntas sobre el programa del ramo usando solo esta información:\n\n{pdf_text}"},
                    {"role": "user", "content": message}
                ]
            )
            reply = response.choices[0].message.content
        
        send_whatsapp(phone, reply, conversation_id)
        return jsonify({"status": "ok"})
    
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
