# 🤝 Contributing to Movie Library Manager

First off, thank you for considering contributing! It's people like you that make the open-source community such an amazing place to learn, inspire, and create.

## 🐛 How to Report Bugs

1. **Search existing issues**: Your problem might already be discussed.
2. **Open a new issue**: Include as much detail as possible.
   - Describe the expected vs. actual behavior.
   - Provide your environment details (Python version, OS).
   - Attach logs from `data/enrichment.log`.
   - Provide example filenames that caused the issue.

## 💡 How to Suggest Features

1. **Check the roadmap**: See `DESIGN_PHILOSOPHY.md` for future plans.
2. **Open an issue**: Use the "Feature Request" label.
   - Explain why this feature would be useful.
   - Describe how it should work.

## 💻 How to Submit Code

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally.
3. **Create a branch** for your fix or feature (`git checkout -b feat/your-feature`).
4. **Implementation**: Ensure your code follows the existing style and architecture (see `CODE_DOCUMENTATION.md`).
5. **Test locally**: Verify your changes don't break existing functionality.
6. **Commit with clarity**: Use descriptive commit messages.
7. **Push to your fork** and **Submit a Pull Request (PR)**.

## 🛠 Development Setup

1. **Python 3.9+** is required.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment**:
   Create a `.env` file with your `GEMINI_API_KEY` and `OMDB_API_KEY`. Add `GROQ_API_KEY` only if you want to use the optional Groq provider (`AI_PROVIDER=groq` or `--provider groq`). Groq adds no new pip dependency — it reuses the existing `requests`.
4. **VLC Media Player**: Required for testing the playback feature.

### Useful CLI flags

- `--provider {gemini,groq}` — choose the AI backend for a run.
- `--model <name>` — override the model used by the active provider.
- `--retry-failed` — re-run movies left in the failed state (`is_active=4`).

### Adding a new AI provider

The AI layer is provider-agnostic. To add one, implement the shared interface in a new client module — `identify_movie`, `identify_movies_bulk`, and `set_model` (mirroring `gemini_client.py` / `groq_client.py`) — then register it in `ai_provider._PROVIDERS`. The enrichment pipeline needs no changes.

## ✅ Testing Checklist

Before submitting a PR, please verify:
- [ ] Code follows Python PEARL/PEP8 standards.
- [ ] New functions have docstrings and basic error handling.
- [ ] The web UI still loads and filters correctly.
- [ ] `main.py --stats` runs without error.
- [ ] No API keys or secrets are committed.

## 📜 License

By contributing, you agree that your contributions will be licensed under its **GNU GPL v3.0 License**.
