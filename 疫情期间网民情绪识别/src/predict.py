# coding=utf-8
# author=yphacker

import os
import argparse
from tqdm import tqdm
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from conf import config
from model.bert import Model
from utils.bert_data_utils import MyDataset

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def predict(model):
    test_dataset = MyDataset(test_df, 'test')
    test_loader = DataLoader(test_dataset, batch_size=config.batch_size, shuffle=False)

    model.eval()
    pred_list = []
    with torch.no_grad():
        for batch_x, _ in tqdm(test_loader):
            batch_x = batch_x.to(device)
            # compute output
            probs = model(batch_x)
            # preds = torch.argmax(probs, dim=1)
            # pred_list += [p.item() for p in preds]
            pred_list.extend(probs.cpu().numpy())
    return pred_list


def multi_model_predict():
    preds_dict = dict()
    for model_name in model_name_list:
        for fold_idx in range(5):
            model = Model().to(device)
            model_save_path = os.path.join(config.model_path, '{}_fold{}.bin'.format(model_name, fold_idx))
            model.load_state_dict(torch.load(model_save_path))
            pred_list = predict(model)
            submission = pd.DataFrame(pred_list)
            # submission = pd.DataFrame({"id": range(len(pred_list)), "label": pred_list})
            submission.to_csv('{}/{}_fold{}_submission.csv'
                              .format(config.submission_path, model_name, fold_idx), index=False, header=False)
            preds_dict['{}_{}'.format(model_name, fold_idx)] = pred_list
    pred_list = get_pred_list(preds_dict)
    # pred_list = add_image_info(pred_list)

    submission = pd.read_csv(config.sample_submission_path)
    submission['y'] = pred_list
    print(submission['y'].value_counts())
    # submission.to_csv('{}_submission.csv'.format(model_name), index=False)
    submission.to_csv('submission.csv', index=False)


def file2submission():
    preds_dict = dict()
    for model_name in model_name_list:
        for fold_idx in range(5):
            df = pd.read_csv('{}/{}_fold{}_submission.csv'
                             .format(config.submission_path, model_name, fold_idx), header=None)
            preds_dict['{}_{}'.format(model_name, fold_idx)] = df.values
    pred_list = get_pred_list(preds_dict)
    # pred_list = add_image_info(pred_list)

    submission = pd.read_csv(config.sample_submission_path)
    submission['y'] = pred_list
    print(submission['y'].value_counts())
    # submission.to_csv('{}_submission.csv'.format(model_name), index=False)
    submission.to_csv('submission.csv', index=False)


def get_pred_list(preds_dict):
    pred_list = []
    if mode == 1:
        for i in range(data_len):
            prob = None
            for model_name in model_name_list:
                for fold_idx in range(5):
                    if prob is None:
                        prob = preds_dict['{}_{}'.format(model_name, fold_idx)][i] * ratio_dict.get(model_name, 0)
                    else:
                        prob += preds_dict['{}_{}'.format(model_name, fold_idx)][i] * ratio_dict.get(model_name, 0)
            label_id = np.argmax(prob)
            pred_list.append(label_id)
    else:
        for i in range(data_len):
            preds = []
            for model_name in model_name_list:
                for fold_idx in range(5):
                    prob = preds_dict['{}_{}'.format(model_name, fold_idx)][i]
                    pred = np.argmax(prob)
                    preds.append(pred)
            # pred_set = set([x for x in preds])
            label_id = max(preds, key=preds.count)
            pred_list.append(label_id)

    tmp = pred_list
    pred_list = []
    cnt = 0
    for text in texts:
        if pd.isnull(text):
            # 直接赋值为0
            pred_list.append('0')
        else:
            pred_list.append(config.id2label[tmp[cnt]])
            cnt += 1
    return pred_list


def test():
    df = pd.read_csv('{}/submission.csv'.format(config.submission_path))
    pred_list = df['y'].values
    # pred_list = add_image_info(pred_list)
    # pred_list = add_image_info2(pred_list)

    submission = pd.read_csv(config.sample_submission_path)
    submission['y'] = pred_list
    print(submission['y'].value_counts())
    # submission.to_csv('{}_submission.csv'.format(model_name), index=False)
    submission.to_csv('submission.csv', index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--batch_size", default=64, type=int, help="batch size")
    parser.add_argument("-m", "--model_names", default='bert', type=str, help="model select")
    parser.add_argument("-type", "--pred_type", default='model', type=str, help="pred type")
    parser.add_argument("-mode", "--mode", default=1, type=int, help="1:加权融合，2:投票融合")
    parser.add_argument("-r", "--ratios", default='1', type=str, help="融合比例")
    args = parser.parse_args()
    config.batch_size = args.batch_size
    model_name_list = args.model_names.split('+')
    ratio_dict = dict()
    ratios = args.ratios
    ratio_list = args.ratios.split(',')
    for i, ratio in enumerate(ratio_list):
        ratio_dict[model_name_list[i]] = int(ratio)
    mode = args.mode

    test_df = pd.read_csv(config.test_path)
    print(test_df.shape)
    texts = test_df['微博中文内容'].tolist()
    test_df.dropna(subset=['微博中文内容'], inplace=True)
    print(test_df.shape)

    data_len = test_df.shape[0]
    if args.pred_type == 'model':
        multi_model_predict()
    elif args.pred_type == 'file':
        file2submission()
