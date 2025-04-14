import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, time

# --- Setup page ---
st.set_page_config(page_title="Booking Room Meeting", layout="wide")
st.title("📅 Booking Room Meeting")
st.markdown("Pesan ruangan meeting tanpa bentrok jadwal!")

# --- Koneksi ke Database ---
def connect_booking_db():
    return psycopg2.connect(
        host=st.secrets["booking_db"]["DB_HOST"],
        port=st.secrets["booking_db"]["DB_PORT"],
        database=st.secrets["booking_db"]["DB_NAME"],
        user=st.secrets["booking_db"]["DB_USER"],
        password=st.secrets["booking_db"]["DB_PASS"]
    )

conn = connect_booking_db()
cur = conn.cursor()

# --- Form Booking ---
st.subheader("📝 Form Booking Ruangan")
with st.form("form_booking"):
    nama = st.text_input("Nama Pemesan")
    tanggal = st.date_input("Tanggal", min_value=datetime.today())
    jam_mulai = st.time_input("Jam Mulai", time(9, 0))
    jam_selesai = st.time_input("Jam Selesai", time(10, 0))
    room = st.selectbox("Pilih Ruangan", [f"Room {i}" for i in range(1, 21)])

    submit = st.form_submit_button("🔐 Booking Sekarang")

    if submit:
        if jam_mulai >= jam_selesai:
            st.error("❌ Jam mulai harus sebelum jam selesai.")
        elif not nama.strip():
            st.error("❌ Nama pemesan tidak boleh kosong.")
        else:
            # Cek bentrok jadwal
            cur.execute("""
                SELECT * FROM booking
                WHERE room = %s AND tanggal = %s
                AND (
                    (jam_mulai, jam_selesai) OVERLAPS (%s, %s)
                )
            """, (room, tanggal, jam_mulai, jam_selesai))
            bentrok = cur.fetchall()

            if bentrok:
                st.error("❌ Jadwal ruangan bentrok dengan booking lain.")
            else:
                cur.execute("""
                    INSERT INTO booking (room, nama, tanggal, jam_mulai, jam_selesai)
                    VALUES (%s, %s, %s, %s, %s)
                """, (room, nama, tanggal, jam_mulai, jam_selesai))
                conn.commit()
                st.success("✅ Booking berhasil!")

# --- Tampilkan Booking Aktif ---
st.subheader("📋 Jadwal Booking Aktif")
cur.execute("SELECT * FROM booking ORDER BY tanggal, jam_mulai")
rows = cur.fetchall()
df = pd.DataFrame(rows, columns=["ID", "Ruangan", "Nama", "Tanggal", "Mulai", "Selesai"])

if df.empty:
    st.info("Belum ada booking ruangan.")
else:
    st.dataframe(df.drop("ID", axis=1), use_container_width=True)

# --- Tutup koneksi ---
cur.close()
conn.close()
