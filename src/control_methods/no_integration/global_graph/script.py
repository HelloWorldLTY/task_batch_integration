import scanpy as sc
import sys

## VIASH START

par = {
    'input_dataset': 'resources_test/task_batch_integration/cxg_mouse_pancreas_atlas/dataset.h5ad',
    'output': 'output.h5ad',
}

meta = { 
    'functionality': 'foo',
    'config': 'bar',
    "resources_dir": "src/tasks/batch_integration/control_methods/"
}

## VIASH END

# add helper scripts to path
sys.path.append(meta["resources_dir"])
from utils import _set_uns
from read_anndata_partial import read_anndata


print('Read input_dataset', flush=True)
adata = read_anndata(
    par['input_dataset'],
    obs='obs',
    obsp='obsp',
    uns='uns'
)

print("process dataset", flush=True)
neighbors_map = adata.uns['knn']
adata.obsp['connectivities'] = adata.obsp[neighbors_map['connectivities_key']]
adata.obsp['distances'] = adata.obsp[neighbors_map['distances_key']]
_set_uns(adata, neighbors_key='knn')

print("Store outputs", flush=True)
adata.uns['method_id'] = meta['name']
adata.write_h5ad(par['output'], compression='gzip')