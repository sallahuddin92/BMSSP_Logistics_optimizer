const {test} = require('node:test');
const assert = require('node:assert/strict');
const {normalizeNode,validSolution}=require('../routing_contract.js');
test('node aliases retain full 64-bit string IDs',()=>{
 assert.equal(normalizeNode({id:'9007199254740993',lat:3,lon:101}).node_id,'9007199254740993');
 assert.equal(normalizeNode({node_id:'9223372036854775807',lat:3,lon:101}).node_id,'9223372036854775807');
 for(const raw of [9007199254740993,undefined,null]) assert.throws(()=>normalizeNode({id:raw,lat:3,lon:101}));
 assert.throws(()=>normalizeNode({id:'1',lat:100,lon:101}));
});
const valid=()=>({locations:['1','2'],routes:[[0,1,0]],vehicle_distances:[2],total_distance:2,status:'FEASIBLE',route_feasibility:true,
 selected_engine:'native_bmssp_2025',exact_routing:true,graph_snapshot:'abc',metadata:{depot:0},computation_times:{total:.1},
 route_geometry_segments:[[]],route_legs:[[{from_index:0,to_index:1,source:'1',target:'2',path_status:'VERIFIED',distance:1,geometry_status:'UNAVAILABLE',geometry:[]},
 {from_index:1,to_index:0,source:'2',target:'1',path_status:'VERIFIED',distance:1,geometry_status:'UNAVAILABLE',geometry:[]}]]});
test('200 responses require a verified feasible assignment',()=>{
 assert.equal(validSolution(valid()),true);
 for(const status of ['NO_SOLUTION','TIMEOUT','FAILED','OPTIMAL','INVALID_INPUT']) assert.equal(validSolution({...valid(),status}),false);
 assert.equal(validSolution({...valid(),route_feasibility:false}),false);
 assert.equal(validSolution({...valid(),total_distance:null}),false);
});
test('reject invalid indices, omitted customers, and missing native proofs',()=>{
 assert.equal(validSolution({...valid(),routes:[[0,0]]}),false);
 assert.equal(validSolution({...valid(),routes:[[0,7,0]]}),false);
 assert.equal(validSolution({...valid(),route_legs:[]}),false);
 assert.equal(validSolution({...valid(),exact_routing:false}),false);
 assert.equal(validSolution({...valid(),selected_engine:'fake'}),false);
});
test('legacy approximation remains explicitly identifiable',()=>{
 assert.equal(validSolution({...valid(),selected_engine:'legacy_networkx',status:'APPROXIMATED',exact_routing:false}),true);
});

test('reject malformed geographic response data before drawing',()=>{
 const x=valid();x.route_geometry_segments=[[[[100,101]]]];assert.equal(validSolution(x),false);
 assert.equal(validSolution({...valid(),computation_times:{total:NaN}}),false);
});
