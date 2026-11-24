"""
DuckDB Database Manager for the 4-Table Slim Semantic Mart.
"""

import os
import json
from typing import List, Optional, Dict, Any
import duckdb
from .contracts import RawDocument, SemanticExtraction, ConceptRegistry, EvalAuditLog


class SemanticDatabase:
    def __init__(self, db_path: str = "data/semantic_bi.duckdb"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.con = duckdb.connect(db_path)
        self.init_schema()

    def init_schema(self):
        """Creates the 4 core slim tables if they do not exist."""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS raw_documents (
                document_id VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                raw_text TEXT NOT NULL,
                rating INTEGER,
                created_at TIMESTAMP,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS semantic_extractions (
                extraction_id VARCHAR PRIMARY KEY,
                document_id VARCHAR NOT NULL REFERENCES raw_documents(document_id),
                surface_text VARCHAR NOT NULL,
                concept_id VARCHAR NOT NULL,
                aspect VARCHAR NOT NULL,
                sentiment VARCHAR NOT NULL,
                intensity VARCHAR,
                confidence FLOAT,
                span_start INTEGER,
                span_end INTEGER,
                evidence_quote TEXT,
                method VARCHAR
            );

            CREATE TABLE IF NOT EXISTS concept_registry (
                concept_id VARCHAR PRIMARY KEY,
                canonical_label VARCHAR NOT NULL,
                domain VARCHAR NOT NULL,
                parent_concept_id VARCHAR,
                aliases_json TEXT,
                status VARCHAR NOT NULL,
                version VARCHAR NOT NULL
            );

            CREATE TABLE IF NOT EXISTS eval_audit_log (
                eval_id VARCHAR PRIMARY KEY,
                testbed_name VARCHAR NOT NULL,
                evaluated_at TIMESTAMP NOT NULL,
                pairwise_precision FLOAT,
                pairwise_f1 FLOAT,
                oov_recall FLOAT,
                aggregate_count_error FLOAT,
                text_to_sql_accuracy FLOAT,
                token_reduction_rate FLOAT,
                passed_gates_count INTEGER
            );
        """)

    def insert_documents(self, docs: List[RawDocument]):
        for doc in docs:
            self.con.execute("""
                INSERT OR REPLACE INTO raw_documents VALUES (?, ?, ?, ?, ?, ?)
            """, [
                doc.document_id,
                doc.source,
                doc.raw_text,
                doc.rating,
                doc.created_at,
                json.dumps(doc.metadata, ensure_ascii=False)
            ])

    def insert_extractions(self, extractions: List[SemanticExtraction]):
        for ext in extractions:
            self.con.execute("""
                INSERT OR REPLACE INTO semantic_extractions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                ext.extraction_id,
                ext.document_id,
                ext.surface_text,
                ext.concept_id,
                ext.aspect,
                ext.sentiment,
                ext.intensity,
                ext.confidence,
                ext.span_start,
                ext.span_end,
                ext.evidence_quote,
                ext.method
            ])

    def insert_concepts(self, concepts: List[ConceptRegistry]):
        for c in concepts:
            self.con.execute("""
                INSERT OR REPLACE INTO concept_registry VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                c.concept_id,
                c.canonical_label,
                c.domain,
                c.parent_concept_id,
                json.dumps(c.aliases, ensure_ascii=False),
                c.status,
                c.version
            ])

    def insert_eval_audit(self, audit: EvalAuditLog):
        self.con.execute("""
            INSERT OR REPLACE INTO eval_audit_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            audit.eval_id,
            audit.testbed_name,
            audit.evaluated_at,
            audit.pairwise_precision,
            audit.pairwise_f1,
            audit.oov_recall,
            audit.aggregate_count_error,
            audit.text_to_sql_accuracy,
            audit.token_reduction_rate,
            audit.passed_gates_count
        ])

    def query_df(self, sql: str):
        return self.con.execute(sql).df()

    def close(self):
        self.con.close()
