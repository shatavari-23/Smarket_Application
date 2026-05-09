import re
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(ROOT, 'templates')
APP_PY = os.path.join(ROOT, 'app.py')
MAIN_PY = os.path.join(ROOT, 'routes', 'main.py')

urlfor_re = re.compile(r"url_for\('\s*([a-zA-Z0-9_]+)\s*'")
def_re = re.compile(r"^def\s+([a-zA-Z0-9_]+)\s*\(")
endpoint_re = re.compile(r"endpoint\s*=\s*['\"]([a-zA-Z0-9_]+)['\"]")

endpoints = set()
for dirpath, _, filenames in os.walk(TEMPLATES_DIR):
    for fn in filenames:
        if not fn.endswith('.html'):
            continue
        path = os.path.join(dirpath, fn)
        with open(path, encoding='utf-8') as f:
            txt = f.read()
        for m in urlfor_re.finditer(txt):
            endpoints.add(m.group(1))

app_defs = set()
if os.path.exists(APP_PY):
    with open(APP_PY, encoding='utf-8') as f:
        for line in f:
            m = def_re.match(line)
            if m:
                app_defs.add(m.group(1))

    # Also extract any explicit endpoints added via app.add_url_rule(..., endpoint='name')
    with open(APP_PY, encoding='utf-8') as f:
        txt = f.read()
    for m in endpoint_re.finditer(txt):
        app_defs.add(m.group(1))

main_defs = set()
if os.path.exists(MAIN_PY):
    with open(MAIN_PY, encoding='utf-8') as f:
        for line in f:
            m = def_re.match(line)
            if m:
                main_defs.add(m.group(1))

    # endpoints added via add_url_rule in app.py may reference blueprint targets; capture them too
    if os.path.exists(APP_PY):
        with open(APP_PY, encoding='utf-8') as f:
            txt = f.read()
        for m in endpoint_re.finditer(txt):
            # avoid duplicating static
            if m.group(1) != 'static':
                main_defs.add(m.group(1))

# endpoints that are built-in or static
builtins = {'static'}

missing = sorted([e for e in endpoints if e not in app_defs and e not in main_defs and e not in builtins])

print('Found endpoints in templates ({}):'.format(len(endpoints)))
for e in sorted(endpoints):
    print(' -', e)

print('\nFunction names in app.py ({}):'.format(len(app_defs)))
for e in sorted(app_defs):
    print(' -', e)

print('\nFunction names in routes/main.py ({}):'.format(len(main_defs)))
for e in sorted(main_defs):
    print(' -', e)

print('\nMissing endpoints ({}):'.format(len(missing)))
for e in missing:
    print(' -', e)

# Try importing the Flask app to inspect the registered URL map (preferable). This
# will give the actual runtime endpoints including those added via add_url_rule.
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('app_module', APP_PY)
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    flask_app = getattr(app_module, 'app', None)
    if flask_app:
        runtime_endpoints = sorted(set(r.endpoint for r in flask_app.url_map.iter_rules()))
        print('\nRuntime endpoints (from app.url_map):')
        for e in runtime_endpoints:
            print(' -', e)
        # Recompute missing using runtime endpoints
        missing_runtime = sorted([e for e in endpoints if e not in runtime_endpoints and e not in builtins])
        print('\nMissing endpoints after inspecting runtime URL map ({}):'.format(len(missing_runtime)))
        for e in missing_runtime:
            print(' -', e)
except Exception as exc:
    print('\nCould not import app to inspect runtime URL map:', exc)

# Also detect an `alias_map` dict in app.py (keys are extra endpoint names)
try:
    with open(APP_PY, encoding='utf-8') as f:
        txt = f.read()
    alias_map = {}
    m = re.search(r"alias_map\s*=\s*\{([\s\S]*?)\}", txt)
    if m:
        body = '{' + m.group(1) + '}'
        import ast
        try:
            alias_map = ast.literal_eval(body)
        except Exception:
            alias_map = {}
    if alias_map:
        print('\nDetected alias_map keys in app.py:')
        for k in sorted(alias_map.keys()):
            print(' -', k)
        # Recompute missing including these aliases
        missing_with_aliases = sorted([e for e in endpoints if e not in app_defs and e not in main_defs and e not in alias_map.keys() and e not in builtins])
        print('\nMissing endpoints after accounting for alias_map ({}):'.format(len(missing_with_aliases)))
        for e in missing_with_aliases:
            print(' -', e)
except Exception:
    pass
