import psycopg2

def connect_booking_db():
    return psycopg2.connect(
        host=st.secrets["booking_db"]["DB_HOST"],
        port=st.secrets["booking_db"]["DB_PORT"],
        database=st.secrets["booking_db"]["DB_NAME"],
        user=st.secrets["booking_db"]["DB_USER"],
        password=st.secrets["booking_db"]["DB_PASS"]
    )
