import psycopg2
import datetime

from django.db.models.expressions import result

conn = psycopg2.connect(
            host="192.168.110.54",
            port="5432",
            database="overlord_db",
            user="user1",
            password="user555Y1"
        )
cursor = conn.cursor()


crawl_date = datetime.datetime.now().strftime("%Y-%m-%d")
rank = 1
rank_category = "embroidery"
crawl_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
product_id = "111"

query = f"""
SELECT EXISTS(
        SELECT 1
        FROM product_rank_history
        WHERE product_id = 'B0CRYKQ97C'
        AND crawled_at = '2026-01-05 11:02:54'
    )
"""
cursor.execute(query)
# cursor.execute(query, (crawl_date, rank, rank_category, crawl_at, product_id))
result = cursor.fetchone()[0]
print(result)

