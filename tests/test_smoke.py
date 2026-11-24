"""
Smoke and Unit Tests for Semantic Engine v0.1 and Pydantic Contracts.
"""

import pytest
from src.texttosql_research.contracts import RawDocument, SemanticExtraction, ConceptRegistry
from src.texttosql_research.engine import SemanticEngineV01


def test_citation_mixin_passes_on_verbatim_quote():
    raw_text = "피부에 안맞아서 미개봉 2개를 반품요청 했으나 반품이 안된다고 하네요 ㅡ.ㅡ"
    ext = SemanticExtraction.model_validate(
        {
            "extraction_id": "test_1",
            "document_id": "doc_1",
            "surface_text": "반품",
            "concept_id": "PRICE_RETURN",
            "aspect": "가격/반품",
            "sentiment": "NEGATIVE",
            "evidence_quote": "반품요청 했으나 반품이 안된다고 하네요",
            "span_start": 13,
            "span_end": 35
        },
        context={"raw_text": raw_text}
    )
    assert ext.evidence_quote in raw_text


def test_citation_mixin_fails_on_hallucinated_quote():
    raw_text = "배송이 아주 빠르고 포장도 꼼꼼해요"
    with pytest.raises(ValueError, match="Citation violation"):
        SemanticExtraction.model_validate(
            {
                "extraction_id": "test_2",
                "document_id": "doc_2",
                "surface_text": "환불",
                "concept_id": "PRICE_RETURN",
                "aspect": "가격/반품",
                "sentiment": "NEGATIVE",
                "evidence_quote": "환불 요청을 거부당했습니다",  # Hallucinated phrase not in raw text!
                "span_start": 0,
                "span_end": 10
            },
            context={"raw_text": raw_text}
        )


def test_engine_negation_and_slang():
    engine = SemanticEngineV01()
    
    # 1. Slang reversal: "속건조 잡힘" -> Positive
    doc1 = RawDocument(
        document_id="doc_test_1",
        source="TEST",
        raw_text="속건조가 심했는데 이거 바르고 싹 잡힘! 쫀쫀해요",
        rating=5
    )
    res1 = engine.extract_semantic_v01(doc1)
    aspects = {r.aspect: r.sentiment for r in res1}
    assert "보습력/수분감" in aspects
    assert aspects["보습력/수분감"] == "POSITIVE"

    # 2. Multi-aspect separation: "피부에 안맞아서 반품" -> Trouble Negative + Return Negative
    doc2 = RawDocument(
        document_id="doc_test_2",
        source="TEST",
        raw_text="피부에 안맞아서 미개봉 2개를 반품요청 했으나 반품이 안된다고 하네요 ㅡ.ㅡ",
        rating=1
    )
    res2 = engine.extract_semantic_v01(doc2)
    aspects2 = {r.aspect: r.sentiment for r in res2}
    assert "트러블/자극" in aspects2
    assert "가격/반품" in aspects2
    assert aspects2["트러블/자극"] == "NEGATIVE"
    assert aspects2["가격/반품"] == "NEGATIVE"


def test_embedding_provider_mock_and_factory():
    from src.texttosql_research.embeddings import get_embedding_provider, MockEmbeddingProvider
    provider = get_embedding_provider(provider_type="mock")
    assert isinstance(provider, MockEmbeddingProvider)
    
    vecs = provider.embed_texts(["속건조 잡힘", "피부 트러블"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 128
    sim = provider.similarity(vecs[0], vecs[1])
    assert -1.0 <= sim <= 1.0

