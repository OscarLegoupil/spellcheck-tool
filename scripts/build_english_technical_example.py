"""Build a selectable-text technical PDF sample with a verified typo count."""

from pathlib import Path

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples" / "northstar-edge-operations-en.pdf"
PAGE_SIZE = (612, 792)
MARGIN = 48
BODY_WIDTH = PAGE_SIZE[0] - 2 * MARGIN

INK = (0.12, 0.18, 0.25)
MUTED = (0.36, 0.43, 0.5)
NAVY = (0.1, 0.2, 0.31)
TEAL = (0.0, 0.43, 0.47)
PALE = (0.91, 0.96, 0.96)
ROW = (0.95, 0.97, 0.98)
RULE = (0.82, 0.86, 0.89)
WHITE = (1, 1, 1)

PAGES = [
    {
        "title": "Edge Gateway",
        "subtitle": "Operations and Reliability Manual | Revision 3.2 | 16 October 2026",
        "items": [
            (
                "p",
                "Edge Gateway is a regional request gateway for product APIs. It terminates client TLS, applies routing policy, and forwards requests to independently deployed services. Its architecure is intentionally small: three stateless gateway pools, a control plane, and a managed key store. This handbook describes the production operating model rather than application development. Operators should use it alongside the current change ticket and service dashboard.",
            ),
            (
                "callout",
                "SERVICE OBJECTIVE",
                "The service targets 99.95% monthly availabilty for accepted requests. A request is available when the gateway returns a valid response or a documented upstream error within two seconds. The objective excludes planned maintenance announced at least seven days in advance.",
            ),
            (
                "p",
                "The primary region serves customer traffic; a warm secondary region is kept ready for controlled recovery. Regional teams own capacity, certificates, and incident response. The operatonal checklist is designed for a two-person change window, with one operator executing and one reviewing. Never make a production change from an untracked local file.",
            ),
            (
                "table",
                ["Service property", "Production baseline", "Owner"],
                [
                    ["Availability objective", "99.95% per calendar month", "SRE"],
                    ["Normal request limit", "2 seconds end to end", "Platform"],
                    ["Maximum body size", "8 MB; larger uploads rejected", "API team"],
                    ["External dependecy", "Managed key store and regional DNS", "Security"],
                ],
            ),
            (
                "p",
                "The gateway does not store business records. It may hold a short-lived request buffer in memory while forwarding traffic; access logs contain identifiers and timing data, not request bodies. These boundaries simplify recovery, but they do not remove the need to verify downstream health before shifting traffic.",
            ),
        ],
    },
    {
        "title": "Architecture and request flow",
        "subtitle": "Traffic path, failure domains, and capacity boundaries",
        "items": [
            (
                "p",
                "Public DNS resolves each regional hostname to a managed load balancer. The balancer distributes traffic across three gateway pools in separate zones. Gateways obtain signed routing bundles from the control plane and forward requests over mutually authenticated connections. The design keeps througput scaling independent from policy publication and limits the impact of a single-zone failure through pool isloation.",
            ),
            (
                "diagram",
                [
                    ("Client", "TLS 1.2+\nPublic DNS"),
                    ("Regional LB", "Health probes\nZone aware"),
                    ("Gateway pools", "3 zones\nStateless"),
                    ("Services", "Private links\nPer-service limits"),
                ],
            ),
            (
                "table",
                ["Hop", "Typical latency", "Failure signal"],
                [
                    ["DNS and connect", "20-80 ms", "Resolution or handshake errors"],
                    ["Load balancer", "5-15 ms", "Target health below 2 of 3 zones"],
                    ["Gateway policy", "Under 10 ms", "Bundle age exceeds 15 minutes"],
                    ["Upstream service", "Varies by route", "Timeout or 5xx rate increase"],
                ],
            ),
            (
                "p",
                "The gateway reports client-perceived latncy separately from upstream duration. Capacity alarms use the former because it captures queueing and connection setup. Each pool has one spare replica at normal load. During a zone loss, the balancer drains unhealthy targets and the remaining pools accept traffic only while their CPU stays below the emergency limit.",
            ),
            (
                "callout",
                "FAILURE DOMAIN",
                "A redundent pool is not a substitute for a tested failover. The secondary region has independent DNS, certificates, and service credentials; it shares neither a network route nor a deploy lock with the primary.",
            ),
            (
                "p",
                "Keep health probes cheap and deterministic. A probe checks process readiness and the active routing bundle; it must not call every upstream dependency. This prevents one slow service from removing otherwise healthy gateway capacity.",
            ),
        ],
    },
    {
        "title": "Installation and bootstrap",
        "subtitle": "Preparing a node image and joining a regional pool",
        "items": [
            (
                "p",
                "Build node images from the approved base image in the release pipeline. The bootstrap proccess verifies the image signature, installs the gateway package, and requests a short-lived node identity. Images are immutable after publication; configuration is mounted at startup and is never patched in place. Record the image digest in the deployment ticket before adding capacity.",
            ),
            (
                "table",
                ["Stage", "Required evidence", "Stop condition"],
                [
                    ["Image build", "Signed digest and dependency report", "Signature invalid"],
                    ["Node registration", "Zone, pool, and owner labels", "Identity request denied"],
                    ["Readiness", "Bundle loaded and probe passing", "Stale policy or failed probe"],
                    ["Traffic admission", "Canary metrics within baseline", "5xx or latency regression"],
                ],
            ),
            (
                "bullets",
                [
                    "Confirm the node is in the approved subnet and the correct availability zone.",
                    "Verify the control-plane conection before enabling the load-balancer target.",
                    "Keep image promotion and traffic admission as separate reviewed actions.",
                ],
            ),
            (
                "p",
                "The image contains no environment-specific secret. At boot, the workload identity exchanges its node assertion for a short-lived certificate, then fetches the signed route bundle. The seperation between image and runtime settings allows the same artifact to be promoted through test, staging, and production without rebuilding it.",
            ),
            (
                "callout",
                "ROLL FORWARD",
                "If bootstrap fails after registration, remove the node from the target group, preserve its startup log, and replace it from the last known-good image. Do not repair a failed node manually; that creates an unreviewed state that cannot be reproduced during maintenence.",
            ),
        ],
    },
    {
        "title": "Network and traffic policy",
        "subtitle": "Ingress, egress, timeouts, and safe configuration changes",
        "items": [
            (
                "p",
                "Ingress is limited to the regional load balancer on the published HTTPS listener. The gateway has no public administration port. Egress is denied by default and opened only to named upstream services, the control plane, DNS, and time synchronization. Network policy configuation changes require the same peer review as application code because an overly broad rule can bypass service boundaries. Intermitant DNS failures should be checked against the regional resolver dashboard.",
            ),
            (
                "table",
                ["Policy", "Default", "Change guidance"],
                [
                    ["Client timeout", "2 seconds", "Raise only with an owner and measured need"],
                    ["Upstream timeout", "1.5 seconds", "Keep below caller deadline"],
                    ["Retry count", "1 for safe GET requests", "Never retry non-idempotent writes"],
                    ["Connection pool", "Per route and zone", "Drain before reducing limits"],
                    ["Egress", "Deny by default", "Name service, port, and expiry"],
                ],
            ),
            (
                "p",
                "A route change is published as a signed, versioned bundle. The control plane validates schema, destination ownership, and timeout bounds before distribution. Operators can pause a rollout, but cannot edit a commited bundle. Correct errors in source control, create a new version, and verify the resulting policy diff before promotion.",
            ),
            (
                "bullets",
                [
                    "Use an explicit environment label; do not infer production from a hostname.",
                    "Test a new upstream path from a canary node before broad admission.",
                    "Confirm the DNS target against the enviroment in the change review.",
                ],
            ),
            (
                "p",
                "Network records are retained for 90 days. Each rule includes a technical owner, a business purpose, and a review date. Expired exceptions are removed automatically unless the owner renews them through the normal approval path. Emergency openings must be time-bound and reviewed on the next business day.",
            ),
        ],
    },
    {
        "title": "Identity and secret handling",
        "subtitle": "Workload identity, operator access, and certificate rotation",
        "items": [
            (
                "p",
                "Human access uses the corporate identity provider with phishing-resistant multifactor authentication. Operators receive time-limited access to the regional control plane through a named group. Shared accounts are prohibited. A second reviewer approves production changes, while read-only dashboard access remains available to incident responders without elevated privileges. Failed authentiction attempts are rate-limited and audited.",
            ),
            (
                "table",
                ["Credential", "Lifetime", "Storage and rotation"],
                [
                    ["Node identity", "15 minutes", "Renewed by workload identity"],
                    ["Gateway certificate", "30 days", "Automated rotation at 10 days remaining"],
                    ["Operator session", "8 hours", "Re-authenticate for privileged actions"],
                    ["Emergency credential", "60 minutes", "Vaulted, audited, and revoked after use"],
                ],
            ),
            (
                "p",
                "The identity service grants the minimum privilage required for each process. Gateway nodes can read their route bundle and publish health, but cannot edit routing policy or retrieve customer data. Human credentials are never copied into node images, startup scripts, or shell history.",
            ),
            (
                "callout",
                "ROTATION SAFETY",
                "Rotate certificates with an overlap window: publish the new trust chain, confirm all zones accept it, then retire the old key. Never remove the previous certificate until the fleet reports the new serial number and successful handshake metrics.",
            ),
            (
                "p",
                "Secret access is logged with actor, resource, region, and request identifier. Logs contain credential metadata only, never secret values. If credentails may have been exposed, revoke them immediately, preserve the audit trail, and follow the incident procedure on page 9. Data in transit uses TLS; stored key material is protected by envelope encrypton in the managed key store.",
            ),
        ],
    },
    {
        "title": "Observability and service objectives",
        "subtitle": "Signals, alert thresholds, and weekly reliability review",
        "items": [
            (
                "p",
                "Every request contributes a duration histogram, response class, route identifier, and zone label. Request bodies and authorization headers are excluded. The observabilty stack aggregates metrics by region and service route; dashboards show both the customer view and the gateway's internal queue depth so teams can distinguish upstream slowness from local saturation.",
            ),
            (
                "table",
                ["Signal", "Warning", "Page immediately"],
                [
                    ["Availability", "Below 99.97% over 30 min", "Below 99.90% over 10 min"],
                    ["p95 request duration", "Above 700 ms for 15 min", "Above 1.2 s for 5 min"],
                    ["Gateway 5xx", "Above 0.5% for 10 min", "Above 2% for 5 min"],
                    ["Bundle age", "Above 5 min", "Above 15 min"],
                    ["Healthy zones", "Two zones remain", "One zone remains"],
                ],
            ),
            (
                "p",
                "Use a rolling window for alert evaluation and compare it with the previous week at the same hour. A single occurence can be noisy during a deploy; a sustained pattern is actionable. The alert threshhold is not permission to wait when customer impact is already confirmed. Page the on-call engineer and record the first known impact time.",
            ),
            (
                "bullets",
                [
                    "Check regional health, then identify the most affected route and zone.",
                    "Correlate gateway duration with upstream duration before changing limits.",
                    "Annotate dashboards with deploy, rollback, and network maintenance events.",
                ],
            ),
            (
                "callout",
                "DATA QUALITY",
                "Each measurment is tagged with a schema version. If a dashboard shows an incorret unit or an unexpected gap, do not tune alert thresholds to hide it; repair the metric mapping and backfill where possible.",
            ),
        ],
    },
    {
        "title": "Data durability and regional recovery",
        "subtitle": "State boundaries, backup assumptions, and traffic restoration",
        "items": [
            (
                "p",
                "The gateway is stateless. Route bundles and certificates are stored in managed systems with version history, while node-local caches are disposable. This boundary gives the platform predictable durabilty without treating a running process as a source of truth. On restart, a node loads the last verified bundle and reports its version before it is considered ready.",
            ),
            (
                "table",
                ["Asset", "Recovery source", "Target"],
                [
                    ["Route bundle", "Signed control-plane history", "RPO 0; restore in 10 min"],
                    ["Certificates", "Managed key store replicas", "RPO 0; rotate in 30 min"],
                    ["Node state", "Immutable image registry", "Rebuild in 20 min"],
                    ["Audit events", "Regional log archive", "RPO under 5 min"],
                ],
            ),
            (
                "p",
                "The primary and secondary regions receive the same approved policy version, but each has independent network and compute resources. Data consitency is verified by comparing bundle hashes, not by assuming that a successful publication reached every pool. The release controller pauses promotion if any healthy zone reports a different active version. A replcia is rebuilt from the image registry during recovry.",
            ),
            (
                "bullets",
                [
                    "Confirm secondary-region service health and certificate validity.",
                    "Compare route-bundle hashes and verify upstream capacity before cutover.",
                    "Shift traffic in stages; stop if error rate or duration exceeds baseline.",
                ],
            ),
            (
                "p",
                "A gateway replica can be recreated from the image registry; no local database restore is required. A lost policy version is recovered from the signed control-plane history. If a managed dependency is unavailable, keep traffic in the healthy region and use the incident commander to coordinate the recovery window. Never create an undocumented manual bundle as a shortcut.",
            ),
            (
                "callout",
                "RECOVERY VALIDATION",
                "After cutover, test a representative read and write route, confirm audit events arrive, and keep the previous region warm until traffic and customer support signals are stable for 30 minutes.",
            ),
        ],
    },
    {
        "title": "Release and change management",
        "subtitle": "Canary stages, rollback gates, and production evidence",
        "items": [
            (
                "p",
                "Releases are promoted through development, staging, and production from one signed artifact. The release record includes source revision, image digest, dependency report, policy schema, and approver identities. A deployement is not complete when the controller reports success; it is complete after the canary window closes and the operator records metric evidence.",
            ),
            (
                "table",
                ["Stage", "Traffic share", "Minimum observation"],
                [
                    ["Canary", "1% in one zone", "10 minutes"],
                    ["Regional", "10% across zones", "20 minutes"],
                    ["Broad", "50%, then 100%", "30 minutes per step"],
                    ["Completion", "All healthy targets", "Post-change review"],
                ],
            ),
            (
                "p",
                "The release owner watches the dashboard while the reviewer checks the change record. Abort promotion if error budget burn doubles, the active bundle hash differs, or a zone loses readiness. A rollbak returns to the last known-good artifact and policy version; it does not reverse unrelated service changes.",
            ),
            (
                "bullets",
                [
                    "Confirm client and upstream health before the first traffic shift.",
                    "Record the exact build and policy version at each canary stage.",
                    "Validate API compatiblity with a representative synthetic request.",
                ],
            ),
            (
                "callout",
                "SUCCESS CRITERION",
                "A release is succesfully closed only after all regions report the intended version, the rollback window is documented, and no new high-severity alert remains unassigned.",
            ),
        ],
    },
    {
        "title": "Incident response",
        "subtitle": "Triage, containment, communication, and post-incident learning",
        "items": [
            (
                "p",
                "The first responder acknowledges a page, opens the incident channel, and names an incident commander. The commander coordinates decisions and communications; a technical lead investigates the failure; a scribe maintains the timeline. One person may hold multiple roles for a small event, but ownership must be explicit before a risky change is made.",
            ),
            (
                "table",
                ["Severity", "Customer impact", "Initial response"],
                [
                    ["SEV-1", "Broad outage or data exposure", "Page immediately; command bridge"],
                    ["SEV-2", "Regional or major route degradation", "Page on-call; assess in 10 min"],
                    ["SEV-3", "Limited impact with workaround", "Business-hours owner response"],
                    ["SEV-4", "No active customer impact", "Track in normal backlog"],
                ],
            ),
            (
                "p",
                "To troublshoot a traffic issue, compare regional availability, gateway 5xx, and upstream timing. Check recent deploys and policy updates before restarting nodes. For a suspected credential event, revoke the affected identity first and preserve the audit log. Do not post customer data or secret values in the incident channel.",
            ),
            (
                "bullets",
                [
                    "State what is known, unknown, and being tested; avoid unsupported cause claims.",
                    "Assign one owner to customer updates and one owner to the technical timeline.",
                    "Escalate to the service owner if impact crosses a region or objective boundary.",
                ],
            ),
            (
                "p",
                "The incident commander has responsibilty for risk decisions and the recovery checkpoint. After stabilization, capture the impact window, contributing conditions, and follow-up owners. The review focuses on system changes, not individual blame. Track escalaton delays and recurring alerts as reliability work, not as personal performance measures.",
            ),
            (
                "callout",
                "COMMUNICATION CADENCE",
                "For a SEV-1, publish an internal update every 15 minutes and a customer-facing status note at the cadence agreed with communications. The next update time is part of every message, even when there is no new diagnosis.",
            ),
        ],
    },
    {
        "title": "Maintenance and reference",
        "subtitle": "Recurring tasks, retention schedule, and change-window checklist",
        "items": [
            (
                "p",
                "Routine work is scheduled in the regional maintenance calendar and linked to a change record. The owner confirms customer impact, target versions, the rollback plan, and staffing before the window opens. Maintenance must not overlap a major product launch, a known dependency event, or a separate regional recovery exercise.",
            ),
            (
                "table",
                ["Frequency", "Task", "Evidence"],
                [
                    ["Daily", "Review paging and failed health checks", "On-call handoff note"],
                    ["Weekly", "Inspect capacity and policy drift", "Reliability review"],
                    ["Monthly", "Test certificate rotation and restore path", "Signed exercise record"],
                    ["Quarterly", "Review access groups and egress rules", "Owner attestation"],
                    ["Annually", "Run regional recovery exercise", "Action plan and completion dates"],
                ],
            ),
            (
                "p",
                "Audit events are retained for 400 days; service metrics are retained at full resolution for 30 days and downsampled for one year. The retenion policy supports complience review while limiting unnecessary data storage. Each archive export is encrypted, access-controlled, and tested for retrieval during the annual exercise.",
            ),
            (
                "bullets",
                [
                    "Confirm change ticket, peer approval, and active on-call coverage.",
                    "Capture current health, image digest, policy version, and traffic split.",
                    "Run the post-change checks, attach evidence, and close the maintenance window.",
                ],
            ),
            (
                "callout",
                "CONTROL RECORD",
                "An auditible record contains the actor, timestamp, affected region, old and new versions, approval, and verification result. Keep the record in the change system rather than a personal notebook.",
            ),
            (
                "p",
                "The platform team reviews this manual after a material architecture change and at least every six months. Send a recomendation with the affected section, operational evidence, and proposed owner to the service documentation queue. The current approved copy and supporting change history are maintained in the internal engineering registry.",
            ),
        ],
    },
]

