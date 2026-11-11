"""Read-only exact frozen data. Never invoke application/OSM loaders."""
import json
from pathlib import Path
from production_adapter import require
from production_adapter.graphs import frozen_graph
from .io import encode,sha

REGIONS=('seremban-small','seremban-medium','seremban-port-dickson')
COUNTS=((834,1776),(14464,35530),(24736,60214))


def selection(p,region):
    inp=p['inputs'][region]
    require(sha(encode(inp['source_positions']).rstrip(b'\n'))==inp['source_position_identity_sha256'],'SOURCE_LIST_IDENTITY')
    return {'region':region,'original_position':0,'source_id':int(inp['source_positions'][0]),'source_occurrence':1,
            'snapshot_id':inp['snapshot_id'],'source_list_sha256':inp['source_position_identity_sha256'],
            'path_targets':list(map(int,inp['path_targets']))}


def load(p,region):
    require(region in REGIONS,'FIXED_REGION_REQUIRED')
    inp=p['inputs'][region]
    graph=frozen_graph(inp)
    require((len(graph.vertices),len(graph.edges))==COUNTS[REGIONS.index(region)],'GRAPH_DIMENSIONS')
    chosen=selection(p,region)
    require(all(v in graph.vertices for v in [chosen['source_id']]+chosen['path_targets']),'SOURCE_TARGET_MEMBERSHIP')
    manifest=json.loads(Path(inp['fixture_manifest_path']).read_bytes())
    require(manifest['snapshot_id']==inp['snapshot_id'] and manifest['graph_sha256']==inp['graph_sha256'],'MANIFEST_SNAPSHOT')
    return graph,chosen


class Budget:
    def __init__(self,p):self.p=p;self.cursor=0;self.failed=False
    def claim(self,region,source):
        require(not self.failed and self.cursor<3,'ROAD_SOLVE_BUDGET_EXHAUSTED')
        require(region==REGIONS[self.cursor] and type(source) is int and source==selection(self.p,region)['source_id'],'FIXED_SOURCE_ORDER')
        self.cursor+=1
