# Google Cloud Vision API Setup Guide

Complete guide to set up Google Cloud Vision API for TFT screenshot OCR in the Guardian Angel League Discord Bot.

---

## 🎯 Why Cloud Vision?

- **95-98% accuracy** (vs 62-87% with PaddleOCR)
- **Zero maintenance** (no preprocessing tuning)
- **Free for your use case** (16 images/month = $0.00)
- **400 lines of code** (vs 2600+ lines)

---

## 📋 Prerequisites

1. Google account
2. Credit card (required for Google Cloud, but won't be charged under free tier)
3. 10 minutes of setup time

---

## 🚀 Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project details:
   - **Project name:** `GAL-Discord-Bot` (or any name you prefer)
   - **Organization:** (leave default)
4. Click **"Create"**
5. Wait ~30 seconds for project creation

---

### Step 2: Enable Cloud Vision API

1. In Cloud Console, use the search bar at the top
2. Search for: **"Vision API"**
3. Click **"Cloud Vision API"**
4. Click **"Enable"** button
5. Wait for API to enable (~10 seconds)

✅ **Free Tier:** First 1,000 images/month = $0.00

---

### Step 3: Create Service Account

1. In Cloud Console, go to **"IAM & Admin"** → **"Service Accounts"**
   - Or search: "Service Accounts"
2. Click **"+ Create Service Account"**
3. Fill in details:
   - **Service account name:** `gal-vision-ocr`
   - **Service account ID:** (auto-generated)
   - **Description:** "OCR for TFT tournament screenshots"
4. Click **"Create and Continue"**
5. Grant role:
   - Click **"Select a role"** dropdown
   - Search: **"Cloud Vision"**
   - Select: **"Cloud Vision API User"**
6. Click **"Continue"**
7. Click **"Done"** (skip optional steps)

---

### Step 4: Create Service Account Key (JSON)

1. In Service Accounts list, find `gal-vision-ocr`
2. Click on the service account email
3. Go to **"Keys"** tab
4. Click **"Add Key"** → **"Create new key"**
5. Select **"JSON"** format
6. Click **"Create"**

📥 **A JSON file will download automatically**
- **Filename:** `gal-discord-bot-xxxxx.json` (random ID)
- **⚠️ IMPORTANT:** This file contains credentials - keep it secure!
- **Save location:** Recommended: project root folder

---

### Step 5: Set Up Credentials (Local Testing)

#### Option A: Environment Variable (Recommended)

**Windows (PowerShell):**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\gal-discord-bot-xxxxx.json"
```

**Windows (Command Prompt):**
```cmd
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\gal-discord-bot-xxxxx.json
```

**Linux/Mac:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/gal-discord-bot-xxxxx.json"
```

#### Option B: Add to `.env` File

1. Open or create `.env` file in project root
2. Add line:
```env
GOOGLE_APPLICATION_CREDENTIALS=./google-creds.json
```
3. Copy your JSON file to project root and rename to `google-creds.json`

⚠️ **Security:** Make sure `google-creds.json` is in `.gitignore`!

---

### Step 6: Install Dependencies

```bash
# Install google-cloud-vision package
pip install google-cloud-vision>=3.7.0
```

---

### Step 7: Test Locally

```bash
# Run test script
python test_cloud_vision.py
```

**Expected output:**
```
================================================================================
GOOGLE CLOUD VISION OCR TEST
================================================================================

✅ Cloud Vision client initialized

Testing: Lobby A Round 3
File: dashboard/screenshots/lobbyaround3.png
Expected: 8 players
--------------------------------------------------------------------------------
✅ Detected: 8/8 players
📊 Accuracy: 100.0% (8/8 correct)
🎯 Confidence: 95.7%

Players extracted:
  ✅ 1. coco (8 pts)
  ✅ 2. Astrid (7 pts)
  ✅ 3. Snowstorm (6 pts)
  ✅ 4. Nidaleesha (5 pts)
  ✅ 5. hint (4 pts)
  ✅ 6. MaryamIsBad (3 pts)
  ✅ 7. Kalimier (2 pts)
  ✅ 8. Evermore (1 pt)

... (similar for other screenshots)

================================================================================
SUMMARY
================================================================================
✅ Lobby A Round 3: 8/8 (100.0%)
✅ Lobby B Round 3: 8/8 (100.0%)
✅ Lobby C Round 3: 8/8 (100.0%)

Overall Accuracy: 100.0% (24/24)

🎉 EXCELLENT! Cloud Vision is performing at 95%+ accuracy!
================================================================================
```

---

### Step 8: Deploy to Railway

#### Method 1: Environment Variable (JSON as String)

1. Open Railway dashboard
2. Go to your project
3. Click **"Variables"** tab
4. Add new variable:
   - **Name:** `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - **Value:** (paste entire JSON file contents)

5. Update `bot.py` to write JSON from environment variable:

```python
import os
import json

# Write Google credentials from environment variable (Railway deployment)
if os.getenv("RAILWAY_ENVIRONMENT"):
    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json:
        # Write credentials to file
        with open("google-creds.json", "w") as f:
            f.write(creds_json)
        # Set environment variable to point to file
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./google-creds.json"
        print("✅ Google Cloud credentials loaded from environment")
```

Add this code at the **very top** of `bot.py` before any other imports.

#### Method 2: Railway Secret (Recommended)

1. In Railway, go to **"Variables"** tab
2. Click **"Raw Editor"**
3. Add:
```json
{
  "GOOGLE_APPLICATION_CREDENTIALS": "/app/google-creds.json",
  "GOOGLE_CLOUD_PROJECT": "your-project-id",
  "GOOGLE_CREDS_JSON": "{\"type\": \"service_account\", \"project_id\": \"...\", ...}"
}
```

4. Update startup script to write credentials:

```python
import os
import json

# Railway deployment: write Google credentials
if creds_data := os.getenv("GOOGLE_CREDS_JSON"):
    creds_path = "/app/google-creds.json"
    with open(creds_path, "w") as f:
        f.write(creds_data)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
```

---

### Step 9: Set Cost Protection (Recommended)

#### Budget Alert

1. In Google Cloud Console, go to **"Billing"** → **"Budgets & alerts"**
2. Click **"Create Budget"**
3. Configure:
   - **Name:** "GAL Vision API Budget"
   - **Projects:** Select your project
   - **Services:** Cloud Vision API
   - **Budget type:** Specified amount
   - **Amount:** $1.00/month
4. Set alerts:
   - 50% threshold
   - 90% threshold
   - 100% threshold
5. Add your email for notifications
6. Click **"Finish"**

#### API Quota Limit

1. Go to **"APIs & Services"** → **"Cloud Vision API"** → **"Quotas"**
2. Find: **"TEXT_DETECTION requests per minute"**
3. Click **"Edit Quotas"**
4. Set limit: **100 requests/day** (3,000/month max)
5. This prevents accidental runaway costs

---

## 💰 Cost Breakdown

### Your Use Case: 16 images/month (1 tournament)

| Item | Cost |
|------|------|
| **Cloud Vision API** | $1.50 per 1,000 images |
| **Your usage** | 16 images/month |
| **Calculation** | 16 × $0.0015 = $0.024 |
| **Monthly cost** | **$0.024 (~2.4 cents)** |
| **Free tier** | First 1,000/month FREE |
| **Actual cost** | **$0.00** |

### Worst-Case Scenario

If you somehow process 100 images in one month:
- **Cost:** 100 × $0.0015 = $0.15/month (~15 cents)
- **With quota limit:** Capped at 100/day = max $4.50/month
- **With budget alert:** Get notified at $0.50 (50% of $1 budget)

---

## 🧪 Testing Checklist

- [ ] Google Cloud project created
- [ ] Vision API enabled
- [ ] Service account created
- [ ] JSON credentials downloaded
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` environment variable set
- [ ] `pip install google-cloud-vision` completed
- [ ] `python test_cloud_vision.py` runs successfully
- [ ] All 3 screenshots show 95%+ accuracy
- [ ] Railway environment variables configured
- [ ] Bot deployed and tested with real screenshot upload
- [ ] Budget alert configured ($1/month)
- [ ] API quota limit set (100/day)

---

## 🐛 Troubleshooting

### Error: "Could not automatically determine credentials"

**Cause:** `GOOGLE_APPLICATION_CREDENTIALS` not set

**Fix:**
```bash
# Set environment variable
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\credentials.json

# Or check .env file
cat .env  # Should contain: GOOGLE_APPLICATION_CREDENTIALS=./google-creds.json
```

### Error: "Permission denied" or "403 Forbidden"

**Cause:** Service account doesn't have Vision API User role

**Fix:**
1. Go to IAM & Admin → Service Accounts
2. Click on service account
3. Go to "Permissions" tab
4. Add role: "Cloud Vision API User"

### Error: "API not enabled"

**Cause:** Vision API not enabled for project

**Fix:**
1. Go to APIs & Services → Library
2. Search "Vision API"
3. Click "Enable"

### Test script fails with "No text detected"

**Cause:** Image file path incorrect

**Fix:**
```bash
# Check if screenshots exist
ls dashboard/screenshots/*.png

# Use absolute paths if needed
python test_cloud_vision.py
```

### Railway deployment: "Failed to initialize Vision API"

**Cause:** Credentials not loaded on Railway

**Fix:**
1. Check Railway environment variables
2. Add startup code to write credentials file (see Step 8)
3. Verify `GOOGLE_APPLICATION_CREDENTIALS_JSON` contains full JSON

---

## 📚 Additional Resources

- [Cloud Vision API Documentation](https://cloud.google.com/vision/docs)
- [Vision API Pricing](https://cloud.google.com/vision/pricing)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [Railway Environment Variables](https://docs.railway.app/develop/variables)

---

## 🎉 Success!

Once testing shows 95%+ accuracy, you're ready to use Cloud Vision in production!

**Next steps:**
1. Delete old PaddleOCR/Tesseract code (cleanup)
2. Deploy to Railway
3. Test with real tournament screenshots
4. Monitor usage in Google Cloud Console

**Questions?** Check the troubleshooting section or contact support.

---

**Last updated:** 2026-01-01
**Bot version:** Cloud Vision Migration v1.0
