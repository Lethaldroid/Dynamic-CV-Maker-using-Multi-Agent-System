import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.schemas import JobSubmitRequest


if __name__ == "__main__":
    payload = JobSubmitRequest(cv_text="Name: Test Candidate\nSkills: Python, SQL", jd_text="Looking for Python and SQL")
    print(app.title)
    print(app.version)
    print(payload.model_dump())
