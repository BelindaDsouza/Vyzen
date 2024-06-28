from flask import Flask, render_template, request
import fitz  # PyMuPDF for PDF extraction
import docx
import re
import os
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from spacy.matcher import Matcher

# Ensure NLTK downloads are available
nltk.download('stopwords')
nltk.download('wordnet')

app = Flask(__name__)

# Initialize the WordNet Lemmatizer and Porter Stemmer
lemmatizer = WordNetLemmatizer()
stemmer = PorterStemmer()

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Function to extract text from PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

# Function to extract text from DOCX file
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = '\n'.join([para.text for para in doc.paragraphs])
    return text

# Function to extract text from TXT file
def extract_text_from_txt(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as file:
        text = file.read()
    return text

# Function to extract name using spaCy matcher
def extract_name(nlp_text):
    pattern = [{'POS': 'PROPN'}, {'POS': 'PROPN'}]
    matcher = Matcher(nlp.vocab)
    matcher.add("NAME", [pattern])
    matches = matcher(nlp_text)
    for match_id, start, end in matches:
        span = nlp_text[start:end]
        return span.text

# Function to remove objective section from resume text
def remove_objective_section(text):
    pattern = re.compile(r'objective[\s\S]+?(?=(?:\n[A-Z][a-z]*\n)|$)', re.IGNORECASE)
    return re.sub(pattern, '', text)

# Function to extract specific section from resume text
def extract_section(text, section_name):
    pattern = re.compile(rf'{section_name}[\s\S]+?(?=(?:\n[A-Z][a-z]*\n)|$)', re.IGNORECASE)
    matches = pattern.findall(text)
    if matches:
        return matches[0].strip()
    return ""

# Function to parse resume and extract relevant information
def parse_resume(file_path, file_type):
    if file_type == 'pdf':
        resume_text = extract_text_from_pdf(file_path)
    elif file_type == 'docx':
        resume_text = extract_text_from_docx(file_path)
    elif file_type == 'txt':
        resume_text = extract_text_from_txt(file_path)
    else:
        raise ValueError("Unsupported file type")

    # Remove the "Objective" section from the resume text
    resume_text = remove_objective_section(resume_text)

    nlp_text = nlp(resume_text)

    name = extract_name(nlp_text)
    education = extract_section(resume_text, 'education')
    skills = extract_section(resume_text, 'skills')
    experience = extract_section(resume_text, 'experience')

    return {
        "Name": name,
        "Education": education,
        "Skills": skills,
        "Experience": experience,
    }

# Function to preprocess text (lowercase, remove non-alphabetic characters, tokenize, remove stopwords, lemmatize and stem)
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    words = text.split()
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word not in stop_words]
    words = [lemmatizer.lemmatize(word) for word in words]
    words = [stemmer.stem(word) for word in words]
    processed_text = ' '.join(words)
    return processed_text

# Route for index page
@app.route('/', methods=['GET', 'POST'])
def index():
    all_resumes_data = []

    if request.method == 'POST':
        # Get form data
        resume_folder = request.form['resume_folder']
        job_description_file = request.files['job_description_file']

        # Create 'temp' directory if it doesn't exist
        if not os.path.exists('temp'):
            os.makedirs('temp')

        # Save job description file to temporary location
        job_description_path = os.path.join('temp', job_description_file.filename)
        job_description_file.save(job_description_path)

        # Read job description text from the uploaded file
        job_description_text = ""
        if job_description_path.endswith('.pdf'):
            job_description_text = extract_text_from_pdf(job_description_path)
        elif job_description_path.endswith('.docx'):
            job_description_text = extract_text_from_docx(job_description_path)
        elif job_description_path.endswith('.txt'):
            job_description_text = extract_text_from_txt(job_description_path)

        # Iterate over files in the resume folder
        for filename in os.listdir(resume_folder):
            file_path = os.path.join(resume_folder, filename)

            # Determine file type based on extension
            if filename.endswith(".pdf"):
                resume_type = "pdf"
            elif filename.endswith(".docx"):
                resume_type = "docx"
            elif filename.endswith(".txt"):
                resume_type = "txt"
            else:
                continue  # Skip files that are not PDF, DOCX, or TXT

            # Parse resume to extract information
            resume_info = parse_resume(file_path, resume_type)

            # Calculate similarity scores using CountVectorizer and cosine similarity
            resume_text = '\n'.join([
                preprocess_text(resume_info['Education']),
                preprocess_text(resume_info['Experience']),
                preprocess_text(resume_info['Skills'])
            ])

            job_text = preprocess_text(job_description_text)

            # Initialize the CountVectorizer
            cv = CountVectorizer()

            # Transform the text data into a count matrix
            count_matrix = cv.fit_transform([resume_text, job_text])

            # Calculate cosine similarity between the two text vectors
            cosine_sim = cosine_similarity(count_matrix)
            match_percentage = cosine_sim[0][1] * 100  # similarity between resume and job description

            # Add similarity score to resume info
            resume_info['SimilarityScore'] = match_percentage

            # Add extracted data to the list
            all_resumes_data.append(resume_info)

        # Delete the temporary job description file
        os.remove(job_description_path)

    # Render the index.html template with parsed data
    return render_template('index.html', resumes=all_resumes_data)

if __name__ == '__main__':
    app.run(debug=True)
