import pymysql

def get_connection():
    return pymysql.connect(
        host='10.10.8.9',
        user='minwoo',
        password='dkagh1.',
        database='newsdb',
        charset='utf8mb4'
    )

conn = get_connection()
with conn.cursor() as cursor:
    cursor.execute("SELECT DATABASE();")
    result = cursor.fetchone()
    print("Connected to database:", result)

conn.close()

