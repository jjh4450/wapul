"""The block model's command line.

python -m wapul_ml train                    # fit and save to models/segmenter-v2/
python -m wapul_ml predict FILE LANGUAGE    # print the labels of one file as JSON
python -m wapul_ml review [N]               # N random unlabeled corpus solutions -> cache/review.html
"""

import json
import sys
from pathlib import Path

from wapul_ml.evaluation.review import review
from wapul_ml.models.segmenter import BlockModel, train


def main() -> None:
    cmd = sys.argv[1]
    if cmd == "train":
        train()
    elif cmd == "predict":
        code = Path(sys.argv[2]).read_text(encoding="utf-8")
        print(json.dumps(BlockModel().predict(code, sys.argv[3]), ensure_ascii=False))
    elif cmd == "review":
        review(int(sys.argv[2]) if len(sys.argv) > 2 else 40)


if __name__ == "__main__":
    main()
