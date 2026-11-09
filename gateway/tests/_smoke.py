from app.services.auth import hash_password, verify_password
from app.services.openapi_import import extract_operations, parse_openapi_text

spec = parse_openapi_text(
    '{"openapi":"3.0.0","info":{"title":"t","version":"1"},"paths":{"/x":{"get":{"responses":{"200":{"description":"ok"}}}}}}'
)
assert len(extract_operations(spec)) == 1
h = hash_password("admin123")
assert verify_password("admin123", h)
from app.main import app

print("ok", len(app.routes))
