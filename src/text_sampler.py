"""
Smart Book Digest — Adaptive text sampling for large books.

Instead of blindly truncating to the first N characters (which misses
the second half of long books), this module creates a representative
digest that covers the entire narrative arc.

No external NLP dependencies — pure Python string operations.
"""

import re
import math


# Words that indicate descriptive/narrative text (not dialogue)
DESCRIPTIVE_INDICATORS = {
    # Colors
    'red', 'blue', 'green', 'golden', 'silver', 'dark', 'bright', 'pale',
    'white', 'black', 'crimson', 'scarlet', 'azure', 'grey', 'gray',
    # Physical descriptors
    'tall', 'short', 'thin', 'thick', 'massive', 'tiny', 'enormous',
    'slender', 'broad', 'narrow', 'wide', 'long', 'round',
    # Sensory
    'cold', 'warm', 'hot', 'soft', 'hard', 'rough', 'smooth', 'sharp',
    'loud', 'quiet', 'silent', 'sweet', 'bitter', 'faint',
    # Atmospheric
    'ancient', 'ruined', 'crumbling', 'towering', 'vast', 'shadowy',
    'gleaming', 'dusty', 'moonlit', 'sunlit', 'misty', 'foggy',
    # Emotional intensity
    'suddenly', 'desperately', 'furiously', 'trembling', 'screaming',
    'whispered', 'sobbing', 'laughing', 'gasped', 'shouted',
}

# Chapter heading patterns (ordered by specificity)
CHAPTER_PATTERNS = [
    # "Chapter 1", "CHAPTER ONE", "Chapter I", "Chapter 1: Title"
    re.compile(r'^\s*(chapter|chapitre|kapittel|kapitel)\s+[\dIVXLCivxlc]+[.:\s—–-]*.*$', re.IGNORECASE | re.MULTILINE),
    # "Part 1", "PART ONE", "Part I"
    re.compile(r'^\s*(part|book|section|act)\s+[\dIVXLCivxlc]+[.:\s—–-]*.*$', re.IGNORECASE | re.MULTILINE),
    # Numbered: "1.", "1)", "I.", but only when alone on a line
    re.compile(r'^\s*[\dIVXLCivxlc]+[.)]\s*$', re.MULTILINE),
    # All-caps headings (short lines, likely titles)
    re.compile(r'^[A-Z][A-Z\s\d]{3,50}$', re.MULTILINE),
]


def split_into_chapters(text: str) -> list:
    """
    Split book text into chapters using regex pattern matching.
    
    Returns a list of dicts: [{"title": "Chapter 1", "content": "...", "index": 0}, ...]
    If no chapters detected, splits into ~10 equal segments.
    """
    # Try each pattern until we find one that gives reasonable results
    for pattern in CHAPTER_PATTERNS:
        matches = list(pattern.finditer(text))
        
        # Need at least 2 chapters to be meaningful
        if len(matches) >= 2:
            chapters = []
            for i, match in enumerate(matches):
                title = match.group().strip()
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                
                # Skip very short "chapters" (likely false positives)
                if len(content) < 200:
                    continue
                    
                chapters.append({
                    "title": title[:80],
                    "content": content,
                    "index": len(chapters)
                })
            
            if len(chapters) >= 2:
                print(f"Detected {len(chapters)} chapters using pattern: {pattern.pattern[:40]}...")
                return chapters
    
    # No chapters detected — split into equal segments
    print("No chapter headings detected. Splitting into segments...")
    return _split_into_segments(text)


def _split_into_segments(text: str, words_per_segment: int = 5000) -> list:
    """
    Split text into roughly equal segments of about N words, 
    breaking cleanly at paragraph boundaries.
    """
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    segments = []
    current_segment_paragraphs = []
    current_word_count = 0
    segment_index = 0
    
    for p in paragraphs:
        word_count = len(p.split())
        current_segment_paragraphs.append(p)
        current_word_count += word_count
        
        # If we hit the target word count, finalize this segment
        if current_word_count >= words_per_segment:
            content = "\n\n".join(current_segment_paragraphs)
            segments.append({
                "title": f"Segment {segment_index + 1}",
                "content": content,
                "index": segment_index
            })
            segment_index += 1
            current_segment_paragraphs = []
            current_word_count = 0
            
    # Add any remaining paragraphs as the final segment
    if current_segment_paragraphs:
        content = "\n\n".join(current_segment_paragraphs)
        segments.append({
            "title": f"Segment {segment_index + 1}",
            "content": content,
            "index": segment_index
        })
        
    return segments


