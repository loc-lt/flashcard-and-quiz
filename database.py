from flask_marshmallow import Marshmallow
import psycopg2

ma = Marshmallow()

# Replace the while loop with a direct connection attempt
try:
    conn = psycopg2.connect(
        host="localhost",
        database="flashcard_and_quiz",
        user="postgres",
        password="loc//14122000",  # Replace with your actual password
        port=5432
    )
    cursor = conn.cursor()
except psycopg2.Error as err:
    print(f"Error connecting to PostgreSQL: {err}")
    # Handle the error, e.g., retry or log the error

# Đóng kết nối nếu kết nối thành công
conn.close()
cursor.close()