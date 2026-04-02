"""Low-level Lightroom XMP helpers used by characterization tests."""

from __future__ import annotations

import zlib
from xml.etree import ElementTree

from pixelpast.ingestion.lightroom_catalog.contracts import LightroomXmpPayload

_NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xmpMM": "http://ns.adobe.com/xap/1.0/mm/",
    "lr": "http://ns.adobe.com/lightroom/1.0/",
}

_XMP_META_TAG = "{adobe:ns:meta/}xmpmeta"
_RDF_TAG = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"
_DESCRIPTION_TAG = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description"


def decompress_lightroom_xmp_blob(blob: bytes) -> bytes:
    """Decompress a Lightroom XMP BLOB using the fixture-backed v1 rule."""

    if len(blob) < 5:
        raise ValueError("Lightroom XMP blob must include a 4-byte header and payload.")
    return zlib.decompress(blob[4:])


def parse_lightroom_xmp_payload(*, image_id: int, blob: bytes) -> LightroomXmpPayload:
    """Parse one Lightroom XMP BLOB into the stable v1 payload contract."""

    xml_bytes = decompress_lightroom_xmp_blob(blob)
    root = ElementTree.fromstring(xml_bytes)
    if root.tag != _XMP_META_TAG:
        raise ValueError(
            "Lightroom XMP payload must start with an x:xmpmeta root element."
        )

    rdf = root.find(_RDF_TAG)
    if rdf is None:
        raise ValueError("Lightroom XMP payload must contain an rdf:RDF node.")
    description = rdf.find(_DESCRIPTION_TAG)
    if description is None:
        raise ValueError(
            "Lightroom XMP payload must contain an rdf:Description node."
        )

    return LightroomXmpPayload(
        image_id=image_id,
        xml_text=xml_bytes.decode("utf-8"),
        document_id=_normalize_optional_text(
            description.attrib.get(f"{{{_NS['xmpMM']}}}DocumentID")
        ),
        preserved_file_name=_normalize_optional_text(
            description.attrib.get(f"{{{_NS['xmpMM']}}}PreservedFileName")
        ),
        title=_normalize_optional_text(
            root.findtext(".//dc:title/rdf:Alt/rdf:li", namespaces=_NS)
        ),
        explicit_keywords=tuple(
            keyword
            for keyword in (
                _normalize_optional_text(node.text)
                for node in root.findall(".//dc:subject/rdf:Bag/rdf:li", _NS)
            )
            if keyword is not None
        ),
        hierarchical_keywords=tuple(
            keyword
            for keyword in (
                _normalize_optional_text(node.text)
                for node in root.findall(
                ".//lr:hierarchicalSubject/rdf:Bag/rdf:li",
                _NS,
            )
            )
            if keyword is not None
        ),
    )


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    return normalized


__all__ = [
    "decompress_lightroom_xmp_blob",
    "parse_lightroom_xmp_payload",
]
