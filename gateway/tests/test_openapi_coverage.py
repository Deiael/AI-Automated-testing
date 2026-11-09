from app.services.openapi_import import build_point_and_cases, extract_operations, operation_key, parse_openapi_text

SPEC = """
openapi: 3.0.0
info:
  title: Petstore
  version: "1.0"
paths:
  /pets:
    get:
      summary: list pets
      responses:
        "200": { description: ok }
    post:
      summary: create pet
      security:
        - bearer: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name: { type: string }
      responses:
        "201": { description: created }
  /pets/{id}:
    get:
      summary: get pet
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string }
      responses:
        "200": { description: ok }
"""


def test_parse_and_cases():
    spec = parse_openapi_text(SPEC)
    ops = extract_operations(spec)
    assert len(ops) == 3
    keys = {operation_key(o["method"], o["path"]) for o in ops}
    assert "GET /pets" in keys
    assert "POST /pets" in keys
    assert "GET /pets/{}" in keys
    _point, cases = build_point_and_cases(next(o for o in ops if o["method"] == "POST"), project_id="p", pipeline_id="pl")
    titles = {c["title"] for c in cases}
    assert any("正向" in t for t in titles)
    assert any("未授权" in t for t in titles)


def test_operation_key_normalizes_params():
    assert operation_key("get", "/pets/{petId}") == operation_key("GET", "/pets/{id}")
