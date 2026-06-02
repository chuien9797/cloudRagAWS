import re


# =========================================================
# QUESTION TYPE DETECTOR
# =========================================================
def is_factual_question(question: str) -> bool:
    q = question.lower().strip()

    factual_signals = [
        "how much", "how many", "what is", "what are",
        "who is", "who are", "when is", "when was",
        "where is", "where was", "which", "what was",
        "what did", "how did", "does", "did", "is there",
        "what price", "what cost", "how old", "how long",
        "what color", "what colour", "how far", "how fast",
    ]

    return any(q.startswith(s) for s in factual_signals)


def is_summary_request(question: str) -> bool:
    q = question.lower().strip()
    summary_signals = [
        "summarize", "summary", "overview", "key contributions",
        "main contributions", "limitations", "future work",
        "executive summary", "what is this paper about",
    ]
    return any(signal in q for signal in summary_signals)


def is_comparison_request(question: str) -> bool:
    q = question.lower().strip()
    comparison_signals = [
        "rank",
        "ranking",
        "strongest",
        "best",
        "better",
        "compare",
        "comparison",
        "most suitable",
        "most promising",
        "recommend",
        "which should",
        "which is stronger",
        "which is the strongest",
    ]
    return any(signal in q for signal in comparison_signals)


def is_people_ranking_request(question: str) -> bool:
    q = question.lower().strip()
    people_signals = [
        "team",
        "member",
        "members",
        "person",
        "people",
        "student",
        "students",
        "candidate",
        "candidates",
        "who is the strongest",
        "who seems strongest",
    ]
    return is_comparison_request(question) and any(signal in q for signal in people_signals)


# =========================================================
# DIRECT QA PROMPT
# FIX: no bullet rules — just a clean instruction + format
# =========================================================
def prompt_direct_qa(context: str, question: str, filename: str) -> str:
    return f"""Read the context and answer the user's question directly.
Only use information from the context. If the answer is not there, say "Not found in document."
Be concrete and complete when the question asks for multiple items or detailed methodology.
If the user asks more than one question, answer every part explicitly in separate short paragraphs.
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the context.

Context: {context}

Question: {question}

Answer:"""


def prompt_comparison_qa(context: str, question: str, filename: str) -> str:
    return f"""Read the context and answer the user's question as an evidence-based comparison.
Only use information from the context.
If the user asks you to rank, compare, choose the strongest option, or recommend one option over another, infer a reasonable ranking from the available evidence even if the document does not explicitly provide a final ranking.
First identify the distinct candidates that appear in the context by their exact names.
Do not invent candidates, rename candidates, or list the same candidate more than once.
If the document contains numbered ideas or proposals, preserve their numbering and titles exactly as written.
State the criteria you used, compare the candidates against those criteria, and then give a clear conclusion.
If the context is too incomplete to compare all candidates fairly, give a partial ranking of the candidates you can see and explicitly say which candidates or evidence are missing instead of saying "Not found in document."
Return the answer in this format:
1. Candidate name
   - Why it ranks here
   - Feasibility
   - Technical depth
   - Capstone suitability
After the ranking, add a short final note called "Confidence / gaps" describing any uncertainty or missing context.
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the context.

Context: {context}

Question: {question}

Answer:"""


def prompt_people_comparison_qa(context: str, question: str, filename: str) -> str:
    return f"""Read the context and answer the user's question as a careful evidence-based comparison of people or team members.
Only use information from the context.
First identify the distinct people or candidates that appear in the context by their exact names.
Do not invent people, rename them, or list the same person more than once.
If the question is vague, such as "who is the strongest", do not treat it as an absolute truth claim.
Instead, state the evaluation dimension you are using based on the document, such as suitability for this project, technical depth, implementation readiness, or relevant prior experience.
If the document does not justify a single clear winner, say that explicitly and describe the strongest candidate only in the specific sense supported by the evidence.
Compare the candidates fairly, mention uncertainty, and avoid overclaiming.
Return the answer in this format:
1. Candidate name
   - Why this person ranks here
   - Most relevant strengths from the document
   - Limits or missing evidence
After the ranking or recommendation, add a short final note called "Assumption used" that states the evaluation dimension you chose, and a short note called "Confidence / gaps" that explains any uncertainty.
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the context.

Context: {context}

Question: {question}

Answer:"""


# =========================================================
# RESEARCH PAPER PROMPT
# FIX: rules removed from body, instruction is conversational
# =========================================================
def prompt_research_paper(context: str, question: str, filename: str) -> str:
    return f"""Read the following excerpts from the research paper '{filename}' and fill in the template below.
Only use information from the excerpts. Copy numbers and model names exactly. If a section is not covered, write "Not found in document."
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the excerpts.

Excerpts:
{context}

Fill in this template:

**Paper Title & Authors:**
[title and authors from the excerpts, or "Not stated"]

**Overview:**
[one or two sentences on what problem the paper solves and how]

**Key Contributions:**
1. [first contribution]
2. [second contribution]
3. [third contribution or "Not stated"]

**Method:**
[the proposed technique, with exact model names and terms]

**Results:**
[exact accuracy numbers and comparisons from the excerpts]

**Limitations / Future Work:**
[limitations or future directions, or "Not found in document"]
"""


