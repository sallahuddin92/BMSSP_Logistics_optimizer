# Exact native logistics integration — Task 7

`POST /vrp` accepts `engine` in the existing JSON body: `native_bmssp_2025`,
`native_reference_dijkstra`, or default `legacy_networkx`. A query selection is also
accepted; conflicting explicit selections are rejected. Native requests preserve
one validated immutable snapshot, build one directed matrix, and retain one native
SSSP result per distinct location for all subsequent leg reconstruction. No
NetworkX path search or implicit native engine substitution occurs. Native research
sources are unchanged. This is verified offline integration, not certification of
production road coverage, traffic durations, or globally optimal vehicle tours.

## Request and response

Existing locations, vehicle_count, depot, demands, capacities and time_windows
fields remain. Node IDs are strings across search, browser state, requests and path
responses; normalized signed-64-bit IDs are used internally. VRP rejects repeated
normalized graph-node IDs, including aliases such as `1` and `01`, with a validation error.
Customers are mandatory, exactly once in the stop-index routes. Passing through a
customer's road vertex during another leg is not a service visit. Route indices
continue to reference submitted locations; original and normalized edge/node
identities remain mapped by the snapshot.

New optional inputs are duration_matrix (seconds), service_durations (seconds),
vehicle_start_windows, vehicle_end_windows (seconds), max_wait_seconds (default
86400), max_search_seconds (default 1), and place. Demand/capacity counts are
nonnegative integers, provided together, with exact lengths. Depot demand is zero.
Zero demand/capacity is valid. Enabled but incomplete inputs are rejected.

The response retains locations, routes, route_locations, location_coordinates,
route_geometries, total_distance, vehicle_distances, status, computation_times and
metadata. It adds selected_engine, graph_snapshot, exact_routing, weight_units,
duration_units, solver_status, route_feasibility, schedules, vehicle_loads,
route_legs and route_geometry_segments. Native matrix metadata retains reachability,
unreachable_pair_count, approximation provenance and native execution diagnostics.
Every leg includes submitted source/target indices and IDs, normalized native IDs,
original directed vertices/edges, string native edge IDs, distance, duration when
available, path_status and geometry_status. Large IDs never pass through JavaScript
Number conversion.

Invalid native input returns 400/422; explicit resource limits 413; unavailable
local data/module or busy admission 503; execution/post-validation failure 500 with
no route and a public error that excludes server internals. A solver search without
an assignment returns an explicit failed result (possibly HTTP 200); consumers must
inspect status and route_feasibility. Missing native data never creates a test graph
or downloads OSM data. The application loader no longer substitutes synthetic
graphs on legacy OSM loading failures either; its explicit demo helper remains
available outside the production loading path. Native node search also uses the strict local loader and
worker admission. Haversine proximity is used only for discovering nearby nodes,
never for road feasibility or route cost.

## Hard feasibility and truthful status

Every unreachable pair is removed from the successor domains using
`routing.NextVar(from_index).RemoveValue(to_index)`. All manager indices are
considered, including each replicated vehicle start and end. No large penalty,
finite unreachable replacement, optional-customer disjunction or hidden drop is
used. The internal callback's zero for an excluded value is an inert placeholder
for a hard-forbidden transition, not a usable arc cost. Selected transitions are
checked against original finite matrix entries after solving. All mandatory
customers and per-vehicle capacity totals are independently checked again.

An assignment is reported FEASIBLE after checks. The heuristic (PATH_CHEAPEST_ARC
then GREEDY_DESCENT with an explicit time limit) does not prove global optimality.
NO_SOLUTION means no assignment was established; raw ROUTING_INFEASIBLE proves
infeasibility only for the represented integer model. ROUTING_FAIL is not a proof
of global infeasibility, ROUTING_FAIL_TIMEOUT maps to TIMEOUT, and NOT_SOLVED maps
to FAILED. Invalid solver-model status raises an execution error. The raw solver
status/code is retained. An unreachable depot-to-stop or stop-to-depot pair gives
a specific directed-road failure reason. No failure is overwritten by approximation
metadata and no failed assignment returns a fabricated route.

## Distance arithmetic

The native matrix and reported distances remain binary64 meters. OR-Tools objective
costs use scale 1000: nearest integer, half up, calculated from the exact binary64
integer ratio; positive values rounding to zero are raised to one. Zero remains
zero. Ordinary error is at most 0.0005 meters per arc, except positive sub-half-unit
values have error strictly below 0.001 meters due to the minimum-one rule. These
costs can alter the chosen tour and do not define the reported road distance.

Scaled values and maximum possible tour cost `(n-1+vehicles)*max_cost` must fit
`(INT64_MAX // 8)`; no saturation occurs. Counts/demand sums and duration arithmetic
have corresponding checked budgets. The original selected native matrix entries
are summed with math.fsum per vehicle, then across vehicles for total_distance.
Each leg separately reproduces the native path's sequential original-edge weight
sum exactly, without epsilon. The integer objective is independently compared with
the selected scaled arcs and serialized as a decimal string in API metadata to
avoid JavaScript integer precision loss.

## Time model: seconds, service-start windows and waiting

Distance never implies duration. Supply a matching nonnegative duration matrix in
seconds, or provide valid `travel_time` seconds on every original edge selected by
the native distance-shortest paths. Derived times sum those exact selected edges;
this is not a separate fastest-time path. The model fixes these distance-shortest
leg paths; it does not jointly search longer/faster alternatives that might satisfy
otherwise infeasible time constraints. No implicit speed is invented. Native
time-window requests without a usable source return an actionable validation error.
Caller-supplied durations are declared data for the submitted pairs; the caller is
responsible for their relationship to the selected road paths/traffic conditions.

