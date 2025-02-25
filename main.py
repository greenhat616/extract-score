import os
import fnmatch
from datetime import datetime
import json

from pydantic import BaseModel

type_weights_factor = {  
    'pdf': 1.0,
    'txt': 0.5,
    'html': 0.4,
}

def get_type_weight(file_path: str) -> float:
    file_type = file_path.split('.')[-1]
    return type_weights_factor.get(file_type, 0.9)

freshness_decay_factor = {
    1: 1.0,
    3: 0.9,
    7: 0.8,
    30: 0.6,
    90: 0.4,
    180: 0.2,
}

def get_freshness_weight(days_old: int) -> float:
    def get_days_span(days_old: int) -> int:
        if days_old <= 1:
            return 1
        elif days_old <= 3:
            return 3
        elif days_old <= 7:
            return 7
        elif days_old <= 30:
            return 30
        elif days_old <= 90:
            return 90
        else:
            return 180

    days_span = get_days_span(days_old)
    return freshness_decay_factor.get(days_span, 0.2)

def get_filename_weight(filename: str) -> float:
    # is filename has unicode
    if any(ord(c) >= 128 for c in filename):
        return 1.2
    else:
        return 1.0

def get_file_size_weight(file_size: int) -> float:
    size_in_kb = file_size / 1024.0
    if size_in_kb <= 512:
        return 1.0
    elif size_in_kb <= 1024:
        return 0.9
    elif size_in_kb <= 2048:
        return 0.8
    elif size_in_kb <= 4096:
        return 0.7
    else:
        factor = (size_in_kb - 4096) / 4096.0
        if factor >= 1.0:
            return 0.999
        return 1.0 - factor

def get_path_depth_weight(file_path: str) -> float:
    return 1.0 - len(file_path.split('/')) / 10.0

high_priority_folders_globs = [
    '**/OneDrive/**',
    '**/WeChat Files/**',
    '**/FileRecv/**',
    '**/Tencent Files/**',
    '**/*Downloads/**',
    '**/*Download/**',
    '**/文档/**',
    '**/Documents/**',
    '**/Desktop/**',
    '**/Downloads/**',
    '**/Public/**',  
]

low_priority_folders_globs = [
    '**/logs/**',
    '**/tmp/**',
    '**/cache/**',
    '**/temp/**',
    '**/scoop/**',
]


def get_folder_weight(file_path: str) -> float:
    for glob in high_priority_folders_globs:
        if fnmatch.fnmatch(file_path, glob):
            return 1.0
    for glob in low_priority_folders_globs:
        if fnmatch.fnmatch(file_path, glob):
            return 0.2
    return 0.5

class Item(BaseModel):
    filename: str
    path: str
    size: int
    last_modified: int # timestamp

def calc_file_score(item: Item) -> float:
    weight = 1.0
    weight *= get_type_weight(item.filename)
    days_old = round((datetime.now().timestamp() - item.last_modified) / 86400)
    weight *= get_freshness_weight(days_old)
    weight *= get_filename_weight(item.filename)
    weight *= get_file_size_weight(item.size)
    weight *= get_path_depth_weight(item.path)
    weight *= get_folder_weight(item.path)
    return weight



def calc_files_scores(files: list[Item]) -> list[tuple[Item, float]]:
    return sorted(
        [(file, 1000 - 1000 * min(calc_file_score(file), 1.0)) for file in files],
        # ASC order
        key=lambda x: x[1],
        reverse=False
    )
    
OUTPUT_DIR = "output"
if __name__ == "__main__":
    with open(os.path.join(OUTPUT_DIR, "items.json"), "r") as f:
        items = [Item(**item) for item in json.load(f)]
    # print(calc_files_scores(items))
    with open(os.path.join(OUTPUT_DIR, "items_scores.json"), "w") as f:
        json.dump([(item.path, score) for item, score in calc_files_scores(items)], f)
