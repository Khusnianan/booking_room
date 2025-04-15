import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, time

# ------------------- CONFIG & STYLE -------------------
st.set_page_config(page_title="Booking Room Meeting", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #f0f9ff;}
    .stButton>button {background-color:#007acc; color:white;}
    .stTextInput>div>div>input, .stDateInput>div>input, .stTimeInput>div>input {
        background-color:#ffffff; border-radius: 5px;
    }
    .stSelectbox>div>div {background-color:#ffffff;}
    </style>
""", unsafe_allow_html=True)

st.title("📅 Booking Room Meeting")
st.caption("Atur jadwal dulu sebelum meeting 🎯")

# ------------------- DB CONNECTION -------------------
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

# ------------------- LOGIN SYSTEM -------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    menu = st.radio("Menu", ["🔐 Login", "✍️ Registrasi User Baru"])

    if menu == "🔐 Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            cur.execute("SELECT id FROM users WHERE username=%s AND password=%s", (username, password))
            user = cur.fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.username = username
                st.success(f"✅ Login berhasil sebagai `{username}`")
                st.rerun()
            else:
                st.error("❌ Username atau password salah.")

    elif menu == "✍️ Registrasi User Baru":
        new_user = st.text_input("Username Baru")
        new_pass = st.text_input("Password Baru", type="password")
        if st.button("Buat Akun"):
            if not new_user or not new_pass:
                st.warning("❗ Username dan password tidak boleh kosong.")
            else:
                try:
                    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (new_user, new_pass))
                    conn.commit()
                    st.success("✅ Registrasi berhasil! Silakan login.")
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    st.error("❌ Username sudah digunakan.")
    st.stop()

# ------------------- MAIN APP -------------------
st.markdown(f"👤 Login sebagai: **{st.session_state.username}**")

# --- Form Booking ---
st.subheader("📝 Booking Ruangan")
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
st.subheader("📋 Jadwal Booking Aktif")
cur.execute("""
    SELECT b.id, b.room, b.nama, b.tanggal, b.jam_mulai, b.jam_selesai, u.username
    FROM booking b
    JOIN users u ON b.user_id = u.id
    ORDER BY b.tanggal, b.jam_mulai
""")
rows = cur.fetchall()
df = pd.DataFrame(rows, columns=["ID", "Ruangan", "Nama", "Tanggal", "Mulai", "Selesai", "User"])
st.dataframe(df.drop(columns=["ID"]), use_container_width=True)

# --- Edit & Delete Booking Sendiri ---
st.subheader("✏️ Edit Booking Saya")
my_bookings = df[df["User"] == st.session_state.username]

if my_bookings.empty:
    st.info("📭 Kamu belum memiliki booking.")
else:
    options = {f"{row['Tanggal']} - {row['Ruangan']} ({row['Mulai']} - {row['Selesai']})": row["ID"] for _, row in my_bookings.iterrows()}
    selected_label = st.selectbox("Pilih booking untuk diedit", ["Pilih..."] + list(options.keys()))

    if selected_label != "Pilih...":
        selected_id = options[selected_label]
        cur.execute("SELECT room, nama, tanggal, jam_mulai, jam_selesai FROM booking WHERE id=%s", (selected_id,))
        old_room, old_nama, old_tgl, old_start, old_end = cur.fetchone()

        with st.expander("🔧 Edit Booking"):
            with st.form("form_edit"):
                new_room = st.selectbox("Ruangan", [f"Room {i}" for i in range(1, 21)], index=int(old_room.split()[-1]) - 1)
                new_nama = st.text_input("Nama", value=old_nama)
                new_tanggal = st.date_input("Tanggal", value=old_tgl)
                new_start = st.time_input("Jam Mulai", value=old_start)
                new_end = st.time_input("Jam Selesai", value=old_end)
                update = st.form_submit_button("💾 Simpan Perubahan")

                if update:
                    if new_start >= new_end:
                        st.error("❌ Jam mulai harus sebelum jam selesai.")
                    else:
                        cur.execute("""
                            SELECT * FROM booking
                            WHERE room = %s AND tanggal = %s
                            AND (jam_mulai, jam_selesai) OVERLAPS (%s, %s)
                            AND id != %s
                        """, (new_room, new_tanggal, new_start, new_end, selected_id))
                        if cur.fetchone():
                            st.error("❌ Jadwal bentrok dengan booking lain.")
                        else:
                            cur.execute("""
                                UPDATE booking
                                SET room=%s, nama=%s, tanggal=%s, jam_mulai=%s, jam_selesai=%s
                                WHERE id = %s
                            """, (new_room, new_nama, new_tanggal, new_start, new_end, selected_id))
                            conn.commit()
                            st.success("✅ Booking berhasil diperbarui!")
                            st.rerun()

        # --- Konfirmasi Hapus Booking ---
        with st.expander("🗑️ Hapus Booking Ini?", expanded=False):
            st.warning("⚠️ Tindakan ini akan menghapus booking secara permanen.")
            konfirmasi = st.checkbox("Saya yakin ingin menghapus booking ini")

            if konfirmasi:
                if st.button("✅ Konfirmasi Hapus"):
                    cur.execute("DELETE FROM booking WHERE id = %s AND user_id = %s", (selected_id, st.session_state.user_id))
                    conn.commit()
                    st.success("✅ Booking berhasil dihapus.")
                    st.rerun()

# --- Tombol Logout di Bawah ---
st.markdown("---")
if st.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- Tutup koneksi ---
cur.close()
conn.close()
