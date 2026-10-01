from ui_components import chip


def test_chip_escapes_dangerous_html():
    out = str(chip('<img src=x onerror="alert(1)">'))

    assert out == (
        '<span class="mf-chip">'
        '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'
        '</span>'
    )
