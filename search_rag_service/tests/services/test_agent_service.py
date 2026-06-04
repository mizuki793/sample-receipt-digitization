from types import SimpleNamespace

from services.agent_service import ShoppingAgent


class DummyMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


def test_should_continue_when_tool_calls_exist():
    agent = object.__new__(ShoppingAgent)
    state = {"messages": [DummyMessage(content="hello", tool_calls=[{"name": "tool"}])]}  

    assert agent._should_continue(state) == "continue"


def test_should_end_when_no_tool_calls():
    agent = object.__new__(ShoppingAgent)
    state = {"messages": [DummyMessage(content="hello")]}  

    assert agent._should_continue(state) == "end"


def test_call_model_invokes_model_with_system_prompt():
    fake_response = SimpleNamespace(content="hello")

    def fake_invoke(messages):
        assert len(messages) == 2
        assert messages[0].content.startswith("現在の注文当日の日付は")
        assert messages[1].content == "user input"
        return fake_response

    agent = object.__new__(ShoppingAgent)
    agent.model = SimpleNamespace(invoke=fake_invoke)

    result = agent._call_model({"messages": [DummyMessage(content="user input")]})

    assert result == {"messages": [fake_response]}
