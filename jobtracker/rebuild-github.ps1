$ErrorActionPreference = "Stop"

$RepoPath = "C:\Users\omran\OneDrive\Desktop\CV\jobtracker"
$SourcePath = "C:\Users\omran\OneDrive\Desktop\CvPics"
$AssetsPath = Join-Path $RepoPath "assets\images"
$DocsPath = Join-Path $RepoPath "docs"

New-Item -ItemType Directory -Force -Path $AssetsPath | Out-Null
New-Item -ItemType Directory -Force -Path $DocsPath | Out-Null

$Mapping = [ordered]@{
    "HomeCV.png"          = "home-page.png"
    "AddJobCv.png"        = "add-job-page.png"
    "DashCv.png"          = "dashboard-page.png"
    "PROFILECV.png"       = "profile-page.png"
    "BaselineCV.png"      = "baseline-cv-page.png"
    "CvManual1.png"       = "manual-cv-page.png"
    "CvHistory.png"       = "cv-history-page.png"
    "ContentBlocksCV.png" = "content-blocks-page.png"
    "AiCV1.png"           = "ai-page-1.png"
    "Ai2cv.png"           = "ai-page-2.png"
    "aIASSISTANTCV.png"   = "ai-assistant-page.png"
}

foreach ($item in $Mapping.GetEnumerator()) {
    $src = Join-Path $SourcePath $item.Key
    $dst = Join-Path $AssetsPath $item.Value
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Host "Copied $($item.Key) -> $($item.Value)" -ForegroundColor Green
    }
    else {
        Write-Host "Missing: $($item.Key)" -ForegroundColor Yellow
    }
}

$Readme = @"
# Job Application Toolkit

An AI-powered job application platform built to make CV tailoring, job tracking, and document generation faster, cleaner, and more organized.

## Overview

This project was created to solve a common problem: applying for jobs usually means rewriting the same CV again and again, adjusting details manually, keeping track of versions, and wasting time on repetitive formatting. A deeply inspiring use of human life.

The toolkit turns that process into a structured workflow. Instead of editing documents blindly, the user manages job applications through a system that supports tailored CV creation, AI-assisted adaptation, document history, and export-ready outputs.

## Core Capabilities

- AI-assisted CV tailoring based on job descriptions
- Job-specific CV versioning and history
- Baseline CV management
- Manual CV editing and content block control
- Bilingual CV workflow support
- PDF export for polished application documents
- ATS-aware keyword alignment
- Dashboard-style application tracking
- Streamlit-based interactive interface

## Why This Project Stands Out

This is not just a CV generator. It is a workflow system for managing the job application process from one place.

The project combines:
- practical automation
- structured document management
- AI-assisted writing support
- user-friendly interface design
- export-ready outputs for real-world use

It is built for people who want a more efficient and systematic way to prepare strong job applications without losing control over the final result.

## Tech Stack

- Python
- Streamlit
- OpenAI API
- ReportLab
- SQLite

## Project Structure

- `jobtracker/` - main application entry and core app files
- `jobtracker/pages/` - Streamlit pages for app workflows
- `jobtracker/lib/` - utility logic, PDF generation, ATS logic, and database handling
- `jobtracker/exports/` - generated CV and cover letter outputs
- `assets/images/` - repository screenshots used in documentation
- `docs/` - supporting documentation and screenshot gallery

## Key Screens

### Home Page
![Home Page](assets/images/home-page.png)

### Add Job Flow
![Add Job Flow](assets/images/add-job-page.png)

### Dashboard
![Dashboard](assets/images/dashboard-page.png)

### Baseline CV Builder
![Baseline CV Builder](assets/images/baseline-cv-page.png)

### AI CV Workflow
![AI CV Workflow](assets/images/ai-page-1.png)

### Profile / User Configuration
![Profile / User Configuration](assets/images/profile-page.png)

More screenshots are available in [docs/screenshots.md](docs/screenshots.md).

## Use Case

A typical workflow looks like this:

1. Add a target job
2. Store or paste the relevant job description
3. Build from a baseline CV or edit manually
4. Use AI to tailor the CV to the role
5. Review and refine content blocks
6. Export professional final documents
7. Keep version history for future applications

## Future Improvements

- richer analytics for application performance
- more advanced ATS scoring and recommendations
- stronger document comparison tools
- improved multilingual workflows
- enhanced UI polish and navigation

## Author

**Amran**  
Information Systems graduate focused on building practical systems that combine automation, structure, and usable design.
"@

$Screenshots = @"
# Screenshot Gallery

This gallery shows the main screens and workflows of the Job Application Toolkit.

## Main Pages

### Home Page
![Home Page](../assets/images/home-page.png)

### Add Job Page
![Add Job Page](../assets/images/add-job-page.png)

### Dashboard
![Dashboard](../assets/images/dashboard-page.png)

### Profile Page
![Profile Page](../assets/images/profile-page.png)

## CV Management

### Baseline CV
![Baseline CV](../assets/images/baseline-cv-page.png)

### Manual CV Editing
![Manual CV Editing](../assets/images/manual-cv-page.png)

### CV History
![CV History](../assets/images/cv-history-page.png)

### Content Blocks
![Content Blocks](../assets/images/content-blocks-page.png)

## AI Workflow

### AI CV Generation - View 1
![AI CV Generation - View 1](../assets/images/ai-page-1.png)

### AI CV Generation - View 2
![AI CV Generation - View 2](../assets/images/ai-page-2.png)

### AI Assistant
![AI Assistant](../assets/images/ai-assistant-page.png)
"@

Set-Content -Path (Join-Path $RepoPath "README.md") -Value $Readme -Encoding UTF8
Set-Content -Path (Join-Path $DocsPath "screenshots.md") -Value $Screenshots -Encoding UTF8

Write-Host ""
Write-Host "README.md rebuilt successfully." -ForegroundColor Cyan
Write-Host "docs\screenshots.md created successfully." -ForegroundColor Cyan
Write-Host "assets\images populated successfully." -ForegroundColor Cyan
Write-Host ""
Write-Host "Next run:" -ForegroundColor White
Write-Host "git add ." -ForegroundColor Green
Write-Host 'git commit -m "Rebuild GitHub README and screenshot gallery"' -ForegroundColor Green
Write-Host "git push origin main" -ForegroundColor Green