Windows constrain service-start arrival time; service may finish after a customer
window closes. Depot windows apply to every vehicle's start and return arrival,
intersected with optional vehicle-specific start/end windows. Depot service applies
at departure (including unused vehicles), not again at return. All departure,
customer and return arrival times, service, waits, capacities and original seconds
are post-validated. Schedules report original service seconds and physical waiting
consistent with the original duration matrix, plus separate model service/wait
values. End-of-route service/wait is zero.

The discrete time model uses millisecond ticks: travel/service round up, lower
window bounds round up, upper bounds round down. Each conversion can add less than
one millisecond. A global maximum travel+service rounding reserve is deducted from
allowed model waiting so physical waiting remains within the original allowance.
Rational checks using original binary64 ratios verify this without epsilon. An
insufficient waiting allowance for the rounding reserve is rejected explicitly.
Narrow/fixed fractional windows may contain no representable tick; this conservative
model can reject continuously feasible schedules. It must not be interpreted as a
proof of continuous-time infeasibility. Units and time_scale=1000 are explicit.

For old low-level callers, time windows without durations return INVALID_INPUT with
empty routes, never a distance-as-time assignment. Legacy API compatibility retains
that failed structured response; the frontend rejects it even if HTTP is 200. Valid
legacy time inputs can be supplied explicitly. Legacy routing remains labeled
non-certified and never gains native exactness through approximation metadata.

## Geometry and snapshot ownership

Snapshots now capture immutable node coordinates, selected-edge LineStrings,
lengths and travel_time values, including these in freshness fingerprints. Changes
to geometry, coordinates or travel times invalidate cache reuse. Query, solver,
path and geometry stages read captured data, not a mutable source NetworkX graph.
Source graph mutation must be serialized during capture; a source changed after
capture cannot alter the in-flight request. Active requests retain their snapshot.

Canonical geometry is `[[latitude,longitude], ...]` in WGS84. Missing CRS is treated
as the caller's WGS84 declaration; other/projected CRS is unsupported for drawing,
not automatically reprojected. Coordinate bounds/finiteness and endpoint continuity
are checked. Reversed stored LineStrings are oriented to their actual directed
edge. Junction duplicates are removed within 1e-7 degrees (geometry-only endpoint
matching, never a distance tolerance). Parallel-edge geometry comes from the exact
selected native edge mapping. Explicit malformed/misaligned geometry produces
UNAVAILABLE; it does not become an invented segment. If geometry is absent, valid
actual endpoint coordinates are allowed with ENDPOINTS_ONLY status, so curvature
is not claimed.

Unavailable legs break route_geometry_segments. The old flat route_geometries
entry is populated only if the whole route is continuous and available; otherwise
it is empty. The UI draws only supplied canonical segments, never a straight-line
fallback between stops or across missing legs. Stationary unused-vehicle legs need
no road line. Geometry limitations are visible independently of exact distance.

## Resources, execution and UI

Graph capture, native preprocessing/queries, OR-Tools, reconstruction, geometry and
JSON encoding run in a bounded worker using Task 6 admission. Existing graph/source
budgets still apply. Added positive-integer settings:

| Setting | Default | Scope |
|---|---:|---|
| VRP_MAX_LOCATIONS | 32 | Submitted stops including depot |
| VRP_MAX_VEHICLES | 10 | Vehicle count |
| VRP_MAX_SEARCH_SECONDS | 10 | Requested OR-Tools search limit |
| VRP_MAX_TIME_SECONDS | 604800 | Maximum window/wait horizon |
| VRP_MAX_GEOMETRY_POINTS | 100000 | Logical response points before repeated compatibility fields |
| VRP_MAX_PATH_EDGES | 100000 | Reconstructed response edges |
| NATIVE_SNAPSHOT_MAX_GEOMETRY_POINTS | 200000 | Captured LineString points across snapshot edges |

Exceeding limits fails explicitly; no silent truncation. Limits are per process and
structural; they are not hard allocator/cancellation guarantees. Two native workers
are admitted by default; all active queries have independent native state. Legacy
geometry responses are also bounded and incomplete segments are not joined.

The existing frontend layout is retained. Search aliases normalize to string IDs;
unsafe numeric IDs are rejected. Depot and stop add/remove/duplicate handling works.
Noninteractive decorative coverage layers no longer intercept map clicks. Search
radii are 1000/2000/5000/10000 meters, matching server limits. Vehicle, capacity and
seconds inputs distinguish zero from missing data. A duration JSON matrix follows
depot-then-listed-stop order. Engine selection remains explicit and never changes
on error. Results list actual vehicle stop assignments and original meter totals.
FEASIBLE, approximate legacy, NO_SOLUTION, TIMEOUT and failed responses are distinct;
HTTP 200 alone is never success. Stale results are cleared on selection/configuration
changes, and in-flight results are ignored after changes. Server error text is not
inserted as HTML. Shape/path/geometry checks precede native drawing.

See [Task 7 validation](exact_logistics_validation.md) for tests, browser acceptance,
measured costs and remaining limitations. No real-road/production-coverage or Linux
validation claim is made. Task 8 is not started.


## Task 8 real-road fixtures

An explicit `osm-fixture:<region>` selection uses a source/file-checksum-verified
private immutable snapshot through the same native matrix and logistics path.
The frontend native dataset selector clears stale locations when changed. Default
engine and production admission limits are unchanged. Prepared native VRP fixtures
require a native engine; legacy routing remains available for its existing input.
See [preparation, clipping, licensing and numerical contracts](real_road_workflow.md)
and [measured validation](real_road_validation.md).