# =========================================================
# BUSINESS REPORT PROMPT
# =========================================================
def prompt_business_report(context: str, question: str, filename: str) -> str:
    return f"""Read the following excerpts from '{filename}' and fill in the template below.
Only use information from the excerpts. Include exact figures and percentages. If a section is not covered, write "Not found in document."
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the excerpts.

Excerpts:
{context}

Fill in this template:

**Report Title & Period:**
[infer from excerpts]

**Executive Summary:**
[key takeaway in 2-3 sentences]

**Key Metrics:**
- [metric 1: value]
- [metric 2: value]
- [metric 3: value]

**Performance Analysis:**
[what went well, what declined, key drivers]

**Risks & Challenges:**
[risks or concerns mentioned]

**Outlook / Recommendations:**
[forward-looking statements or recommendations]
"""


# =========================================================
# TECHNICAL DOC PROMPT
# =========================================================
def prompt_technical_doc(context: str, question: str, filename: str) -> str:
    return f"""Read the following excerpts from '{filename}' and fill in the template below.
Only use information from the excerpts. Be precise about names, parameters, and steps. If a section is not covered, write "Not found in document."
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the excerpts.

Excerpts:
{context}

Fill in this template:

**Tool / System Name:**
[infer from excerpts]

**Purpose:**
[what this tool or system does]

**Key Components:**
- [component 1]
- [component 2]
- [component 3]

**Usage / Setup:**
[how to install, configure, or use it]

**API / Interface:**
[key endpoints, functions, or parameters]

**Notes & Limitations:**
[caveats, known issues, or requirements]
"""


# =========================================================
# LEGAL DOC PROMPT
# =========================================================
def prompt_legal_doc(context: str, question: str, filename: str) -> str:
    return f"""Read the following excerpts from '{filename}' and fill in the template below.
Only use information from the excerpts. Do not interpret beyond what is written. If a section is not covered, write "Not found in document."
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the excerpts.

Excerpts:
{context}

Fill in this template:

**Document Type & Parties:**
[infer from excerpts]

**Purpose:**
[what this document establishes or governs]

**Key Terms & Obligations:**
- [term or obligation 1]
- [term or obligation 2]
- [term or obligation 3]

**Rights & Restrictions:**
[what each party is allowed or not allowed to do]

**Duration & Termination:**
[how long the agreement lasts and how it can end]

**Notable Clauses:**
[unusual, important, or high-risk clauses]
"""


# =========================================================
# NEWS ARTICLE PROMPT
# =========================================================
def prompt_news_article(context: str, question: str, filename: str) -> str:
    return f"""Read the following excerpts from '{filename}' and fill in the template below.
Only use information from the excerpts. Stick to stated facts only. If a section is not covered, write "Not found in document."
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the excerpts.

Excerpts:
{context}

Fill in this template:

**Headline:**
[infer from excerpts]

**Summary:**
[what happened, in 2-3 sentences]

**Key Facts:**
- [fact 1]
- [fact 2]
- [fact 3]

**People / Organisations Involved:**
[who is mentioned and their role]

**Context & Background:**
[background information provided]

**Implications:**
[what this means going forward, if mentioned]
"""


# =========================================================
# GENERAL PROMPT
# =========================================================
def prompt_general(context: str, question: str, filename: str) -> str:
    return f"""Read the following excerpts from '{filename}' and fill in the template below.
Only use information from the excerpts. If a section is not covered, write "Not found in document."
Use citation markers like [1] after every factual claim. Only cite source numbers that appear in the excerpts.

Excerpts:
{context}

Fill in this template:

**Document Title:**
[infer from excerpts]

**Overview:**
[what this document is about]

**Key Points:**
1. [key point 1]
2. [key point 2]
3. [key point 3]

**Details:**
[important details, data, or specifics]

**Conclusion / Summary:**
[final takeaway or conclusion]
"""


# =========================================================
# TEMPLATE ROUTER
# =========================================================
TEMPLATE_MAP = {
    "research_paper":  prompt_research_paper,
    "business_report": prompt_business_report,
    "technical_doc":   prompt_technical_doc,
    "legal_doc":       prompt_legal_doc,
    "news_article":    prompt_news_article,
    "general":         prompt_general,
}


def build_prompt(
    context:  str,
    question: str,
    filename: str,
    doc_type: str
) -> str:
    if is_people_ranking_request(question):
        return prompt_people_comparison_qa(context, question, filename or "the document")

    if is_comparison_request(question):
        return prompt_comparison_qa(context, question, filename or "the document")

    if is_factual_question(question) or not is_summary_request(question):
        return prompt_direct_qa(context, question, filename or "the document")

    template_fn = TEMPLATE_MAP.get(doc_type, prompt_general)
    return template_fn(context, question, filename or "the document")
