# Copyright 2023 BioMap (Beijing) Intelligence Technology Limited

import argparse
import random,os
import numpy as np
import pandas as pd
import argparse
import torch
from tqdm import tqdm
import scipy.sparse
from scipy.sparse import issparse
import scanpy as sc
from load import *


def main_gene_selection(X_df, gene_list):
    """
    Describe:
        rebuild the input adata to select target genes encode protein 
    Parameters:
        adata->`~anndata.AnnData` object: adata with var index_name by gene symbol
        gene_list->list: wanted target gene 
    Returns:
        adata_new->`~anndata.AnnData` object
        to_fill_columns->list: zero padding gene
    """
    to_fill_columns = list(set(gene_list) - set(X_df.columns))
    padding_df = pd.DataFrame(np.zeros((X_df.shape[0], len(to_fill_columns))), 
                              columns=to_fill_columns, 
                              index=X_df.index)
    X_df = pd.DataFrame(np.concatenate([df.values for df in [X_df, padding_df]], axis=1), 
                        index=X_df.index, 
                        columns=list(X_df.columns) + list(padding_df.columns))
    X_df = X_df[gene_list]
    
    var = pd.DataFrame(index=X_df.columns)
    var['mask'] = [1 if i in to_fill_columns else 0 for i in list(var.index)]
    return X_df, to_fill_columns,var
gene_list_df = pd.read_csv('./OS_scRNA_gene_index.19264.tsv', header=0, delimiter='\t')
gene_list = list(gene_list_df['gene_name'])

