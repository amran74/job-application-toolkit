# AI CV Generator

An AI-powered job application toolkit that generates tailored CVs and cover letters based on specific job descriptions.

## Overview
This project was built to make the job application process more efficient and structured. Instead of manually rewriting a CV for every role, the system uses AI to tailor a base CV to match different job descriptions while keeping the content relevant and organized.

## Features
- AI-powered CV tailoring using OpenAI
- Automatic bilingual CV generation in English and Hebrew
- Professional PDF export for CVs and cover letters
- ATS keyword matching based on job descriptions
- Versioned CV generation for different applications
- Job-specific customization notes for better control over AI output
- Interactive user interface built with Streamlit

## How It Works
1. The user provides a base CV
2. The user adds or selects a job description
3. The system analyzes the role requirements
4. AI tailors the CV to fit the position
5. The system generates:
   - Tailored English CV
   - Hebrew CV version
   - Cover letter
6. All documents are exported as styled PDF files

## Tech Stack
- Python
- Streamlit
- OpenAI API
- ReportLab
- SQLite
- PowerShell

## Project Structure
- `jobtracker/lib/` - core logic such as PDF generation, ATS analysis, and database utilities
- `jobtracker/pages/` - Streamlit application pages
- `jobtracker/exports/` - generated CV and cover letter files
- `jobtracker/` - main application files and app entry point

## Purpose
Job applications often require adjusting a CV for every role. This project automates that process while keeping the information structured, consistent, and easier to manage.

The goal is not only to generate documents, but to provide a simple workflow system for organizing and improving job applications.

## Author
Amran
