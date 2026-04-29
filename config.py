from dotenv import load_dotenv
import os
import json

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")
TARGET_SCORE = int(os.getenv("TARGET_SCORE", 90))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 10))