def score_paragraph(paragraph: str) -> float:
    """
    Score a paragraph's "descriptiveness" using simple heuristics.
    Higher score = more visually descriptive / narratively important.
    
    No NLP/spaCy — just word-level statistics.
    """
    if not paragraph or len(paragraph) < 30:
        return 0.0
    
    words = paragraph.lower().split()
    word_count = len(words)
    
    if word_count < 5:
        return 0.0
    
    score = 0.0
    
    # 1. Length bonus: longer paragraphs are usually narrative, not dialogue
    #    Sweet spot is 50-200 words
    if 50 <= word_count <= 200:
        score += 2.0
    elif 30 <= word_count <= 300:
        score += 1.0
    
    # 2. Descriptive word density
    descriptive_count = sum(1 for w in words if w.strip('.,!?;:"\'-()') in DESCRIPTIVE_INDICATORS)
    descriptive_density = descriptive_count / word_count
    score += descriptive_density * 15  # Max ~3-4 points for very descriptive text
    
    # 3. Comma density (complex sentences = more description)
    comma_count = paragraph.count(',')
    comma_density = comma_count / max(1, word_count)
    score += min(comma_density * 10, 2.0)  # Cap at 2 points
    
    # 4. Dialogue penalty: text heavy with quotes is dialogue, not description
    quote_chars = paragraph.count('"') + paragraph.count("'") + paragraph.count('\u201c') + paragraph.count('\u201d')
    if quote_chars > 4:
        score -= 1.5  # Penalty for heavy dialogue
    
    # 5. Action/drama bonus: exclamation marks, question marks
    if '!' in paragraph or '?' in paragraph:
        score += 0.5
    
    # 6. Paragraph with proper nouns (capitalized words not at sentence start)
    #    These often introduce characters or places
    sentences = re.split(r'[.!?]\s+', paragraph)
    proper_nouns = 0
    for sent in sentences:
        words_in_sent = sent.split()
        # Skip first word of each sentence (always capitalized)
        for w in words_in_sent[1:]:
            if w and w[0].isupper() and w.isalpha():
                proper_nouns += 1
    if proper_nouns >= 2:
        score += 1.0
    
    return score


def _get_paragraphs(text: str) -> list:
    """Split text into paragraphs, filtering out empty ones."""
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 30]


