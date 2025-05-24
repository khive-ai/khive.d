# 📍 Researcher CLI Extension

_You have all global commands plus:_

### Advanced Search Patterns

```bash
# Multi-angle research function
research_topic() {
    echo "=== Searching: $1 ==="
    khive info search --provider perplexity --query "$1 current best practices 2024-2025"
    khive info search --provider perplexity --query "$1 common pitfalls problems disadvantages"
    khive info search --provider perplexity --query "$1 alternatives comparisons tradeoffs"
}

# Use like: research_topic "Redis connection pooling async Python"
```

### Power Combos

```bash
# PDF Deep Dive
khive reader open --path_or_url "paper.pdf"
khive info search --provider perplexity --query \
  "Summary and critiques of [paper title] focusing on practical applications"
```
