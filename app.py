from flask import Flask, request, jsonify, render_template
import ast
import os
from dotenv import load_dotenv
from google import genai 

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

# Securely fetch the API key
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# --- Robust AST Logic (Python Only) ---
def analyze_ast(code):
    features = {"loops": 0, "conditions": 0, "functions": 0, "syntax_error": None}
    bugs = []
    
    try:
        # This will only succeed if the code is valid Python
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)): features["loops"] += 1
            if isinstance(node, ast.If): features["conditions"] += 1
            if isinstance(node, ast.FunctionDef): features["functions"] += 1
            
            # Detect Division by Zero using AST
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    bugs.append("Logic Error: Division by zero detected.")
    except SyntaxError:
        # Silently ignore syntax errors so we don't flag non-Python languages as broken.
        features["syntax_error"] = "Code could not be parsed as Python. Skipping local AST check."
        
    return features, bugs

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    code = data.get("code", "")
    profile = data.get("profile", "General Software")
    
    # 1. Run local AST analysis
    features, manual_bugs = analyze_ast(code)
    
    # 2. Universal Polyglot Prompt
    prompt = f"""Act as a senior polyglot developer specializing in {profile}. 
    Analyze the provided code for bugs, logic errors, and vulnerabilities. 
    First, explicitly identify the programming language. Then, explain the issues and provide a short, optimized version. 
    
    CRITICAL INSTRUCTION: You must wrap all optimized code in standard markdown format with the correct language identifier tag (e.g., ```python, ```javascript, ```c, ```verilog, etc.).
    
    Code to analyze:
    {code}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        ai_suggestion = response.text
    except Exception as e:
        ai_suggestion = f"AI analysis error: {str(e)}"

    return jsonify({
        "features": features,
        "bugs": manual_bugs,
        "ai_analysis": ai_suggestion
    })

if __name__ == "__main__":
    app.run(debug=True)