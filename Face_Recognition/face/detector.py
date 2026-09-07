"""Face detection (YuNet) + embedding (SFace) using OpenCV Zoo models.

No dlib / face_recognition. Pure opencv-python + the two ONNX models
already in models/.
"""
import os
import cv2

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
DETECTOR_MODEL = os.path.join(MODELS_DIR, "face_detection_yunet_2026may.onnx")
RECOGNIZER_MODEL = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")


class FaceIdentifier:
    def __init__(self):
        if not os.path.exists(DETECTOR_MODEL):
            raise FileNotFoundError(f"Detector model not found: {DETECTOR_MODEL}")
        if not os.path.exists(RECOGNIZER_MODEL):
            raise FileNotFoundError(f"Recognizer model not found: {RECOGNIZER_MODEL}")

        self.detector = cv2.FaceDetectorYN_create(
            DETECTOR_MODEL, "", (320, 320), score_threshold=0.7
        )
        self.recognizer = cv2.FaceRecognizerSF_create(RECOGNIZER_MODEL, "")

    def process(self, image_path: str):
        """Returns (aligned_face_bgr, embedding, num_faces_detected).

        Raises FileNotFoundError / ValueError / RuntimeError with a clear
        message on missing file, unreadable file, or no face found.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image (unsupported/corrupt file): {image_path}")

        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)

        if faces is None or len(faces) == 0:
            raise RuntimeError("No face detected in the image.")

        num_faces = len(faces)
        if num_faces > 1:
            # Largest bounding box (index 2,3 = w,h) = most likely subject.
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)

        face = faces[0]
        aligned = self.recognizer.alignCrop(img, face)
        embedding = self.recognizer.feature(aligned)

        return aligned, embedding, num_faces