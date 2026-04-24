from symboliclight.lexer import lex


def test_lexer_tokenizes_app_core_syntax() -> None:
    tokens = lex('app Todo { route GET "/todos" -> List<Todo> { return [] } }')
    values = [token.value for token in tokens]

    assert "app" in values
    assert "route" in values
    assert "/todos" in values
    assert "->" in values
