# Compensation Data Fix Plan

## Problem
Jobs and internships are missing salary and stipend data in the database.

## Root Cause
Some jobs were synced before the comprehensive compensation extraction logic was in place, or the extraction logic didn't run during sync.

## Solution
Backfill missing compensation data by re-running the extraction logic on all jobs that currently lack compensation information.

## Steps to Execute

### 1. Test the Extraction Logic
```bash
cd backend
python ../scratch/test_compensation_extraction.py
```

This validates that the extraction logic works for various formats:
- LPA ranges (₹12-15 LPA)
- Monthly stipends (₹25000/month)
- Structured ATS payloads (Ashby, Lever, Greenhouse)
- Qualitative phrases ("Best in industry", "Competitive compensation")

### 2. Run the Backfill
```bash
cd backend
python ../scratch/backfill_compensation_data.py
```

This will:
- Scan all jobs in the database
- Re-extract compensation from `raw_payload` and `jd_text`
- Update jobs that are missing compensation data
- Report statistics on coverage

### 3. Verify the Results
```bash
cd backend
python ../scratch/diagnose_compensation_missing.py
```

This shows:
- How many jobs now have compensation data
- Coverage percentages for full-time jobs vs internships
- Examples of any remaining jobs without compensation

## Files Modified

### Backend
- `backend/app/modules/jobs/compensation_extractor.py` - Core extraction logic
- `backend/app/modules/jobs/services.py` - Merge conflict resolved
- `backend/app/modules/jobs/routes.py` - Minor changes

### Frontend
- `frontend/src/components/jobs/JobMatchCard.tsx` - Display logic for compensation
- `frontend/src/pages/opportunities/Jobs.tsx` - Jobs page
- `frontend/src/pages/opportunities/Internships.tsx` - Internships page

### Scripts Created
- `scratch/test_compensation_extraction.py` - Test extraction with sample cases
- `scratch/backfill_compensation_data.py` - Re-extract and update all jobs
- `scratch/diagnose_compensation_missing.py` - Diagnostic report

## Expected Outcomes

After running the backfill:
- **Numeric compensation**: Jobs with explicit salary/stipend values will have `compensation_type: "NUMERIC"` and populated `salary_min`/`salary_max` or `stipend_min`/`stipend_max`
- **Qualitative compensation**: Jobs with phrases like "Best in industry salary" will have `compensation_type: "QUALITATIVE"` and `compensation_text`
- **Undisclosed**: Jobs without any compensation signals will remain as `compensation_type: "UNDISCLOSED"`

Target coverage: 60-80% of jobs should have at least qualitative compensation data after backfill.

## Notes

- The extraction logic handles false positives (company revenue, experience years, etc.)
- It supports multiple formats: LPA, lakhs, full INR amounts, monthly stipends
- Structured ATS payloads are prioritized over text extraction
- Internship-specific patterns are handled separately
