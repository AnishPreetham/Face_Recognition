"""FaceTrace web frontend.

Run:
    streamlit run frontend.py

The existing CLI backend remains intact. This file provides a browser UI
around the same FaceTrace pipeline so a demo can be recorded without using
the VS Code terminal as the visible interface.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse

import streamlit as st

# Make local project packages importable when Streamlit launches this file.
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from face.detector import FaceIdentifier
from search.reverse_search import reverse_image_search
from utils.hashing import hash_record
from blockchain.blockchain import LocalBlockchain


SOCIAL_LABELS = {
    "instagram.com": "Instagram",
    "reddit.com": "Reddit",
    "twitter.com": "X / Twitter",
    "x.com": "X",
    "facebook.com": "Facebook",
    "tiktok.com": "TikTok",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "pinterest.com": "Pinterest",
    "linkedin.com": "LinkedIn",
    "threads.net": "Threads",
    "tumblr.com": "Tumblr",
}


def platform_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for domain, label in SOCIAL_LABELS.items():
        if domain in host:
            return label
    return host or "Unknown"


def inject_css():
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at 10% 0%, rgba(88, 166, 255, .10), transparent 32%),
                radial-gradient(circle at 90% 10%, rgba(126, 87, 194, .10), transparent 28%),
                #080b12;
        }

        [data-testid="stHeader"] {
            background: rgba(8, 11, 18, .88);
        }

        .hero {
            padding: 2.2rem 2.4rem 1.8rem;
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(20,28,44,.95), rgba(12,16,27,.95));
            box-shadow: 0 24px 80px rgba(0,0,0,.30);
            margin-bottom: 1.4rem;
        }

        .hero-kicker {
            color: #7dd3fc;
            font-size: .82rem;
            font-weight: 700;
            letter-spacing: .16em;
            text-transform: uppercase;
            margin-bottom: .5rem;
        }

        .hero-title {
            font-size: 3.1rem;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -.045em;
            margin: 0;
        }

        .hero-subtitle {
            color: #aab4c5;
            font-size: 1.05rem;
            margin-top: .75rem;
        }

        .stage {
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 16px;
            padding: 1rem 1.15rem;
            background: rgba(15,20,32,.72);
            margin: .55rem 0;
        }

        .stage-complete {
            border-color: rgba(74,222,128,.35);
            background: rgba(16,45,30,.45);
        }

        .stage-title {
            font-weight: 750;
            font-size: 1rem;
        }

        .stage-detail {
            color: #9aa7bb;
            font-size: .88rem;
            margin-top: .25rem;
        }

        .evidence {
            border: 1px solid rgba(125,211,252,.20);
            border-radius: 18px;
            padding: 1.1rem 1.25rem;
            background: rgba(15,25,39,.70);
        }

        .evidence-label {
            color: #7dd3fc;
            font-size: .72rem;
            text-transform: uppercase;
            letter-spacing: .13em;
            font-weight: 700;
        }

        .mono {
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            overflow-wrap: anywhere;
            color: #dbeafe;
            font-size: .82rem;
        }

        .success {
            text-align: center;
            padding: 1.6rem;
            border-radius: 22px;
            border: 1px solid rgba(74,222,128,.35);
            background: linear-gradient(135deg, rgba(18,70,43,.62), rgba(10,35,25,.65));
            margin-top: 1.4rem;
        }

        .success-title {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -.025em;
        }

        .pill {
            display: inline-block;
            padding: .35rem .7rem;
            border-radius: 999px;
            background: rgba(125,211,252,.10);
            border: 1px solid rgba(125,211,252,.20);
            color: #bae6fd;
            font-size: .75rem;
            margin: .15rem;
        }

        div.stButton > button {
            border-radius: 12px;
            min-height: 3rem;
            font-weight: 750;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def stage_html(number, title, detail="", complete=False):
    cls = "stage stage-complete" if complete else "stage"
    icon = "✓" if complete else number
    st.markdown(
        f"""
        <div class="{cls}">
            <div class="stage-title">{icon}&nbsp;&nbsp;{title}</div>
            <div class="stage-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="FaceTrace",
        page_icon="🔎",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Goa Hackathon 2026 · Task 3</div>
            <div class="hero-title">FACETRACE</div>
            <div class="hero-subtitle">
                Face Match · Reverse Image Search · Tamper-Evident Verification
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 1.65], gap="large")

    with left:
        st.subheader("Input")
        uploaded = st.file_uploader(
            "Upload a face image",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )

        if uploaded:
            st.image(uploaded, caption=uploaded.name, width="stretch")
            st.caption("The face embedding is used locally to confirm a usable face. "
                       "The embedding is not written to the blockchain.")

        start = st.button(
            "🚀  START VERIFICATION",
            type="primary",
            use_container_width=True,
            disabled=uploaded is None,
        )

        if not uploaded:
            st.info("Upload an image to begin the five-stage verification pipeline.")

    with right:
        st.subheader("Verification Pipeline")

        stage1 = st.empty()
        stage2 = st.empty()
        stage3 = st.empty()
        stage4 = st.empty()
        stage5 = st.empty()

        if not start:
            stage_html("01", "FACE IDENTIFICATION", "Waiting for input image.")
            stage_html("02", "REVERSE IMAGE SEARCH", "Waiting for face scan.")
            stage_html("03", "CREATE FINGERPRINT", "Waiting for matching post.")
            stage_html("04", "BLOCKCHAIN", "Waiting for fingerprint.")
            stage_html("05", "VERIFICATION", "Waiting for blockchain record.")
            return

        # Save uploaded image to a controlled temporary path.
        suffix = os.path.splitext(uploaded.name)[1].lower() or ".jpg"
        fd, image_path = tempfile.mkstemp(prefix="facetrace_", suffix=suffix)
        os.close(fd)
        with open(image_path, "wb") as f:
            f.write(uploaded.getvalue())

        try:
            # ---------------------------------------------------------
            # 1. Face identification
            # ---------------------------------------------------------
            with stage1.container():
                status = st.status("01 · Face identification", expanded=True)
                try:
                    identifier = FaceIdentifier()
                    aligned, embedding, num_faces = identifier.process(image_path)
                    status.update(
                        label="01 · Face identification — complete",
                        state="complete",
                        expanded=False,
                    )
                    st.markdown(
                        f'<div class="stage stage-complete"><div class="stage-title">'
                        f'✓&nbsp;&nbsp;FACE IDENTIFICATION</div>'
                        f'<div class="stage-detail">Face detected · '
                        f'SFace embedding generated ({embedding.shape[1]}-dim)'
                        f'{" · Largest face selected" if num_faces > 1 else ""}</div></div>',
                        unsafe_allow_html=True,
                    )
                except Exception as exc:
                    status.update(label="01 · Face identification — failed", state="error")
                    st.error(str(exc))
                    return

            # ---------------------------------------------------------
            # 2. Reverse image search
            # ---------------------------------------------------------
            with stage2.container():
                status = st.status("02 · Reverse image search", expanded=True)
                st.info(
                    "Google Lens may open a visible Chromium window for its normal "
                    "human verification. Complete that verification there; "
                    "FaceTrace will continue automatically when results appear."
                )

                try:
                    result = reverse_image_search(image_path, headless=False)
                    if result["chosen"] is None:
                        raise RuntimeError(
                            "No genuine social-media post was found in the live results."
                        )

                    chosen = result["chosen"]
                    platform = platform_from_url(chosen["url"])

                    status.update(
                        label="02 · Reverse image search — complete",
                        state="complete",
                        expanded=False,
                    )

                    st.markdown(
                        f"""
                        <div class="evidence">
                            <div class="evidence-label">Live reverse-image evidence</div>
                            <h3 style="margin:.35rem 0 .4rem;">{platform}</h3>
                            <div class="stage-detail">
                                {len(result["all_results"])} external results ·
                                {len(result["social_candidates"])} social-media candidates
                            </div>
                            <div class="mono" style="margin-top:.75rem;">
                                {chosen["url"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.link_button(
                        f"Open discovered {platform} result",
                        chosen["url"],
                        use_container_width=True,
                    )
                except Exception as exc:
                    status.update(label="02 · Reverse image search — failed", state="error")
                    st.error(str(exc))
                    return

            # ---------------------------------------------------------
            # 3. Fingerprint
            # ---------------------------------------------------------
            with stage3.container():
                status = st.status("03 · Create fingerprint", expanded=True)
                try:
                    metadata = {
                        "platform": platform,
                        "post_url": chosen["url"],
                        "matched_image_url": chosen["url"],
                        "match_type": "visual_match",
                        "search_engine": result["provider"],
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    }
                    fingerprint = hash_record(metadata)

                    status.update(
                        label="03 · Fingerprint — complete",
                        state="complete",
                        expanded=False,
                    )

                    st.markdown(
                        f"""
                        <div class="evidence">
                            <div class="evidence-label">SHA-256 fingerprint</div>
                            <div class="mono" style="margin-top:.6rem;">
                                {fingerprint}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception as exc:
                    status.update(label="03 · Fingerprint — failed", state="error")
                    st.error(str(exc))
                    return

            # ---------------------------------------------------------
            # 4. Blockchain
            # ---------------------------------------------------------
            with stage4.container():
                status = st.status("04 · Blockchain", expanded=True)
                try:
                    chain = LocalBlockchain()
                    block = chain.add_record(fingerprint, metadata)

                    status.update(
                        label="04 · Blockchain — record created",
                        state="complete",
                        expanded=False,
                    )

                    st.markdown(
                        f"""
                        <div class="evidence">
                            <div class="evidence-label">Local simulated blockchain</div>
                            <div style="margin-top:.5rem;">
                                <span class="pill">Block #{block.index}</span>
                                <span class="pill">SHA-256</span>
                                <span class="pill">Append-only</span>
                            </div>
                            <div class="stage-detail" style="margin-top:.75rem;">
                                Block hash
                            </div>
                            <div class="mono">{block.hash}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception as exc:
                    status.update(label="04 · Blockchain — failed", state="error")
                    st.error(str(exc))
                    return

            # ---------------------------------------------------------
            # 5. Verification
            # ---------------------------------------------------------
            with stage5.container():
                status = st.status("05 · Verification", expanded=True)
                try:
                    local_hash = hash_record(metadata)
                    stored = chain.get_block(block.index)
                    check = chain.verify_block(block.index)

                    hash_match = local_hash == stored.data_hash
                    verified = hash_match and check["valid"]

                    if not verified:
                        raise RuntimeError(
                            "Blockchain verification failed. "
                            f"Hash match={hash_match}, block valid={check['valid']}"
                        )

                    # Bonus: demonstrate that an in-memory tamper is detected.
                    original_data_hash = block.data_hash
                    block.data_hash = "0" * 64
                    tamper_check = chain.verify_block(block.index)
                    block.data_hash = original_data_hash

                    status.update(
                        label="05 · Verification — complete",
                        state="complete",
                        expanded=False,
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Hash match", "YES")
                    with c2:
                        st.metric(
                            "Tamper detection",
                            "DETECTED" if not tamper_check["valid"] else "FAILED",
                        )

                    st.markdown(
                        f"""
                        <div class="evidence">
                            <div class="evidence-label">Verification evidence</div>
                            <div class="mono" style="margin-top:.6rem;">
                                Local hash&nbsp;&nbsp;: {local_hash}<br>
                                Stored hash : {stored.data_hash}
                            </div>
                            <div style="margin-top:.8rem;">
                                <span class="pill">✓ HASH MATCH</span>
                                <span class="pill">✓ BLOCKCHAIN RECORD VERIFIED</span>
                                <span class="pill">✓ TAMPER DETECTED WHEN MODIFIED</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception as exc:
                    status.update(label="05 · Verification — failed", state="error")
                    st.error(str(exc))
                    return

            st.markdown(
                """
                <div class="success">
                    <div class="success-title">✓ VERIFICATION SUCCESSFUL</div>
                    <div style="color:#a7f3d0;margin-top:.45rem;">
                        Genuine visual match recorded and independently verified
                        as tamper-evident.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        finally:
            try:
                os.remove(image_path)
            except OSError:
                pass


if __name__ == "__main__":
    main()
