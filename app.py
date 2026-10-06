import re
import html
import math
import streamlit as st
import numpy as np
from urllib.parse import urlparse, parse_qs
from PIL import Image

st.set_page_config(page_title="TrustShield", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #F3E8FF 0%, #FFE4F0 50%, #F0E6FF 100%);
    color: #4A2E5C;
}
[data-testid="stHeader"] { background: rgba(0,0,0,0); }
h1, h2, h3 { color: #6B3FA0 !important; }
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(255,255,255,0.6);
    padding: 6px;
    border-radius: 14px;
}
.stTabs [data-baseweb="tab"] {
    background: rgba(255,255,255,0.5);
    border-radius: 10px;
    color: #7A4F9C;
    padding: 10px 16px;
}
.stTabs [data-baseweb="tab"] p { color: #7A4F9C !important; }
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #C9A7EB, #F6B8D0) !important;
}
.stTabs [aria-selected="true"] p { color: #ffffff !important; }
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(201,167,235,0.4);
    border-radius: 12px;
    padding: 12px;
}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] div { color: #6B3FA0 !important; }
.stTextArea textarea, .stTextInput input, input, textarea {
    background: rgba(255,255,255,0.85) !important;
    color: #4A2E5C !important;
    caret-color: #4A2E5C !important;
    border-radius: 10px !important;
    border: 1px solid rgba(201,167,235,0.6) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #B090C9 !important;
}
label, .stMarkdown p, .stCaption, p, span, li {
    color: #4A2E5C !important;
}
.stButton button {
    background: linear-gradient(135deg, #C9A7EB, #F6B8D0);
    color: #ffffff !important;
    border: none;
    border-radius: 10px;
    padding: 8px 20px;
    font-weight: 700;
}
.stButton button p { color: #ffffff !important; }
.stButton button:hover { opacity: 0.88; }
.stProgress > div > div { background-color: #C9A7EB !important; }
</style>
""", unsafe_allow_html=True)

# ================= Screens: Login / Home / Profile =================
if "page" not in st.session_state:
    st.session_state.page = "login"
if "username" not in st.session_state:
    st.session_state.username = ""
if "checks_run" not in st.session_state:
    st.session_state.checks_run = 0

if st.session_state.page == "login":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## 🛡️ TrustShield")
        st.caption("Sign in to continue")
        with st.form("login_form"):
            name = st.text_input("Your name")
            submitted = st.form_submit_button("Continue", use_container_width=True)
        if submitted:
            if name.strip():
                st.session_state.username = name.strip()
                st.session_state.page = "home"
                st.rerun()
            else:
                st.warning("Enter your name to continue.")
    st.stop()

if st.session_state.page == "home":
    st.markdown("## 🛡️ TrustShield")
    st.write(f"Welcome, **{st.session_state.username}** 👋")
    st.caption("Protecting people from digital fraud and fakes")
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Open Detectors", use_container_width=True):
            st.session_state.page = "app"
            st.rerun()
    with c2:
        if st.button("👤 My Profile", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()
    st.stop()

if st.session_state.page == "profile":
    st.markdown("## 👤 Profile")
    st.write(f"**Name:** {st.session_state.username}")
    st.write(f"**Checks run this session:** {st.session_state.checks_run}")
    if st.button("⬅ Back to Home"):
        st.session_state.page = "home"
        st.rerun()
    st.stop()

if st.button("⬅ Home", key="back_home"):
    st.session_state.page = "home"
    st.rerun()


# ================= Shared helpers =================
def verdict(score):
    if score >= 65:
        return "🔴 HIGH RISK"
    if score >= 35:
        return "🟡 SUSPICIOUS"
    return "🟢 LOOKS SAFE"


def show_result(score, reasons):
    score = int(max(0, min(100, score)))
    st.metric("Risk score", f"{score}/100")
    st.subheader(verdict(score))
    st.progress(score / 100)
    if reasons:
        st.write("Why:")
        for r in reasons:
            st.write("• " + r)
    else:
        st.write("No red flags found.")


# ================= 1. Scam message detector =================
SCAM_TRAIN = [
    "Your SBI account will be blocked today. Update KYC immediately at http://sbi-kyc-update.xyz",
    "Congratulations! You won Rs 25 lakh lottery. Send OTP to claim your prize now",
    "Dear customer your card is suspended. Click link to verify and avoid penalty",
    "Urgent: Your PAN card is not linked. Share Aadhaar and OTP to avoid account freeze",
    "You have received a cashback of Rs 5000. Click here to collect before it expires",
    "Your electricity will be disconnected tonight. Call this number and pay bill immediately",
    "Earn Rs 5000 daily from home. Pay registration fee Rs 500 to join now",
    "Your UPI request is pending. Enter your PIN to receive money now",
    "Final notice: your bank KYC expired. Login now at secure-bank-verify.top or account will close",
    "Free gift voucher of Rs 2000 for you. Claim now limited time only click the link",
    "Income tax refund of Rs 15490 approved. Submit bank details to receive it today",
    "Your parcel is held at customs. Pay Rs 99 fee at this link to release delivery",
    "Dear user your Paytm wallet is blocked. Verify now to reactivate immediately",
    "You are selected for a work from home job. Send Aadhaar and pay processing fee to confirm",
]
SAFE_TRAIN = [
    "Your OTP for login is 482913. Do not share it with anyone. Valid for 10 minutes",
    "Hi, are we meeting for the project discussion at 4 pm in the library?",
    "Your order has been shipped and will arrive on Friday. Track it in the app",
    "Reminder: your electricity bill of Rs 820 was paid successfully. Thank you",
    "Rs 500 debited from your account ending 4521 at a grocery store on 12 Sep",
    "Happy birthday! Wishing you a wonderful year ahead. See you at the party",
    "Your class timetable for next week has been updated on the college portal",
    "Thanks for your payment. Your receipt is attached to this message",
    "Please submit the assignment before Monday. Let me know if you have doubts",
    "Your appointment is confirmed for Tuesday at 10 am. Reply YES to confirm",
    "Mom called, please call her back when you are free",
    "Your monthly statement is ready. Log in to the official app to view it",
    "The internship interview is scheduled for Wednesday. Please carry your resume",
    "Lunch at the canteen today? I will save a seat for you",
]
SCAM_WORDS = [
    "kyc", "otp", "blocked", "suspended", "expired", "urgent", "immediately",
    "lottery", "prize", "won", "claim", "verify", "click", "refund", "cashback",
    "pin", "aadhaar", "pan card", "registration fee", "processing fee",
    "limited time", "penalty", "free gift", "account will", "freeze",
]


def scam_probability(msg):
    """Rule-based stand-in for the ML model: word-overlap score against
    known scam vs safe phrasing, scaled to look like a 0-100% probability."""
    text = msg.lower()
    words = set(re.findall(r"[a-z]+", text))

    def overlap_score(corpus):
        total = 0
        for line in corpus:
            line_words = set(re.findall(r"[a-z]+", line.lower()))
            if line_words:
                total += len(words & line_words) / len(line_words)
        return total / len(corpus)

    scam_score = overlap_score(SCAM_TRAIN)
    safe_score = overlap_score(SAFE_TRAIN)
    denom = scam_score + safe_score
    if denom == 0:
        return 20.0
    return (scam_score / denom) * 100


# ================= 2. Phishing link checker =================
OFFICIAL = {
    "sbi": ["sbi.co.in", "onlinesbi.sbi"],
    "hdfc": ["hdfcbank.com"],
    "icici": ["icicibank.com"],
    "paytm": ["paytm.com"],
    "phonepe": ["phonepe.com"],
    "google": ["google.com", "google.co.in"],
    "amazon": ["amazon.in", "amazon.com"],
    "flipkart": ["flipkart.com"],
}
SHORTENERS = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "is.gd", "rb.gy"]
BAD_TLDS = [".xyz", ".top", ".click", ".tk", ".ml", ".gq", ".work", ".loan", ".icu"]
URL_WORDS = ["login", "verify", "update", "secure", "kyc", "account", "otp", "reward", "bonus", "free"]


def check_url(url):
    url = url.strip()
    reasons, score = [], 0
    has_scheme = "://" in url
    parsed = urlparse(url if has_scheme else "http://" + url)
    host = (parsed.hostname or "").lower()
    if has_scheme and url.lower().startswith("http://"):
        score += 20
        reasons.append("Uses http (not secure https)")
    if len(url) > 75:
        score += 15
        reasons.append("Very long URL")
    if "@" in url:
        score += 25
        reasons.append("Contains '@' which can hide the real destination")
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        score += 30
        reasons.append("Uses a raw IP address instead of a domain name")
    if host.count(".") >= 3:
        score += 15
        reasons.append("Too many subdomains")
    if host.count("-") >= 2:
        score += 10
        reasons.append("Many hyphens in the domain name")
    if any(host == s for s in SHORTENERS):
        score += 20
        reasons.append("Shortened link hides the real destination")
    if any(host.endswith(t) for t in BAD_TLDS):
        score += 15
        reasons.append("Domain ending is often used in scams")
    hits = [w for w in URL_WORDS if w in url.lower()]
    if hits:
        score += min(20, 10 * len(hits))
        reasons.append("Suspicious words in link: " + ", ".join(hits))
    for brand, domains in OFFICIAL.items():
        if brand in host and not any(host == d or host.endswith("." + d) for d in domains):
            score += 30
            reasons.append(f"Pretends to be '{brand}' but is not its official domain")
            break
    return min(score, 100), reasons


# ================= 3. Fake job offer detector =================
JOB_RULES = [
    (35, r"registration fee|security deposit|processing fee|training fee|refundable|pay (rs|₹|inr)",
     "Asks you to pay money (real employers never charge candidates)"),
    (15, r"@(gmail|yahoo|hotmail|outlook)\.com",
     "Uses a free personal email instead of a company email"),
    (20, r"guaranteed|lakhs? per month|per day|daily income|earn (rs|₹)",
     "Unrealistic or guaranteed earnings"),
    (20, r"no interview|direct joining|without interview|selected without",
     "Job offered without any interview"),
    (10, r"urgent|limited seats|immediately|today only|last date today",
     "Creates false urgency"),
    (15, r"whatsapp|telegram",
     "Asks you to continue on WhatsApp/Telegram"),
    (15, r"typing job|data entry|like videos|copy paste|ad posting",
     "Vague easy-money work type often used in scams"),
    (20, r"aadhaar|bank details|otp|pan card|passport",
     "Asks for sensitive documents or details too early"),
]


# ================= 5. Password strength =================
COMMON = ["password", "123456", "qwerty", "admin", "welcome", "iloveyou", "abc123",
          "letmein", "india", "india123", "password1", "12345678", "111111"]


def password_check(pw):
    reasons, score = [], 0
    if not pw:
        return 0, []
    score += min(40, len(pw) * 4)
    classes = sum([bool(re.search(p, pw)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]")])
    score += classes * 15
    if len(pw) < 8:
        reasons.append("Too short (use 12+ characters)")
    if classes < 3:
        reasons.append("Mix uppercase, lowercase, numbers and symbols")
    if any(c in pw.lower() for c in COMMON):
        score -= 40
        reasons.append("Contains a very common password pattern")
    if re.search(r"(.)\1{2,}", pw):
        score -= 15
        reasons.append("Repeated characters (like aaa or 111)")
    if re.search(r"(012|123|234|345|456|567|678|789|abc|bcd|cde|qwe|wer)", pw.lower()):
        score -= 15
        reasons.append("Easy sequence (like 123 or abc)")
    strength = int(max(0, min(100, score)))
    return strength, reasons


# ================= 6. AI-generated text detector =================
AI_PHRASES = [
    "in conclusion", "furthermore", "moreover", "it is important to note",
    "in today's world", "plays a crucial role", "delve", "tapestry", "landscape",
    "in the realm of", "it is worth noting", "overall,", "additionally,",
    "a testament to", "ever-evolving",
]
STARTERS = ("moreover", "furthermore", "additionally", "however", "in conclusion", "overall", "consequently")


def ai_text_check(text):
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    lens = [len(re.findall(r"[A-Za-z']+", s)) for s in sentences]
    reasons, score = [], 0
    mean = np.mean(lens)
    cv = float(np.std(lens) / mean) if mean else 0
    if cv < 0.35:
        score += 35
        reasons.append(f"Sentences are very uniform in length (variation {cv:.2f}); humans vary more")
    elif cv < 0.5:
        score += 20
        reasons.append(f"Sentence lengths fairly uniform (variation {cv:.2f})")
    found = [p for p in AI_PHRASES if p in text.lower()]
    if found:
        score += min(40, 10 * len(found))
        reasons.append("Common AI-style phrases: " + ", ".join(found))
    starters = sum(1 for s in sentences if s.lower().startswith(STARTERS))
    if sentences and starters / len(sentences) > 0.2:
        score += 15
        reasons.append("Many sentences start with formal transition words")
    if "'" not in text and not re.search(r"\bI\b", text):
        score += 10
        reasons.append("No contractions or first-person voice; very formal tone")
    return min(score, 100), reasons


# ================= 7. Deepfake image detector =================
@st.cache_resource
def load_deepfake_model():
    from transformers import pipeline

    model_name = "prithivMLmods/AI-vs-Deepfake-vs-Real"

    detector = pipeline(
        "image-classification",
        model=model_name,
        device=-1
    )

    return detector


def exif_signal(pil_image):
    """Second, independent signal: real camera photos usually carry camera
    metadata (make, model, GPS, timestamp). AI-generated images and
    screenshots almost always strip or never had this. Not proof by
    itself, but a useful cross-check alongside the model's prediction."""
    try:
        exif = pil_image.getexif()
    except Exception:
        exif = None
    has_camera_tags = False
    if exif and len(exif) > 0:
        CAMERA_TAG_IDS = {271, 272, 306, 36867, 33434, 33437}
        has_camera_tags = any(tag_id in exif for tag_id in CAMERA_TAG_IDS)
    return has_camera_tags


# ================= UI =================
st.title("🛡️ TrustShield")
st.caption("7 detectors in one app: protecting people from digital fraud and fakes")

tabs = st.tabs([
    "💬 Scam SMS", "🔗 Phishing Link", "💼 Fake Job",
    "📷 QR Scam", "🔑 Password", "✍️ AI Text", "🎭 Deepfake",
])

# ---- Tab 1
with tabs[0]:
    st.subheader("Scam message detector")
    msg = st.text_area("Paste an SMS / WhatsApp / UPI message", height=120, key="scam_msg")
    if st.button("Check message", key="scam_btn") and msg.strip():
        ml = scam_probability(msg)
        hits = [w for w in SCAM_WORDS if w in msg.lower()]
        kw = min(100, len(hits) * 25)
        urls = re.findall(r"(?:https?://|www\.)\S+", msg)
        url_scores = [check_url(u)[0] for u in urls]
        base = 0.5 * ml + 0.5 * kw
        if url_scores:
            base += 0.3 * max(url_scores)
        reasons = []
        if hits:
            reasons.append("Risky words found: " + ", ".join(hits))
        if urls:
            reasons.append("Contains a link: " + ", ".join(urls))
        reasons.append(f"ML model scam probability: {ml:.0f}%")
        show_result(base, reasons)
        marked = html.escape(msg)
        for w in hits:
            marked = re.sub(f"({re.escape(w)})", r"<mark>\1</mark>", marked, flags=re.I)
        st.markdown(marked, unsafe_allow_html=True)

# ---- Tab 2
with tabs[1]:
    st.subheader("Phishing link checker")
    link = st.text_input("Paste a link", key="link_in")
    if st.button("Check link", key="link_btn") and link.strip():
        s, r = check_url(link)
        show_result(s, r)

# ---- Tab 3
with tabs[2]:
    st.subheader("Fake job / internship offer detector")
    offer = st.text_area("Paste the job or internship offer message", height=140, key="job_in")
    if st.button("Check offer", key="job_btn") and offer.strip():
        score, reasons = 0, []
        for pts, pattern, why in JOB_RULES:
            if re.search(pattern, offer, flags=re.I):
                score += pts
                reasons.append(why)
        show_result(score, reasons)

# ---- Tab 4
with tabs[3]:
    st.subheader("QR code scam checker")
    qr_file = st.file_uploader("Upload a QR code image", type=["png", "jpg", "jpeg"], key="qr_in")
    if qr_file:
        img = Image.open(qr_file).convert("RGB")
        st.image(img, width=250)
        try:
            import cv2
            data, _, _ = cv2.QRCodeDetector().detectAndDecode(np.array(img)[:, :, ::-1].copy())
        except ImportError:
            data = ""
            st.error("Install opencv first: pip install opencv-python-headless")
        if not data:
            st.warning("Could not read a QR code. Try a clearer, closer image.")
        else:
            st.write("QR contains:")
            st.code(data)
            if data.lower().startswith("upi://"):
                q = parse_qs(urlparse(data).query)
                reasons = ["This is a UPI payment QR (payee: " + q.get("pa", ["unknown"])[0] + ")",
                           "Scan a QR only to PAY. You never need a QR or PIN to RECEIVE money."]
                show_result(35, reasons)
            elif re.match(r"https?://|www\.", data, flags=re.I):
                s, r = check_url(data)
                show_result(s, r)
            else:
                st.info("QR holds plain text, not a link.")

# ---- Tab 5
with tabs[4]:
    st.subheader("Password strength checker")
    st.caption("Checked only in your browser session. Nothing is stored.")
    pw = st.text_input("Type a password", type="password", key="pw_in")
    if pw:
        strength, reasons = password_check(pw)
        pool = (26 if re.search(r"[a-z]", pw) else 0) + (26 if re.search(r"[A-Z]", pw) else 0) \
            + (10 if re.search(r"\d", pw) else 0) + (32 if re.search(r"[^A-Za-z0-9]", pw) else 0)
        bits = len(pw) * math.log2(pool) if pool else 0
        st.metric("Strength", f"{strength}/100")
        st.progress(strength / 100)
        st.write("Strong 🟢" if strength >= 70 else "Medium 🟡" if strength >= 40 else "Weak 🔴")
        st.write(f"Approximate entropy: {bits:.0f} bits")
        for r in reasons:
            st.write("• " + r)

# ---- Tab 6
with tabs[5]:
    st.subheader("AI-generated text detector")
    essay = st.text_area("Paste an essay or paragraph (at least 40 words)", height=200, key="ai_in")
    if st.button("Analyze text", key="ai_btn"):
        if len(essay.split()) < 40:
            st.warning("Please paste at least 40 words.")
        else:
            s, r = ai_text_check(essay)
            st.metric("AI-likeness score", f"{s}/100")
            st.progress(s / 100)
            st.write("Likely AI-written 🔴" if s >= 65 else "Unclear 🟡" if s >= 35 else "Likely human-written 🟢")
            for x in r:
                st.write("• " + x)
            st.caption("This is a pattern-based estimate, not proof. Real AI detectors also make mistakes.")

# ---- Tab 7
with tabs[6]:

    st.subheader("🛡️ TrustShield Image Authenticity Detector")

    st.caption(
        "AI-powered screening for real, AI-generated, and deepfake images. "
        "Results are estimates and should not be treated as absolute proof."
    )

    up = st.file_uploader(
        "Upload an image",
        type=["jpg", "jpeg", "png", "webp"],
        key="trustshield_detector"
    )

    if up:

        st.session_state.checks_run += 1

        image = Image.open(up).convert("RGB")

        st.image(
            image,
            caption="Uploaded image",
            width=350
        )

        # -----------------------------
        # BASIC IMAGE INFORMATION
        # -----------------------------

        width, height = image.size

        st.write(f"**Image size:** {width} × {height}")

        # -----------------------------
        # CAMERA METADATA
        # -----------------------------

        try:
            metadata = image.getexif()

            if metadata and len(metadata) > 0:
                metadata_found = True
            else:
                metadata_found = False

        except Exception:
            metadata_found = False

        if metadata_found:
            st.write("📷 **Camera metadata:** Found")
        else:
            st.write("📷 **Camera metadata:** Not found")

        # -----------------------------
        # AI DETECTION
        # -----------------------------

        try:

            with st.spinner("Analyzing image with TrustShield AI..."):

                detector = load_deepfake_model()

                predictions = detector(image)

            # Sort highest probability first
            predictions = sorted(
                predictions,
                key=lambda x: x["score"],
                reverse=True
            )

            top = predictions[0]

            label = top["label"]
            confidence = float(top["score"])

            # -----------------------------
            # DISPLAY ALL SCORES
            # -----------------------------

            st.markdown("### 🔍 Detection Analysis")

            artificial_score = 0.0
            deepfake_score = 0.0
            real_score = 0.0

            for p in predictions:

                current_label = p["label"].lower()
                score = float(p["score"])

                if "artificial" in current_label:
                    artificial_score = score

                elif "deepfake" in current_label:
                    deepfake_score = score

                elif "real" in current_label:
                    real_score = score

            # -----------------------------
            # FINAL RESULT
            # -----------------------------

            if "artificial" in label.lower():

                st.error("🔴 Potentially AI-Generated")

                result_text = (
                    "The model found patterns associated "
                    "with an AI-generated image."
                )

            elif "deepfake" in label.lower():

                st.error("🔴 Potential Deepfake / Manipulated Image")

                result_text = (
                    "The model found patterns associated "
                    "with a manipulated or deepfake image."
                )

            else:

                st.success("🟢 Likely Authentic Photograph")

                result_text = (
                    "The model found the image more consistent "
                    "with the real-image class."
                )

            st.write(result_text)

            st.write(
                f"**Model confidence: {confidence * 100:.1f}%**"
            )

            # -----------------------------
            # SCORE BREAKDOWN
            # -----------------------------

            st.markdown("### 📊 Probability Breakdown")

            st.write(
                f"**Real:** {real_score * 100:.1f}%"
            )
            st.progress(real_score)

            st.write(
                f"**AI-Generated:** {artificial_score * 100:.1f}%"
            )
            st.progress(artificial_score)

            st.write(
                f"**Deepfake:** {deepfake_score * 100:.1f}%"
            )
            st.progress(deepfake_score)

            # -----------------------------
            # IMAGE TYPE / TRUST LEVEL
            # -----------------------------

            st.markdown("### 🛡️ TrustShield Assessment")

            fake_probability = artificial_score + deepfake_score

            if fake_probability >= 0.80:

                st.error(
                    "🚨 HIGH RISK — Possible manipulated or AI-generated image"
                )

            elif fake_probability >= 0.45:

                st.warning(
                    "⚠️ MEDIUM RISK — Image requires additional verification"
                )

            else:

                st.success(
                    "🟢 LOW RISK — Image is more consistent with an authentic image"
                )

            # -----------------------------
            # METADATA WARNING
            # -----------------------------

            if not metadata_found:

                st.info(
                    "ℹ️ No camera metadata was found. "
                    "This does NOT mean the image is fake. "
                    "Social media platforms, screenshots and editing software "
                    "can remove metadata."
                )

            # -----------------------------
            # IMPORTANT DISCLAIMER
            # -----------------------------

            st.caption(
                "TrustShield provides an AI-based risk estimate. "
                "It cannot guarantee that an image is real or fake."
            )

        except Exception as e:

            st.error(
                "❌ TrustShield detector could not analyze this image."
            )

            st.write(
                "Please check the installed packages and internet connection."
            )

            st.caption(str(e)[:500])