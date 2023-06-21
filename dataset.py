import numpy as np
from gluonts.dataset.field_names import FieldName
from gluonts.dataset.common import ListDataset

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