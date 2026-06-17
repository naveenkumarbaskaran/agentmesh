#!/usr/bin/env bash
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$REPO/.venv/bin/python"
cd "$REPO"
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
PASS=0; FAIL=0
_ok()      { echo -e "  ${GREEN}✓${NC}  $1"; ((PASS++)); }
_fail()    { echo -e "  ${RED}✗${NC}  $1"; ((FAIL++)); }
_section() { echo -e "\n${CYAN}━━━  $1  ━━━${NC}"; }

echo -e "\n${CYAN}  agentmesh — Regression Suite${NC}\n"

_section "1. pytest"
OUT=$("$PYTHON" -m pytest tests/ -q --tb=short 2>&1 || true)
SUM=$(echo "$OUT" | grep -E "passed|failed" | tail -1)
if echo "$SUM" | grep -q "failed"; then _fail "pytest: $SUM"
elif echo "$SUM" | grep -q "passed"; then _ok "pytest: $SUM"
else _fail "pytest: no results"; fi

_section "2. Exports"
RES=$("$PYTHON" -c "
import sys; sys.path.insert(0,'src')
import agentmesh
missing=[x for x in agentmesh.__all__ if getattr(agentmesh,x,None) is None]
print('MISSING:'+','.join(missing)) if missing else print(f'OK:{len(agentmesh.__all__)} symbols')
" 2>/dev/null)
echo "$RES" | grep -q "^OK:" && _ok "All exports resolve ($(echo "$RES"|cut -d: -f2))" || _fail "Missing: $RES"

_section "3. AgentMesh start/close"
"$PYTHON" -c "
import sys,asyncio; sys.path.insert(0,'src')
from agentmesh import AgentMesh
async def run():
    m=AgentMesh(); await m.start(); await m.close()
asyncio.run(run()); print('OK')
" 2>/dev/null && _ok "AgentMesh start/close" || _fail "AgentMesh failed"

_section "4. Publish + subscribe"
"$PYTHON" -c "
import sys,asyncio; sys.path.insert(0,'src')
from agentmesh import AgentMesh,AgentEvent
async def run():
    m=AgentMesh(); await m.start(); received=[]
    @m.subscribe('test.event')
    async def h(e): received.append(e)
    await m.publish('test.event',data={'x':1},publisher_id='p',session_id='s',run_id='r')
    await asyncio.sleep(0.05)
    assert len(received)==1
    await m.close()
asyncio.run(run()); print('OK')
" 2>/dev/null && _ok "Publish + subscribe" || _fail "Publish + subscribe failed"

_section "5. Deduplication"
"$PYTHON" -c "
import sys,asyncio; sys.path.insert(0,'src')
from agentmesh import AgentMesh,AgentEvent
async def run():
    m=AgentMesh(); await m.start(); received=[]
    @m.subscribe('dup.test')
    async def h(e): received.append(e)
    for _ in range(3):
        await m.publish('dup.test',data={},publisher_id='p',session_id='s',run_id='r',event_id='dup-001')
    await asyncio.sleep(0.05)
    assert len(received)==1,f'expected 1, got {len(received)}'
    await m.close()
asyncio.run(run()); print('OK')
" 2>/dev/null && _ok "Deduplication: 3 publishes → 1 delivery" || _fail "Deduplication failed"

_section "6. Version"
PV=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
IV=$("$PYTHON" -c "import sys; sys.path.insert(0,'src'); import agentmesh; print(agentmesh.__version__)" 2>/dev/null)
[ "$PV" = "$IV" ] && _ok "Version consistent: $PV" || _fail "Mismatch: pyproject=$PV vs __version__=$IV"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}✓ ALL PASSED${NC}  ($PASS passed)"; echo "  Safe to push."
else
    echo -e "  ${RED}✗ FAILURES${NC}  ($PASS passed, $FAIL failed)"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
[ "$FAIL" -eq 0 ]
