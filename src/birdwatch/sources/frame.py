from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass(frozen=True)
class Frame:
    image: np.ndarray
    captured_at: datetime 
