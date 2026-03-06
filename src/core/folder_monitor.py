import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PySide6.QtCore import QObject, Signal, QThread

class FolderEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        
    def _check_and_notify(self, path_str):
        path = Path(path_str)
        if path.suffix.lower() in ['.tif', '.tiff', '.jpg', '.jpeg']:
            # 名前制限を解除し、画像ファイルなら何でも通知する
            print(f"Watchdog trigger: {path_str}")
            self.callback(path_str)

    def on_created(self, event):
        if not event.is_directory:
            self._check_and_notify(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            # リネーム先 (dest_path) をチェック
            self._check_and_notify(event.dest_path)
            
    def on_modified(self, event):
        # on_modified は頻発するため、アプリ側で重複排除が必要だが念のため追加
        if not event.is_directory:
            self._check_and_notify(event.src_path)

class FolderMonitor(QObject):
    image_detected = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.observer = None
        self.target_folder = None
        
    def start_monitoring(self, folder_path: str):
        self.target_folder = folder_path
        event_handler = FolderEventHandler(self._on_file_created)
        
        self.observer = Observer()
        self.observer.schedule(event_handler, folder_path, recursive=False)
        self.observer.start()
        
    def stop_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            
    def _on_file_created(self, file_path: str):
        # UIスレッドに通知する
        self.image_detected.emit(file_path)
