"""
Google Cloud Vision OCR for TFT Screenshots

Simple wrapper that uses Google Cloud Vision API.
Replaces complex multi-engine preprocessing pipelines.
"""

import logging
from typing import Dict

# Import Cloud Vision OCR engine
from integrations.cloud_vision_ocr import get_cloud_vision_ocr, CloudVisionOCR

log = logging.getLogger(__name__)


# Singleton instance
_ocr_pipeline_instance = None


def get_ocr_pipeline() -> CloudVisionOCR:
    """
    Get or create OCR pipeline instance.
    
    Now returns Cloud Vision OCR engine instead of multi-engine pipeline.
    Maintains API compatibility with existing code.
    """
    global _ocr_pipeline_instance
    if _ocr_pipeline_instance is None:
        log.info("Initializing Cloud Vision OCR pipeline")
        _ocr_pipeline_instance = get_cloud_vision_ocr()
    return _ocr_pipeline_instance
