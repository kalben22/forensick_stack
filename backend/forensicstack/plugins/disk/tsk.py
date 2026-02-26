import pytsk3
from typing import Dict, Any, List

class TSKPlugin:
    """TSK using pytsk3 library"""
    
    def __init__(self):
        self.name = "tsk"
        self.version = "pytsk3 " + pytsk3.get_version()
    
    def open_image(self, image_path: str):
        """Open disk image"""
        try:
            img_info = pytsk3.Img_Info(image_path)
            return img_info
        except Exception as e:
            return None
    
    def list_partitions(self, image_path: str) -> Dict[str, Any]:
        """List partitions (mmls equivalent)"""
        try:
            img = pytsk3.Img_Info(image_path)
            volume = pytsk3.Volume_Info(img)
            
            partitions = []
            for part in volume:
                partitions.append({
                    "slot": part.addr,
                    "start": part.start,
                    "length": part.len,
                    "description": part.desc.decode() if part.desc else ""
                })
            
            return {
                "status": "success",
                "partitions": partitions,
                "total": len(partitions)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def list_files(self, image_path: str, partition_offset: int = 0) -> Dict[str, Any]:
        """List files (fls equivalent)"""
        try:
            img = pytsk3.Img_Info(image_path)
            fs = pytsk3.FS_Info(img, offset=partition_offset * 512)
            
            files = []
            root = fs.open_dir(path="/")
            
            for entry in root:
                if entry.info.name.name in [b".", b".."]:
                    continue
                    
                files.append({
                    "name": entry.info.name.name.decode(),
                    "inode": entry.info.meta.addr if entry.info.meta else 0,
                    "type": "dir" if entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR else "file"
                })
            
            return {
                "status": "success",
                "files": files,
                "total": len(files)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


def get_tsk_plugin() -> TSKPlugin:
    return TSKPlugin()
