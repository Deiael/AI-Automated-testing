from app.services.openapi_import import (
    build_point_and_cases,
    extract_operations,
    operation_key,
    parse_openapi_text,
)

SPEC = """
openapi: 3.0.0
info:
  title: Demo
  version: "1.0"
paths:
  /pets/{id}:
    get:
      summary: Get pet
      security:
        - bearerAuth: []
      parameters:
        - name: id
          in: path
          required: true
      responses:
        "200":
          description: ok
        "401":
          description: unauth
  /pets:
    post:
      summary: Create pet
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
      responses:
        "201":
          description: created
"""


def test_parse_and_generate():
    spec = parse_openapi_text(SPEC)
    ops = extract_operations(spec)
    assert len(ops) == 2
    keys = {operation_key(o["method"], o["path"]) for o in ops}
    assert "GET /pets/{}" in keys
    assert "POST /pets" in keys
    point, cases = build_point_and_cases(ops[0], project_id="p", pipeline_id="pl")
    assert point["title"].startswith("[API]")
    assert cases
    assert any("正向" in c["title"] for c in cases)