SUPPLEMENTAL_PARAGRAPHS = [
    [
        "Service owners review the request path whenever a new product route is introduced. The review records the expected peak rate, response deadline, data classification, and downstream owner. Routes with different traffic patterns receive separate limits rather than inheriting a broad default. This gives incident responders a clear place to start and prevents a high-volume integration from consuming capacity reserved for interactive clients.",
        "The regional control plane publishes a signed policy snapshot every five minutes and records the active version reported by each pool. The platform dashboard highlights pools that are healthy but behind the desired version. Operators investigate those differences before a release or recovery exercise, because a stale snapshot can produce inconsistent routing even when every process is running.",
    ],
    [
        "Pool size is based on measured concurrent connections and CPU use under representative load. During a capacity test, teams include both steady traffic and short bursts, then confirm that the balancer distributes connections evenly across zones. Results are compared with the previous test and stored with the image digest so a later release can be assessed against the same baseline.",
        "Policy bundles are immutable once signed. Each bundle includes a monotonically increasing version, a creation time, and the identity of the approving service owner. Gateways reject a bundle with an invalid signature or unsupported schema and continue using the last verified version while raising a control-plane alert.",
    ],
    [
        "Before a node joins a pool, verify that its operating system patch level matches the approved image record and that the expected monitoring agent is reporting. Bootstrap logs are forwarded to the regional archive with a node identifier and image digest. These checks help distinguish a package regression from a zone-level networking problem when new capacity fails readiness.",
        "A node is admitted gradually. The first target receives synthetic traffic, then a small customer share, while the operator compares error rates and resource use with an existing target. If any measure leaves its normal range, stop admission and preserve the bundle, startup log, and release reference for the platform team.",
    ],
    [
        "Rate limits are applied by client identity and route, with a regional ceiling as a final guardrail. The gateway returns a retry hint only when the request can be safely attempted again. Product teams publish their expected burst profile before a limit is raised; the platform team checks that the proposed change will not starve unrelated routes sharing the same pool.",
        "Timeouts are budgets, not independent allowances. The client deadline must exceed the gateway and upstream budgets by enough time to return a useful error. When a downstream service changes its latency profile, its owner and the gateway owner review the complete request path together rather than increasing every timeout in isolation.",
    ],
    [
        "Access group membership is reviewed quarterly by each service owner. Remove access when an operator changes role or leaves the response rotation, and confirm that emergency access expires after its approved window. The audit report lists granted roles and last-use time so reviewers can identify dormant privileges without inspecting secret values.",
        "Certificate rotation is monitored by expiry date and by handshake success. A failed renewal pages the security on-call before the overlap window closes. During an incident, responders may revoke a certificate immediately, but they must also verify that replacement credentials are available in every active region before restoring traffic.",
    ],
    [
        "Service-level indicators are calculated from successful requests and total eligible requests, with exclusions documented beside the dashboard. The weekly review checks whether an alert reflects customer impact, whether its operating guide is current, and whether the owning team can act on it. Repeated pages with no follow-up action are moved into a monitored work item instead of being ignored.",
        "Metric labels are bounded to prevent a unique customer identifier from creating unbounded time series. Route names come from the approved registry, and unknown values are grouped under a visible fallback label. Sampling is used only for high-volume diagnostic traces; objective and paging metrics retain complete event counts.",
    ],
    [
        "Regional recovery begins with a decision record that names the incident commander, the destination region, and the reason for moving traffic. Before the first shift, verify that the receiving region has adequate upstream quotas and that its policy snapshot matches the approved release. The record includes each traffic percentage and the time at which the health checks were reviewed.",
        "Return to the primary region is a separate change, not an automatic reversal. The owner first confirms that the original fault is resolved, that the recovered region has current policy, and that customer traffic has remained stable in the secondary region. A staged return reduces the risk of repeating the original failure during restoration.",
    ],
    [
        "The release pipeline stores build provenance beside every signed image. Reviewers can trace an artifact to its source revision, builder identity, and dependency manifest without relying on a workstation cache. Production nodes accept only artifacts from the approved registry and verify the signature before startup.",
        "When a canary is paused, leave the current healthy version in service and record the exact observation that blocked promotion. The release owner decides whether to correct the candidate or abandon it. A new candidate receives a new version and repeats the required stages; operators do not edit a running container to make a release appear healthy.",
    ],
    [
        "Declare an incident when impact is material or the response needs coordinated action across teams. Record the first alert, first confirmed customer impact, mitigation start, and recovery time. If evidence is uncertain, mark it as an estimate and update it when logs or customer reports provide a better timestamp.",
        "Preserve relevant logs and dashboard links before routine retention removes high-resolution data. The incident scribe records decisions, experiments, and results in time order. This timeline supports the post-incident review and prevents teams from repeating a failed mitigation during a later event.",
    ],
    [
        "The documentation owner checks that command examples, dashboard names, and escalation contacts still match production. Reviewers validate procedures in a staging region before publishing a substantial change. Each approved revision includes a date, owner, and summary of changed operating steps so on-call staff can identify what differs from the copy used during the previous rotation.",
        "Keep this handbook focused on actions that are stable across releases. Link short-lived deployment instructions from the change record rather than copying them here. A useful procedure step identifies the precondition, action, expected result, and safe stop point; procedures that cannot be tested are rewritten or removed.",
    ],
]

