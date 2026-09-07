"""FaceTrace: Face Match + Blockchain Verification CLI.

Pipeline:
  input image -> YuNet detection + SFace embedding
              -> reverse image search (Google Lens / Bing, live)
              -> canonical metadata -> SHA-256 fingerprint
              -> local hash-linked blockchain record
              -> retrieval + re-verification
"""
import argparse
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from face.detector import FaceIdentifier
from search.reverse_search import reverse_image_search
from utils.hashing import hash_record
from blockchain.blockchain import LocalBlockchain

BANNER = """==================================================
             FACETRACE
   Face Match + Blockchain Verification
==================================================
"""

PLATFORM_NAMES = ["instagram", "reddit", "twitter", "x.com", "facebook",
                   "tiktok", "youtube", "pinterest", "linkedin", "threads", "tumblr"]


def platform_from_url(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    for name in PLATFORM_NAMES:
        if name in netloc:
            return name.replace(".com", "").capitalize()
    return netloc or "Unknown"


def build_metadata(result: dict) -> dict:
    chosen = result["chosen"]
    return {
        "platform": platform_from_url(chosen["url"]),
        "post_url": chosen["url"],
        "matched_image_url": chosen["url"],
        "match_type": "visual_match",
        "search_engine": result["provider"],
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="FaceTrace pipeline")
    parser.add_argument("--image", default="sample/input.jpg", help="Path to input face image")
    parser.add_argument("--headless", action="store_true",
                         help="Run the search browser headless (off by default so you can watch/assist during the demo)")
    parser.add_argument("--tamper-demo", action="store_true",
                         help="After a successful run, simulate tampering with the stored record and show verification fail")
    args = parser.parse_args()

    print(BANNER)

    # [1/5] Face identification
    print("[1/5] FACE IDENTIFICATION")
    try:
        identifier = FaceIdentifier()
        print("  Image loaded")
        aligned, embedding, num_faces = identifier.process(args.image)
        print("  Face detected")
        if num_faces > 1:
            print(f"  Note: {num_faces} faces detected, using the largest one")
        print("  Face landmarks extracted (via alignCrop)")
        print(f"  SFace embedding generated ({embedding.shape[1]}-dim)")
    except Exception as e:
        print(f"  FACE IDENTIFICATION FAILED: {e}")
        sys.exit(1)

    # [2/5] Reverse image search
    print("\n[2/5] REVERSE IMAGE SEARCH")
    try:
        result = reverse_image_search(args.image, headless=args.headless)
        print(f"  Provider: {result['provider']}")
        print("  Search completed")
        print(f"  Matching pages found: {len(result['all_results'])}")
        print(f"  Social-media candidates: {len(result['social_candidates'])}")
        if result["chosen"] is None:
            print("  No social-media post found among the results.")
            print("  Cannot proceed: a genuine social-media match is required.")
            sys.exit(1)
        print("  Matching social-media post found")
        print(f"  Platform: {platform_from_url(result['chosen']['url'])}")
        print(f"  Post URL: {result['chosen']['url']}")
    except Exception as e:
        print(f"  REVERSE IMAGE SEARCH FAILED: {e}")
        sys.exit(1)

    # [3/5] Fingerprint
    print("\n[3/5] CREATE FINGERPRINT")
    try:
        metadata = build_metadata(result)
        fingerprint = hash_record(metadata)
        print("  Metadata generated")
        print(f"  SHA-256: {fingerprint}")
    except Exception as e:
        print(f"  FINGERPRINT CREATION FAILED: {e}")
        sys.exit(1)

    # [4/5] Blockchain
    print("\n[4/5] BLOCKCHAIN")
    try:
        chain = LocalBlockchain()
        block = chain.add_record(fingerprint, metadata)
        print("  Network: Local Simulated Blockchain")
        print("  Record added")
        print("  Block created")
        print(f"  Block hash: {block.hash}")
    except Exception as e:
        print(f"  BLOCKCHAIN WRITE FAILED: {e}")
        sys.exit(1)

    # [5/5] Verification
    print("\n[5/5] VERIFICATION")
    try:
        local_hash = hash_record(metadata)
        stored = chain.get_block(block.index)
        check = chain.verify_block(block.index)
        print(f"  Local hash:  {local_hash}")
        print(f"  Stored hash: {stored.data_hash}")
        if local_hash != stored.data_hash:
            print("  HASH MISMATCH")
            sys.exit(1)
        print("  HASH MATCH")
        if not check["valid"]:
            print(f"  BLOCKCHAIN VERIFICATION FAILED: {check}")
            sys.exit(1)
        print("  BLOCKCHAIN RECORD VERIFIED")
        print("  TAMPER-EVIDENT RECORD VALID")
    except Exception as e:
        print(f"  VERIFICATION FAILED: {e}")
        sys.exit(1)

    print("\n==================================================")
    print("SUCCESS")
    print("==================================================")

    if args.tamper_demo:
        print("\n[BONUS] TAMPER DETECTION DEMO (not saved to disk)")
        original = block.data_hash
        block.data_hash = "0" * 64  # simulate someone editing the stored record
        tampered = chain.verify_block(block.index)
        print("  Simulated an edit to the stored record's data_hash...")
        print(f"  Re-verification result: {'VALID' if tampered['valid'] else 'INVALID - tamper detected'}")
        block.data_hash = original  # restore in-memory object; nothing was persisted


if __name__ == "__main__":
    main()