class JoriAI:
    """Simple AI facade.

    Example:
        from jori_health.ai import joriai
        joriai.ask("hello")  # -> "world"
    """

    def ask(self, prompt: str) -> str:
        normalized = prompt.strip().lower()
        if normalized == "hello":
            return "world"
        return f"Echo: {prompt}"


# Default instance for convenience: `from jori_health.ai import joriai`
joriai = JoriAI()
