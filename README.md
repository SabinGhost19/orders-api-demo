# orders-api-demo

Python demo app (api + worker) with **two jobs** in the platform:

1. **GUAC correlation showcase** — it deliberately shares packages and CVEs with
   the other Python demo apps so the **Blast Radius** graph links multiple ZTA
   apps together instead of showing isolated nodes.
2. **ZeroTrustSecret showcase** — Vault secret injection gated on the supply
   chain being `Verified` first.

## 1. GUAC correlation (why the deps are pinned-vulnerable)

`python:3.11-slim` base + shared pip pins create shared nodes in the GUAC
knowledge graph, so a Blast Radius query lights up across apps:

| package (pin) | advisory | shared with | verdict here |
|---|---|---|---|
| `cryptography==41.0.0` (api + worker) | **CVE-2023-50782** / GHSA-jm77-qphf-c4w8 | analytics-worker | **affected** (red) |
| `pyyaml==6.0` (worker) | **CVE-2020-14343** | analytics-worker | **VEX not_affected** (green) |
| `requests==2.31.0` (worker) | (transitive) | analytics-worker | — |
| `fastapi`/`uvicorn` (api) | — | demo-app | shared package nodes |
| `python:3.11-slim` base | `debian-cve-*` (DEBIAN namespace) | demo-app, analytics | shared OS layer |

Result in the Blast Radius tab: a query for **`cve-2023-50782`** returns both
`orders` and `analytics-worker` (correlated via the shared `cryptography@41.0.0`
node); the DEBIAN base-layer advisories link every Python app; and the new tag
filter (`DEBIAN / GHSA / CVE / other`) has real data to filter on. One node
(`pyyaml` CVE-2020-14343) is VEX-exempted so the graph shows a single **green**
verdict next to the **red** affected ones.

> The pinned deps live in `requirements.txt` purely for the SBOM/CVE footprint;
> `main.py` stays dependency-light (fastapi/pydantic) so the tests need nothing
> exotic — same convention as `analytics-engine-demo`. Demo only — never deploy
> for real, and do **not** bump the pins (that defeats the demo).

The cluster-side SCA (`orders-verified-policy`) is intentionally **tolerant**
(`maxAllowedSeverity: Critical`, `failOnFixable: false`, `onVulnerabilityFound:
Alert`) so the app still **deploys** despite the CVEs — that is what gives the
graph live *deployment* nodes to correlate. Strict blocking is `payments-api`'s
job, not this one.

## 2. The ZeroTrustSecret story

`manifests-demo-app/orders-api/zts.yaml` declares a `ZeroTrustSecret` with
`zeroTrustConditions.requireVerifiedStatus: true`. The `zta-operator` only
injects `DB_USERNAME` / `DB_PASSWORD` (from Vault at
`secret/data/prod/orders-api/config`) into the `orders-api` Deployment once the
matching `ZeroTrustApplication` is admitted. `services/api/main.py` logs **only
whether each is present** (never the value):

```
orders-api secret check: DB_USERNAME present=true, DB_PASSWORD present=true
```

## Components

- `services/api/` — FastAPI service (`/health`, `/orders`, `/total`). `/total`
  validates `currency ∈ {USD,EUR,RON}` + the line items and sums
  `qty*unit_price` (pure `compute_order_total`, unit-tested). Reads the
  ZTS-injected DB creds at startup.
- `services/worker/` — stdlib process loop draining an orders queue; pure
  `parse_tick_interval()` is unit-tested.
- `.github/workflows/` — **modular** pipeline (orchestrator `ci-cd.yaml` +
  `job-*.yml`), per-service jobs **parameterized** (api/worker) via a `service`
  input. `build-metadata` = `py_compile`; `unit-tests` = `pytest` (gates build).
- `security-policy.yaml` — input for `policyAttestor-action`; declares
  `secrets.requireZeroTrustSecrets: true` + the pinned Vault path.
- `vex.json` — one OpenVEX `not_affected` (pyyaml CVE-2020-14343).

Test deps come from `requirements-dev.txt` only (never baked into the images).

**Images produced (after push):**

- `ghcr.io/sabinghost19/orders-api@sha256:...`
- `ghcr.io/sabinghost19/orders-worker@sha256:...`

## Local tests

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r services/api/requirements.txt -r requirements-dev.txt
( cd services/api && python -m pytest -q )
( cd services/worker && python -m pytest -q )
```

## First-run setup

The pipeline reuses the manifests repo `SabinGhost19/vulfastapi-manifests-samples`
(same one the other demo apps use), mirrored locally as `manifests-demo-app/`;
sub-path `orders-api/`.

1. Create the source repo:

   ```bash
   gh repo create SabinGhost19/orders-api-demo --public --source=. --remote=origin
   ```

2. Add secrets (reusable with the `vulfastapi` ones):

   ```bash
   gh secret set VBBI_HMAC_KEY --body "<same-key-as-vulfastapi>"
   gh secret set MANIFESTS_REPO_TOKEN --body "<PAT with repo scope on vulfastapi-manifests-samples>"
   ```

3. Ensure manifests exist in the shared repo (sub-path `orders-api/`):

   ```bash
   git clone https://github.com/SabinGhost19/vulfastapi-manifests-samples
   cd vulfastapi-manifests-samples
   mkdir -p orders-api/api orders-api/worker
   cp ../customCRD/demo-repos-apps/manifests-demo-app/orders-api/sca.yaml ./orders-api/
   cp ../customCRD/demo-repos-apps/manifests-demo-app/orders-api/api/zta-api.yaml ./orders-api/api/
   cp ../customCRD/demo-repos-apps/manifests-demo-app/orders-api/worker/zta-worker.yaml ./orders-api/worker/
   cp ../customCRD/demo-repos-apps/manifests-demo-app/orders-api/zts.yaml ./orders-api/
   git add -A && git commit -m "add orders-api manifests" && git push
   ```

4. Push the source repo:

   ```bash
   git init -b main && git add -A && git commit -m "init"
   git remote add origin https://github.com/SabinGhost19/orders-api-demo.git
   git push -u origin main
   ```

5. Inspect artifacts, then apply (SCA + ZTAs first, then ZTS):

   ```bash
   cosign tree ghcr.io/sabinghost19/orders-api:sha-<commit>
   kubectl apply -f orders-api/sca.yaml
   kubectl apply -f orders-api/api/zta-api.yaml
   kubectl apply -f orders-api/worker/zta-worker.yaml
   kubectl apply -f orders-api/zts.yaml
   ```

6. In the dashboard → **Blast Radius**, search `cve-2023-50782` and watch
   `orders` + `analytics-worker` light up together.
