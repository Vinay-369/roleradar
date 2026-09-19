import sys
import os

print("PYTHON EXEC:", sys.executable)
print("CWD:", os.getcwd())

sys.path.insert(0, os.path.abspath("."))

try:
    from app.main import app
    print("APP IMPORTED SUCCESSFULLY")
except Exception as e:
    import traceback
    print("ERROR IMPORTING APP:", e)
    traceback.print_exc()
