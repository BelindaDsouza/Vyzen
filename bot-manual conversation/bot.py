from flask import Flask, request, jsonify, render_template
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import nltk
import pandas as pd

# Download required NLTK data
nltk.download('punkt')
nltk.download('wordnet')

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
                "responses": ["Hello! "]
            },
            {
                "tag": "job_openings",
                "patterns": ["What job openings are available?", "Tell me about current job vacancies","job openings","current job openings"],
                "responses": ["You can view all current job openings on our careers page: [URL]."]
            },
            {
                "tag": "application_process",
                "patterns": ["How do I apply for a job?", "What is the application process?","appling for job"],
                "responses": ["To apply for a job, visit our careers page, select the desired role, and click on 'Apply Now'."]
            },
            {
                "tag": "application_status",
                "patterns": ["What is the status of my application?", "How can I check my application status?", "status of my application", "what is the status of my application","application status"],
                "responses": ["Please provide your application ID to check the status."]
            },
            {
                "tag": "feedback",
                "patterns": ["I have feedback", "How can I provide feedback?", "I want to give feedback","feedback"],
                "responses": ["How would you rate your experience with our chatbot? Please provide your feedback."]
            },
            {
                "tag": "thanks",
                "patterns": ["Thank you", "Thanks a lot", "Thanks for your help","thanks"],
                "responses": ["You're welcome!", "Glad I could help!", "Anytime!"]
            },
            {
                "tag": "goodbye",
                "patterns": ["Goodbye", "Bye", "See you later"],
                "responses": ["Goodbye! Have a great day!", "Bye! Come back soon.", "See you later!"]
            },
            {
                "tag": "fallback",
                "patterns": ["I'm sorry, I didn't understand that.", "Can you please rephrase?"],
                "responses": ["I apologize, I'm still learning. Could you ask in a different way?"]
            }
        ]
    
    def preprocess(self, sentence):
        tokens = word_tokenize(sentence.lower())
        tokens = [self.lemmatizer.lemmatize(word) for word in tokens if word.isalnum()]
        return tokens
    
    def detect_intent(self, sentence):
        tokens = self.preprocess(sentence)
        for intent in self.intents:
            for pattern in intent["patterns"]:
                pattern_tokens = self.preprocess(pattern)
                if all(token in tokens for token in pattern_tokens):
                    return intent["tag"]
        return "fallback"
    
    def load_application_statuses(self):
        df = pd.read_excel('E:/Vyzen/bot-manual conversation/application_status.xlsx')
        return df.set_index('applicant_id').to_dict(orient='index')
    
    def get_response(self, intent):
        for intent_data in self.intents:
            if intent_data['tag'] == intent:
                return intent_data['responses'][0]
        return self.intents[-1]['responses'][0]
    
    def handle_message(self, message):
        intent = self.detect_intent(message)
        
        if intent == "application_status":
            self.awaiting_application_id = True
            return self.get_response("application_status")
        
        elif self.awaiting_application_id:
            application_id = message.strip()  # Assuming user message contains application ID
            
            # Check if the input is a valid application ID
            if application_id.isdigit():
                application_id = int(application_id)
                
                if application_id in self.application_statuses:
                    status_info = self.application_statuses[application_id]
                    response = f"Your application for the role of {status_info['job role']} at {status_info['company']} is currently {status_info['status']}."
                    return response
                else:
                    return "Application ID not found. Please provide a valid ID."
            else:
                self.awaiting_application_id = False  # Reset the flag as input is not a valid ID
                return self.get_response(intent)
        
        elif intent != "fallback":
            return self.get_response(intent)
        
        else:
            return self.get_response("fallback")

# Initialize chatbot
chatbot = JobApplicationChatbot()

# Initialize Flask app
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    response = chatbot.handle_message(user_message)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