def main_get(task_name = 'bec', 
                            input_type = 'singlecell',
                            output_type = 'cell',
                            pool_type = 'all',
                            tgthighres='t4',
                            data=None,
                            save_path='./',
                            pre_normalized='F',
                            demo='store_true',
                            version='ce',
                            model_path='None',
                            ckpt_name='01B-resolution'):

    args = argparse.Namespace()
    args.task_name = task_name
    args.input_type = input_type
    args.output_type = output_type
    args.pool_type = pool_type
    args.tgthighres = tgthighres
    args.data = data
    args.save_path = save_path
    args.pre_normalized = pre_normalized
    args.demo = demo
    args.version = version
    args.model_path = model_path
    args.ckpt_name = ckpt_name

    #Set random seed
    random.seed(0)
    np.random.seed(0)  # numpy random generator

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    #Load data
    gexpr_feature = data
    idx = gexpr_feature.obs_names.tolist()
    try:
        col = gexpr_feature.var.gene_name.tolist()
    except:
        col = gexpr_feature.var_names.tolist()
    if issparse(gexpr_feature.X):
        gexpr_feature = gexpr_feature.X.toarray()
    else:
        gexpr_feature = gexpr_feature.X
    gexpr_feature = pd.DataFrame(gexpr_feature,index=idx,columns=col)
    
    if gexpr_feature.shape[1]<19264:
        print('covert gene feature into 19264')
        gexpr_feature, to_fill_columns,var = main_gene_selection(gexpr_feature,gene_list)
        assert gexpr_feature.shape[1]>=19264
    
    if (args.pre_normalized == 'F') and (args.input_type == 'bulk'):
        adata = sc.AnnData(gexpr_feature)
        sc.pp.normalize_total(adata)
        sc.pp.log1p(adata)
        gexpr_feature = pd.DataFrame(adata.X,index=adata.obs_names,columns=adata.var_names)

    if args.demo:
        gexpr_feature = gexpr_feature.iloc[:10,:]
    print(gexpr_feature.shape)

    #Load model
    if args.version == 'noversion':
        ckpt_path = args.model_path
        key=None
    else:
        ckpt_path = './models/models.ckpt'
        if args.output_type == 'cell':
            if args.version == 'ce':
                key = 'cell'
            elif args.version == 'rde':
                key = 'rde'
            else:
                raise ValueError('No version found')
        elif args.output_type == 'gene':
            key = 'gene'
        elif args.output_type == 'gene_batch':
            key = 'gene'
        elif args.output_type == 'gene_expression': # Not recommended
            key = 'gene'
        else:
            raise ValueError('output_mode must be one of cell gene, gene_batch, gene_expression')
    pretrainmodel,pretrainconfig = load_model_frommmf(ckpt_path,key)
    pretrainmodel.eval()

    geneexpemb=[]
    batchcontainer = []
    strname = os.path.join(args.save_path, args.task_name +'_'+ args.ckpt_name +"_"+ args.input_type + '_' + args.output_type + '_embedding_' + args.tgthighres + '_resolution.npy')
    print('save at {}'.format(strname))
    
    #Inference
    for i in tqdm(range(gexpr_feature.shape[0])):
        with torch.no_grad():
            #Bulk
            if args.input_type == 'bulk':
                if args.pre_normalized == 'T':
                    totalcount = gexpr_feature.iloc[i,:].sum()
                elif args.pre_normalized == 'F':
                    totalcount = np.log10(gexpr_feature.iloc[i,:].sum())
                else:
                    raise ValueError('pre_normalized must be T or F')
                tmpdata = (gexpr_feature.iloc[i,:]).tolist()
                pretrain_gene_x = torch.tensor(tmpdata+[totalcount,totalcount]).unsqueeze(0).cuda()
                data_gene_ids = torch.arange(19266, device=pretrain_gene_x.device).repeat(pretrain_gene_x.shape[0], 1)
            
            #Single cell
            elif args.input_type == 'singlecell':
                # pre-Normalization
                if args.pre_normalized == 'F':
                    tmpdata = (np.log1p(gexpr_feature.iloc[i,:]/(gexpr_feature.iloc[i,:].sum())*1e4)).tolist()
                elif args.pre_normalized == 'T':
                    tmpdata = (gexpr_feature.iloc[i,:]).tolist()
                elif args.pre_normalized == 'A':
                    tmpdata = (gexpr_feature.iloc[i,:-1]).tolist()
                else:
                    raise ValueError('pre_normalized must be T,F or A')

                if args.pre_normalized == 'A':
                    totalcount = gexpr_feature.iloc[i,-1]
                else:
                    totalcount = gexpr_feature.iloc[i,:].sum()

                # select resolution
                if args.tgthighres[0] == 'f':
                    pretrain_gene_x = torch.tensor(tmpdata+[np.log10(totalcount*float(args.tgthighres[1:])),np.log10(totalcount)]).unsqueeze(0).cuda()
                elif args.tgthighres[0] == 'a':
                    pretrain_gene_x = torch.tensor(tmpdata+[np.log10(totalcount)+float(args.tgthighres[1:]),np.log10(totalcount)]).unsqueeze(0).cuda()
                elif args.tgthighres[0] == 't':
                    pretrain_gene_x = torch.tensor(tmpdata+[float(args.tgthighres[1:]),np.log10(totalcount)]).unsqueeze(0).cuda()
                else:
                    raise ValueError('tgthighres must be start with f, a or t')
                data_gene_ids = torch.arange(19266, device=pretrain_gene_x.device).repeat(pretrain_gene_x.shape[0], 1)

            value_labels = pretrain_gene_x > 0
            x, x_padding = gatherData(pretrain_gene_x, value_labels, pretrainconfig['pad_token_id'])

            #Cell embedding
            if args.output_type=='cell':
                position_gene_ids, _ = gatherData(data_gene_ids, value_labels, pretrainconfig['pad_token_id'])
                x = pretrainmodel.token_emb(torch.unsqueeze(x, 2).float(), output_weight = 0)
                position_emb = pretrainmodel.pos_emb(position_gene_ids)
                x += position_emb
                geneemb = pretrainmodel.encoder(x,x_padding)

                geneemb1 = geneemb[:,-1,:]
                geneemb2 = geneemb[:,-2,:]
                geneemb3, _ = torch.max(geneemb[:,:-2,:], dim=1)
                geneemb4 = torch.mean(geneemb[:,:-2,:], dim=1)
                if args.pool_type=='all':
                    geneembmerge = torch.concat([geneemb1,geneemb2,geneemb3,geneemb4],axis=1)
                elif args.pool_type=='max':
                    geneembmerge, _ = torch.max(geneemb, dim=1)
                else:
                    raise ValueError('pool_type must be all or max')
                geneexpemb.append(geneembmerge.detach().cpu().numpy())

            #Gene embedding
            elif args.output_type=='gene':
                pretrainmodel.to_final = None
                encoder_data, encoder_position_gene_ids, encoder_data_padding, encoder_labels, decoder_data, decoder_data_padding, new_data_raw, data_mask_labels, decoder_position_gene_ids = getEncoerDecoderData(pretrain_gene_x.float(),pretrain_gene_x.float(),pretrainconfig)
                out = pretrainmodel.forward(x=encoder_data, padding_label=encoder_data_padding,
                            encoder_position_gene_ids=encoder_position_gene_ids,
                            encoder_labels=encoder_labels,
                            decoder_data=decoder_data,
                            mask_gene_name=False,
                            mask_labels=None,
                            decoder_position_gene_ids=decoder_position_gene_ids,
                            decoder_data_padding_labels=decoder_data_padding,
                            )
                out = out[:,:19264,:].contiguous()
                geneexpemb.append(out.detach().cpu().numpy())

            #Gene batch embedding
            elif args.output_type=='gene_batch':
                batchcontainer.append(pretrain_gene_x.float())
                if len(batchcontainer)==gexpr_feature.shape[0]:
                    batchcontainer = torch.concat(batchcontainer,axis=0)
                else:
                    continue
                pretrainmodel.to_final = None
                encoder_data, encoder_position_gene_ids, encoder_data_padding, encoder_labels, decoder_data, decoder_data_padding, new_data_raw, data_mask_labels, decoder_position_gene_ids = getEncoerDecoderData(batchcontainer,batchcontainer,pretrainconfig)
                out = pretrainmodel.forward(x=encoder_data, padding_label=encoder_data_padding,
                            encoder_position_gene_ids=encoder_position_gene_ids,
                            encoder_labels=encoder_labels,
                            decoder_data=decoder_data,
                            mask_gene_name=False,
                            mask_labels=None,
                            decoder_position_gene_ids=decoder_position_gene_ids,
                            decoder_data_padding_labels=decoder_data_padding,
                            )
                geneexpemb = out[:,:19264,:].contiguous().detach().cpu().numpy()
            #Gene_expression
            elif args.output_type=='gene_expression':
                encoder_data, encoder_position_gene_ids, encoder_data_padding, encoder_labels, decoder_data, decoder_data_padding, new_data_raw, data_mask_labels, decoder_position_gene_ids = getEncoerDecoderData(pretrain_gene_x.float(),pretrain_gene_x.float(),pretrainconfig)
                out = pretrainmodel.forward(x=encoder_data, padding_label=encoder_data_padding,
                            encoder_position_gene_ids=encoder_position_gene_ids,
                            encoder_labels=encoder_labels,
                            decoder_data=decoder_data,
                            mask_gene_name=False,
                            mask_labels=None,
                            decoder_position_gene_ids=decoder_position_gene_ids,
                            decoder_data_padding_labels=decoder_data_padding,
                            )
                out = out[:,:19264].contiguous()
                geneexpemb.append(out.detach().cpu().numpy())                
            else:
                raise ValueError('output_type must be cell or gene or gene_batch or gene_expression')
    geneexpemb = np.squeeze(np.array(geneexpemb))
    print(geneexpemb.shape)
    np.save(strname,geneexpemb)

    return geneexpemb 
