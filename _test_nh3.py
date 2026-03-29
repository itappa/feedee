import nh3

tags = {
    "p",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
    "img",
    "strong",
    "em",
    "u",
    "br",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "table",
    "tr",
    "td",
    "th",
}
attrs = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height"},
    "table": {"border", "cellpadding", "cellspacing"},
    "*": {"class"},
}

cases = {
    "script": '<p>Hello</p><script>alert("XSS")</script><p>World</p>',
    "iframe": '<p>Embedded:</p><iframe src="https://malicious.com"></iframe>',
    "onclick": '<a href="https://example.com" onclick="alert()">Link</a>',
    "js_href": "<a href=\"javascript:alert('XSS')\">Link</a>",
    "class": '<p class="highlight">Highlighted paragraph</p>',
    "form": '<form action="https://malicious.com"><input type="submit"></form>',
    "style": "<p>Text</p><style>body { display: none; }</style>",
}

for name, html in cases.items():
    r = nh3.clean(html, tags=tags, attributes=attrs, link_rel=None)
    print(f"{name}: {repr(r)}")
