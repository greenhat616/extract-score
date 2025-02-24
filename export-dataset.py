import sqlite3
from pydantic import BaseModel
from typing import Optional
import os
import json
from dateutil import parser

DB_PATH = "C:\\Users\\a6320\\AppData\\Roaming\\ai.gety\\user_data\\tabular.db"
OUTPUT_DIR = "output"

CONNECTORS_TABLE = [
    "index_index_ntfs_019537dc0e1d7d90b3cb0a42af7bf3eb",
    "index_index_ntfs_019537dc0e1e75f3856d2b11356e9c36",
    "index_index_ntfs_019537dc0e1f72d1a7b2f46a400c0e8d",
    "index_index_ntfs_019537dc0e1f72d1a7b2f474befd9aba",
    "index_index_ntfs_019537dc0e2079e0aafa8a5d60184254",
]

class Item(BaseModel):
    filename: str
    path: str
    size: int
    last_modified: int # timestamp
    
class ItemMetadata(BaseModel):
    is_folder: bool
    hide_from_search: bool

class ConnectorItem(BaseModel):
    id: str
    parent_id: Optional[str]
    title: str
    doc_updated_at: str # 2022-12-21 08:33:51.318090200+00:00
    metadata: Optional[ItemMetadata]

def get_items_from_table(table_name: str) -> list[Item]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    id_map: dict[str, ConnectorItem] = {}
    for row in rows :
        d = dict(zip(row.keys(), row))
        d["metadata"] = ItemMetadata(**json.loads(d["metadata"])) if d["metadata"] else None
        id_map[d["id"]] = ConnectorItem(**d)
    
    '''
        Build the vail list
    '''
    def get_path(input_id: str) -> str:
        path_components: list[str] = []
        id: str | None = input_id
        while id is not None:
            id_item = id_map[id]
            path_components.append(id_item.title)
            id = id_item.parent_id
        if path_components[-1].endswith("\\"):
            path_components[-1] = path_components[-1][:-1]
        return "\\".join(path_components[::-1])

    l: list[Item] = []
    for id, item in id_map.items():
        if item.metadata is not None and item.metadata.is_folder:
            continue
        path = get_path(id)
        size = os.path.getsize(path)
        last_modified = int(parser.isoparse(item.doc_updated_at).timestamp())
        item = Item(filename=item.title, path=path, size=size, last_modified=last_modified)
        l.append(item)
    return l
        

if __name__ == "__main__":
    all_items: list[Item] = []
    for table in CONNECTORS_TABLE:
        print(f"Exporting {table}...")
        items = get_items_from_table(table)
        path = os.path.join(OUTPUT_DIR, f"{table}.json")
        with open(path, "w") as f:
            json.dump([item.model_dump() for item in items], f)
        print(f"Exported {len(items)} items from {table} to {path}")
        all_items.extend(items)

    # sort by last_modified
    all_items.sort(key=lambda x: x.last_modified)

    # export to json
    path = os.path.join(OUTPUT_DIR, "items.json")
    with open(path, "w") as f:
        json.dump([item.model_dump() for item in all_items], f)
    print(f"Exported {len(all_items)} items to {path}")
