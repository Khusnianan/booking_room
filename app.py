import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, time

# --- Konfigurasi ---
st.set_page_config(page_title="Booking Room", layout="wide")
st.title("📅 Booking Room Meeting")

# --- Koneksi ke DB ---
def connect_db():
    return psycopg2.connect(
        host=st.secrets["booking_db"]["DB_HOST"],
        port=st.secrets["booking_db"]["DB_PORT"],
        database=st.secrets["booking_db"]["DB_NAME"],
        user=st.secrets["booking_db"]["DB_USER"],
        password=st.secrets["booking_db"]["DB_PASS"]
    )

conn = connect_db()
cur = conn.cursor()

# --- Login ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        cur.execute("SELECT id FROM users WHERE username=%s AND password=%s", (username, password))
        result = cur.fetchone()
        if result:
            st.session_state.logged_in = True
            st.session_state.user_id = result[0]
            st.session_state.username = username
            st.success(f"✅ Login berhasil sebagai `{username}`")
            st.rerun()
        else:
            st.error("❌ Username atau password salah.")
    st.stop()

st.markdown(f"👤 Login sebagai **{st.session_state.username}**")

# --- Form Booking ---
st.subheader("📝 Form Booking Ruangan")
with st.form("form_booking"):
    nama = st.text_input("Nama Pemesan", value=st.session_state.username)
    tanggal = st.date_input("Tanggal", min_value=datetime.today())
    jam_mulai = st.time_input("Jam Mulai", time(9, 0))
    jam_selesai = st.time_input("Jam Selesai", time(10, 0))
    room = st.selectbox("Pilih Ruangan", [f"Room {i}" for i in range(1, 21)])
    simpan = st.form_submit_button("🔐 Booking Sekarang")

    if simpan:
        if jam_mulai >= jam_selesai:
            st.error("❌ Jam mulai harus sebelum jam selesai.")
        else:
            cur.execute("""
                SELECT * FROM booking
                WHERE room = %s AND tanggal = %s
                AND (jam_mulai, jam_selesai) OVERLAPS (%s, %s)
            """, (room, tanggal, jam_mulai, jam_selesai))
            if cur.fetchone():
                st.error("❌ Jadwal ruangan bentrok.")
            else:
                cur.execute("""
                    INSERT INTO booking (room, nama, tanggal, jam_mulai, jam_selesai, user_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (room, nama, tanggal, jam_mulai, jam_selesai, st.session_state.user_id))
                conn.commit()
                st.success("✅ Booking berhasil!")
                st.rerun()

# --- Tampilkan Semua Booking ---
st.subheader("📋 Jadwal Booking Semua User")
cur.execute("""
    SELECT b.id, b.room, b.nama, b.tanggal, b.jam_mulai, b.jam_selesai, u.username
    FROM booking b
    JOIN users u ON b.user_id = u.id
    ORDER BY b.tanggal, b.jam_mulai
""")
rows = cur.fetchall()
df = pd.DataFrame(rows, columns=["ID", "Ruangan", "Nama", "Tanggal", "Mulai", "Selesai", "User"])
st.dataframe(df.drop(columns=["ID"]), use_container_width=True)

# --- Edit Booking User Sendiri ---
st.subheader("✏️ Edit Booking Saya")
my_bookings = df[df["User"] == st.session_state.username]

if my_bookings.empty:
    st.info("Kamu belum memiliki booking.")
else:
    booking_options = {f"{row['Tanggal']} - {row['Ruangan']} ({row['Mulai']} - {row['Selesai']})": row["ID"] for _, row in my_bookings.iterrows()}
    selected = st.selectbox("Pilih booking untuk diedit", list(booking_options.keys()))
    selected_id = booking_options[selected]

    cur.execute("SELECT room, nama, tanggal, jam_mulai, jam_selesai FROM booking WHERE id = %s", (selected_id,))
    old_room, old_nama, old_tgl, old_start, old_end = cur.fetchone()

    with st.form("form_edit_booking"):
        new_room = st.selectbox("Ruangan", [f"Room {i}" for i in range(1, 21)], index=int(old_room.split()[-1]) - 1)
        new_nama = st.text_input("Nama Pemesan", value=old_nama)
        new_tanggal = st.date_input("Tanggal", value=old_tgl)
        new_mulai = st.time_input("Jam Mulai", value=old_start)
        new_selesai = st.time_input("Jam Selesai", value=old_end)
        update = st.form_submit_button("💾 Simpan Perubahan")

        if update:
            if new_mulai >= new_selesai:
                st.error("❌ Jam mulai harus sebelum selesai.")
            else:
                cur.execute("""
                    SELECT * FROM booking
                    WHERE room = %s AND tanggal = %s
                    AND (jam_mulai, jam_selesai) OVERLAPS (%s, %s)
                    AND id != %s
                """, (new_room, new_tanggal, new_mulai, new_selesai, selected_id))
                if cur.fetchone():
                    st.error("❌ Jadwal bentrok dengan booking lain.")
                else:
                    cur.execute("""
                        UPDATE booking
                        SET room=%s, nama=%s, tanggal=%s, jam_mulai=%s, jam_selesai=%s
                        WHERE id = %s
                    """, (new_room, new_nama, new_tanggal, new_mulai, new_selesai, selected_id))
                    conn.commit()
                    st.success("✅ Booking berhasil diperbarui!")
                    st.rerun()

# --- Tutup koneksi ---
cur.close()
conn.close()
