"""Download all local model weights at Docker build time.

Keeps container cold starts fast and avoids runtime downloads on hosts with
slow or rate-limited egress. Safe to run locally too (populates your caches).
"""

from sentence_transformers import SentenceTransformer

print("Preloading embeddings: sentence-transformers/all-MiniLM-L6-v2")
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")

from doctr.models import ocr_predictor  # noqa: E402

print("Preloading DocTR: db_resnet50 + parseq")
ocr_predictor(det_arch="db_resnet50", reco_arch="parseq", pretrained=True)

from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # noqa: E402

print("Preloading TrOCR: microsoft/trocr-small-handwritten")
TrOCRProcessor.from_pretrained("microsoft/trocr-small-handwritten")
VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-small-handwritten")

print("All models cached.")
