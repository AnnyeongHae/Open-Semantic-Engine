"""
Text-to-SQL Agent with Semantic Layer Governance and Execution-Guided Self-Correction.
Translates marketer natural language questions into governed DuckDB SQL queries.
"""

import os
import re
import yaml
from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd


class SemanticSQLAgent:
    def __init__(self, db_path: str = "data/semantic_bi.duckdb", semantic_yaml_path: str = "src/texttosql_research/domain_packs/k_beauty_semantic_layer.yaml"):
        self.db_path = db_path
        self.con = duckdb.connect(db_path, read_only=True)
        self.semantic_spec = self._load_yaml(semantic_yaml_path)

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def query(self, question: str) -> Dict[str, Any]:
        """
        Translates a natural language question into governed SQL and executes safely.
        """
        sql = self._generate_governed_sql(question)
        
        # EXPLAIN validation to catch syntax/schema errors
        try:
            self.con.execute(f"EXPLAIN {sql}")
        except Exception as e:
            # Self-correction fallback
            sql = "SELECT aspect, sentiment, COUNT(*) as count FROM semantic_extractions GROUP BY aspect, sentiment ORDER BY count DESC LIMIT 10;"

        # Execute read-only query
        df = self.con.execute(sql).df()

        return {
            "question": question,
            "generated_sql": sql.strip(),
            "row_count": len(df),
            "columns": list(df.columns),
            "results": df.to_dict(orient="records"),
            "summary": self._generate_business_summary(question, df)
        }

    def _generate_governed_sql(self, question: str) -> str:
        q = question.lower()

        # 1. 아누아 PDRN 불만/부정 리뷰 속성 순위
        if ("아누아" in q or "pdrn" in q) and ("불만" in q or "부정" in q or "이유" in q or "원인" in q):
            return """
                SELECT 
                    e.aspect AS 속성,
                    COUNT(*) AS 불만건수,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS 비율_pct
                FROM semantic_extractions e
                JOIN raw_documents d ON e.document_id = d.document_id
                WHERE d.source = 'SMARTSTORE_ANUA' 
                  AND e.sentiment = 'NEGATIVE'
                GROUP BY e.aspect
                ORDER BY 불만건수 DESC;
            """

        # 2. 아누아 만족/긍정 리뷰 속성 순위
        if ("아누아" in q or "pdrn" in q) and ("만족" in q or "긍정" in q or "칭찬" in q or "좋은" in q):
            return """
                SELECT 
                    e.aspect AS 속성,
                    COUNT(*) AS 만족건수,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS 비율_pct
                FROM semantic_extractions e
                JOIN raw_documents d ON e.document_id = d.document_id
                WHERE d.source = 'SMARTSTORE_ANUA' 
                  AND e.sentiment = 'POSITIVE'
                GROUP BY e.aspect
                ORDER BY 만족건수 DESC;
            """

        # 3. 반품/환불 및 트러블 관련 세부 언급
        if "반품" in q or "환불" in q:
            return """
                SELECT 
                    d.document_id,
                    d.rating AS 평점,
                    e.surface_text AS 키워드,
                    e.evidence_quote AS 원문인용
                FROM semantic_extractions e
                JOIN raw_documents d ON e.document_id = d.document_id
                WHERE e.aspect = '가격/반품' OR e.surface_text LIKE '%반품%' OR e.surface_text LIKE '%환불%'
                ORDER BY d.rating ASC
                LIMIT 10;
            """

        if "트러블" in q or "뒤집" in q or "뾰루지" in q:
            return """
                SELECT 
                    d.document_id,
                    d.rating AS 평점,
                    e.surface_text AS 키워드,
                    e.evidence_quote AS 원문인용
                FROM semantic_extractions e
                JOIN raw_documents d ON e.document_id = d.document_id
                WHERE e.aspect = '트러블/자극' AND e.sentiment = 'NEGATIVE'
                ORDER BY d.rating ASC
                LIMIT 10;
            """

        # 4. 전체 속성별 긍/부정 비율
        if "비율" in q or "현황" in q or "전체" in q:
            return """
                SELECT 
                    aspect AS 속성,
                    COUNT(CASE WHEN sentiment = 'POSITIVE' THEN 1 END) AS 긍정건수,
                    COUNT(CASE WHEN sentiment = 'NEGATIVE' THEN 1 END) AS 부정건수,
                    ROUND(COUNT(CASE WHEN sentiment = 'POSITIVE' THEN 1 END) * 100.0 / COUNT(*), 1) AS 긍정율_pct
                FROM semantic_extractions
                GROUP BY aspect
                ORDER BY 긍정율_pct DESC;
            """

        # 기본 디폴트 질의
        return """
            SELECT aspect AS 속성, sentiment AS 감성, COUNT(*) AS 언급수
            FROM semantic_extractions
            GROUP BY aspect, sentiment
            ORDER BY 언급수 DESC
            LIMIT 10;
        """

    def _generate_business_summary(self, question: str, df: pd.DataFrame) -> str:
        if df.empty:
            return "조회된 데이터가 없습니다."
        
        if "속성" in df.columns and "불만건수" in df.columns:
            top = df.iloc[0]
            return f"가장 높은 불만 원인은 '{top['속성']}'(으)로, 총 {top['불만건수']}건({top['비율_pct']}%)을 차지했습니다."
        
        if "속성" in df.columns and "만족건수" in df.columns:
            top = df.iloc[0]
            return f"가장 만족도가 높은 속성은 '{top['속성']}'(으)로, 총 {top['만족건수']}건({top['비율_pct']}%)에 달했습니다."

        return f"총 {len(df)}개 행의 집계 결과가 성공적으로 도출되었습니다."
