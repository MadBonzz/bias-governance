from flask import Flask, render_template, request, session
import text_extraction
import bias_functions
import asyncio
import requests
import pandas as pd
import numpy as np
import os
import json
from datetime import date 
import base64
from aif360.sklearn import metrics

app = Flask(__name__)
app.secret_key = 'kv-654c'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return 'No file part'
    
    files = request.files.getlist('files')
    
    for file in files:
        file.filename = file.filename.split('/')[1]
        file.save('./uploads/' + file.filename)
            
    asyncio.run(text_extraction.start_extraction())
    return {"message": "Files uploaded successfully"}

@app.route('/check_bias', methods=['POST'])
def score():
    data = request.json
    job_description = data.get('jd')

    df = bias_functions.read_json_files('./uploads/parsed_json/')
    print("Extracting text from files")
    texts = bias_functions.extract_text('./uploads/parsed_files/')
    print(texts)

    url = 'https://dev.api.talentmarx.in/api/v1/ml/similarity/'
    data = {
      "queryDocumentString": job_description,
      "documentStrings": texts
    }
    print("Calculating similarity scores")
    response = requests.post(url, json=data)
    scores = eval(response.text)['similarities']
    print(scores)
    df['similarity'] = scores
    df.sort_values(by='similarity', ascending=False, inplace=True)

    n = len(df) / 2

    selected = [1 if i < n else 0 for i in range(len(df))]
    df['selected'] = selected
    df.drop(columns=['similarity'], inplace=True)

    bias_functions.store_results(df)

    print("Checking for bias")
    age_bias = bias_functions.check_bias_binary(df, 'age', 1)
    experience_bias = bias_functions.check_bias_binary(df, 'experience', 1)
    gender_bias = bias_functions.check_bias_binary(df, 'gender', 'Male')
    degree_bias, fav_degrees = bias_functions.check_bias_multi(df, 'degree', 3)
    city_bias, fav_cities = bias_functions.check_bias_multi(df, 'city', 3)
    institute_bias, fav_institutes = bias_functions.check_bias_multi(df, 'institute', 3)
    employer_bias, fav_employers = bias_functions.check_bias_multi(df, 'employer', 3)
    return {"messages": "Bias checked", "age_bias": age_bias, "experience_bias": experience_bias, "gender_bias": gender_bias, "degree_bias":degree_bias, "fav_degrees":fav_degrees, "city_bias": city_bias, "fav_cities": fav_cities, "institute_bias": institute_bias, "fav_institutes":fav_institutes, "employer_bias":employer_bias, "fav_employers":fav_employers}

if __name__ == '__main__':
    app.run(debug=True)