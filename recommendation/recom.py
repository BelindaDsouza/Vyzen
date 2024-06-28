from flask import Flask, render_template, request, session
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from wordcloud import WordCloud, STOPWORDS
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure key in production

# Load data
data = pd.read_excel("E:/Vyzen/recommendation/jobs.xlsx")

# Ensure all relevant columns are converted to string, handle NaNs
data["Key Skills"] = data["Key Skills"].astype(str).fillna('')
data["Functional Area"] = data["Functional Area"].astype(str).fillna('')
data["Role"] = data["Role"].astype(str).fillna('')
data["Location"] = data["Location"].astype(str).fillna('')

# Sample the entire dataset for analysis
sampled_data = data

# Clean job titles and locations in the sampled data
sampled_data["Role"] = sampled_data["Role"].str.strip().str.lower()
sampled_data["Location"] = sampled_data["Location"].str.strip().str.lower()

# TF-IDF Vectorization
tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(sampled_data["Key Skills"])

# Generate word clouds (optional, for visualization)
def generate_wordcloud(text, title):
    wordcloud = WordCloud(stopwords=STOPWORDS, background_color="white").generate(text)
    wordcloud.to_file(f"{title}.png")

# Concatenate all key skills into one string and generate a word cloud
key_skills_text = " ".join(sampled_data["Key Skills"])
generate_wordcloud(key_skills_text, "Key_Skills_Word_Cloud")

# Compute cosine similarity matrix
similarity = cosine_similarity(tfidf_matrix)

# Build indices
indices = pd.Series(sampled_data.index, index=sampled_data['Role']).drop_duplicates()

def skill_match(key_skills, user_skills):
    job_skills = [skill.strip().lower() for skill in key_skills.split('|')]
    return any(skill in job_skills for skill in user_skills)

def jobs_recommendation(skills, preferred_roles, locations, num_recommendations=10):
    # Clean and prepare the input preferences
    cleaned_roles = [role.strip().lower() for role in preferred_roles]
    cleaned_skills = [skill.strip().lower() for skill in skills.split(',')]
    cleaned_locations = [location.strip().lower() for location in locations.split(',')]

    # Filter the jobs based on user preferences
    filtered_data = sampled_data[
        sampled_data['Role'].isin(cleaned_roles) &
        sampled_data['Location'].str.lower().isin(cleaned_locations) &
        sampled_data['Key Skills'].apply(lambda x: skill_match(x, cleaned_skills))
    ]

    if filtered_data.empty:
        return None

    # TF-IDF Vectorization on filtered data
    filtered_tfidf_matrix = tfidf.transform(filtered_data["Key Skills"])

    # Compute cosine similarity with the entire TF-IDF matrix
    similarity_scores = cosine_similarity(filtered_tfidf_matrix, tfidf_matrix)

    # Get the mean similarity scores for the filtered data
    mean_similarity_scores = similarity_scores.mean(axis=0)

    # Sort the jobs based on the mean similarity scores
    sorted_indices = mean_similarity_scores.argsort()[::-1]

    # Exclude the jobs already in the filtered data
    filtered_indices = filtered_data.index.tolist()
    recommended_indices = [idx for idx in sorted_indices if idx in filtered_indices][:num_recommendations]

    return sampled_data.loc[recommended_indices, ['Job Title', 'Job Experience Required', 'Key Skills', 'Location']].to_dict('records')

@app.route('/', methods=['GET', 'POST'])
def index():
    recommendations = None

    if request.method == 'POST':
        # Store form data in session to retain inputs after submission
        session['name'] = request.form['name']
        session['dob'] = request.form['dob']
        session['school'] = request.form['school']
        session['degree'] = request.form['degree']
        session['field_of_study'] = request.form['field_of_study']
        session['year_of_passing'] = request.form['year_of_passing']
        session['grade'] = request.form['grade']
        session['skills'] = request.form.getlist('skills')
        session['preferred_location'] = request.form.getlist('preferred_location')
        session['preferred_job_role'] = request.form.getlist('preferred_job_role')

        # Call jobs_recommendation function with form data
        skills_str = ', '.join(session['skills'])
        preferred_location_str = ', '.join(session['preferred_location'])
        preferred_job_role_str = ', '.join(session['preferred_job_role'])

        recommendations = jobs_recommendation(skills_str, session['preferred_job_role'], preferred_location_str)

    # Initialize session variables if not set
    if 'skills' not in session:
        session['skills'] = []
    if 'preferred_location' not in session:
        session['preferred_location'] = []
    if 'preferred_job_role' not in session:
        session['preferred_job_role'] = []

    return render_template('index.html', recommendations=recommendations, session=session)

if __name__ == '__main__':
    app.run(debug=True)
