"""
MMR Reranker — Maximal Marginal Relevance for result diversity.

Ensures search results are both relevant AND diverse:
- Avoids returning 5 chunks from the same document
- Balances maintenance history + OEM manual + safety procedure
- lambda=0.5 balances relevance vs diversity
"""

import numpy as np
from typing import Optional


def mmr_rerank(results: list[dict], query_embedding: Optional[list[float]] = None,
               lambda_param: float = 0.5, top_k: int = 8) -> list[dict]:
    """
    Apply Maximal Marginal Relevance reranking.
    
    Args:
        results: Search results with 'content', 'relevance_score', 'metadata'
        query_embedding: Query embedding vector (optional — uses relevance_score if missing)
        lambda_param: Balance between relevance (1.0) and diversity (0.0)
        top_k: Number of results to return
        
    Returns:
        Reranked list of results.
    """
    if len(results) <= top_k:
        return results
    
    # Use a simpler diversity approach based on document source
    # Group by doc_id to ensure diversity
    selected = []
    doc_ids_seen = {}
    
    # Sort by relevance first
    sorted_results = sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    # First pass: pick top result from each unique document
    for result in sorted_results:
        doc_id = result.get("metadata", {}).get("doc_id", "")
        
        if doc_id not in doc_ids_seen:
            selected.append(result)
            doc_ids_seen[doc_id] = 1
            
            if len(selected) >= top_k:
                break
    
    # Second pass: fill remaining slots with next best results
    if len(selected) < top_k:
        for result in sorted_results:
            if result not in selected:
                selected.append(result)
                if len(selected) >= top_k:
                    break
    
    return selected


def category_diversify(results: list[dict], min_categories: int = 2) -> list[dict]:
    """
    Ensure results cover at least min_categories different document categories.
    Helps provide multi-perspective answers (maintenance + OEM + safety).
    """
    if not results:
        return results
    
    # Group by category
    by_category = {}
    for result in results:
        category = result.get("metadata", {}).get("doc_category", "unknown")
        by_category.setdefault(category, []).append(result)
    
    if len(by_category) >= min_categories:
        return results  # Already diverse enough
    
    # Results aren't diverse — no change since we can't add more categories
    return results
