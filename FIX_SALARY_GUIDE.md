# FIXING MISSING SALARY/STIPEND DATA - QUICK START GUIDE

## Problem
Salary and stipend data is not visible on the website because the compensation fields are empty in the database.

## Solution
Run the backfill script to extract compensation from existing job descriptions and raw payloads.

---

## STEP-BY-STEP INSTRUCTIONS

### Step 1: Ensure MongoDB is Running
```bash
# Check if MongoDB is running
mongod --version
# If not running, start it (adjust path as needed)
```

### Step 2: Run the Diagnostic (Optional but Recommended)
```bash
cd C:\VINAY\roleradar\backend
python ..\scratch\diagnose_salary_visibility.py
```

This will show you:
- How many jobs currently have compensation data
- What the extraction logic finds in sample jobs
- Whether the data is making it to the API response

### Step 3: Run the Backfill Script
```bash
cd C:\VINAY\roleradar\backend
python ..\scratch\run_backfill_simple.py
```

This will:
- Extract compensation from all jobs in the database
- Update jobs with newly extracted salary/stipend data
- Show progress and statistics

**Expected time**: 2-5 minutes depending on number of jobs

### Step 4: Verify the Results
After the backfill completes, check:

1. **Backend logs**: The backfill script will show how many jobs were updated
2. **Database**: Check a few sample jobs have compensation data
3. **Website**: Refresh your browser and check if salaries now appear

```bash
# Quick verification query
cd C:\VINAY\roleradar\backend
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings
from app.db.mongo import Collections

async def check():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    total = await db[Collections.JOBS].count_documents({})
    with_salary = await db[Collections.JOBS].count_documents({
        '\$or': [
            {'salary_min': {'\$exists': True, '\$ne': None}},
            {'salary_max': {'\$exists': True, '\$ne': None}},
            {'stipend_min': {'\$exists': True, '\$ne': None}},
            {'compensation_text': {'\$exists': True, '\$ne': None}}
        ]
    })
    
    print(f'Total jobs: {total}')
    print(f'Jobs with compensation: {with_salary}')
    print(f'Coverage: {with_salary/total*100:.1f}%')
    
    await client.close()

asyncio.run(check())
"
```

### Step 5: Restart Backend Server
If the backend is running, restart it to ensure fresh data:

```bash
# Stop the current server (Ctrl+C)
# Then restart:
cd C:\VINAY\roleradar\backend
uvicorn app.main:app --reload
```

### Step 6: Check the Website
1. Open your browser to the jobs/internships page
2. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
3. Verify that salary/stipend data now appears on job cards

---

## What Gets Extracted

The backfill will extract:

### Numeric Compensation:
- **LPA ranges**: "₹12-15 LPA" → salary_min: 12, salary_max: 15
- **Single LPA**: "10 LPA" → salary_min: 10
- **Monthly stipends**: "₹25,000/month" → stipend_min: 25000
- **Full INR amounts**: "INR 800000 to 1200000" → converted to LPA

### Qualitative Compensation:
- "Best in industry salary" → compensation_text: "Best in industry"
- "Competitive compensation" → compensation_text: "Competitive compensation"
- "Paid internship" → compensation_text: "Paid internship"

### From Structured Payloads:
- **Ashby**: compensation.summaryComponents
- **Greenhouse**: pay.min_value / pay.max_value
- **Lever**: salaryRange.min / salaryRange.max
- **SmartRecruiters**: customField data

---

## Troubleshooting

### Issue: "Cannot connect to MongoDB"
**Solution**: Ensure MongoDB is running. Check connection string in `.env`:
```
MONGODB_URL=mongodb://localhost:27017
```

### Issue: "No module named 'motor'"
**Solution**: Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### Issue: "Backfill completed but website still shows no salary"
**Solutions**:
1. Hard refresh the browser (Ctrl+Shift+R)
2. Clear browser cache
3. Check browser console for errors (F12)
4. Restart the backend server
5. Check if API is returning data:
   ```bash
   curl http://localhost:8000/api/jobs/matches?limit=5
   ```

### Issue: "Many jobs still show no compensation after backfill"
**This is expected**. Not all job descriptions contain explicit salary information. Target coverage is 60-80%.

For jobs without explicit compensation, you can:
- Contact employers directly
- Mark as "Competitive compensation" if mentioned
- Leave blank if truly undisclosed

---

## Expected Results

After running the backfill:
- **60-80% of jobs** should have at least qualitative compensation data
- **30-50% of jobs** should have numeric salary/stipend data
- **Jobs from major ATSs** (Ashby, Greenhouse, Lever) should have the highest coverage

---

## Files Modified

All the necessary code changes have already been made:
- ✅ `backend/app/modules/jobs/compensation_extractor.py` - Extraction logic
- ✅ `backend/app/modules/jobs/services.py` - Merge conflict resolved
- ✅ `backend/app/modules/jobs/routes.py` - API processing
- ✅ `frontend/src/components/jobs/JobMatchCard.tsx` - Display logic
- ✅ `frontend/src/pages/opportunities/Jobs.tsx` - Jobs page
- ✅ `frontend/src/pages/opportunities/Internships.tsx` - Internships page

**All code is ready - you just need to run the backfill script!**

---

## Quick Command Summary

```bash
# 1. Diagnose (optional)
cd C:\VINAY\roleradar\backend
python ..\scratch\diagnose_salary_visibility.py

# 2. Run backfill (MAIN STEP)
python ..\scratch\run_backfill_simple.py

# 3. Verify
python -c "import asyncio; from motor.motor_asyncio import AsyncIOMotorClient; from app.core.config import get_settings; from app.db.mongo import Collections; async def check(): settings = get_settings(); client = AsyncIOMotorClient(settings.MONGODB_URL); db = client[settings.MONGODB_DB_NAME]; total = await db[Collections.JOBS].count_documents({}); with_salary = await db[Collections.JOBS].count_documents({'\$or': [{'salary_min': {'\$exists': True, '\$ne': None}}, {'compensation_text': {'\$exists': True, '\$ne': None}}]}); print(f'Coverage: {with_salary}/{total} ({with_salary/total*100:.1f}%)'); await client.close(); asyncio.run(check())"

# 4. Restart backend
uvicorn app.main:app --reload
```

---

## Need Help?

If you encounter issues:
1. Check the terminal output for error messages
2. Verify MongoDB connection
3. Check backend logs
4. Inspect browser console (F12) for frontend errors

The backfill script is idempotent - safe to run multiple times.