def create_book_digest(full_text: str, target_chars: int = 70000) -> str:
    """
    Creates a representative digest of the full book.
    
    Covers beginning, middle, and end proportionally by:
    1. Splitting into chapters
    2. Allocating char budget per chapter (proportional to length)
    3. Selecting the best paragraphs from each chapter
    4. Stitching with chapter markers
    
    Args:
        full_text: The complete book text
        target_chars: Target size for the digest (~70K default)
    
    Returns:
        A digest string covering the full narrative arc
    """
    # If text is already small enough, return as-is
    if len(full_text) <= target_chars:
        print(f"Book is {len(full_text)} chars - no digest needed (under {target_chars} limit)")
        return full_text
    
    print(f"Creating book digest: {len(full_text)} chars -> target {target_chars} chars")
    
    # 1. Split into chapters
    chapters = split_into_chapters(full_text)
    
    if not chapters:
        print("Could not split text. Using proportional sampling.")
        return _proportional_sample(full_text, target_chars)
    
    # 2. Calculate total content and allocate budget
    total_content_chars = sum(len(ch["content"]) for ch in chapters)
    
    # Reserve some chars for chapter markers
    marker_budget = len(chapters) * 50  # ~50 chars per marker
    content_budget = target_chars - marker_budget
    
    # 3. Give early chapters slightly more budget (character/world introductions)
    # First 20% of chapters get 30% of budget, rest is proportional
    early_cutoff = max(1, len(chapters) // 5)
    early_chapters = chapters[:early_cutoff]
    later_chapters = chapters[early_cutoff:]
    
    early_budget = int(content_budget * 0.30) if later_chapters else content_budget
    later_budget = content_budget - early_budget
    
    # 4. Sample from each chapter
    digest_parts = []
    
    # Process early chapters (more budget)
    if early_chapters:
        per_chapter_early = early_budget // len(early_chapters)
        for ch in early_chapters:
            sampled = _sample_chapter(ch, per_chapter_early)
            digest_parts.append(f"--- {ch['title']} ---\n{sampled}")
    
    # Process later chapters (proportional budget)
    if later_chapters:
        later_total = sum(len(ch["content"]) for ch in later_chapters)
        for ch in later_chapters:
            # Proportional allocation based on chapter length
            if later_total > 0:
                proportion = len(ch["content"]) / later_total
                chapter_budget = int(later_budget * proportion)
            else:
                chapter_budget = later_budget // len(later_chapters)
            
            # Minimum budget per chapter
            chapter_budget = max(chapter_budget, 500)
            
            sampled = _sample_chapter(ch, chapter_budget)
            digest_parts.append(f"--- {ch['title']} ---\n{sampled}")
    
    digest = "\n\n".join(digest_parts)
    
    # Trim to target if slightly over
    if len(digest) > target_chars:
        digest = digest[:target_chars]
    
    print(f"Book digest created: {len(digest)} chars covering {len(chapters)} chapters")
    return digest


def _sample_chapter(chapter: dict, budget: int) -> str:
    """
    Sample the best paragraphs from a chapter within a character budget.
    
    Strategy:
    - Always include opening paragraph (setup)
    - Always include closing paragraph (transition/cliffhanger)
    - Fill middle with highest-scored paragraphs
    """
    content = chapter["content"]
    
    # If chapter fits in budget, return it all
    if len(content) <= budget:
        return content
    
    paragraphs = _get_paragraphs(content)
    
    if not paragraphs:
        return content[:budget]
    
    if len(paragraphs) <= 3:
        # Very few paragraphs — just truncate
        return content[:budget]
    
    # Always take first and last paragraph
    first = paragraphs[0]
    last = paragraphs[-1]
    
    # Score the middle paragraphs
    middle = paragraphs[1:-1]
    scored = [(score_paragraph(p), i, p) for i, p in enumerate(middle)]
    scored.sort(key=lambda x: x[0], reverse=True)  # Highest score first
    
    # Build selection: first + best middle paragraphs + last
    selected = [first]
    remaining_budget = budget - len(first) - len(last) - 20  # 20 chars for separators
    
    # Add highest-scored paragraphs until budget is exhausted
    # Keep track of original order for coherent reading
    selected_middle = []
    for score, orig_idx, para in scored:
        if remaining_budget <= 0:
            break
        if len(para) <= remaining_budget:
            selected_middle.append((orig_idx, para))
            remaining_budget -= len(para) + 2  # +2 for newlines
    
    # Sort by original position to maintain reading order
    selected_middle.sort(key=lambda x: x[0])
    selected.extend([p for _, p in selected_middle])
    selected.append(last)
    
    return "\n\n".join(selected)


def _proportional_sample(text: str, target_chars: int) -> str:
    """
    Fallback: sample proportionally from beginning, middle, and end.
    """
    third = target_chars // 3
    
    beginning = text[:third]
    
    mid_start = (len(text) // 2) - (third // 2)
    middle = text[mid_start:mid_start + third]
    
    end = text[-(third):]
    
    return f"{beginning}\n\n--- [middle section] ---\n\n{middle}\n\n--- [final section] ---\n\n{end}"


def get_best_excerpt(full_text: str, target_chars: int = 2000) -> str:
    """
    Find the single most interesting/dramatic passage in the book.
    
    Used for audio preview — picks the best excerpt instead of 
    just the first 2000 characters.
    
    Args:
        full_text: Complete book text
        target_chars: Target excerpt length
    
    Returns:
        The most interesting excerpt from the book
    """
    if len(full_text) <= target_chars:
        return full_text
    
    paragraphs = _get_paragraphs(full_text)
    
    if not paragraphs:
        return full_text[:target_chars]
    
    # Score all paragraphs
    scored = [(score_paragraph(p), i, p) for i, p in enumerate(paragraphs)]
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Take the highest-scored paragraphs that fit in budget
    selected = []
    remaining = target_chars
    
    # Collect best paragraphs, maintaining original order
    best_indices = []
    for score, idx, para in scored:
        if remaining <= 0:
            break
        if len(para) <= remaining:
            best_indices.append((idx, para))
            remaining -= len(para) + 2
    
    # Sort by position for coherent reading
    best_indices.sort(key=lambda x: x[0])
    
    if best_indices:
        return "\n\n".join(p for _, p in best_indices)
    
    # Fallback: just return from the first third of the book (most context)
    return full_text[:target_chars]
