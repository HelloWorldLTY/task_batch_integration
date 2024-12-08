import sys
import tempfile
import scanpy as sc
import anndata as ad
import gdown
import cellplm
import torch

import warnings
warnings.filterwarnings("ignore")
from CellPLM.utils import set_seed

import numpy as np
import anndata as ad
from CellPLM.pipeline.cell_embedding import CellEmbeddingPipeline

## VIASH START
# Note: this section is auto-generated by viash at runtime. To edit it, make changes
# in config.vsh.yaml and then run `viash config inject config.vsh.yaml`.

drive_path = f"https://drive.google.com/drive/folders/1C2fVNEKX3plHnagaTwpuPW5tpwv1up9G?usp=sharing"
model_dir = tempfile.TemporaryDirectory()
print(f"Downloading from '{drive_path}'", flush=True)
gdown.download_folder(drive_path, output=model_dir.name, quiet=True)
print(f"Model directory: '{model_dir.name}'", flush=True)

set_seed(24)
PRETRAIN_VERSION = '20231027_85M'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

par = {
  'input': 'resources_test/.../input.h5ad',
  'output': 'output.h5ad'
}
meta = {
  'name': 'cellplm'
}
## VIASH END
print(f"====== scGPT version {PRETRAIN_VERSION} ======", flush=True)

sys.path.append(meta["resources_dir"])
from read_anndata_partial import read_anndata

print("\n>>> Reading input files...", flush=True)
print(f"Input H5AD file: '{par['input']}'", flush=True)
adata = read_anndata(par["input"], X="layers/counts", obs="obs", var="var", uns="uns")

if adata.uns["dataset_organism"] != "homo_sapiens":
    raise ValueError(
        f"CellPLM can only be used with human data "
        f"(dataset_organism == \"{adata.uns['dataset_organism']}\")"
    )

print(adata, flush=True)

print('Preprocess data', flush=True)
# ... preprocessing ...
sc.pp.normalize_total(adata)
sc.pp.log1p(adata)

print('Train model', flush=True)
# ... train model ...

pipeline = CellEmbeddingPipeline(pretrain_prefix=PRETRAIN_VERSION, # Specify the pretrain checkpoint to load
                                 pretrain_directory=model_dir)

embedding = pipeline.predict(adata, # An AnnData object
                device=DEVICE) # Specify a gpu or cpu for model inference

embedding = embedding.cpu().numpy()

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

print("\n>>> Cleaning up temporary directories...", flush=True)
model_dir.cleanup()