TYPO_LEDGER = [
    "architecure",
    "availabilty",
    "operatonal",
    "dependecy",
    "througput",
    "latncy",
    "redundent",
    "isloation",
    "conection",
    "seperation",
    "proccess",
    "maintenence",
    "configuation",
    "enviroment",
    "commited",
    "intermitant",
    "privilage",
    "credentails",
    "encrypton",
    "authentiction",
    "observabilty",
    "measurment",
    "threshhold",
    "incorret",
    "durabilty",
    "consitency",
    "replcia",
    "recovry",
    "deployement",
    "rollbak",
    "compatiblity",
    "succesfully",
    "troublshoot",
    "responsibilty",
    "escalaton",
    "occurence",
    "retenion",
    "complience",
    "auditible",
    "recomendation",
]


def wrap(text, font, size, width):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and fitz.get_text_length(candidate, fontname=font, fontsize=size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def draw_text_lines(page, text, x, y, width, size=9.1, line_height=12.4, color=INK, font="helv"):
    lines = wrap(text, font, size, width)
    for index, line in enumerate(lines):
        page.insert_text(
            (x, y + size + index * line_height),
            line,
            fontname=font,
            fontsize=size,
            color=color,
        )
    return y + len(lines) * line_height


def draw_paragraph(page, text, y):
    return draw_text_lines(page, text, MARGIN, y, BODY_WIDTH) + 8


def draw_bullets(page, entries, y):
    for entry in entries:
        page.draw_circle((MARGIN + 4, y + 8), 2.2, color=TEAL, fill=TEAL)
        y = draw_text_lines(page, entry, MARGIN + 16, y, BODY_WIDTH - 16) + 4
    return y + 4


def column_widths(headers, rows, total):
    measures = []
    for index, header in enumerate(headers):
        cells = [header] + [row[index] for row in rows]
        measures.append(max(fitz.get_text_length(cell, fontname="helv", fontsize=8) for cell in cells))
    raw = [max(value, 52) for value in measures]
    widths = [max(total * 0.16, total * value / sum(raw)) for value in raw]
    factor = total / sum(widths)
    return [width * factor for width in widths]


def draw_table(page, headers, rows, y):
    widths = column_widths(headers, rows, BODY_WIDTH)
    header_lines = [wrap(cell, "hebo", 8, width - 12) for cell, width in zip(headers, widths)]
    header_height = max(24, max(map(len, header_lines)) * 10 + 10)
    page.draw_rect(fitz.Rect(MARGIN, y, MARGIN + BODY_WIDTH, y + header_height), color=NAVY, fill=NAVY)
    x = MARGIN
    for cell_lines, width in zip(header_lines, widths):
        draw_text_lines(page, "\n".join(cell_lines), x + 6, y + 5, width - 12, 8, 10, WHITE, "hebo")
        x += width
    y += header_height
    for row_index, row in enumerate(rows):
        cell_lines = [wrap(cell, "helv", 8, width - 12) for cell, width in zip(row, widths)]
        row_height = max(24, max(map(len, cell_lines)) * 10 + 10)
        fill = ROW if row_index % 2 == 0 else WHITE
        page.draw_rect(fitz.Rect(MARGIN, y, MARGIN + BODY_WIDTH, y + row_height), color=RULE, fill=fill, width=0.4)
        x = MARGIN
        for lines, width in zip(cell_lines, widths):
            draw_text_lines(page, "\n".join(lines), x + 6, y + 5, width - 12, 8, 10)
            x += width
            page.draw_line((x, y), (x, y + row_height), color=RULE, width=0.4)
        y += row_height
    return y + 10


def draw_callout(page, label, text, y):
    lines = wrap(text, "helv", 8.8, BODY_WIDTH - 24)
    height = 31 + len(lines) * 12
    rect = fitz.Rect(MARGIN, y, MARGIN + BODY_WIDTH, y + height)
    page.draw_rect(rect, color=PALE, fill=PALE)
    page.draw_rect(fitz.Rect(MARGIN, y, MARGIN + 4, y + height), color=TEAL, fill=TEAL)
    page.insert_text((MARGIN + 14, y + 15), label, fontname="hebo", fontsize=7.4, color=TEAL)
    draw_text_lines(page, text, MARGIN + 14, y + 20, BODY_WIDTH - 28, 8.8, 12)
    return y + height + 10


def draw_diagram(page, nodes, y):
    gap = 18
    width = (BODY_WIDTH - gap * (len(nodes) - 1)) / len(nodes)
    height = 62
    for index, (title, details) in enumerate(nodes):
        x = MARGIN + index * (width + gap)
        rect = fitz.Rect(x, y, x + width, y + height)
        page.draw_rect(rect, color=RULE, fill=ROW, width=0.7)
        page.insert_text((x + 9, y + 20), title, fontname="hebo", fontsize=8.5, color=NAVY)
        for line_index, line in enumerate(details.splitlines()):
            page.insert_text(
                (x + 9, y + 37 + line_index * 10),
                line,
                fontname="helv",
                fontsize=7.2,
                color=MUTED,
            )
        if index < len(nodes) - 1:
            start = (x + width + 3, y + height / 2)
            end = (x + width + gap - 3, y + height / 2)
            page.draw_line(start, end, color=TEAL, width=1.3)
            page.draw_line((end[0] - 4, end[1] - 3), end, color=TEAL, width=1.3)
            page.draw_line((end[0] - 4, end[1] + 3), end, color=TEAL, width=1.3)
    return y + height + 12


def draw_page(document, page_number, page_data):
    page = document.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    page.draw_rect(fitz.Rect(0, 0, PAGE_SIZE[0], 5), color=TEAL, fill=TEAL)
    page.insert_text((MARGIN, 25), "EDGE PLATFORM  /  ENGINEERING", fontname="hebo", fontsize=7.5, color=NAVY)
    page.insert_text((PAGE_SIZE[0] - MARGIN - 120, 25), "OPERATIONS HANDBOOK", fontname="helv", fontsize=7, color=MUTED)
    page.draw_line((MARGIN, 36), (PAGE_SIZE[0] - MARGIN, 36), color=RULE, width=0.7)
    page.insert_text((MARGIN, 67), page_data["title"], fontname="hebo", fontsize=20, color=NAVY)
    page.insert_text((MARGIN, 88), page_data["subtitle"], fontname="helv", fontsize=8.5, color=MUTED)
    page.draw_line((MARGIN, 101), (PAGE_SIZE[0] - MARGIN, 101), color=RULE, width=0.7)
    y = 112
    for item in page_data["items"]:
        if item[0] == "p":
            y = draw_paragraph(page, item[1], y)
        elif item[0] == "bullets":
            y = draw_bullets(page, item[1], y)
        elif item[0] == "table":
            y = draw_table(page, item[1], item[2], y)
        elif item[0] == "callout":
            y = draw_callout(page, item[1], item[2], y)
        elif item[0] == "diagram":
            y = draw_diagram(page, item[1], y)
        if y > 722:
            raise ValueError(f"Page {page_number} content overflows the page at y={y:.1f}.")
    for paragraph in SUPPLEMENTAL_PARAGRAPHS[page_number - 1]:
        y = draw_paragraph(page, paragraph, y)
    if y > 722:
        raise ValueError(f"Page {page_number} supplemental content overflows at y={y:.1f}.")
    page.draw_line((MARGIN, 752), (PAGE_SIZE[0] - MARGIN, 752), color=RULE, width=0.7)
    page.insert_text((MARGIN, 769), "INTERNAL OPERATIONS  |  EDGE GATEWAY", fontname="helv", fontsize=7, color=MUTED)
    page.insert_text((PAGE_SIZE[0] - MARGIN - 34, 769), f"{page_number:02d} / 10", fontname="hebo", fontsize=7, color=NAVY)


def main():
    if len(PAGES) != 10 or len(TYPO_LEDGER) != 40:
        raise ValueError("Expected exactly 10 pages and 40 deliberate spelling mistakes.")
    document = fitz.open()
    document.set_metadata(
        {
            "title": "Edge Gateway Operations and Reliability Manual",
            "author": "Platform Engineering",
            "subject": "Fictional technical operations sample for proofreading",
            "keywords": "operations, gateway, reliability, sample",
        }
    )
    for page_number, page_data in enumerate(PAGES, 1):
        draw_page(document, page_number, page_data)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT, garbage=4, deflate=True)
    document.close()

    with fitz.open(OUTPUT) as check:
        extracted = "\n".join(page.get_text(sort=True) for page in check)
        counts = {word: extracted.casefold().count(word.casefold()) for word in TYPO_LEDGER}
        missing_or_repeated = {word: count for word, count in counts.items() if count != 1}
        if len(check) != 10 or missing_or_repeated:
            raise ValueError(
                f"PDF verification failed: pages={len(check)}, typo mismatches={missing_or_repeated}"
            )
    print(f"Created {OUTPUT}")
    print(f"Verified: 10 pages, {sum(counts.values())} deliberate spelling mistakes.")


if __name__ == "__main__":
    main()