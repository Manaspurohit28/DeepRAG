from flask import Flask, request, render_template, jsonify
import fitz  # PyMuPDF
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.models import OllamaModel
from test_llm import get_ollama_response
from rag_app import create_rag_chain

app = Flask(__name__)
chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    pdf_bytes = file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    context = "".join(page.get_text() for page in doc)
    return jsonify({"context": context})

def parse_qa(text: str):
    qas, q, a = [], None, None
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("question"):
            if q and a:
                qas.append((q, a))
            q, a = line.split(":", 1)[1].strip(), None
        elif line.lower().startswith("answer"):
            a = line.split(":", 1)[1].strip()
    if q and a:
        qas.append((q, a))
    return qas

@app.route("/generate_qa", methods=["POST"])
def generate_qa():
    context = request.json.get("context")
    count = request.json.get("count", 0)

    if not context:
        return jsonify({"error": "Missing context"}), 400

    prompt = f"""
    You are an expert Question-Answer generation assistant.
    Your task is to generate exactly {count} high-quality, factual QA pairs based only on the document provided below.
    Document:
    \"\"\"{context}\"\"\"

    Please strictly follow this format (without any extra text):
    Question 1: <your question>
    Answer 1: <your answer>

    ... and so on, up to {count} pairs only.

    Do NOT include any introduction, summary, or explanation — only the QA pairs in the specified format.
    """
    
    qa_text = get_ollama_response(prompt)
    return jsonify({"qa_pairs": parse_qa(qa_text)})

@app.route("/evaluate", methods=["POST"])
def evaluate():
    data = request.json
    context = data.get("context")
    qa_pairs = data.get("qa_pairs")

    if not context or not qa_pairs:
        return jsonify({"error": "Missing context or qa_pairs"}), 400

    rag_chain = create_rag_chain(context)
    metric = AnswerRelevancyMetric(
        model=OllamaModel(model="devstral_sd", base_url="http://10.0.7.190:8082"),
        threshold=0.7,
    )

    results = []
    for question, llm_answer in qa_pairs:
        rag_answer = rag_chain.run(question)
        tc = LLMTestCase(
            input=question,
            expected_output=rag_answer,
            actual_output=llm_answer,
            context=[context],
        )
        score = metric.measure(tc)
        results.append({
            "question": question,
            "rag_answer": rag_answer,
            "llm_answer": llm_answer,
            "score": round(score, 2),
            "pass": "Pass" if score >= metric.threshold else "Fail",
        })

    return jsonify({"results": results})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("message")
    context = data.get("context")

    if not question or not context:
        return jsonify({"error": "Missing message or context"}), 400

    rag_chain = create_rag_chain(context)
    rag_response = rag_chain.run(question)
    llm_response = get_ollama_response(question)

    chat_history.extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": rag_response},
    ])
    return jsonify({
    "response": rag_response,           # Show RAG answer in chat
    "rag_answer": rag_response,
    "llm_answer": llm_response
})


if __name__ == "__main__":
    app.run(debug=True)
