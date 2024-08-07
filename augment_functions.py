import numpy as np
import pandas as pd
import requests
import re
from scipy.stats import f_oneway
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
import json

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak

def process_column(column):
    def process_value(value):
        if isinstance(value, str):
            value = value.lower()
            value = value.strip()
            match = re.match(r'(\d+(\.\d+)?)\+', value)
            if match:
                return int(match.group(1))
            match = re.match(r'(\d+(\.\d+)?)\s*years?', value, re.IGNORECASE)
            if match:
                return int(match.group(1))
            if value.upper() == 'NULL':
                return np.nan
            try:
                return int(value)
            except ValueError:
                return np.nan  
        elif isinstance(value, (int, float)):
            return int(value)
        else:
            return np.nan  
    return column.apply(process_value)

def clean_column(column):
    def clean_value(value):
        if isinstance(value, str):
            value = value.lower()
            value = value.strip()
            value = value.replace('"', '')
            if any(char.isdigit() for char in value):
                return np.nan
            if value == 'NULL' or value == 'India' or value == 'Gender' or value == 'City':
                return np.nan
        return value
    return column.apply(clean_value)

def clean_and_convert_column(column):
    def clean_value(value):
        if pd.isna(value): 
            return value
        value = str(value).strip() 
        try:
            return float(value)
        except ValueError:
            if any(char.isdigit() for char in value):
                try:
                    return float(value)
                except ValueError:
                    return np.nan
            else:
                return np.nan
    return column.apply(clean_value)

def create_info_text(df):
    strings = []
    for _, row in df.iterrows():
        s = ""
        keys = row.keys()
        for i, element in enumerate(row):
            s += keys[i] + ": " + str(element).strip() + "\n"
        strings.append(s)
    return strings

def scale_score(x):
    return (x+1) / 2

def find_score(df, colname, j_embed, url):
    for val in df[colname].unique().tolist():
        if 'nan' in str(val):
            continue
        temp_df = df.copy()
        temp_df[colname] = val
        for index, row in temp_df.iterrows():
            data = {
            "skills": 
                list(temp_df.at[index, 'skill']) if 'nan' not in str(temp_df.at[index, 'skill']) else []
            ,
            "experienceMonths": int(temp_df.at[index, 'experiencemonths']) if '[]' not in str(temp_df.at[index, 'experiencemonths']) else 0,
            "experience": [
                {
                "role": temp_df.at[index, 'curr_title'] if temp_df.at[index, 'curr_title'] != "nan" else "",
                "company": temp_df.at[index, 'company'] if temp_df.at[index, 'company'] != "nan" else "",
                }
            ],
            "education": [
                {
                "degree": temp_df.at[index, 'degree'] if temp_df.at[index, 'degree'] != "nan" else "",
                "insititution": temp_df.at[index, 'college'] if temp_df.at[index, 'college'] != "nan" else ""
                }
            ]
            }
            data_json = json.dumps(data)
            c_embed = requests.post(url, data=data_json).text
            j_embed_norm = np.array([eval(j_embed)["NormalizedEmbedding"]])
            c_embed_norm = np.array([eval(c_embed)["NormalizedEmbedding"]])
            
            score = (cosine_similarity(c_embed_norm, j_embed_norm) + 1) /2
            df.at[index, "Score_{}_{}".format(colname, str(val))] = score[0][0]
    return "Added score columns"

def get_bias_score(df, col, job_num, unique_list):
    print("Column name is  :", col)
    graph_path = None
    min_elements = None
    max_elements = None
    col_list = []

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading1']
    body_style = styles['BodyText']
    elements = []
    
    job_title = Paragraph("For JOB ID : {}".format(job_num), title_style)
    elements.append(job_title)

    title =  Paragraph("Bias Analysis for {}".format(col), title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    for val in unique_list:
        print("The current value is : ", val)
        col_list.append('Score_'+col+'_'+str(val))
    print("Values in test list are : ", col_list)
    means = []
    for colname in col_list:
        if colname in df.columns.tolist():
            mean = df[colname].mean()
            means.append(mean)
        else:
            col_list.remove(colname)
        
    en_means = list(enumerate(means))
    en_means.sort(key=lambda x: x[1], reverse=True)
    min_idx = []
    max_idx = []
    if len(en_means) > 3:
        for i in range(3):
            min_idx.append(en_means[-(i + 1)][0])
            max_idx.append(en_means[i][0])
        min_elements = [(col_list[i], means[i]) for i in min_idx]
        max_elements = [(col_list[i], means[i]) for i in max_idx]

        sec1 = Paragraph("Top 3 Categories with Minimum Mean Similarity Score: ", heading_style)
        elements.append(sec1)
        elements.append(Spacer(1, 12))
        for elem in min_elements:
            elements.append(Paragraph(f"{elem[0]} , {elem[1]}", body_style))
            elements.append(Spacer(1, 12))
        elements.append(Spacer(1, 12))

        sec2 = Paragraph("Top 3 Categories with Maximum Mean Similarity Score: ", heading_style)
        elements.append(sec2)
        elements.append(Spacer(1, 12))
        for elem in max_elements:
            elements.append(Paragraph(f"{elem[0]} , {elem[1]}", body_style))
            elements.append(Spacer(1, 12))
        elements.append(Spacer(1, 12))

    else:
        sec1 = Paragraph("All Categories with Mean Similarity Score: ", heading_style)
        elements.append(sec1)
        elements.append(Spacer(1, 12))
        for elem in [(col_list[i], means[i]) for i in range(len(means))]:
            elements.append(Paragraph(f"{elem[0]} , {elem[1]}", body_style))
            elements.append(Spacer(1, 12))
        elements.append(Spacer(1, 12))

    data = []
    for colname in col_list:
        if colname not in df.columns.tolist():
            continue
        data.append(df[colname])
    #data = [df[colname] for colname in col_list]
    print("The column list for P-Value test is : ", col_list)
    print(data)
    p_value = f_oneway(*data)[1]

    p_val = Paragraph(f"P-Value: {p_value}", body_style)
    elements.append(p_val)
    elements.append(Spacer(1, 12))

    if p_value < 0.05:
        plt.figure(figsize=(10, 12))
        plt.plot(col_list, means)
        plt.xticks(rotation=90, fontsize = 6)
        graph_path = col + "_score"
        plt.savefig(graph_path, format='png')
        plt.close()
        
        elements.append(Paragraph("Graphical Representation of all Scores", heading_style))
        elements.append(Spacer(1, 12))
        elements.append(Image(graph_path, width=500, height=500))
        elements.append(Spacer(1, 12))

        heading_style.textColor = colors.red
        elements.append(Paragraph("Bias Detected", heading_style))
        heading_style.textColor = colors.black
        elements.append(Spacer(1, 12))
    else:
        heading_style.textColor = colors.green
        elements.append(Paragraph("No Bias Detected", heading_style))
        heading_style.textColor = colors.black
        elements.append(Spacer(1, 12))
    
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())

    if p_value < 0.05:
        is_biased = 1
    else:
        is_biased = 0

    return elements, is_biased, max_elements