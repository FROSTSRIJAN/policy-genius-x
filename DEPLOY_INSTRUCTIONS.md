# 🚀 Quick Deployment Guide

## Step 1: Create New GitHub Repository

1. Go to [GitHub.com](https://github.com)
2. Click "New repository"
3. Name: `PolicyGenius-X`
4. Set as Public
5. **DON'T** initialize with README
6. Click "Create repository"

## Step 2: Upload Files

### Option A: GitHub Web Interface (Easiest)
1. In your new repository, click "uploading an existing file"
2. Drag and drop all files from this `deployment_package` folder
3. Commit message: "Initial commit: PolicyGenius X"
4. Click "Commit changes"

### Option B: Git Commands (if working)
```bash
cd deployment_package
git init
git add .
git commit -m "Initial commit: PolicyGenius X"
git branch -M main
git remote add origin https://github.com/YourUsername/PolicyGenius-X.git
git push -u origin main
```

## Step 3: Deploy on Vercel

1. Go to [vercel.com](https://vercel.com)
2. Sign in with GitHub
3. Click "New Project"
4. Import your `PolicyGenius-X` repository
5. **Framework Preset**: Other
6. **Root Directory**: `./` (default)
7. **Build Command**: Leave empty
8. **Output Directory**: Leave empty
9. **Environment Variables** → Add:
   - `GEMINI_API_KEY` = `your_actual_gemini_api_key`
10. Click "Deploy"

## Step 4: Get Your Endpoint

After deployment completes:
- Your API endpoint: `https://your-project-name.vercel.app/hackrx/run`
- Health check: `https://your-project-name.vercel.app/health`

## Step 5: Test Your API

```bash
curl -X POST "https://your-project-name.vercel.app/hackrx/run" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/policy.pdf",
    "questions": ["Does this policy cover hospitalization?"]
  }'
```

## 🎉 You're Done!

Your HackRx 6.0 compliant API is now live and ready for submission!
