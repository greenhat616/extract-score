import os
import fnmatch
from datetime import datetime
import json
from pydantic import BaseModel

# 每个因素的最大分值定义（总分1000分）
SCORE_WEIGHTS = {
    'type': 200,        # 文件类型权重
    'freshness': 125,   # 时间新鲜度权重
    'filename': 125,    # 文件名权重（与新鲜度相同）
    'file_size': 150,   # 文件大小权重
    'path_depth': 100,  # 路径深度权重
    'folder': 300       # 文件夹重要性权重（最高）
}

# 文件类型评分
def get_type_score(file_path: str) -> float:
    file_type = file_path.split('.')[-1].lower()
    type_scores = {
        'pdf': 1.0,
        'txt': 0.5,
        'html': 0.4,
    }
    score_ratio = type_scores.get(file_type, 0.9)
    return score_ratio * SCORE_WEIGHTS['type']

# 新鲜度评分
def get_freshness_score(days_old: int) -> float:
    freshness_scores = {
        1: 1.0,    # 1天内
        3: 0.9,    # 1-3天
        7: 0.8,    # 3-7天
        30: 0.6,   # 7-30天
        90: 0.4,   # 30-90天
        180: 0.2,  # 90-180天
    }
    
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
    score_ratio = freshness_scores.get(days_span, 0.2)
    return score_ratio * SCORE_WEIGHTS['freshness']

# 文件名评分
def get_filename_score(filename: str) -> float:
    # 如果文件名包含unicode字符（可能是中文等）
    score_ratio = 1.2 if any(ord(c) >= 128 for c in filename) else 1.0
    return min(score_ratio, 1.0) * SCORE_WEIGHTS['filename']

# 文件大小评分
def get_file_size_score(file_size: int) -> float:
    size_in_kb = file_size / 1024.0
    
    if size_in_kb <= 512:
        score_ratio = 1.0
    elif size_in_kb <= 1024:
        score_ratio = 0.9
    elif size_in_kb <= 2048:
        score_ratio = 0.8
    elif size_in_kb <= 4096:
        score_ratio = 0.7
    else:
        factor = (size_in_kb - 4096) / 4096.0
        score_ratio = max(0.4, 1.0 - factor)
        
    return score_ratio * SCORE_WEIGHTS['file_size']

# 路径深度评分
def get_path_depth_score(file_path: str) -> float:
    depth = len(file_path.split('\\'))
    if depth <= 4:
        score_ratio = 1.0
    elif depth <= 6:
        score_ratio = 0.8
    elif depth <= 8:
        score_ratio = 0.5
    else:
        score_ratio = 0
        
    return score_ratio * SCORE_WEIGHTS['path_depth']

# 高优先级文件夹
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

# 低优先级文件夹
low_priority_folders_globs = [
    '**/logs/**',
    '**/tmp/**',
    '**/cache/**',
    '**/temp/**',
    '**/scoop/**',
]

# 文件夹优先级评分
def get_folder_score(file_path: str) -> float:
    for glob in high_priority_folders_globs:
        if fnmatch.fnmatch(file_path, glob):
            return 1.0 * SCORE_WEIGHTS['folder']
            
    for glob in low_priority_folders_globs:
        if fnmatch.fnmatch(file_path, glob):
            return 0.2 * SCORE_WEIGHTS['folder']
            
    return 0.5 * SCORE_WEIGHTS['folder']

class Item(BaseModel):
    filename: str
    path: str
    size: int
    last_modified: int  # timestamp

# 计算单个文件的总分数
def calc_file_score(item: Item) -> float:
    total_score = 0
    
    # 累加各项分数
    total_score += get_type_score(item.filename)
    
    days_old = round((datetime.now().timestamp() - item.last_modified) / 86400)
    total_score += get_freshness_score(days_old)
    
    total_score += get_filename_score(item.filename)
    total_score += get_file_size_score(item.size)
    total_score += get_path_depth_score(item.path)
    total_score += get_folder_score(item.path)
    
    # 为保持与原算法一致，分数越低越好，所以使用满分减去当前得分
    return 1000 - total_score

class OutputItem(BaseModel):
    path: str
    score: float

# 计算所有文件的分数并排序
def calc_files_scores(files: list[Item]) -> list[OutputItem]:
    l = [OutputItem(path=file.path, score=calc_file_score(file)) for file in files]
    return sorted(
        l,
        # ASC order
        key=lambda x: x.score,
        reverse=False
    )

OUTPUT_DIR = "output"
if __name__ == "__main__":
    with open(os.path.join(OUTPUT_DIR, "items.json"), "r") as f:
        items = [Item(**item) for item in json.load(f)]
    
    with open(os.path.join(OUTPUT_DIR, "items_scores.json"), "w", encoding="utf8") as f:
        json.dump([item.model_dump() for item in calc_files_scores(items)], f, ensure_ascii=False, indent=2)