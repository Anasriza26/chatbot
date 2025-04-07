from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect('knowledge_base.db')
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS static_responses
                 (question TEXT PRIMARY KEY, answer TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS education_facts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  topic TEXT, 
                  level TEXT, 
                  information TEXT,
                  last_updated TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS conversation_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_input TEXT,
                  bot_response TEXT,
                  timestamp TIMESTAMP,
                  feedback TEXT DEFAULT NULL)''')
    
    # Insert some static responses
    static_data = [
        ("thank you", "You're welcome! How else can I assist you with Sri Lankan education?"),
        ("hello", "Hello! How can I help you with Sri Lankan education today?"),
        ("good morning", "Good morning! Ready to explore Sri Lanka's education system?"),
        ("goodbye", "Goodbye! Feel free to return if you have more questions about Sri Lankan education."),
        ("hi", "Hi there! Ask me anything about education in Sri Lanka from Grade 1 to Graduate level."),
    ]
    
    try:
        c.executemany("INSERT OR IGNORE INTO static_responses VALUES (?, ?)", static_data)
    except:
        pass
    
    # Insert some education facts
    education_data = [
        ("primary education", "Grade 1-5", "Primary education in Sri Lanka covers Grades 1-5 and is compulsory for all children.", datetime.now()),
        ("scholarship exam", "Grade 5", "The Grade 5 Scholarship Exam is conducted annually and provides opportunities for students to enter prestigious schools.", datetime.now()),
        ("ordinary level", "Grade 6-11", "Secondary education includes Grades 6-11, culminating in the GCE Ordinary Level (O/L) examination.", datetime.now()),
        ("advanced level", "Grade 12-13", "After O/Ls, students can proceed to GCE Advanced Level (A/L) studies in one of three streams: Arts, Commerce, or Science.", datetime.now()),
        ("university admission", "Undergraduate", "University admissions are based on Z-scores calculated from A/L results, with quotas for each district.", datetime.now()),
        ("technical education", "Vocational", "Sri Lanka has vocational training institutes (NVQ system) offering practical skills development.", datetime.now()),
    ]
    
    try:
        c.executemany("INSERT OR IGNORE INTO education_facts (topic, level, information, last_updated) VALUES (?, ?, ?, ?)", education_data)
    except:
        pass
    
    conn.commit()
    conn.close()

init_db()

# DeepSeek API integration
DEEPSEEK_API_KEY = ""
DEEPSEEK_API_URL = ""

def query_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant specialized in Sri Lankan education system from Grade 1 to Graduate level. Provide concise, accurate answers."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error querying DeepSeek API: {e}")
        return None

# Inference Engine
def get_response(user_input):
    conn = sqlite3.connect('knowledge_base.db')
    c = conn.cursor()
    
    # First check static responses
    c.execute("SELECT answer FROM static_responses WHERE LOWER(question) = LOWER(?)", (user_input,))
    static_response = c.fetchone()
    
    if static_response:
        conn.close()
        return static_response[0]
    
    # Check if it's a database query (simple pattern matching)
    if "what is" in user_input.lower() or "tell me about" in user_input.lower():
        topic = user_input.lower().replace("what is", "").replace("tell me about", "").strip()
        c.execute("SELECT information FROM education_facts WHERE LOWER(topic) LIKE ? LIMIT 1", (f"%{topic}%",))
        db_response = c.fetchone()
        
        if db_response:
            conn.close()
            return db_response[0]
    
    # Check for grade-specific questions
    grade_keywords = ["grade", "o/l", "a/l", "ordinary level", "advanced level", "primary", "secondary", "university"]
    if any(keyword in user_input.lower() for keyword in grade_keywords):
        # Try to find relevant info from database
        c.execute("SELECT information FROM education_facts WHERE LOWER(?) LIKE '%' || LOWER(level) || '%' OR LOWER(?) LIKE '%' || LOWER(topic) || '%' LIMIT 1", 
                 (user_input, user_input))
        db_response = c.fetchone()
        
        if db_response:
            conn.close()
            return db_response[0]
    
    # If no match found, use DeepSeek API
    deepseek_response = query_deepseek(f"Question about Sri Lankan education system: {user_input}")
    
    # Log the conversation
    c.execute("INSERT INTO conversation_log (user_input, bot_response, timestamp) VALUES (?, ?, ?)",
             (user_input, deepseek_response or "I couldn't find an answer to that. Could you rephrase your question?", datetime.now()))
    conn.commit()
    conn.close()
    
    return deepseek_response or "I couldn't find an answer to that question about Sri Lankan education. Could you try rephrasing it?"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data['message']
    response = get_response(user_input)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)

