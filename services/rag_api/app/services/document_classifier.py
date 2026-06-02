import re

# =========================================================
# DOCUMENT TYPE CLASSIFIER
# =========================================================

def classify_document(text: str) -> str:
    sample = text[:2000].lower()

    research_signals = [
        "abstract", "introduction", "related work",
        "methodology", "experiments", "conclusion",
        "arxiv", "et al", "figure", "table",
        "accuracy", "dataset", "baseline", "training",
        "neural", "model", "loss", "epoch", "benchmark"
    ]

    business_signals = [
        "revenue", "quarterly", "fiscal", "earnings",
        "stakeholder", "profit", "loss", "market share",
        "executive summary", "kpi", "forecast", "growth",
        "q1", "q2", "q3", "q4", "yoy", "roi"
    ]

    technical_signals = [
        "api", "endpoint", "function", "parameter",
        "returns", "install", "configuration", "usage",
        "dockerfile", "requirements", "deploy", "setup",
        "class", "method", "import", "library", "sdk"
    ]

    legal_signals = [
        "whereas", "hereinafter", "indemnify", "liability",
        "jurisdiction", "pursuant", "agreement", "clause",
        "party", "parties", "contract", "terms and conditions",
        "notwithstanding", "governing law", "arbitration"
    ]

    news_signals = [
        "reported", "according to", "spokesperson",
        "breaking", "journalist", "editor", "published",
        "press release", "interview", "sources said",
        "correspondent", "news agency"
    ]

    def score(signals):
        return sum(1 for s in signals if s in sample)

    scores = {
        "research_paper":  score(research_signals),
        "business_report": score(business_signals),
        "technical_doc":   score(technical_signals),
        "legal_doc":       score(legal_signals),
        "news_article":    score(news_signals),
    }

    best       = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score < 3:
        return "general"

    return best


def get_format_label(doc_type: str) -> str:
    return {
        "research_paper":  "Research Paper",
        "business_report": "Business Report",
        "technical_doc":   "Technical Documentation",
        "legal_doc":       "Legal Document",
        "news_article":    "News Article",
        "general":         "Document",
    }.get(doc_type, "Document")