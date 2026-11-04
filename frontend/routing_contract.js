/* Shared browser/Node contracts; no floating conversion of external node IDs. */
(function(root) {
    function normalizeNode(node) {
        const raw = node.node_id ?? node.id;
        if ((typeof raw !== 'string' && !Number.isSafeInteger(raw)) || String(raw).length === 0) throw new Error('Unsafe node identifier');
        if (!Number.isFinite(node.lat) || !Number.isFinite(node.lon) || Math.abs(node.lat)>90 || Math.abs(node.lon)>180) throw new Error('Invalid geographical coordinates');
        return {...node, node_id: String(raw)};
    }
    function validSolution(solution) {
        if (!['FEASIBLE','APPROXIMATED'].includes(solution.status) || solution.route_feasibility !== true
            || !Array.isArray(solution.locations) || !solution.locations.every(x => typeof x === 'string')
            || !Array.isArray(solution.routes) || !solution.routes.length
            || !Array.isArray(solution.vehicle_distances) || solution.vehicle_distances.length !== solution.routes.length
            || !Number.isFinite(solution.total_distance) || solution.total_distance < 0
            || !solution.vehicle_distances.every(x => Number.isFinite(x) && x>=0)) return false;
        if (!Number.isFinite(solution.computation_times?.total) || solution.computation_times.total < 0) return false;
        const depot = solution.metadata?.depot;
        if (!Number.isInteger(depot) || depot < 0 || depot >= solution.locations.length) return false;
        const visited = [];
        for (const route of solution.routes) {
            if (!Array.isArray(route) || route.length<2 || route[0] !== depot || route[route.length-1] !== depot
                || !route.every(i => Number.isInteger(i) && i>=0 && i<solution.locations.length)) return false;
            visited.push(...route.slice(1,-1));
        }
        const expected = solution.locations.map((_,i) => i).filter(i => i!==depot);
        if (JSON.stringify(visited.sort((a,b)=>a-b)) !== JSON.stringify(expected)) return false;
        if (solution.selected_engine === 'legacy_networkx') return true;
        if (!['native_bmssp_2025','native_reference_dijkstra'].includes(solution.selected_engine)
            || !solution.exact_routing || typeof solution.graph_snapshot !== 'string'
            || !Array.isArray(solution.route_legs) || solution.route_legs.length !== solution.routes.length
            || !Array.isArray(solution.route_geometry_segments) || solution.route_geometry_segments.length !== solution.routes.length) return false;
        const point = p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite) && Math.abs(p[0])<=90 && Math.abs(p[1])<=180;
        if (!solution.route_geometry_segments.every(parts => Array.isArray(parts) && parts.every(points => Array.isArray(points) && points.every(point)))) return false;
        return solution.route_legs.every((legs,v) => Array.isArray(legs) && legs.length === solution.routes[v].length-1
            && legs.every((leg,j) => leg.path_status === 'VERIFIED' && Number.isFinite(leg.distance) && leg.distance >= 0
                && ['AVAILABLE','ENDPOINTS_ONLY','STATIONARY','UNAVAILABLE'].includes(leg.geometry_status)
                && Array.isArray(leg.geometry) && leg.geometry.every(point)
                && (leg.geometry_status === 'UNAVAILABLE' ? leg.geometry.length === 0 : leg.geometry.length >= 1) && leg.from_index === solution.routes[v][j]
                && leg.to_index === solution.routes[v][j+1] && leg.source === solution.locations[leg.from_index]
                && leg.target === solution.locations[leg.to_index]));
    }
    const api = {normalizeNode, validSolution};
    if (typeof module !== 'undefined') module.exports = api;
    root.RoutingContract = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
