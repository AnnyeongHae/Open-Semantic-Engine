"""
Hybrid Semantic Normalization & Aspect-Based Sentiment Analysis (ABSA) Engine (v0.1)
Combines Kiwi morphological parsing, user-dictionary tuning, context-aware negation handling,
and Instructor-style Citation verification.
"""

import re
import os
import yaml
from typing import List, Dict, Any, Tuple, Optional
from kiwipiepy import Kiwi
from .contracts import RawDocument, SemanticExtraction, ConceptRegistry


class SemanticEngineV01:
    def __init__(self, domain_pack_path: str = "src/texttosql_research/domain_packs/k_beauty.yaml"):
        self.kiwi = Kiwi()
        self.domain_pack = self._load_domain_pack(domain_pack_path)
        self._register_user_words()

    def _load_domain_pack(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {"aspects": [], "slangs": []}

    def _register_user_words(self):
        """Registers specialized K-Beauty terms into Kiwi to prevent bad token fragmentation."""
        for s in self.domain_pack.get("slangs", []):
            slang = s.get("slang")
            if slang:
                try:
                    self.kiwi.add_user_word(slang, "NNG", score=10.0)
                except Exception:
                    pass
        # Add common compounding terms
        for word in ["피디알엔", "PDRN", "히알루론산", "선스틱", "재구매", "미개봉", "유브이"]:
            try:
                self.kiwi.add_user_word(word, "NNG", score=10.0)
            except Exception:
                pass

    def get_canonical_concepts(self) -> List[ConceptRegistry]:
        """Generates ConceptRegistry items from the domain pack."""
        concepts = []
        for aspect in self.domain_pack.get("aspects", []):
            concepts.append(ConceptRegistry(
                concept_id=aspect["id"],
                canonical_label=aspect["canonical_label"],
                domain=self.domain_pack.get("domain", "K_BEAUTY"),
                aliases=aspect.get("keywords", []),
                status="APPROVED",
                version=self.domain_pack.get("version", "0.1.0")
            ))
        for s in self.domain_pack.get("slangs", []):
            concepts.append(ConceptRegistry(
                concept_id=s["concept_id"],
                canonical_label=s["canonical_label"],
                domain=self.domain_pack.get("domain", "K_BEAUTY"),
                parent_concept_id=s.get("aspect"),
                aliases=[s["slang"]],
                status="APPROVED",
                version=self.domain_pack.get("version", "0.1.0")
            ))
        return concepts

    def analyze_legacy_token_baseline(self, doc: RawDocument) -> Dict[str, Any]:
        """
        Legacy Baseline 1 (Naïve Tokenizer / Bag of Words):
        Splits tokens without aspect-sentiment linking. Represents traditional open-source NLP.
        """
        tokens = [t.form for t in self.kiwi.tokenize(doc.raw_text)]
        return {
            "method": "LEGACY_TOKEN_BASELINE",
            "token_count": len(tokens),
            "sample_tokens": tokens[:10],
            "explanation": "단어 빈도만 계산 가능. 단어와 감성/속성을 결합하지 못해 '안맞아서 반품' 같은 맥락을 분리 불가."
        }

    def analyze_naive_rule_baseline(self, doc: RawDocument) -> List[Dict[str, Any]]:
        """
        Legacy Baseline 2 (Naïve Keyword Matching):
        Matches keywords flatly without negation or context reversal.
        """
        results = []
        text = doc.raw_text
        for aspect in self.domain_pack.get("aspects", []):
            for kw in aspect.get("keywords", []):
                if kw in text:
                    # Naïve polarity: assume positive unless harsh words appear
                    pol = "POSITIVE" if "좋" in text or "짱" in text or "굿" in text else "NEGATIVE"
                    results.append({
                        "aspect": aspect["canonical_label"],
                        "keyword": kw,
                        "sentiment": pol,
                        "method": "NAIVE_KEYWORD_RULE"
                    })
                    break
        return results

    def extract_semantic_v01(self, doc: RawDocument) -> List[SemanticExtraction]:
        """
        Proposed v0.1 Hybrid Semantic Engine:
        Sentence segmentation -> Aspect discovery -> Contextual Polarity Inversion -> Citation verification.
        """
        extractions: List[SemanticExtraction] = []
        raw_text = doc.raw_text
        sentences = self.kiwi.split_into_sents(raw_text)

        ext_idx = 1
        for sent in sentences:
            stext = sent.text.strip()
            if not stext:
                continue

            sent_start = sent.start
            sent_end = sent.end

            # 1. Check slang matches first (High precision)
            for s in self.domain_pack.get("slangs", []):
                slang = s["slang"]
                if slang in stext:
                    # Context negation check e.g. "속건조 잡힘", "뒤집어짐 없음"
                    sentiment = s["sentiment"]
                    if "잡힘" in stext or "해결" in stext or "없" in stext or "개선" in stext:
                        if sentiment == "NEGATIVE":
                            sentiment = "POSITIVE"  # e.g., "속건조 잡힘" -> POSITIVE

                    # Citation quote
                    q_start = raw_text.find(stext)
                    q_end = q_start + len(stext) if q_start >= 0 else sent_end

                    ext = SemanticExtraction.model_validate(
                        {
                            "extraction_id": f"{doc.document_id}_ext_{ext_idx}",
                            "document_id": doc.document_id,
                            "surface_text": slang,
                            "concept_id": s["concept_id"],
                            "aspect": s["aspect"],
                            "sentiment": sentiment,
                            "intensity": "STRONG",
                            "confidence": 0.96,
                            "evidence_quote": stext,
                            "span_start": sent_start,
                            "span_end": sent_end,
                            "method": "SLANG_NORMALIZATION"
                        },
                        context={"raw_text": raw_text}
                    )
                    extractions.append(ext)
                    ext_idx += 1

            # 2. Check general aspect matching
            for aspect in self.domain_pack.get("aspects", []):
                matched_kw = None
                for kw in aspect.get("keywords", []):
                    if kw in stext:
                        matched_kw = kw
                        break
                
                if matched_kw:
                    # Contextual Sentiment Disambiguation
                    pos_score = sum(1 for cue in aspect.get("positive_cues", []) if cue in stext)
                    neg_score = sum(1 for cue in aspect.get("negative_cues", []) if cue in stext)

                    # Negation patterns: "안", "못", "않", "없"
                    has_negation = bool(re.search(r"(안\s+|못\s+|않|없|별로|비추|아니)", stext))
                    has_positive_tone = bool(re.search(r"(좋|최고|짱|굿|만족|추천|순해)", stext))
                    has_negative_tone = bool(re.search(r"(불편|따가|트러블|비싸|안맞|반품|환불|자극|끈적)", stext))

                    if neg_score > pos_score or (has_negative_tone and not has_negation):
                        sentiment = "NEGATIVE"
                    elif pos_score > neg_score or (has_positive_tone and not has_negation):
                        sentiment = "POSITIVE"
                    elif "끈적이지 않" in stext or "당김 없" in stext or "자극 없" in stext:
                        sentiment = "POSITIVE"  # Negative trait negated = Positive
                    elif has_negation and has_positive_tone:
                        sentiment = "NEGATIVE"  # e.g., "좋지 않다"
                    else:
                        # Fallback by rating if available
                        if doc.rating is not None:
                            sentiment = "POSITIVE" if doc.rating >= 4 else ("NEGATIVE" if doc.rating <= 2 else "NEUTRAL")
                        else:
                            sentiment = "NEUTRAL"

                    # Avoid duplicate extraction on same sentence for same aspect
                    if any(e.evidence_quote == stext and e.aspect == aspect["canonical_label"] for e in extractions):
                        continue

                    ext = SemanticExtraction.model_validate(
                        {
                            "extraction_id": f"{doc.document_id}_ext_{ext_idx}",
                            "document_id": doc.document_id,
                            "surface_text": matched_kw,
                            "concept_id": aspect["id"],
                            "aspect": aspect["canonical_label"],
                            "sentiment": sentiment,
                            "intensity": "MODERATE",
                            "confidence": 0.90,
                            "evidence_quote": stext,
                            "span_start": sent_start,
                            "span_end": sent_end,
                            "method": "CONTEXT_ASPECT_ABSA"
                        },
                        context={"raw_text": raw_text}
                    )
                    extractions.append(ext)
                    ext_idx += 1

        # Fallback if no sentence triggered an aspect but document has clear content
        if not extractions:
            sentiment = "POSITIVE" if (doc.rating and doc.rating >= 4) else ("NEGATIVE" if (doc.rating and doc.rating <= 2) else "NEUTRAL")
            first_sent = sentences[0].text.strip() if sentences else raw_text[:50]
            extractions.append(SemanticExtraction.model_validate(
                {
                    "extraction_id": f"{doc.document_id}_ext_1",
                    "document_id": doc.document_id,
                    "surface_text": "전반적 사용감",
                    "concept_id": "ASPECT_GENERAL",
                    "aspect": "사용감/종합",
                    "sentiment": sentiment,
                    "intensity": "MODERATE",
                    "confidence": 0.70,
                    "evidence_quote": first_sent,
                    "span_start": 0,
                    "span_end": min(len(raw_text), len(first_sent)),
                    "method": "FALLBACK_RATING_ABSA"
                },
                context={"raw_text": raw_text}
            ))

        return extractions
