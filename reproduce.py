import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from gluonts.dataset.common import ListDataset
from gluonts.dataset.field_names import FieldName
from gluonts.dataset.multivariate_grouper import MultivariateGrouper
from gluonts.dataset.repository.datasets import dataset_recipes, get_dataset
from gluonts.evaluation import MultivariateEvaluator
from gluonts.evaluation.backtest import make_evaluation_predictions

from pts import Trainer
from pts.model.tempflow import TempFlowEstimator
from pts.model.time_grad import TimeGradEstimator
from pts.model.transformer_tempflow import TransformerTempFlowEstimator


def plot(target, forecast, prediction_length, prediction_intervals=(50.0, 90.0), color='g', fname=None):
    label_prefix = ""
    rows = 4
    cols = 4
    fig, axs = plt.subplots(rows, cols, figsize=(24, 24))
    axx = axs.ravel()
    seq_len, target_dim = target.shape
    
    ps = [50.0] + [
            50.0 + f * c / 2.0 for c in prediction_intervals for f in [-1.0, +1.0]
        ]
        
    percentiles_sorted = sorted(set(ps))
    
    def alpha_for_percentile(p):
        return (p / 100.0) ** 0.3
        
    for dim in range(0, min(rows * cols, target_dim)):
        ax = axx[dim]

        target[-2 * prediction_length :][dim].plot(ax=ax)
        
        ps_data = [forecast.quantile(p / 100.0)[:,dim] for p in percentiles_sorted]
        i_p50 = len(percentiles_sorted) // 2
        
        p50_data = ps_data[i_p50]
        p50_series = pd.Series(data=p50_data, index=forecast.index)
        p50_series.plot(color=color, ls="-", label=f"{label_prefix}median", ax=ax)
        
        for i in range(len(percentiles_sorted) // 2):
            ptile = percentiles_sorted[i]
            alpha = alpha_for_percentile(ptile)
            ax.fill_between(
                forecast.index,
                ps_data[i],
                ps_data[-i - 1],
                facecolor=color,
                alpha=alpha,
                interpolate=True,
            )
            # Hack to create labels for the error intervals.
            # Doesn't actually plot anything, because we only pass a single data point
            pd.Series(data=p50_data[:1], index=forecast.index[:1]).plot(
                color=color,
                alpha=alpha,
                linewidth=10,
                label=f"{label_prefix}{100 - ptile * 2}%",
                ax=ax,
            )

    legend = ["observations", "median prediction"] + [f"{k}% prediction interval" for k in prediction_intervals][::-1]    
    axx[0].legend(legend, loc="upper left")
    
    if fname is not None:
        plt.savefig(fname, bbox_inches='tight', pad_inches=0.05)

def make_custom_dataset(target: np.ndarray, metadata: dict) -> tuple[list, list]:
    train_ds = ListDataset(
        [{FieldName.TARGET: target, FieldName.START: start} for (target, start) in zip(target[:, : -metadata["prediction_length"]], metadata["start"])],
        freq=metadata["freq"],
    )
    
    test_ds = ListDataset(
        [{FieldName.TARGET: target, FieldName.START: start} for (target, start) in zip(target, metadata["start"])],
        freq=metadata["freq"],
    )
    
    return train_ds, test_ds

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default="electricity_nips")
    parser.add_argument("--save", type=str, default="reproduce_electricity.png")
    parser.add_argument("--input_size", type=int, default=404)                  # default 1484
    parser.add_argument("--epochs", type=int, default=2)                        # default 20
    parser.add_argument("--learning_rate", type=float, default=1e-3)                # default 1e-3
    parser.add_argument("--num_batches_per_epoch", type=int, default=100)           # default 100
    parser.add_argument("--batch_size", type=int, default=64)                       # default 64
    
    args = parser.parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # device = torch.device('mps')
    # dataset = get_dataset(args.dataset, regenerate=False)
    # print(dataset.metadata)
    # print(args.dataset, args.save)
    
    # train_grouper = MultivariateGrouper(max_target_dim=min(2000, int(dataset.metadata.feat_static_cat[0].cardinality)))
    # test_grouper = MultivariateGrouper(num_test_dates=int(len(dataset.test)/len(dataset.train)), max_target_dim=min(2000, int(dataset.metadata.feat_static_cat[0].cardinality)))
    
    # dataset_train = train_grouper(dataset.train)
    # dataset_test = test_grouper(dataset.test)
    
    # estimator = TimeGradEstimator(
    #     target_dim=int(dataset.metadata.feat_static_cat[0].cardinality),
    #     prediction_length=dataset.metadata.prediction_length,
    #     context_length=dataset.metadata.prediction_length,
    #     cell_type='GRU',
    #     input_size=args.input_size,
    #     freq=dataset.metadata.freq,
    #     loss_type='l2',
    #     scaling=True,
    #     diff_steps=100,
    #     beta_end=0.1,
    #     beta_schedule="linear",
    #     trainer=Trainer(device=device,
    #                     epochs=20,
    #                     learning_rate=1e-3,
    #                     num_batches_per_epoch=100,
    #                     batch_size=64),
    #     max_idle_transforms=100,
    # )
    np.random.seed(1)
    # metadata = {'prediction_length': 24, 'start': [pd.Period('2011-01-01 00:00', freq='H') for _ in range(100)], 'freq': 'H'}
    metadata = {'prediction_length': 24, 'start': pd.Period('2011-01-01 00:00', freq='H'), 'freq': 'H'}
    target = np.random.normal(size=(100, 1484))
    # dataset_train, dataset_test = make_custom_dataset(target, metadata)
    
    dataset_train = [{'target': target[:, : -metadata["prediction_length"]], 'start': metadata['start']}]
    dataset_test = [{'target': target, 'start': metadata['start']}]
    
    target_dim = 100
    prediction_length = 24
    input_size = args.input_size
    freq = 'H'
    
    
    estimator = TimeGradEstimator(
        target_dim=target_dim,
        prediction_length=prediction_length,
        context_length=prediction_length,
        cell_type='GRU',
        input_size=input_size,
        freq=freq,
        loss_type='l2',
        scaling=True,
        diff_steps=100,
        beta_end=0.1,
        beta_schedule="linear",
        trainer=Trainer(device=device, epochs=args.epochs, learning_rate=args.learning_rate, num_batches_per_epoch=args.num_batches_per_epoch, batch_size=args.batch_size),
        max_idle_transforms=100,
    )
    
    predictor = estimator.train(dataset_train, num_workers=8)
    
    forecast_it, ts_it = make_evaluation_predictions(dataset=dataset_test, predictor=predictor, num_samples=100)
    
    forecasts = list(forecast_it)
    targets = list(ts_it)
    
    plot(
        target=targets[0],
        forecast=forecasts[0],
        prediction_length=prediction_length,
    )
    plt.savefig(args.save)
    
    evaluator = MultivariateEvaluator(quantiles=(np.arange(20)/20.0)[1:], target_agg_funcs={'sum': np.sum})
    
    agg_metric, item_metrics = evaluator(targets, forecasts, num_series=len(dataset_test))
    
    print("CRPS:", agg_metric["mean_wQuantileLoss"])
    print("ND:", agg_metric["ND"])
    print("NRMSE:", agg_metric["NRMSE"])
    print("")
    print("CRPS-Sum:", agg_metric["m_sum_mean_wQuantileLoss"])
    print("ND-Sum:", agg_metric["m_sum_ND"])
    print("NRMSE-Sum:", agg_metric["m_sum_NRMSE"])