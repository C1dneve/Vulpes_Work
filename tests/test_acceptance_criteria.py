from tools.probe_acceptance_criteria import extract_acceptance_criteria, issue_hash


def heading(text, level=2):
    return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}


def paragraph(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def test_missing_acceptance_section():
    result = extract_acceptance_criteria({"type": "doc", "content": [heading("Resumo"), paragraph("Texto") ]})
    assert result.classification == "sem_secao"


def test_empty_acceptance_section():
    result = extract_acceptance_criteria({"type": "doc", "content": [heading("Critérios de aceite"), paragraph("Texto livre"), heading("Notas")]})
    assert result.classification == "secao_vazia"


def test_bullet_ordered_and_task_lists_are_extracted_including_nested_items():
    nested = {"type": "bulletList", "content": [{"type": "listItem", "content": [paragraph("item aninhado")]}]}
    content = [heading("CRITERIOS DE ACEITE!"),
               {"type": "taskList", "content": [{"type": "taskItem", "attrs": {"state": "TODO"}, "content": [paragraph("validar login"), nested]}]},
               {"type": "orderedList", "content": [{"type": "listItem", "content": [paragraph("validar logout")]}]},
               heading("Próxima seção"),
               {"type": "bulletList", "content": [{"type": "listItem", "content": [paragraph("não incluir")]}]}]
    result = extract_acceptance_criteria({"type": "doc", "content": content})
    assert result.classification == "ok"
    assert result.item_count == 3


def test_empty_and_punctuation_only_items_are_invalid():
    content = [heading("Critérios de aceite"), {"type": "bulletList", "content": [
        {"type": "listItem", "content": [paragraph("")]},
        {"type": "listItem", "content": [paragraph("!!! ... ???")]},
        {"type": "listItem", "content": [paragraph("critério válido")]},
    ]}]
    result = extract_acceptance_criteria({"type": "doc", "content": content})
    assert result.classification == "ok_com_itens_invalidos"
    assert result.item_count == 3
    assert result.invalid_item_count == 2
    assert set(result.reasons) == {"item_vazio", "somente_pontuacao"}


def test_issue_key_is_not_present_in_short_hash():
    key = "PROJ-123"
    assert key not in issue_hash(key)
    assert len(issue_hash(key)) == 10


def test_acceptance_heading_is_recognized_at_any_level_with_accents_and_punctuation():
    content = [heading("Resumo", level=1), heading("CrItÉrIos de aceite!!!", level=1),
               {"type": "bulletList", "content": [{"type": "listItem", "content": [paragraph("critério")]}]}]
    result = extract_acceptance_criteria({"type": "doc", "content": content})
    assert result.classification == "ok"
    assert result.item_count == 1
