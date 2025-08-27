from jori_health.ai import joriai, JoriAI


def test_hello_world():
    assert joriai.ask("hello") == "world"


def test_echo_other():
    ai = JoriAI()
    assert ai.ask("something else") == "Echo: something else"
