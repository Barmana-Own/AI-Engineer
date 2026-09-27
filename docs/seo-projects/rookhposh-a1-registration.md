# Rookhposh SEO — A1 Registration and Baseline

| Field | Value |
|---|---|
| Generated | 2026-09-26 (Gregorian) / 1405-07-04 (Jalali) |
| Project | Rookhposh SEO |
| Project ID | `04469407-8792-4ef9-b514-bbd6b91fc4b5` |
| Primary property | `https://rookhposh.ir/` |
| Source workspace | `F:/AI-Engineer/workspaces/rookhposh` |
| Access mode | Public URL and source |
| Declared platform | Next.js 16 App Router |
| Detected platform | Next.js, confidence 0.98 |
| Frontend | React 19 |
| Language / direction | `fa` / RTL |

## Registration

The primary Rookhposh property is registered in the existing AI-Engineer project and SEO persistence model. The supplied source archive was copied into the configured workspace without importing its own orchestration, task, authentication, or persistence framework.

Related hosts are separate SEO properties under the same project and are not assumed to share the primary deployable repository:

| Property | Site ID | Source mode | Source workspace |
|---|---|---|---|
| Rookhposh primary | `d1711216-6c46-4b70-8920-a0411ded9e0a` | public URL and source | `F:/AI-Engineer/workspaces/rookhposh` |
| Rookhposh blog | `8cac1acb-e387-4748-88e9-e12f1654b6b2` | public URL only | not provided |
| Rookhposh dashboard | `458c6db2-efd6-44d8-8ebb-a10c88acb952` | public URL only | not provided |

## Baseline evidence

Audits used the existing bounded, same-host, SSRF-safe crawler. The baseline is raw HTML evidence; no browser-rendered DOM or Search Console/Analytics data was used.

### Primary property

- Snapshot: `3fa35322-4251-4ae9-8954-9ef143dd4220`
- HTTP result: `200`
- Pages analyzed: `1`
- Observed title: `رخ پوش | پرو مجازی و پلن‌ها`
- Meta description: present
- H1: present
- Canonical: not observed (medium finding)
- Robots: `/robots.txt` returned `404` (low finding)
- Sitemap: `/sitemap.xml` returned `404` (low finding)
- Image accessibility: two images without `alt` were observed (low findings)
- Title heuristic: observed length `27`; review recommended (medium finding)
- Search Console and Analytics: `DATA NOT AVAILABLE`

### Dashboard related property

- Snapshot: `7ae1ce39-c49d-4ea2-afd2-6e5be7658f91`
- HTTP result: `200`
- Pages analyzed: `1`
- Platform: not detected from the public response; source was not supplied
- Findings: short title, missing meta description, missing canonical, and missing H1
- Search Console and Analytics: `DATA NOT AVAILABLE`

### Blog related property

The first bounded attempt did not complete because DNS resolution failed (`getaddrinfo failed`). No SEO conclusion is drawn from that failure. A separate retry is required after the host resolves.

## Current status

| Gate | Status | Evidence |
|---|---|---|
| Project registration | PASS | Project and three isolated site records persisted |
| Primary source workspace | PASS | Next.js source copied under the configured workspace root |
| Primary public baseline | PASS | Completed snapshot with one observed page and six findings |
| Dashboard public baseline | PASS | Completed snapshot with one observed page and four findings |
| Blog public baseline | BLOCKED | DNS resolution failure; no snapshot persisted |
| Search performance data | NOT_RUN | No Search Console or Analytics integration configured |
| Rendered-JS audit | NOT_RUN | Current baseline is raw HTML only |
| Autonomous repair workflow | NOT_RUN | Findings have not been delegated or modified |

This A1 step registers the project and records evidence only. It does not modify the Rookhposh source, publish WordPress content, change production configuration, or claim ranking/traffic/indexation results.
