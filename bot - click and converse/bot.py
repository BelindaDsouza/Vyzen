from flask import Flask, request, jsonify, render_template
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import pandas as pd

# Download required NLTK data
nltk.download('punkt')
nltk.download('wordnet')

import pandas as pd

class JobApplicationChatbot:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.intents = self.load_intents()
        self.application_statuses = self.load_application_statuses()
        self.awaiting_application_id = False
    
    def load_intents(self):
        return [
            {
                "tag": "greeting",
                "patterns": ["Hi", "Hello", "Hey"],
                "responses": ["Hey there👋 Thanks for making your way over here! How may I help you today?"]
            },
            {
                "tag": "job_openings",
                "patterns": ["Tell me about current job vacancies"],
                "responses": ["You can view all current job openings on our careers page: [URL]."]
            },
            {
                "tag": "application_process",
                "patterns": ["How do I apply for a job?"],
                "responses": ["To apply for a job, visit our careers page, select the desired role, and click on 'Apply Now'."]
            },
            {
                "tag": "application_status",
                "patterns": ["What is the status of my application?"],
                "responses": ["Please provide your application ID to check the status."]
            },
            {
                "tag": "thanks",
                "patterns": ["Thank you", "Thanks"],
                "responses": ["You're welcome! If you have any other questions, feel free to ask."]
            },
            {
                "tag": "goodbye",
                "patterns": ["Goodbye", "Bye"],
                "responses": ["Goodbye! Have a great day!"]
            },
            {
                "tag": "fallback",
                "patterns": ["I'm sorry, I didn't understand that.", "Can you please rephrase?"],
                "responses": ["I apologize, I'm still learning. Could you ask in a different way?"]
            }
        ]
    
    def load_application_statuses(self):
        df = pd.read_excel('E:/Vyzen/bot - click and converse/application_status.xlsx')
        return df.set_index('applicant_id').to_dict(orient='index')
    
    def preprocess(self, text):
        tokens = word_tokenize(text)
        tokens = [self.lemmatizer.lemmatize(token.lower()) for token in tokens]
        return tokens
    
    def detect_intent(self, user_input):
        tokens = self.preprocess(user_input)
        for intent in self.intents:
            for pattern in intent["patterns"]:
                pattern_tokens = self.preprocess(pattern)
                if set(tokens) == set(pattern_tokens):
                    return intent["tag"]
        return "fallback"
    
    def get_response(self, user_input):
        if self.awaiting_application_id:
            self.awaiting_application_id = False
            try:
                application_id = int(user_input)
                if application_id in self.application_statuses:
                    status_info = self.application_statuses[application_id]
                    response = f"Your application for the role of {status_info['job role']} at {status_info['company']} is currently {status_info['status']}."
                    return jsonify(response=response)
                else:
                    return jsonify(response="I'm sorry, I couldn't find your application ID. Please check and try again.")
            except ValueError:
                return jsonify(response="Invalid application ID. Please provide a numeric application ID.")
        
        intent_tag = self.detect_intent(user_input)
        if intent_tag == "application_status":
            self.awaiting_application_id = True
        
        for intent in self.intents:
            if intent['tag'] == intent_tag:
                return jsonify(response=intent['responses'][0])
        
        return jsonify(response="I'm sorry, I didn't understand that. Can you please rephrase?")

app = Flask(__name__)
chatbot = JobApplicationChatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    response = chatbot.get_response(user_input)
    return response

if __name__ == '__main__':
    app.run(debug=True)
