import psycopg2

try:
    conn = psycopg2.connect(
        dbname="d79acrueol1eh4",
        user="ucutunp1cir8b1",
        password="pe5b54c86377e79500baa70a45a0a7523bbab92b61cb6e02bdf38c73a5e9cdd36",  # Replace with your actual password
        host="cb681qjlulc2v0.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
        port=5432
    )
    print("Connected to the PostgreSQL database!")
    conn.close()
except (Exception, psycopg2.Error) as error:
    print("Error connecting to PostgreSQL:", error)