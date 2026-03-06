from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QPainter

class ImageViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        # ズーム・パンの設定
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        self.zoom_factor = 1.0

    def set_image(self, image_np_8bit):
        """
        OpenCV形式 (H, W, 3) のRGB画像 (0-255 uint8) を受け取り、表示する。
        """
        h, w, ch = image_np_8bit.shape
        bytes_per_line = ch * w
        q_img = QImage(image_np_8bit.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        
        # 初回ロード時は画面に合わせる
        if self.zoom_factor == 1.0:
            self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        """マウスホイールでのズーム"""
        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor
        
        # ズーム倍率の制限（必要に応じて）
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.zoom_factor *= zoom_factor
        self.scale(zoom_factor, zoom_factor)
