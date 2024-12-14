import sys
import tempfile
import scanpy as sc
import anndata as ad
import gdown
import torch

import warnings
warnings.filterwarnings("ignore")


import numpy as np
import anndata as ad

## VIASH START
# Note: this section is auto-generated by viash at runtime. To edit it, make changes
# in config.vsh.yaml and then run `viash config inject config.vsh.yaml`.

model_path = "models.ckpt"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

par = {
  'input': 'resources_test/.../input.h5ad',
  'output': 'output.h5ad'
}
meta = {"name": "scfoundation"}
sys.path.append(meta["resources_dir"])
from read_anndata_partial import read_anndata

print("\n>>> Reading input files...", flush=True)
print(f"Input H5AD file: '{par['input']}'", flush=True)
adata = read_anndata(par["input"], X="layers/counts", obs="obs", var="var", uns="uns")


print(adata, flush=True)

print('Preprocess data', flush=True)
# ... preprocessing ...

print('Train model', flush=True)
# ... train model ...

drive_path = f"wait to fill"
model_dir = tempfile.TemporaryDirectory()
print(f"Downloading from '{drive_path}'", flush=True)
gdown.download_folder(drive_path, output=model_dir.name, quiet=True)
print(f"Model directory: '{model_dir.name}'", flush=True)


from get_embedding import main_get
embedding = main_get(data=adata, model_path=model_dir.name + '/' + model_path)

print('Generate predictions', flush=True)
# ... generate predictions ...

output = ad.AnnData(
    obs=adata.obs[[]],
    var=adata.var[[]],
    obsm={
        "X_emb": embedding,
    },
    uns={
        "dataset_id": adata.uns["dataset_id"],
        "normalization_id": adata.uns["normalization_id"],
        "method_id": meta["name"],
    },
)
print(output)

output.write_h5ad(par['output'], compression='gzip')

